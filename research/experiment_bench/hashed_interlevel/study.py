"""Frozen-input stages 2–3, train/validation freeze then one test evaluation."""
import argparse
import csv
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from research.hashgrid_analysis.hashed_context.core import ROOT, sha, ARITHMETIC
from research.hashgrid_analysis.hashed_context.runtime import write_json,save_npz,peak_rss_mib
from .core import ARMS,split_slots,fit_spec,classify,fit_masses,losses,strata

OLD=ROOT/'research/hashed_context_diagnostic_20261013_01'
PAIRS=('L4_to_L5','L5_to_L6')
STORAGES=('dense_u32','packed_u16','sparse_default_u16')

def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def array_sha(x):
    return hashlib.sha256(x.dtype.str.encode()+str(x.shape).encode()+np.ascontiguousarray(x).tobytes()).hexdigest()
def csv_out(path, records):
    with Path(path).open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)

def prepare(run):
    run.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    protected={}
    def check(path,expected):
        assert sha(path)==expected, str(path)
        protected[path.relative_to(ROOT).as_posix()]=expected
    old_final=read(OLD/'final-validation.json');assert old_final['status']=='PASS'
    for name,digest in read(OLD/'protected-input-hashes.json').items(): check(ROOT/name,digest)
    for name,digest in old_final['artifact_hashes'].items(): check(OLD/name,digest)
    for name,info in read(OLD/'source-hashes.json')['effective_sources'].items():
        check(ROOT/name,info['sha256']);check(OLD/info['snapshot'],info['sha256'])
    for name in ('final-validation.json','source-hashes.json','protected-input-hashes.json'):
        path=OLD/name;protected[path.relative_to(ROOT).as_posix()]=sha(path)
    for name in ('context-validation.json','synthetic-tests.json','example_verification/validation.json',
                 'integrity_checks/validation.json','gpu_checks/cross-cpu-parity.json'):
        assert read(OLD/name)['status']=='PASS'
    write_json(run/'protected-input-hashes.json',protected)
    protocol={'version':1,'phase':'2-3','created_before_fitting_and_test':True,
        'pairs':PAIRS,'models':ARMS,'seeds':[0,1,2],'split':'PCG64(seed).permutation slots; floor(.20*N) test first, floor(.16*N) validation next, remainder train; sorted within each',
        'train_slots':335546,'validation_slots':83886,'test_slots':104857,
        'split_rounding_note':'Actual counts asserted from split; train is remainder.',
        'quantiles':'numpy.quantile method=linear, float64, train G2+G3 per channel only',
        'tie_rule':'retain duplicate edges, searchsorted side=right, intervals [-inf,e0), [e0,e1),..., [elast,inf)',
        'std_threshold':'one unconditional median of Std on active train G2+G3 per channel, no per-mean-bin fit',
        'classes':'G0=0 G1=1, active=2+bin8; Mean4=2+bin4; Mean4Std2=2+2*bin4(mean)+bin2(std); Geometry4=g; IID=0',
        'empty_class':'uniform 256 integer masses; all classes transmitted, no omission',
        'mass_rule':'existing models.frequencies: Laplace alpha1, minimum1, stable largest remainder, sum65536',
        'cdf':'strict positive masses and cumulative uint32 CDF; p=mass/65536, same input convention as existing entropy.encode_indexed; coder not imported',
        'validation_selection':'minimum aggregate validation CE among six fixed arms; ties in declared arm order; no refit or hyperparameter tuning; all six test arms prespecified',
        'test':'one evaluation after model+validation freeze and fresh decoder exact class replay; no post-test changes',
        'strata':['all','G0','G1','G2','G3','G3_K2','G3_K3','G3_K4plus'],
        'subgroup_min_slots':100,'subgroups':'K groups descriptive/exploratory; no new fitted classes',
        'paired_intervals':'normal mean +/-1.96*sampleSE of paired slot-average losses; descriptive conditional-on-fit, spatial dependence not corrected; no pooling seeds as independent',
        'storage_candidates':STORAGES,'storage_selection':'smallest measured exact model envelope, independently per arm; stable listed-order tie',
        'forecast':'PREDICTED only: N_full=524288*2 scalar symbols; gross=N_full*(CE_base-CE_candidate)/8; net=gross-(side_candidate-side_base)',
        'GO':'all correctness PASS; Mean4Std2 positive paired gains every seed/channel on both pairs in all and G3 vs Geometry4,Canonical8,Mean8; G3 gain also positive vsMean4; perpair seed aggregate gross>delta_side+max(4096,.2*delta_side) vsGeometry4,Canonical8,Mean8',
        'arithmetic':ARITHMETIC,'python':sys.version,'numpy':np.__version__,
        'cost_forecast':{'cpu_seconds_conservative':180,'peak_additional_mib_conservative':512,
                         'basis':'2x524288 saved contexts, 36 small histogram models, 2 required fresh coarse-only replays; sequential bounded arrays, no slot x256 PMF'},
        'no_new_quantization':True,'actual_entropy_payload':False,'no_training':True}
    actual=split_slots(524288,0)
    for key in ('train','validation','test'):protocol[key+'_slots']=len(actual[key])
    write_json(run/'PREREGISTERED_PROTOCOL.json',protocol)
    write_json(run/'input-validation.json',{'status':'PASS','protected_files':len(protected),
        'seconds':time.perf_counter()-started,'old_final_sha256':sha(OLD/'final-validation.json'),
        'protocol_sha256':sha(run/'PREREGISTERED_PROTOCOL.json')})
    print(json.dumps({'prepared':str(run),'protected':len(protected),'protocol_sha256':sha(run/'PREREGISTERED_PROTOCOL.json')}))

