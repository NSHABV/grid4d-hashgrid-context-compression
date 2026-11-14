"""Reproducible B protocol, twelve paid transports, independent decode, repeats."""
import argparse,csv,gc,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
from research.hashgrid_analysis.hashed_context.core import ROOT,sha,load_bundle,compute_context
from research.hashgrid_analysis.hashed_context.runtime import write_json,peak_rss_mib
from research.experiment_bench.hashed_interlevel.core import fit_spec,classify

A=ROOT/'research/hashed_multiplicity_study_20261014_01'
DIAG=ROOT/'research/hashed_context_diagnostic_20261013_01/L4_to_L5'
TABLE=ROOT/'research/experiment_bench/reference-study/table-8'
ARMS=('IID','Geometry4','Canonical8','Mean8')
STORAGES=('dense_u32','packed_u16','sparse_default_u16')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def source_arrays():
    meta,q4=load_bundle(DIAG/'decoder_bundle')
    q5=np.load(DIAG/'fine_symbols.npy',allow_pickle=False)
    assert q5.dtype==np.uint8 and q5.shape==(524288,2)
    return meta,q4,q5
def csv_out(path,rows):
    with Path(path).open('x',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def prepare(run):
    run.mkdir(parents=True,exist_ok=False);start=time.perf_counter();cpu=time.process_time()
    final=read(A/'final-validation.json');assert final['status']=='PASS'
    assert read(A/'decision.json')['B_Mean8_continues']
    protected=read(A/'protected-input-hashes.json')
    for name,h in final['artifact_hashes'].items():assert sha(A/name)==h,name
    for p in A.rglob('*'):
        if p.is_file():protected[p.relative_to(ROOT).as_posix()]=sha(p)
    for name,h in protected.items():assert sha(ROOT/name)==h,name
    write_json(run/'protected-input-hashes.json',protected)
    meta,q4,q5=source_arrays()
    assert sha(TABLE/'xyz_encoding.u8.bin')==meta['source_symbols_sha256']
    raw=np.memmap(TABLE/'xyz_encoding.u8.bin',mode='r',dtype=np.uint8,shape=(6098108,2))
    for key,q in [('coarse',q4),('fine',q5)]:
        g=meta[key];assert np.array_equal(raw[g['offset_start']:g['offset_end']],q)
    del raw
    manifest=read(TABLE/'manifest.json')
    write_json(run/'PREREGISTERED_PROTOCOL.json',{
        'date':'2026-10-15','scope':'actual scene-specific coding, xyz L4+L5 only',
        'arms':ARMS,'transports':STORAGES,'selection':'minimum actual full file size independently for each arm',
        'fitting':'all symbols; all fitted masses and float64 thresholds transmitted and paid',
        'quantization':'unchanged existing table-wise8; no quantize or training',
        'order':'ch0 ascending all fine slots, then ch1 ascending all fine slots',
        'arithmetic':meta['arithmetic'],'decoder':'one bin data input plus public code/software; pinned CPU NumPy1.26.4',
        'Count6_excluded':'A NO-GO on L5/L6, does not cancel B',
        'GO':'all correctness PASS and Mean8 actual standalone bytes < best IID/Geometry4/Canonical8',
        'runtime_protocol':'12 first encode+fresh strict decode; best per arm one warmup+3 timed byte-identical repeats; IO/startup separately',
        'canonical_payload_validation':'strict decoder reencodes decoded symbols to reject ignored trailing words; timed separately',
        'GPU_used':False,'reason':'canonical CPU contexts previously subsecond; arithmetic exactness retained',
        'limitations':'single scene/checkpoint/quantizer/pair; no whole Grid4D rate or generalization claim'})
    write_json(run/'input-validation.json',{'status':'PASS','protected_files':len(protected),
        'original_slices_exact':True,'checkpoint_sha256':meta['source_checkpoint_sha256'],
        'xyz_symbols_sha256':meta['source_symbols_sha256'],
        'sources':{str(p.relative_to(ROOT)):sha(p) for p in [TABLE/'manifest.json',DIAG/'fine_symbols.npy',DIAG/'decoder_bundle/coarse_symbols.npy',DIAG/'decoder_bundle/decoder_metadata.json',DIAG/'contexts.npz']},
        'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu,'peak_rss_mib':peak_rss_mib()})
    t=time.perf_counter();c=time.process_time();compute_context(meta,q4,vertex_limit=65536)
    wall=time.perf_counter()-t;cpu=time.process_time()-c
    write_json(run/'pilot.json',{'status':'GO','sample_nominal_vertices':65536,'full_nominal_vertices':531441,
        'context_sample_wall_seconds':wall,'context_sample_cpu_seconds':cpu,'projected_context_seconds':wall*531441/65536,
        'conservative_full_experiment_cpu_seconds':300,'projected_peak_mib':512,'measured_peak_rss_mib':peak_rss_mib(),
        'GPU_used':False,'additional_VRAM_bytes':0})
    print(json.dumps({'prepare':'PASS','protected':len(protected),'pilot_wall':wall}))

def execute(run):
    from .format import encode_pair,decode_bytes,array_sha,unpack,section_sizes
    assert read(run/'input-validation.json')['status']=='PASS' and read(run/'pilot.json')['status']=='GO'
    meta,q4,q5=source_arrays();records=[];expected={};allrows=np.arange(len(q5))
    with np.load(DIAG/'contexts.npz') as z:ctx={k:z[k] for k in z.files}
    for name in ARMS:expected[name]=classify(ctx,fit_spec(ctx,allrows,name))
    del ctx;gc.collect()
    for sub in ('streams','first_encode','decoded','logs','records'):(run/sub).mkdir(exist_ok=True)
    shared=None
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPATH']=str(ROOT)+os.pathsep+str(ROOT/'.tools/hashed-pair-deps')
    for name in ARMS:
        for storage in STORAGES:
            key=name+'__'+storage;path=run/'streams'/(key+'.bin');recordpath=run/'records'/(key+'.json')
            if recordpath.exists():
                rec=read(recordpath);assert sha(path)==rec['sha256'];records.append(rec);continue
            data,detail=encode_pair(meta,q4,q5,name,storage)
            assert detail['classes_sha256']==array_sha(expected[name]),'Encoder vs prior diagnostic classes'
            header,sections=unpack(data)
            coarse=(sections['coarse_model'],sections['coarse_payload'])
            if shared is None:shared=coarse
            assert coarse==shared
            if path.exists():assert path.read_bytes()==data,'Resume changed stream'
            else:
                with path.open('xb') as f:f.write(data)
            info=run/'first_encode'/(key+'.json')
            if not info.exists():write_json(info,detail)
            else:detail=read(info)
            out=run/'decoded'/key;attempt=1
            while out.exists():attempt+=1;out=run/'decoded'/(key+f'_attempt{attempt}')
            cmd=[sys.executable,'-m','research.experiment_bench.hashed_pair.replay','--input',str(path),'--output',str(out)]
            t=time.perf_counter();cp=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True);cold=time.perf_counter()-t
            with (run/'logs'/(out.name+'.log')).open('x',encoding='utf-8') as f:f.write(cp.stdout+cp.stderr)
            if cp.returncode:raise RuntimeError(cp.stdout+cp.stderr)
            audit=read(out/'read-audit.json')
            for arrayname,original in [('q4',q4),('q5',q5),('classes',expected[name])]:
                restored=np.load(out/(arrayname+'.npy'),allow_pickle=False)
                assert np.array_equal(restored,original),arrayname
            assert audit['status']=='PASS' and not audit['blocked_reads'] and audit['allowed_data_reads']==[str(path.resolve())]
            sizes=section_sizes(data);assert sizes['total_bytes']==path.stat().st_size
            assert sum(sizes[k] for k in ('coarse_bytes','fine_payload_bytes','model_bytes','metadata_framing_bytes'))==path.stat().st_size
            rec={'model':name,'storage':storage,'path':str(path.relative_to(run)),'sha256':sha(path),**sizes,
                'first_encode_seconds':detail['timing']['encode_total_seconds'],
                'cold_decode_process_seconds':cold,'decoder_body_seconds':audit['body_with_io_seconds'],
                'strict_decode_seconds':audit['timing']['decode_total_seconds'],
                'decoder_context_seconds':audit['timing']['context_seconds'],
                'canonical_validation_seconds':audit['timing']['canonical_validation_seconds'],
                'decoder_peak_rss_mib':audit['peak_rss_mib'],'finite_fine_bits':detail['finite_fine_bits'],
                'decode_directory':str(out.relative_to(run)),'exact_q4':'PASS','exact_q5':'PASS','exact_classes':'PASS'}
            write_json(recordpath,rec);records.append(rec)
            print(json.dumps({'stream':key,'bytes':len(data),'decode':'PASS'}),flush=True)
    # Recheck common coarse bytes also when resuming previously completed records.
    common=[tuple(unpack((run/r['path']).read_bytes())[1][k] for k in ('coarse_model','coarse_payload')) for r in records]
    assert all(v==common[0] for v in common)
    write_json(run/'results.json',records);csv_out(run/'results.csv',records)
    best=[min((r for r in records if r['model']==name),key=lambda r:r['total_bytes']) for name in ARMS]
    write_json(run/'best.json',best);csv_out(run/'best.csv',best)
    warm=[]
    for r in best:
        data=(run/r['path']).read_bytes()
        for rep in range(4):
            b,e=encode_pair(meta,q4,q5,r['model'],r['storage']);assert b==data
            a,b,c,d=decode_bytes(data);assert np.array_equal(a,q4) and np.array_equal(b,q5) and np.array_equal(c,expected[r['model']])
            warm.append({'model':r['model'],'storage':r['storage'],'repeat':rep,'warmup':rep==0,
                'encode':e['timing'],'decode':d['timing'],'peak_rss_mib':peak_rss_mib(),'byte_identical':True})
    write_json(run/'runtime-samples.json',warm)
    source=run/best[-1]['path'];out=run/'forbidden_read_probes'
    forbidden=[ROOT/'outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth',
        TABLE/'xyz_encoding.u8.bin',DIAG/'fine_symbols.npy',DIAG/'decoder_bundle/coarse_symbols.npy',DIAG/'contexts.npz',
        A/'L4_to_L5/seed0_Count6/fitted.npz',run/'first_encode'/(best[-1]['model']+'__'+best[-1]['storage']+'.json')]
    cp=subprocess.run([sys.executable,'-m','research.experiment_bench.hashed_pair.replay','--input',str(source),'--output',str(out),
        '--probe-forbidden',*[str(p) for p in forbidden]],cwd=ROOT,env=env,capture_output=True,text=True)
    if cp.returncode:raise RuntimeError(cp.stdout+cp.stderr)
    write_json(run/'decode-validation.json',{'status':'PASS','streams':len(records),'exact_symbols_per_stream':int(q4.size+q5.size),
        'fine_allocated_slots':len(q5),'channels':2,'all_q4_q5_classes_exact':True,'source_context_classes_exact':True,
        'shared_coarse_identical':True,'byte_identical_repeats':len(warm),'forbidden_read_probes':len(forbidden),
        'peak_encoder_parent_rss_mib':peak_rss_mib(),'GPU_used':False,'VRAM_allocated_bytes':0})
    print(json.dumps({'run':'PASS','files':len(records),'peak_rss_mib':peak_rss_mib()}))

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','execute']);p.add_argument('--run',type=Path,required=True)
    a=p.parse_args();globals()[a.stage](a.run.resolve())
if __name__=='__main__':main()
