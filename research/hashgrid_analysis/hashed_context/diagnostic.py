"""Stages 0–1 only: provenance, pilot, all-slot context and decoder replay."""
import argparse
import csv
import gc
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from .core import ROOT,ARITHMETIC,sha,load_bundle,compute_context,arrays_sha
from .runtime import write_json,save_npz,peak_rss_mib

PAIRS=('L4_to_L5','L5_to_L6')

def prepare(out):
    # Current run directory exists but must still be empty.
    assert out.is_dir() and not any(out.iterdir()), 'Preparation requires a fresh empty run'
    protected={}
    excluded=(out,ROOT/'research/hashgrid_analysis/hashed_context')
    for folder in (ROOT/'research',ROOT/'external/Grid4D-audit-clean'):
        for path in folder.rglob('*'):
            if (not path.is_file() or any(path.is_relative_to(x) for x in excluded)
                or any(x in path.parts for x in ('.git','__pycache__','tmp_build'))):
                continue
            if path.suffix.lower() in ('.md','.json','.csv','.npz','.npy','.png','.svg','.bin','.py','.cu','.cpp','.h','.sh','.yml','.yaml','.ps1'):
                protected[path.relative_to(ROOT).as_posix()]=sha(path)
    checkpoint=ROOT/'outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth'
    protected[checkpoint.relative_to(ROOT).as_posix()]=sha(checkpoint)
    protected['AGENTS.md']=sha(ROOT/'AGENTS.md')
    write_json(out/'protected-input-hashes.json',protected)
    export=ROOT/'research/experiment_bench/reference-study/table-8'
    source=json.loads((export/'manifest.json').read_text(encoding='utf-8'))
    mapping=json.loads((ROOT/'research/analysis_results/mapping-validation.json').read_text(encoding='utf-8'))
    assert source['bits']==8 and source['scope']=='table' and source['kind']=='uniform-quantized'
    assert source['source_sha256']==protected[checkpoint.relative_to(ROOT).as_posix()]
    cuda=ROOT/'external/Grid4D-audit-clean/hashencoder/src/hashencoder.cu'
    assert sha(cuda)==mapping['upstream_cuda_sha256'] and mapping['status']=='PASS'
    g=source['grids']['xyz_encoding.embeddings'];qmeta=g['quantization'][0]
    assert len(g['quantization'])==1 and qmeta['row_start']==0 and qmeta['row_end']==g['shape'][0]
    filename=export/g['payload']['file']
    assert sha(filename)==g['payload']['sha256']
    symbols=np.memmap(filename,dtype=np.uint8,mode='r',shape=tuple(g['shape']))
    for name,coarse_level,fine_level in zip(PAIRS,(4,5),(5,6)):
        folder=out/name;folder.mkdir()
        bundle=folder/'decoder_bundle';bundle.mkdir()
        roles={}
        for role,level in (('coarse',coarse_level),('fine',fine_level)):
            roles[role]={'level':level,'rows':g['table_rows_per_level'][level],
                'offset_start':g['offsets'][level],'offset_end':g['offsets'][level+1],
                'lookup_resolution':mapping['grids']['xyz']['resolutions'][level],
                'scale':mapping['grids']['xyz']['scales'][level]}
            assert roles[role]['lookup_resolution']==g['cuda_lookup_resolutions'][level]
        roles['coarse']['quantization']=qmeta.copy()
        q=np.asarray(symbols[roles['coarse']['offset_start']:roles['coarse']['offset_end']]).copy()
        with (bundle/'coarse_symbols.npy').open('xb') as f:
            np.save(f,q,allow_pickle=False)
        meta={'version':1,'grid':'xyz','arithmetic':ARITHMETIC,**roles,
            'geometry_convention':'nominal-v-in-[0,R);point-v<=floor(scale);u=f32(v)/f32(scale)',
            'fallback':{'features':[0,0],'ordinal':-1,'vertex':[-1,-1,-1],'coordinates':[0,0,0],'representative_valid':False},
            'geometry_categories':{'G0':'nominal empty','G1':'nominal positive;point empty',
                'G2':'point singleton','G3':'point multi'},
            'coarse_symbols_sha256':sha(bundle/'coarse_symbols.npy'),
            'source_checkpoint_sha256':source['source_sha256'],'source_symbols_sha256':g['payload']['sha256'],
            'implementation':{'repo':'external/Grid4D-audit-clean',
                'cuda_sha256':sha(cuda),'coarse_prefix_offsets':g['offsets'][:coarse_level+2],
                'base_resolution':g['base_resolution'],'per_level_scale':g['per_level_scale'],
                'kernel_log2_per_level_scale':g['kernel_log2_per_level_scale']}}
        write_json(bundle/'decoder_metadata.json',meta)
    source_paths=[ROOT/'AGENTS.md',ROOT/'research/RESEARCH_DIRECTION_DECISION.md',
        export/'manifest.json',ROOT/'research/experiment_bench/reference-runtime.json',
        ROOT/'research/analysis_results/mapping-validation.json',
        ROOT/'research/direction_audit_20261011_01/geometry-diagnostic.json',cuda,
        ROOT/'research/grid4d/codec.py',ROOT/'research/experiment_bench/interlevel/context.py',
        ROOT/'research/hashgrid_analysis/mapping.py']
    source_paths+=sorted((ROOT/'research/hashgrid_analysis/hashed_context').glob('*.py'))
    write_json(out/'run-manifest.json',{'stage':'0','status':'PASS','date':'2026-10-13',
        'checkpoint_sha256':source['source_sha256'],'table8_sha256':g['payload']['sha256'],
        'scope':'table','bits':8,'arithmetic':ARITHMETIC,'python':sys.version,'numpy':np.__version__,
        'source_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in source_paths},
        'new_quantization':False,'new_models_coder_training':False,
        'coarse_bundle_method':'exact unchanged saved uint8 coarse slice; decoder-equivalent symbols, no entropy decoding here',
        'protected_files':len(protected)})
    print(json.dumps({'stage0':'PASS','protected_files':len(protected),'bundles':list(PAIRS)}))

