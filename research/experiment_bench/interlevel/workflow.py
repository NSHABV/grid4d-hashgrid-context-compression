import json
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
from research.hashgrid_analysis.common import ROOT,read,write,digest
from .context import context,boundaries,classes,ARITHMETIC

SOURCE=ROOT/'research/interlevel_xyz34_results'
OUTPUT=ROOT/'research/interlevel_xyz34_bitstream'

def sources():
    m=read(SOURCE/'manifest.json');meta=read(SOURCE/'decoder_bundle/decoder_metadata.json')
    assert read(SOURCE/'validation.json')['status']=='PASS'
    assert digest(SOURCE/'pairs.npz')==m['pair_sha256']
    coarse=np.load(SOURCE/'decoder_bundle/coarse_symbols.npy',allow_pickle=False)
    p=dict(np.load(SOURCE/'pairs.npz',allow_pickle=False));fine=p['fine_symbols'].copy()
    assert fine.dtype==np.uint8 and fine.shape==(205379,2) and coarse.shape==(79507,2)
    assert digest(SOURCE/'decoder_bundle/coarse_symbols.npy')==meta['coarse_symbols_sha256']
    assert __import__('hashlib').sha256(fine.tobytes()).hexdigest()==m['fine_symbols_sha256']
    np.testing.assert_array_equal(p['fine_slot_index'],np.arange(205379))
    return meta,coarse,fine,p

def gate_decode(spec,coarse_path,output):
    from .audit import install
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    reads,blocked=install([spec,coarse_path],output)
    spec=read(spec);coarse=np.load(coarse_path,allow_pickle=False)
    c,inside,x=classes(spec['metadata'],coarse,'spatial8',spec['edges'])
    np.savez_compressed(output/'replay.npz',classes=c,inside=inside,context=x)
    write(output/'audit.json',{'status':'PASS','allowed_reads':sorted(set(reads)),'blocked_reads':blocked,'pid':__import__('os').getpid()})

