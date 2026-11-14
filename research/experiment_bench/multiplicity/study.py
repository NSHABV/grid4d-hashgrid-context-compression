"""Count6 follow-up exploratory study: prepare, fit, replay, then one test."""
import argparse,csv,gc,hashlib,io,json,os,shutil,subprocess,sys,time,unittest
from pathlib import Path
import numpy as np
from .geometry import specification,compute_geometry,count6_classes,geometry4_classes
from research.hashgrid_analysis.hashed_context.core import ROOT,sha
from research.hashgrid_analysis.hashed_context.runtime import write_json,save_npz,peak_rss_mib
from research.experiment_bench.hashed_interlevel.core import split_slots,fit_masses,losses,strata
from research.experiment_bench.hashed_interlevel.dry_model import serialize,deserialize,section_sizes

OLD=ROOT/'research/hashed_dispersion_heldout_20261013_01'
DIAG=ROOT/'research/hashed_context_diagnostic_20261013_01'
PAIRS=('L4_to_L5','L5_to_L6');ARMS={'Geometry4':4,'Count6':6}
STORAGES=('dense_u32','packed_u16','sparse_default_u16')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def csv_out(p,rows):
    with Path(p).open('x',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def array_sha(a):return hashlib.sha256(a.dtype.str.encode()+str(a.shape).encode()+a.tobytes()).hexdigest()
def timing(t,c):return {'wall_seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-c,'peak_rss_mib':peak_rss_mib()}
def prepare(run):
    run.mkdir(parents=True,exist_ok=False);t=time.perf_counter();c=time.process_time();protected={}
    def check(p,h):
        assert sha(p)==h,str(p);protected[p.relative_to(ROOT).as_posix()]=h
    final=read(OLD/'final-validation.json');assert final['status']=='PASS'
    for p,h in read(OLD/'protected-input-hashes.json').items():check(ROOT/p,h)
    for p,h in final['artifact_hashes'].items():check(OLD/p,h)
    for p,h in read(OLD/'source-hashes.json').items():check(ROOT/p,h)
    for p in ('final-validation.json','source-hashes.json','protected-input-hashes.json'):check(OLD/p,sha(OLD/p))
    write_json(run/'protected-input-hashes.json',protected)
    protocol={'version':1,'label':'follow-up exploratory study on the same checkpoint and already-inspected test strata',
      'created_before_fitting':True,'pairs':PAIRS,'arms':ARMS,'seeds':[0,1,2],
      'classes':'G0 nominal0; G1 nominal>0 point0; K1 point1; K2 point2; K3 point3; K4plus point>=4',
      'geometry_inputs':'fine resolution/actual scale/rows/offsets/hash; no coarse features, occupancy or targets',
      'splits':'byte-for-byte previous NPZ slots; PCG64 seeds 0/1/2; train335545 validation83886 test104857; channels share slot split',
      'fit':'train-only models.frequencies Laplace1 + min1 + stable largest remainder total65536; all classes transmitted',
      'validation':'descriptive only, no tuning, no arm selection or refit',
      'test':'once after model freeze and exact geometry-only fresh-process replay',
      'subgroups':['all','G0','G1','G2','G3','G3_K2','G3_K3','G3_K4plus'],'minimum_subgroup_slots':100,
      'storage_candidates':STORAGES,'storage_selection':'shortest independently for each arm; listed order ties',
      'metadata':'same complete prior dry metadata envelope for comparability; geometry-only replay uses reduced JSON; model rule id differs',
      'forecast':'PREDICTED gross=1048576*(CE_Geometry4-CE_Count6)/8; net=gross-(side_Count6-side_Geometry4)',
      'GO_per_pair':'correctness PASS; strictly positive gains all/G3 for every seed/channel; every seed net>max(4096,0.2*max(delta_side,0)); independent-checkpoint validation recommended only, no novelty claim',
      'B_independent':'A NO-GO does not cancel Mean8 bitstream experiment B',
      'no_entropy_coding':True,'no_new_quantization':True,'no_training':True,
      'python':sys.version,'numpy':np.__version__}
    write_json(run/'PREREGISTERED_PROTOCOL.json',protocol)
    for pair in PAIRS:
        folder=run/pair;folder.mkdir();meta=read(DIAG/pair/'decoder_bundle/decoder_metadata.json')
        write_json(folder/'geometry-metadata.json',specification(meta))
        for seed in (0,1,2):
            source=OLD/pair/f'splits_seed{seed}.npz';target=folder/source.name
            with source.open('rb') as f,target.open('xb') as g:shutil.copyfileobj(f,g)
            assert sha(source)==sha(target)
            with np.load(target) as z:
                expected=split_slots(524288,seed)
                assert all(np.array_equal(z[k],expected[k]) for k in expected)
                assert np.array_equal(np.sort(np.concatenate([z[k] for k in expected])),np.arange(524288))
    write_json(run/'input-validation.json',{'status':'PASS','protected_files':len(protected),'splits_exact':True,
          'protocol_sha256':sha(run/'PREREGISTERED_PROTOCOL.json'),**timing(t,c)})
    from . import test_geometry
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_geometry))
    with (run/'synthetic-tests.log').open('x',encoding='utf-8') as f:f.write(log.getvalue())
    write_json(run/'synthetic-tests.json',{'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun})
    assert result.wasSuccessful()
    pilot=[]
    for pair in PAIRS:
        spec=read(run/pair/'geometry-metadata.json');t1=time.perf_counter();c1=time.process_time()
        compute_geometry(spec,vertex_limit=65536);total=int(np.prod(spec['fine']['lookup_resolution']))
        pilot.append({'pair':pair,'vertices':65536,'total_vertices':total,**timing(t1,c1)})
    estimate=3*sum(max(r['cpu_seconds'],r['wall_seconds'])*r['total_vertices']/65536 for r in pilot)
    write_json(run/'pilot.json',{'status':'GO','geometry_projection_cpu_seconds':estimate,'conservative_entire_study_cpu_seconds':180,
        'projected_peak_mib':256,'geometry_pilots':pilot,'GPU_used':False,'reason':'integer CPU geometry <seconds; GPU startup/transfer not justified'})
    print(json.dumps({'stage':'prepare','status':'PASS','protected':len(protected),'pilot_seconds':estimate}))

def fit(run):
    assert read(run/'pilot.json')['status']=='GO';t=time.perf_counter();c=time.process_time();sizes=[];vals=[];geometry_records=[]
    for pair in PAIRS:
        folder=run/pair
        with np.load(DIAG/pair/'contexts.npz') as z:
            ctx={k:z[k] for k in ('slot_index','nominal_count','point_count','geometry')}
        q=np.load(DIAG/pair/'fine_symbols.npy',allow_pickle=False);assert q.shape==(524288,2) and q.dtype==np.uint8
        assert np.array_equal(ctx['slot_index'],np.arange(len(q)))
        classes={'Count6':count6_classes(ctx['nominal_count'],ctx['point_count']),
                 'Geometry4':geometry4_classes(ctx['nominal_count'],ctx['point_count'])}
        assert np.array_equal(classes['Geometry4'][:,0],ctx['geometry'])
        save_npz(folder/'expected-classes.npz',classes)
        geometry_records.append({'pair':pair,'allocated':len(q),'Count6_histogram':np.bincount(classes['Count6'][:,0],minlength=6).tolist(),
            'nominal_count_sum':int(ctx['nominal_count'].sum()),'point_count_sum':int(ctx['point_count'].sum()),
            'classes_sha256':{k:array_sha(v) for k,v in classes.items()}})
        meta=read(DIAG/pair/'decoder_bundle/decoder_metadata.json')
        metadata={'decoder':meta,'channels':2,'alphabet':256,'mass_precision':16,
                  'runtime':{'python':'3.12.14','numpy':'1.26.4'},'slot_order':'ascending local slot, channel major for prospective coding',
                  'coarse_payload':'shared prerequisite, not included in dry model bytes'}
        for seed in (0,1,2):
            with np.load(folder/f'splits_seed{seed}.npz') as z:split={k:z[k] for k in z.files}
            for name,C in ARMS.items():
                d=folder/f'seed{seed}_{name}';d.mkdir();cl=classes[name]
                counts,masses=fit_masses(q,cl,split['train'],C)
                # Verify former Geometry4 model and validation exactly, not a newly tuned baseline.
                if name=='Geometry4':
                    with np.load(OLD/pair/f'seed{seed}_Geometry4/fitted.npz') as old:
                        assert np.array_equal(masses,old['masses']) and np.array_equal(counts,old['train_counts'])
                save_npz(d/'fitted.npz',{'masses':masses,'train_counts':counts})
                # Same prior serializer contract; Count6 geometry rule is public and versioned.
                spec={'name':name,'C':C,'rule_version':1,'searchsorted':'right','quantile_method':'linear',
                     'fallback':'G0class0_G1class1','arithmetic':meta['arithmetic']}
                thresholds={'primary':np.empty((2,0),np.float64),'std':np.empty((2,0),np.float64)}
                write_json(d/'spec.json',spec)
                for storage in STORAGES:
                    blob=serialize(masses,thresholds,spec,metadata,storage);a,b,cc,dd=deserialize(blob)
                    assert np.array_equal(a,masses) and cc==spec and dd==metadata
                    assert all(np.array_equal(b[k],thresholds[k]) for k in b)
                    with (d/f'{storage}.model').open('xb') as f:f.write(blob)
                    assert (d/f'{storage}.model').stat().st_size==len(blob)
                    sizes.append({'pair':pair,'seed':seed,'model':name,'storage':storage,**section_sizes(blob),'roundtrip':'PASS'})
                val=losses(q,cl,masses,split['validation'])
                vals.append({'pair':pair,'seed':seed,'model':name,'CE':float(val.mean()),'channel0':float(val[:,0].mean()),'channel1':float(val[:,1].mean()),
                             'classes_train':[np.bincount(cl[split['train'],ch],minlength=C).tolist() for ch in (0,1)]})
        del ctx,q,classes;gc.collect()
    write_json(run/'geometry-summary.json',geometry_records);write_json(run/'model-sizes.json',sizes);csv_out(run/'model-sizes.csv',sizes)
    write_json(run/'validation-scores.json',vals)
    frozen={p.relative_to(run).as_posix():sha(p) for p in run.rglob('*') if p.is_file()}
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in Path(__file__).parent.glob('*.py')}
    write_json(run/'MODEL_FREEZE.json',{'status':'PASS','test_evaluated':False,'frozen_artifacts':frozen,'source_sha256':sources,**timing(t,c)})
    print(json.dumps({'stage':'fit','status':'PASS','models':len(vals),'roundtrips':len(sizes),**timing(t,c)}))

def replay(run):
    records=[]
    for pair in PAIRS:
        folder=run/pair;out=folder/'decoder_replay'
        cmd=[sys.executable,'-m','research.experiment_bench.multiplicity.replay','--spec',str(folder/'geometry-metadata.json'),'--output',str(out)]
        t=time.perf_counter();cp=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        with (folder/'replay.log').open('x',encoding='utf-8') as f:f.write(cp.stdout+cp.stderr)
        if cp.returncode:raise RuntimeError(cp.stdout+cp.stderr)
        cold=time.perf_counter()-t
        audit=read(out/'read-audit.json');assert audit['status']=='PASS'
        with np.load(out/'geometry_classes.npz') as z,np.load(folder/'expected-classes.npz') as e,np.load(DIAG/pair/'contexts.npz') as old:
            for key in ARMS:assert np.array_equal(z[key],e[key])
            for key in ('slot_index','nominal_count','point_count'):assert np.array_equal(z[key],old[key])
            assert len(np.unique(z['slot_index']))==524288
        forbidden=[DIAG/pair/'fine_symbols.npy',DIAG/pair/'contexts.npz',DIAG/pair/'decoder_bundle/coarse_symbols.npy',
            ROOT/'outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth',
            ROOT/'research/experiment_bench/reference-study/table-8/xyz_encoding.u8.bin',folder/'seed0_Count6/fitted.npz']
        cmd[cmd.index('--output')+1]=str(folder/'negative_read_probes');cmd+=['--probe',*[str(p) for p in forbidden]]
        cp=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        if cp.returncode:raise RuntimeError(cp.stdout+cp.stderr)
        records.append({'pair':pair,'exact_classes':True,'exact_counts':True,'rows':524288,'channels':2,'cold_wall_seconds':cold,**audit})
    write_json(run/'replay-validation.json',{'status':'PASS','records':records,'negative_probes_per_pair':6})
    print(json.dumps({'stage':'replay','status':'PASS'}))

def test(run):
    assert read(run/'replay-validation.json')['status']=='PASS';freeze=read(run/'MODEL_FREEZE.json')
    for p,h in freeze['frozen_artifacts'].items():assert sha(run/p)==h,p
    for p,h in freeze['source_sha256'].items():assert sha(ROOT/p)==h,p
    write_json(run/'TEST_EVALUATION_STARTED.json',{'once_only':True,'freeze_sha256':sha(run/'MODEL_FREEZE.json')})
    t=time.perf_counter();c=time.process_time();scores=[];gains=[];forecasts=[];sizes=read(run/'model-sizes.json')
    for pair in PAIRS:
        with np.load(DIAG/pair/'contexts.npz') as z:ctx={k:z[k] for k in ('geometry','point_count')}
        q=np.load(DIAG/pair/'fine_symbols.npy')
        with np.load(run/pair/'expected-classes.npz') as z:classes={k:z[k] for k in ARMS}
        for seed in (0,1,2):
            with np.load(run/pair/f'splits_seed{seed}.npz') as z:rows=z['test']
            masks=strata(ctx,rows);costs={}
            for name in ARMS:
                with np.load(run/pair/f'seed{seed}_{name}/fitted.npz') as z:m=z['masses']
                costs[name]=losses(q,classes[name],m,rows)
                for group,mask in masks.items():
                    for channel in ('both','0','1'):
                        a=costs[name][mask] if channel=='both' else costs[name][mask,int(channel)]
                        scores.append({'pair':pair,'seed':seed,'model':name,'stratum':group,'channel':channel,'slots':int(mask.sum()),
                            'CE':float(a.mean()) if a.size else None,'sufficient':int(mask.sum())>=100})
            for group,mask in masks.items():
                for channel in ('both','0','1'):
                    a=(costs['Geometry4']-costs['Count6'])[mask]
                    a=a.mean(axis=1) if channel=='both' else a[:,int(channel)]
                    gain=float(a.mean()) if a.size else None;se=float(a.std(ddof=1)/np.sqrt(len(a))) if len(a)>1 else None
                    gains.append({'pair':pair,'seed':seed,'stratum':group,'channel':channel,'slots':len(a),
                        'gain_bits_per_symbol':gain,'paired_SE_descriptive':se,'sufficient':len(a)>=100})
            save_npz(run/pair/f'test_losses_seed{seed}.npz',{'slot_index':rows,**costs})
            best={arm:min([v for v in sizes if v['pair']==pair and v['seed']==seed and v['model']==arm],key=lambda v:(v['total'],STORAGES.index(v['storage']))) for arm in ARMS}
            b,a=best['Geometry4'],best['Count6'];delta=a['total']-b['total'];gain=float((costs['Geometry4']-costs['Count6']).mean());gross=1048576*gain/8
            forecasts.append({'pair':pair,'seed':seed,'label':'PREDICTED','delta_CE':gain,'gross_bytes':gross,'delta_side_bytes':delta,
                'net_bytes':gross-delta,'margin_bytes':max(4096,.2*max(delta,0)),'margin_pass':gross-delta>max(4096,.2*max(delta,0)),
                'baseline_model_bytes':b['probability_masses'],'candidate_model_bytes':a['probability_masses'],
                'baseline_side_bytes':b['total'],'candidate_side_bytes':a['total'],'baseline_storage':b['storage'],'candidate_storage':a['storage'],
                'delta_metadata_bytes':(a['total']-a['probability_masses'])-(b['total']-b['probability_masses']),'actual_entropy_bytes':None})
    for filename,data in [('test-scores',scores),('paired-differences',gains),('predicted-net',forecasts)]:
        write_json(run/(filename+'.json'),data);csv_out(run/(filename+'.csv'),data)
    decisions={}
    for pair in PAIRS:
        gain_checks=[r for r in gains if r['pair']==pair and r['stratum'] in ('all','G3') and r['channel'] in ('0','1')]
        fs=[r for r in forecasts if r['pair']==pair];go=all(r['gain_bits_per_symbol']>0 for r in gain_checks) and all(r['margin_pass'] for r in fs)
        decisions[pair]={'decision':'GO' if go else 'NO-GO','nonpositive_gain_checks':sum(r['gain_bits_per_symbol']<=0 for r in gain_checks),
            'margin_pass_seeds':sum(r['margin_pass'] for r in fs),'mean_delta_CE':float(np.mean([r['delta_CE'] for r in fs])),
            'mean_predicted_net_bytes':float(np.mean([r['net_bytes'] for r in fs]))}
    write_json(run/'decision.json',{'correctness':'PASS','pairs':decisions,'scope':'exploratory forecast only, not actual coding or independent confirmation',
        'Count6_bitstream_control_L5':decisions['L4_to_L5']['decision']=='GO','B_Mean8_continues':True,**timing(t,c)})
    print(json.dumps({'stage':'test','decisions':decisions,**timing(t,c)}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['prepare','fit','replay','test']);ap.add_argument('--run',required=True);a=ap.parse_args()
    globals()[a.stage](Path(a.run).resolve())