def fit(run):
    from .dry_model import serialize,deserialize,section_sizes
    assert read(run/'input-validation.json')['status']=='PASS'
    assert not (run/'MODEL_FREEZE.json').exists()
    started=time.perf_counter();cpu=time.process_time();sizes=[];scores=[];selections=[];splits_meta=[]
    for pair in PAIRS:
        folder=run/pair;folder.mkdir(exist_ok=False)
        with np.load(OLD/pair/'contexts.npz',allow_pickle=False) as z: ctx={k:z[k] for k in z.files}
        q=np.load(OLD/pair/'fine_symbols.npy',allow_pickle=False);assert q.shape==(524288,2) and q.dtype==np.uint8
        assert np.array_equal(ctx['slot_index'],np.arange(len(q)))
        meta=read(OLD/pair/'decoder_bundle/decoder_metadata.json')
        # Same public geometry/coarse prerequisite contract in each envelope; no host paths or fitting counts.
        metadata={'decoder':meta,'channels':2,'alphabet':256,'mass_precision':16,
                  'runtime':{'python':'3.12.14','numpy':'1.26.4'},'slot_order':'ascending local slot, channel major for prospective coding',
                  'coarse_payload':'shared prerequisite, not included in dry model bytes'}
        specs=[]
        for seed in (0,1,2):
            split=split_slots(len(q),seed)
            assert np.array_equal(np.sort(np.concatenate(list(split.values()))),np.arange(len(q)))
            save_npz(folder/f'splits_seed{seed}.npz',split)
            splits_meta.append({'pair':pair,'seed':seed,'file':f'{pair}/splits_seed{seed}.npz',
                                'sha256':sha(folder/f'splits_seed{seed}.npz'),'counts':{k:len(v) for k,v in split.items()},
                                'arrays_sha256':{k:array_sha(v) for k,v in split.items()}})
            seed_scores=[]
            for name,C in ARMS.items():
                model_id=f'seed{seed}_{name}';d=folder/model_id;d.mkdir()
                spec=fit_spec(ctx,split['train'],name);classes=classify(ctx,spec)
                counts,masses=fit_masses(q,classes,split['train'],C)
                write_json(d/'spec.json',spec);save_npz(d/'fitted.npz',{'masses':masses,'train_counts':counts})
                save_npz(d/'expected-classes.npz',{'class_ids':classes})
                specs.append({'id':model_id,'spec':spec})
                thresholds={k:np.asarray(v,np.float64) for k,v in spec['edges'].items()}
                transport_spec={k:v for k,v in spec.items() if k!='edges'}
                transport_spec.update({'rule_version':1,'searchsorted':'right','quantile_method':'linear',
                                       'fallback':'G0class0_G1class1','arithmetic':ARITHMETIC})
                for storage in STORAGES:
                    data=serialize(masses,thresholds,transport_spec,metadata,storage)
                    restored,t,s,m=deserialize(data)
                    assert np.array_equal(restored,masses) and s==transport_spec and m==metadata
                    assert all(t[k].dtype==thresholds[k].dtype and t[k].shape==thresholds[k].shape and t[k].tobytes()==thresholds[k].tobytes() for k in t)
                    with (d/f'{storage}.model').open('xb') as f:f.write(data)
                    rec={'pair':pair,'seed':seed,'model':name,'storage':storage,**section_sizes(data),'roundtrip':'PASS'}
                    sizes.append(rec)
                # Class replay uses transmitted and exactly roundtripped thresholds, no probabilities needed.
                specs[-1]['spec']['edges']={k:v.tolist() for k,v in t.items()}
                val_loss=losses(q,classes,masses,split['validation'])
                ce=float(val_loss.mean());seed_scores.append((ce,name))
                scores.append({'pair':pair,'seed':seed,'model':name,'CE':ce,
                    'channel0':float(val_loss[:,0].mean()),'channel1':float(val_loss[:,1].mean()),
                    'occupied_classes_train':[int(np.count_nonzero(counts[ch].sum(axis=1))) for ch in range(2)],
                    'occupied_classes_all':[int(len(np.unique(classes[:,ch]))) for ch in range(2)],
                    'class_sha256':array_sha(classes),
                    'class_counts_train':counts.sum(axis=2).tolist(),
                    'class_counts_all':[np.bincount(classes[:,ch],minlength=C).tolist() for ch in range(2)]})
            winner=min(seed_scores,key=lambda x:(x[0],list(ARMS).index(x[1])))
            selections.append({'pair':pair,'seed':seed,'selected_by_validation':winner[1],'validation_CE':winner[0]})
        write_json(folder/'decoder-specs.json',specs)
        del ctx,q;gc.collect()
    write_json(run/'splits.json',splits_meta);write_json(run/'validation-scores.json',scores)
    write_json(run/'model-sizes.json',sizes);csv_out(run/'model-sizes.csv',sizes)
    protected={p.relative_to(run).as_posix():sha(p) for p in run.rglob('*') if p.is_file()}
    source={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'research/experiment_bench/hashed_interlevel').glob('*.py')
            if p.name not in ('report.py','finalize.py')}
    write_json(run/'MODEL_FREEZE.json',{'status':'PASS','test_evaluated':False,'validation_selections':selections,
        'frozen_artifacts':protected,'source_sha256':source,'protocol_sha256':sha(run/'PREREGISTERED_PROTOCOL.json'),
        'wall_seconds':time.perf_counter()-started,'cpu_seconds':time.process_time()-cpu,'peak_rss_mib':peak_rss_mib()})
    print(json.dumps({'fit':'PASS','models':len(scores),'transport_roundtrips':len(sizes),'seconds':time.perf_counter()-started}))