def pilot(out):
    import io
    import unittest
    from . import test_synthetic
    stream=io.StringIO()
    tests=unittest.defaultTestLoader.loadTestsFromModule(test_synthetic)
    started=time.perf_counter()
    tested=unittest.TextTestRunner(stream=stream,verbosity=2).run(tests)
    with (out/'synthetic-tests.log').open('x',encoding='utf-8') as f:
        f.write(stream.getvalue())
    test_result={'status':'PASS' if tested.wasSuccessful() else 'FAIL','tests':tested.testsRun,
        'failures':len(tested.failures),'errors':len(tested.errors),'seconds':time.perf_counter()-started}
    write_json(out/'synthetic-tests.json',test_result)
    assert tested.wasSuccessful()
    records=[]
    for pair in PAIRS:
        meta,q=load_bundle(out/pair/'decoder_bundle')
        t=time.perf_counter();cpu=time.process_time()
        a=compute_context(meta,q,chunk=65536,vertex_limit=65536)
        elapsed=time.perf_counter()-t;cpu_time=time.process_time()-cpu
        total=int(np.prod(meta['fine']['lookup_resolution']))
        # Three complete passes: parent + two independent chunk/replay runs.
        estimate=max(elapsed,cpu_time)*(total/65536)*3
        records.append({'pair':pair,'pilot_vertices':65536,'wall_seconds':elapsed,'cpu_seconds':cpu_time,
            'peak_rss_mib':peak_rss_mib(),'all_passes_estimated_seconds':estimate,
            'nominal_total':total,'context_array_bytes':sum(x.nbytes for x in a.values())})
        del a;gc.collect()
    projected=sum(r['all_passes_estimated_seconds'] for r in records)
    peak=max(r['peak_rss_mib'] for r in records)
    result={'status':'GO' if projected<1800 and peak<1024 else 'NO-GO','records':records,
        'estimated_compute_seconds':projected,'peak_rss_mib':peak,
        'memory_projection':'bounded same-sized arrays; full CSV streams, no vertices×CDF arrays',
        'estimated_conservative_peak_mib':max(peak*2,256),'budget_seconds':1800,'budget_mib':1024}
    if result['estimated_conservative_peak_mib']>=1024:
        result['status']='NO-GO'
    write_json(out/'pilot.json',result)
    print(json.dumps(result))

def geometry_check(meta,a,audit):
    old=next(r for r in audit['records'] if r['level']==meta['fine']['level'])
    rows=meta['fine']['rows'];n=a['nominal_count'];e=a['point_count'];geo=a['geometry']
    assert np.array_equal(a['slot_index'],np.arange(rows))
    assert len(np.unique(a['slot_index']))==rows
    for key,counts in (('nominal',n),('eligible',e)):
        expected=old[key]
        assert int(counts.sum())==expected['vertices']
        assert int(np.count_nonzero(counts==0))==expected['geometry_unused_slots']
        assert int(np.count_nonzero(counts==1))==expected['singleton_slots']
        assert int(np.count_nonzero(counts>1))==expected['colliding_slots']
        assert int(counts.max())==expected['max_multiplicity']
        assert np.bincount(counts).tolist()==[r['slots'] for r in expected['histogram']]
    assert np.all(e<=n)
    assert int(np.count_nonzero(geo==0))==old['nominal']['geometry_unused_slots']
    assert int(np.count_nonzero(geo==1))==old['nominal_only_slots']
    assert np.all(a['canonical_ordinal'][e==0]==-1)
    assert np.all(a['canonical_vertex'][e==0]==-1)
    for key in ('mean','std','canonical_features','canonical_coordinates'):
        assert np.isfinite(a[key]).all() and np.all(a[key][e==0]==0)
    assert np.all(a['std'][e==1]==0)
    assert np.array_equal(a['mean'][e==1],a['canonical_features'][e==1].astype(np.float64))
    return {'status':'PASS','all_slots':rows,'no_gaps_duplicates':True,
        'nominal_vertices':int(n.sum()),'point_vertices':int(e.sum()),
        'nominal_collision_slots':int(np.count_nonzero(n>1)),
        'point_collision_slots':int(np.count_nonzero(e>1)),
        'geometry_counts':{f'G{i}':int(np.count_nonzero(geo==i)) for i in range(4)},
        'exact_geometry_audit_match':True,'empty_fallback':True,'singleton_std_exact_zero':True}