def gate(out=OUTPUT):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);g=out/'context-gate'
    if g.exists():g=out/('context-gate-recheck-'+str(time.time_ns()))
    g.mkdir(exist_ok=False)
    meta,coarse,fine,p=sources();start=time.perf_counter();x,inside=context(meta,coarse);edges=boundaries(x,inside)
    c,_,_=classes(meta,coarse,'spatial8',edges)
    write(g/'spec.json',{'metadata':meta,'edges':edges.tolist(),'arithmetic':ARITHMETIC})
    np.save(g/'coarse.npy',coarse,allow_pickle=False)
    with (g/'decoder.log').open('w') as log:
        subprocess.run([sys.executable,'-m','research.experiment_bench.interlevel.cli','gate-decode',str(g/'spec.json'),str(g/'coarse.npy'),str(g/'decoded')],check=True,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
    replay=np.load(g/'decoded/replay.npz',allow_pickle=False)
    np.testing.assert_array_equal(c,replay['classes']);np.testing.assert_array_equal(x,replay['context']);np.testing.assert_array_equal(inside,replay['inside'])
    assert not read(g/'decoded/audit.json')['blocked_reads']
    np.testing.assert_array_equal(x,p['coarse_context_cpu'])
    np.testing.assert_array_equal(inside,p['lookup_in_bounds'])
    gpu=p['coarse_context'];gpu_classes=np.column_stack([np.searchsorted(edges[ch],gpu[:,ch],side='right') for ch in range(2)]).astype(np.uint8);gpu_classes[~inside]=8
    feasibility=read(ROOT/'research/interlevel_xyz34_feasibility/results.json')
    old=np.load(ROOT/'research/interlevel_xyz34_feasibility/fitted_histograms.npz',allow_pickle=False)
    old_edges=np.stack([old[f'random-seed0__ch{ch}__quantile-Spatial-8_edges'] for ch in range(2)])
    old_gpu=np.column_stack([np.searchsorted(old_edges[ch],gpu[:,ch],side='right') for ch in range(2)]);old_gpu[~inside]=8
    old_cpu=np.column_stack([np.searchsorted(old_edges[ch],x[:,ch],side='right') for ch in range(2)]);old_cpu[~inside]=8
    result={'status':'PASS','assignments_exact':int(c.size),'fresh_process':read(g/'decoded/audit.json'),'arithmetic':ARITHMETIC,
        'canonical_CPU_equals_prior_CPU':True,'CPU_GPU_max_abs_error':float(np.abs(x-gpu).max()),
        'CPU_GPU_class_mismatches_under_new_edges':int(np.count_nonzero(c!=gpu_classes)),
        'CPU_GPU_class_mismatches_under_prior_seed0_edges':int(np.count_nonzero(old_cpu!=old_gpu)),
        'near_boundaries_exact_context_equal_edge':int(sum(np.count_nonzero(x[inside,ch,None].astype(np.float64)==edges[ch]) for ch in range(2))),
        'quantile_edges':edges.tolist(),'unique_edges_per_channel':[int(len(np.unique(e))) for e in edges],
        'class_counts':[np.bincount(c[:,ch],minlength=9).tolist() for ch in range(2)],'in_bounds':int(inside.sum()),'OOB':int((~inside).sum()),
        'seconds_including_fresh_process':time.perf_counter()-start,
        'supported':'Pinned WSL Linux x86_64 NumPy1.21.6; separate float32 ufunc stages, no fused multiply-add; GPU not used. Universal portability NOT VERIFIED.',
        'feasibility_prediction_bytes':{s:next(a for a in feasibility['summary'] if a['split']=='random' and a['channel']=='total' and a['model_id']=='quantile-Spatial-8')[f] for s,f in [('dense_u32','primary_estimated_net_vs_boundary_bytes'),('packed_u16','packed_u16_net_vs_boundary_bytes'),('sparse_default_u16','sparse_default_u16_net_vs_boundary_bytes')]}}
    write(out/'context-validation.json',result);print('CONTEXT GATE PASS',c.size,'assignments; CPU/GPU differing classes:',result['CPU_GPU_class_mismatches_under_new_edges'],flush=True)
    return result

def encode(path,model,storage):
    from .format import make
    meta,c3,q4,_=sources();data,info=make(meta,c3,q4,model,storage)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(data)
    info.update(model=model,storage=storage,file=str(path),actual_bytes=path.stat().st_size,sha256=digest(path))
    return info

def validate(out=OUTPUT):
    from .format import decode_data,unpack,sha
    from .model_io import fit
    from research.experiment_bench.models import HistogramModel
    out=Path(out);meta,c3,q4,p=sources();checks=[]
    decode_root=out/'decoded'
    if any(decode_root.iterdir()):decode_root=out/('decoded-revalidation-'+str(time.time_ns()));decode_root.mkdir()
    for stream in sorted((out/'bitstreams').glob('*.bin')):
        name=stream.stem;decoded=decode_root/name
        with (out/'logs'/('decode-'+name+'.log')).open('w') as log:
            subprocess.run([sys.executable,'-m','research.experiment_bench.interlevel.cli','decode',str(stream),str(decoded)],cwd=ROOT,check=True,stdout=log,stderr=subprocess.STDOUT)
        arrays,_=decode_data(stream.read_bytes())
        for field,expected in [('coarse',c3),('fine',q4),('classes',arrays['classes']),('inside',p['lookup_in_bounds']),('masses3',arrays['masses3']),('masses4',arrays['masses4'])]:
            np.testing.assert_array_equal(np.load(decoded/(field+'.npy'),allow_pickle=False),expected)
        h,s=unpack(stream.read_bytes());edges=np.frombuffer(s['thresholds'],dtype='<f8').reshape(2,7) if h['model']=='spatial8' else None
        expected_c,_,_=classes(meta,c3,h['model'],edges)
        np.testing.assert_array_equal(expected_c,arrays['classes'])
        expected_m3=HistogramModel.fit(c3).freq;expected_m4=fit(q4,expected_c,{'iid':1,'boundary':2,'spatial8':9}[h['model']])
        np.testing.assert_array_equal(np.load(decoded/'masses3.npy',allow_pickle=False),expected_m3)
        np.testing.assert_array_equal(np.load(decoded/'masses4.npy',allow_pickle=False),expected_m4)
        audit=read(decoded/'decoder.json');assert audit['allowed_data_reads']==[str(stream.resolve())] and not audit['blocked_reads']
        checks.append({'file':name,'status':'PASS','coarse_array_equal':True,'fine_array_equal':True,'both_channels':True,'classes_exact':int(expected_c.size),
            'masses_exact':True,'rows':len(q4),'fresh_process':audit,'sha256':digest(stream)})
        print('Independent decode PASS',name,flush=True)
    if len(checks)!=9:raise ValueError('Expected exactly nine files')
    write(out/'decode-validation.json',{'status':'PASS','files':checks})
    return checks

def benchmark(out=OUTPUT,repeats=3):
    from .format import make,decode_data,sha
    if repeats<3:raise ValueError('At least three measured repetitions required')
    out=Path(out);meta,c3,q4,_=sources();samples=[]
    for model in ('iid','boundary','spatial8'):
        for storage in ('dense_u32','packed_u16','sparse_default_u16'):
            stream=out/'bitstreams'/(model+'-'+storage+'.bin');expected=stream.read_bytes()
            for trial in range(-1,repeats):
                data,info=make(meta,c3,q4,model,storage);assert data==expected
                arrays,timing=decode_data(data);np.testing.assert_array_equal(arrays['coarse'],c3);np.testing.assert_array_equal(arrays['fine'],q4)
                if trial>=0:samples.append({'model':model,'storage':storage,'trial':trial,**info['timing'],**timing})
            print('Benchmark warmup +',repeats,'trials',model,storage,flush=True)
    from research.hashgrid_analysis.common import csv_write
    csv_write(out/'runtime-samples.csv',samples)
    summaries=[]
    for model in ('iid','boundary','spatial8'):
        for storage in ('dense_u32','packed_u16','sparse_default_u16'):
            group=[a for a in samples if a['model']==model and a['storage']==storage];row={'model':model,'storage':storage,'measured_trials':repeats,'warmup_trials':1}
            for field in group[0]:
                if field.endswith('_seconds'):
                    values=[a[field] for a in group]
                    row[field+'_median']=float(np.median(values));row[field+'_min']=float(min(values));row[field+'_max']=float(max(values))
            summaries.append(row)
    write(out/'runtime.json',{'samples':samples,'summary':summaries,'timer_scope':'CPU algorithms+in-memory framing/integrity; excludes imports, process startup, disk IO and plots; shared L3 refit/reencoded in each encode trial',
        'peak_RSS_MiB':__import__('resource').getrusage(__import__('resource').RUSAGE_SELF).ru_maxrss/1024,'VRAM':'NOT MEASURED; CUDA disabled; no GPU operations'})
    return summaries

def run(out=OUTPUT):
    from .format import make,unpack,SHARED,MODELS
    from .model_io import STORAGES
    import unittest
    out=Path(out);assert read(out/'context-validation.json')['status']=='PASS'
    for name in ('bitstreams','decoded','logs'): (out/name).mkdir(exist_ok=False)
    write(out/'manifest.json',{'status':'IN PROGRESS','checkpoint_sha256':read(SOURCE/'manifest.json')['checkpoint_sha256']})
    write(out/'config.json',{'models':list(MODELS),'storages':list(STORAGES),'fit':'all scene L4 symbols; transmit all masses and edges','CPU_arithmetic':ARITHMETIC,'order':'all ch0 rows ascending, then all ch1 rows ascending','repeats':3,'GPU_used':False})
    files=[SOURCE/'pairs.npz',SOURCE/'pairs.csv',SOURCE/'decoder_bundle/coarse_symbols.npy',SOURCE/'decoder_bundle/decoder_metadata.json',ROOT/'research/interlevel_xyz34_feasibility/results.json',ROOT/'outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth']
    hashes={str(p.relative_to(ROOT)):digest(p) for p in files};rows=[];meta,c3,q4,_=sources();shared_ref=None
    suite=unittest.defaultTestLoader.loadTestsFromNames(['research.experiment_bench.interlevel.tests','research.experiment_bench.test_entropy','research.grid4d.test_codec'])
    with (out/'tests.log').open('w') as log:unit=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    assert unit.wasSuccessful()
    for model in MODELS:
        for storage in STORAGES:
            path=out/'bitstreams'/(model+'-'+storage+'.bin');info=encode(path,model,storage);h,sections=unpack(path.read_bytes())
            shared={n:sections[n] for n in SHARED}
            if shared_ref is None:shared_ref=shared
            else:assert shared==shared_ref
            sizes=info['sections'];total=path.stat().st_size;shared_n=sum(sizes[k] for k in SHARED);framing=info['header_json_bytes']+info['prefix_bytes']+info['integrity_bytes']
            assert sum(sizes.values())+framing==total
            row={'model':model,'storage':storage,'file':path.relative_to(out).as_posix(),'sha256':digest(path),'l3_payload_bytes':sizes['l3.payload'],
                'l4_payload_bytes':sizes['l4.payload'],'l3_model_bytes':sizes['l3.model'],'l4_model_bytes':sizes['l4.model'],'threshold_bytes':sizes['thresholds'],
                'quantization_metadata_bytes':sizes['quantization'],'geometry_metadata_bytes':sizes['geometry'],'l3_metadata_bytes':sizes['l3.info'],'l4_metadata_bytes':sizes['l4.info'],
                'framing_integrity_bytes':framing,'shared_l3_bytes':shared_n,'total_standalone_bytes':total,'incremental_l4_bytes':total-shared_n,
                'actual_bits_per_l4_symbol':8*(total-shared_n)/q4.size,'l4_payload_bits_per_symbol':8*sizes['l4.payload']/q4.size,
                'compression_ratio_incremental_vs_raw_uint8_l4':q4.size/(total-shared_n),'compression_ratio_standalone_vs_raw_uint8_pair':(q4.size+c3.size)/total,
                'finite_l4_cross_entropy_bits':info['finite_l4_cross_entropy_bits'],'coder_payload_minus_finite_bits':8*sizes['l4.payload']-info['finite_l4_cross_entropy_bits'],
                'class_counts':info['class_counts'],'omitted_unreachable_rows':info['omitted_unreachable_rows'],'encoder_masses_sha256':info['encoder_masses_sha256']}
            rows.append(row);print('Encoded',model,storage,total,'B',flush=True)
    checks=validate(out);times=benchmark(out)
    for r in rows:
        r['decode']='PASS';r['runtime']=next(t for t in times if t['model']==r['model'] and t['storage']==r['storage'])
        for baseline in ('iid','boundary'):
            same=next(a for a in rows if a['model']==baseline and a['storage']==r['storage']);best=min((a for a in rows if a['model']==baseline),key=lambda a:a['total_standalone_bytes'])
            for label,base in [('same_'+baseline,same),('best_'+baseline,best)]:
                r['gain_vs_'+label+'_bytes']=base['total_standalone_bytes']-r['total_standalone_bytes'];r['gain_vs_'+label+'_percent']=100*r['gain_vs_'+label+'_bytes']/base['total_standalone_bytes']
                r['incremental_gain_vs_'+label+'_percent']=100*r['gain_vs_'+label+'_bytes']/base['incremental_l4_bytes']
    best_spatial=min((a for a in rows if a['model']=='spatial8'),key=lambda a:a['total_standalone_bytes'])
    verdict='ACTUAL COMPRESSION VERIFIED' if max(best_spatial['gain_vs_best_iid_bytes'],best_spatial['gain_vs_best_boundary_bytes'])>0 else 'STATISTICALLY USEFUL, BUT NOT BITRATE-PROFITABLE'
    old=read(out/'context-validation.json')['feasibility_prediction_bytes']
    comparison=[{'storage':r['storage'],'estimated_net_vs_boundary_bytes':old[r['storage']],'actual_net_vs_same_boundary_bytes':r['gain_vs_same_boundary_bytes'],'actual_net_vs_best_boundary_bytes':r['gain_vs_best_boundary_bytes']} for r in rows if r['model']=='spatial8']
    for path,expected in hashes.items():assert digest(ROOT/path)==expected
    write(out/'results.json',{'verdict':verdict,'rows':rows,'shared_l3_identical':True,'input_hashes':hashes,'input_artifacts_unchanged':True,'estimated_vs_actual':comparison,'scope':'Only bouncingballs xyz L3/L4 table-wise8; exact recovery of quantized pair, not full scene compression','fit_protocol':'scene-specific all symbols, distinct from heldout prediction',
        'best_iid':min((r for r in rows if r['model']=='iid'),key=lambda r:r['total_standalone_bytes'])['file'],'best_boundary':min((r for r in rows if r['model']=='boundary'),key=lambda r:r['total_standalone_bytes'])['file'],'best_spatial':best_spatial['file']})
    from research.hashgrid_analysis.common import csv_write
    csv_write(out/'results.csv',[{k:v for k,v in r.items() if not isinstance(v,(dict,list))} for r in rows]);csv_write(out/'estimated-vs-actual.csv',comparison)
    write(out/'validation.json',{'status':'PASS','unit_tests':{'tests':unit.testsRun,'failures':len(unit.failures),'errors':len(unit.errors)},'context_gate':'PASS','independent_decodes':checks,'shared_L3_sections_bitwise_equal':True,'section_sum_equals_filesystem_size':True,'sources_unchanged':True,'bench_reproducibility':'every warmup and timed encode bitwise identical to saved file','GPU':'NOT RUN; CPU canonical mode'})
    write(out/'manifest.json',{'status':'COMPUTED','checkpoint_sha256':read(SOURCE/'manifest.json')['checkpoint_sha256'],'environment':{'python':sys.version,'numpy':np.__version__,'constriction':__import__('importlib.metadata',fromlist=['version']).version('constriction'),'GPU':False},'verdict':verdict,
        'source_code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in list(Path(__file__).parent.glob('*.py'))+[ROOT/'research/experiment_bench/entropy.py']}})
    print(verdict,flush=True)

def comparisons(out=OUTPUT):
    from .format import unpack,decode_data,pack,make,json_bytes
    from .model_io import fit
    from research.hashgrid_analysis.common import csv_write
    out=Path(out);r=read(out/'results.json');meta,c3,q4,p=sources();inside=p['lookup_in_bounds']
    def cost(c,C):
        f=fit(q4,c,C);prob=f[np.arange(2)[None,:],c,q4].astype(np.float64)/65536
        return float(-np.log2(prob).sum())
    gpu=p['coarse_context'];edges=boundaries(gpu,inside)
    gpu_classes=np.column_stack([np.searchsorted(edges[ch],gpu[:,ch].astype(np.float64),side='right') for ch in range(2)]).astype(np.uint8);gpu_classes[~inside]=8
    row_b=next(a for a in r['rows'] if a['model']=='boundary');row_s=next(a for a in r['rows'] if a['model']=='spatial8')
    old=read(ROOT/'research/interlevel_xyz34_feasibility/results.json')
    heldout=next(a for a in old['summary'] if a['split']=='random' and a['channel']=='total' and a['model_id']=='quantile-Spatial-8')['projected_payload_saving_vs_boundary_bytes']
    gpu_full=(row_b['finite_l4_cross_entropy_bits']-cost(gpu_classes,9))/8
    cpu_full=(row_b['finite_l4_cross_entropy_bits']-row_s['finite_l4_cross_entropy_bits'])/8
    actual_payload=row_b['l4_payload_bytes']-row_s['l4_payload_bytes']
    bridge={'previous_heldout_GPU_payload_saving_bytes':heldout,'scene_fitted_GPU_finite_payload_saving_bytes':gpu_full,'scene_fitted_canonical_CPU_finite_payload_saving_bytes':cpu_full,
        'actual_CPU_range_payload_saving_bytes':actual_payload,'full_scene_fit_delta_bytes':gpu_full-heldout,'CPU_context_and_refitted_thresholds_delta_bytes':cpu_full-gpu_full,
        'range24_rounding_finalization_delta_bytes':actual_payload-cpu_full,'interpretation':'Diagnostic attribution in this sequence; CPU-vs-GPU bridge also refits quantile edges. No GPU coding/decoding performed.'}
    write(out/'prediction-bridge.json',bridge)
    failures=[]
    for row in r['rows']:
        data=(out/row['file']).read_bytes();h,s=unpack(data)
        cases={'truncation':data[:-1],'extra_bytes':data+b'x','magic':b'BADMAGIC'+data[8:]}
        damaged=bytearray(data);damaged[-40]^=1;cases['corrupt_payload_integrity']=bytes(damaged)
        bad=bytearray(data);__import__('struct').pack_into('<H',bad,8,65535);cases['version']=bytes(bad)
        info=json.loads(s['l4.info']);info['class_sha256']='0'*64;s['l4.info']=json_bytes(info);cases['rehashed_wrong_context_digest']=pack(h,s)
        for label,invalid in cases.items():
            try:decode_data(invalid)
            except (ValueError,KeyError) as error:failures.append({'file':row['file'],'case':label,'status':'PASS','error':str(error)})
            else:raise AssertionError('Invalid file accepted: '+label)
        # All original files must remain byte-identical and independently valid.
        assert digest(out/row['file'])==row['sha256']
    write(out/'corruption-validation.json',{'status':'PASS','cases':failures,'real_stream_cases':len(failures)})
    validation=read(out/'validation.json');validation['real_stream_corruption_tests']={'status':'PASS','cases':len(failures),'file':'corruption-validation.json'};write(out/'validation.json',validation)
    print('Actual-file corruption tests PASS',len(failures));print(json.dumps(bridge,indent=2))

def compare_runs(first,second):
    first=Path(first);second=Path(second);a=read(first/'results.json');b=read(second/'results.json');checks=[]
    for row in a['rows']:
        matching=next(r for r in b['rows'] if r['model']==row['model'] and r['storage']==row['storage'])
        assert row['sha256']==matching['sha256']==digest(first/row['file'])==digest(second/matching['file'])
        assert row['total_standalone_bytes']==matching['total_standalone_bytes']
        checks.append({'file':row['file'],'status':'PASS','sha256':row['sha256']})
    write(first/'repeat-comparison.json',{'status':'PASS','checks':checks,'against':str(second)})
    print('Nine-stream independent repeat PASS')