def replay(run):
    freeze=read(run/'MODEL_FREEZE.json');assert freeze['status']=='PASS' and not freeze['test_evaluated']
    results=[]
    for pair in PAIRS:
        out=run/pair/'decoder_replay'
        cmd=[sys.executable,'-m','research.experiment_bench.hashed_interlevel.replay','--bundle',str(OLD/pair/'decoder_bundle'),
             '--specs',str(run/pair/'decoder-specs.json'),'--output',str(out)]
        completed=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        with (run/pair/'replay.log').open('x',encoding='utf-8') as f:f.write(completed.stdout+completed.stderr)
        if completed.returncode:raise RuntimeError(completed.stdout+completed.stderr)
        audit=read(out/'read-audit.json');assert audit['status']=='PASS'
        with np.load(out/'class_ids.npz') as decoded:
            for item in read(run/pair/'decoder-specs.json'):
                with np.load(run/pair/item['id']/'expected-classes.npz') as expected:
                    a=expected['class_ids'];b=decoded[item['id']]
                    assert a.shape==(524288,2) and a.dtype==b.dtype and a.tobytes()==b.tobytes()
                results.append({'pair':pair,'model_id':item['id'],'rows':len(a),'channels':2,'exact':True,'sha256':array_sha(a)})
        forbidden=[OLD/pair/'fine_symbols.npy',OLD/pair/'contexts.npz',ROOT/'outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth',
                   ROOT/'research/experiment_bench/reference-study/table-8/xyz_encoding.u8.bin']
        cmd[cmd.index('--output')+1]=str(run/pair/'negative_read_probes');cmd+=['--probe-forbidden',*[str(p) for p in forbidden]]
        completed=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        if completed.returncode:raise RuntimeError(completed.stdout+completed.stderr)
    write_json(run/'replay-validation.json',{'status':'PASS','all_models':results,'test_evaluated':False})
    print(json.dumps({'replay':'PASS','model_arrays':len(results)}))