def export_csv(path,a):
    columns=[('slot_index',None),('global_embedding_row',None),('nominal_count',None),('point_count',None),
        ('geometry',None),('canonical_ordinal',None)]
    columns += [(key,d) for key in ('canonical_vertex','canonical_coordinates') for d in range(3)]
    columns += [(key,d) for key in ('canonical_features','mean','std') for d in range(2)]
    names=[key if d is None else f'{key}_{d}' for key,d in columns]
    with Path(path).open('x',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(names)
        for i in range(len(a['slot_index'])):
            w.writerow([a[key][i].item() if d is None else a[key][i,d].item() for key,d in columns])

def run_full(out):
    assert json.loads((out/'pilot.json').read_text())['status']=='GO'
    audit=json.loads((ROOT/'research/direction_audit_20261011_01/geometry-diagnostic.json').read_text())
    summaries=[]
    for pair in PAIRS:
        folder=out/pair;bundle=folder/'decoder_bundle';meta,q=load_bundle(bundle)
        t=time.perf_counter();cpu=time.process_time()
        a=compute_context(meta,q,chunk=65536)
        signature=arrays_sha(a);elapsed=time.perf_counter()-t;cpu_elapsed=time.process_time()-cpu
        validation=geometry_check(meta,a,audit)
        save_npz(folder/'contexts.npz',a)
        csv_started=time.perf_counter();export_csv(folder/'contexts.csv',a)
        csv_seconds=time.perf_counter()-csv_started
        replays=[]
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
        for chunk in (4096,65536):
            dest=folder/f'decoder_replay_{chunk}'
            r=subprocess.run([sys.executable,'-m','research.hashgrid_analysis.hashed_context.replay',
                '--bundle',str(bundle),'--output',str(dest),'--chunk',str(chunk)],
                cwd=ROOT,env=env,text=True,capture_output=True)
            with (folder/f'replay-{chunk}.log').open('x',encoding='utf-8') as f:
                f.write(r.stdout+r.stderr)
            if r.returncode:
                raise RuntimeError(f'Replay {pair}/{chunk} failed: '+r.stderr[-3000:])
            child=json.loads((dest/'read-audit.json').read_text())
            assert child['arrays_sha256']==signature and child['blocked_reads']==[]
            with np.load(dest/'contexts.npz',allow_pickle=False) as replay:
                assert set(replay.files)==set(a)
                for key in a:
                    assert a[key].dtype==replay[key].dtype and a[key].tobytes()==replay[key].tobytes(),key
            replays.append(child)
        fine_source=ROOT/'research/experiment_bench/reference-study/table-8/xyz_encoding.u8.bin'
        src=np.memmap(fine_source,np.uint8,'r',shape=(6098108,2))
        targets=np.asarray(src[meta['fine']['offset_start']:meta['fine']['offset_end']]).copy()
        with (folder/'fine_symbols.npy').open('xb') as f:
            np.save(f,targets,allow_pickle=False)
        del src,targets
        # Explicit negative audit tests are a different process from successful replay.
        probes=folder/'forbidden_read_probes'
        r=subprocess.run([sys.executable,'-m','research.hashgrid_analysis.hashed_context.replay',
            '--bundle',str(bundle),'--output',str(probes),'--probe-forbidden',
            str(ROOT/'outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth'),
            str(fine_source),str(folder/'fine_symbols.npy'),str(folder/'contexts.npz')],
            cwd=ROOT,env=env,text=True,capture_output=True)
        if r.returncode:
            raise RuntimeError('Negative audit tests failed: '+r.stderr[-3000:])
        probes_result=json.loads((probes/'read-audit.json').read_text())
        assert probes_result['probe_count']==4 and len(probes_result['blocked_reads'])==4
        validation.update({'arrays_sha256':signature,'parent_wall_seconds':elapsed,'parent_cpu_seconds':cpu_elapsed,
            'csv_seconds':csv_seconds,'parent_peak_rss_mib':peak_rss_mib(),
            'decoder_replays':replays,'chunk4096_65536_bitwise_equal':True,'negative_read_probes':probes_result,
            'targets_joined_after_context_and_replay':True,'fine_symbols_sha256':sha(folder/'fine_symbols.npy')})
        assert validation['parent_peak_rss_mib']<1024
        write_json(folder/'validation.json',validation)
        summaries.append({'pair':pair,**{k:v for k,v in validation.items() if k not in ('decoder_replays','negative_read_probes')}})
        print(json.dumps(summaries[-1]))
        del a,q;gc.collect()
    write_json(out/'context-validation.json',{'status':'PASS','pairs':summaries,
        'probability_fitting':'NOT RUN','entropy_coding':'NOT RUN','training':'NOT RUN'})

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','pilot','compute'))
    p.add_argument('--output',required=True);args=p.parse_args()
    out=Path(args.output).resolve()
    {'prepare':prepare,'pilot':pilot,'compute':run_full}[args.action](out)

if __name__=='__main__':main()