def test(run):
    assert read(run/'replay-validation.json')['status']=='PASS'
    assert not (run/'TEST_EVALUATION_STARTED.json').exists(), 'Test can only be evaluated once'
    freeze=read(run/'MODEL_FREEZE.json')
    for name,h in freeze['frozen_artifacts'].items():assert sha(run/name)==h,name
    for name,h in freeze['source_sha256'].items():assert sha(ROOT/name)==h,name
    write_json(run/'TEST_EVALUATION_STARTED.json',{'once_only':True,'freeze_sha256':sha(run/'MODEL_FREEZE.json')})
    start=time.perf_counter();cpu=time.process_time();records=[];paired=[];forecast=[]
    sizes=read(run/'model-sizes.json')
    for pair in PAIRS:
        with np.load(OLD/pair/'contexts.npz') as z:ctx={k:z[k] for k in ('geometry','point_count')}
        q=np.load(OLD/pair/'fine_symbols.npy')
        for seed in (0,1,2):
            with np.load(run/pair/f'splits_seed{seed}.npz') as z:indices=z['test']
            masks=strata(ctx,indices);costs={}
            for name in ARMS:
                d=run/pair/f'seed{seed}_{name}'
                with np.load(d/'expected-classes.npz') as z:classes=z['class_ids']
                with np.load(d/'fitted.npz') as z:masses=z['masses']
                costs[name]=losses(q,classes,masses,indices)
                for group,mask in masks.items():
                    n=int(mask.sum())
                    for channel in ('both','0','1'):
                        x=costs[name][mask] if channel=='both' else costs[name][mask,int(channel)]
                        records.append({'pair':pair,'seed':seed,'model':name,'stratum':group,'channel':channel,
                            'slots':n,'symbols':int(x.size),'CE':float(x.mean()) if n else None,
                            'subgroup_sufficient':n>=100,'exploratory':group.startswith('G3_K')})
            save_npz(run/pair/f'test_losses_seed{seed}.npz',{'slot_index':indices,**costs})
            for candidate,base in [('Canonical8','Geometry4'),('Mean8','Canonical8'),('Mean8','Geometry4'),
                ('Mean4Std2','IID'),('Mean4Std2','Geometry4'),('Mean4Std2','Canonical8'),('Mean4Std2','Mean8'),('Mean4Std2','Mean4')]:
                for group,mask in masks.items():
                    n=int(mask.sum())
                    for channel in ('both','0','1'):
                        diff=(costs[base]-costs[candidate])[mask]
                        diff=diff.mean(axis=1) if channel=='both' else diff[:,int(channel)]
                        mean=float(diff.mean()) if n else None;se=float(diff.std(ddof=1)/np.sqrt(n)) if n>1 else None
                        paired.append({'pair':pair,'seed':seed,'candidate':candidate,'baseline':base,'stratum':group,'channel':channel,
                            'slots':n,'gain_bits_per_symbol':mean,'paired_SE_descriptive':se,
                            'conditional_low':mean-1.96*se if se is not None else None,'conditional_high':mean+1.96*se if se is not None else None,
                            'subgroup_sufficient':n>=100,'exploratory':group.startswith('G3_K')})
                def best(arm):
                    z=[s for s in sizes if s['pair']==pair and s['seed']==seed and s['model']==arm]
                    return min(z,key=lambda s:(s['total'],STORAGES.index(s['storage'])))
                a,b=best(candidate),best(base)
                gain=float((costs[base]-costs[candidate]).mean());extra=a['total']-b['total'];gross=len(q)*2*gain/8
                margin=max(4096,.2*extra)
                forecast.append({'pair':pair,'seed':seed,'candidate':candidate,'baseline':base,'label':'PREDICTED',
                    'N_full_symbols':len(q)*2,'delta_CE_test':gain,'candidate_storage':a['storage'],'baseline_storage':b['storage'],
                    'candidate_side_bytes':a['total'],'baseline_side_bytes':b['total'],'delta_side_bytes':extra,
                    'gross_payload_saving_bytes':gross,'net_saving_bytes':gross-extra,'safety_margin_bytes':margin,
                    'margin_pass':bool(gross>extra+margin),'actual_entropy_stream_bytes':None})
        del q,ctx;gc.collect()
    write_json(run/'test-scores.json',records);csv_out(run/'test-scores.csv',records)
    write_json(run/'paired-differences.json',paired);csv_out(run/'paired-differences.csv',paired)
    write_json(run/'predicted-net.json',forecast);csv_out(run/'predicted-net.csv',forecast)
    gain_tests=[p for p in paired if p['candidate']=='Mean4Std2' and p['baseline'] in ('Geometry4','Canonical8','Mean8')
                and p['stratum'] in ('all','G3') and p['channel'] in ('0','1')]
    std_tests=[p for p in paired if p['candidate']=='Mean4Std2' and p['baseline']=='Mean4' and p['stratum']=='G3' and p['channel'] in ('0','1')]
    cost_tests=[p for p in forecast if p['candidate']=='Mean4Std2' and p['baseline'] in ('Geometry4','Canonical8','Mean8')]
    fails=[p for p in gain_tests+std_tests if p['gain_bits_per_symbol'] is None or p['gain_bits_per_symbol']<=0]
    decision={'decision':'GO' if not fails and all(p['margin_pass'] for p in cost_tests) else 'NO-GO',
        'correctness':'PASS','gain_checks':len(gain_tests),'withinG3_vsMean4_checks':len(std_tests),
        'nonpositive_gain_checks':len(fails),'cost_checks':len(cost_tests),'cost_failures':sum(not p['margin_pass'] for p in cost_tests),
        'failed_gain_checks':fails,'failed_cost_checks':[p for p in cost_tests if not p['margin_pass']],
        'scope':'Only fixed Mean4Std2 H1 on one checkpoint, table8, two pairs; not universal absence of Std information',
        'test_evaluations':1,'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu,'peak_rss_mib':peak_rss_mib(),
        'actual_entropy_coding':False}
    write_json(run/'decision.json',decision)
    print(json.dumps({k:decision[k] for k in ('decision','nonpositive_gain_checks','cost_failures','wall_seconds','peak_rss_mib')}))

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','fit','replay','test']);p.add_argument('--run',required=True,type=Path)
    args=p.parse_args();globals()[args.stage](args.run.resolve())
if __name__=='__main__':main()
