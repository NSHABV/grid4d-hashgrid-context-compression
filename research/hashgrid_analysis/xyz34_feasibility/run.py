"""Fixed CPU diagnostic study; never calls an entropy encoder or a GPU."""
import argparse
import csv
import hashlib
import sys
import time
import unittest
from pathlib import Path
import numpy as np
from research.hashgrid_analysis.common import ROOT,read,write,digest,csv_write
from .core import MODELS,split_rows,fit_edges,classify,fit_histogram,costs,overhead,bootstrap_plan,gain_interval

def array_sha(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()

def inputs(folder):
    manifest=read(folder/'manifest.json');previous=read(folder/'validation.json');meta=read(folder/'decoder_bundle/decoder_metadata.json')
    assert previous['status']=='PASS' and all(r['status']=='PASS' for r in previous['checks'])
    assert manifest['scope']=='table' and manifest['rows']==205379 and manifest['in_bounds']==195112 and manifest['out_of_bounds']==10267
    assert digest(folder/'pairs.npz')==manifest['pair_sha256'] and digest(folder/'pairs.csv')==manifest['csv_sha256']
    pairs={k:v.copy() for k,v in np.load(folder/'pairs.npz',allow_pickle=False).items()};n=len(pairs['fine_slot_index'])
    np.testing.assert_array_equal(pairs['fine_slot_index'],np.arange(n));np.testing.assert_array_equal(pairs['fine_global_row_index'],np.arange(n)+125561)
    v=pairs['vertex_indices'];np.testing.assert_array_equal(v[:,0]+59*v[:,1]+59*59*v[:,2],np.arange(n))
    u=v.astype(np.float32)/np.asarray(meta['fine']['scale'],np.float32)
    np.testing.assert_array_equal(u,pairs['normalized_coordinates']);inside=((u>=0)&(u<=1)).all(axis=1)
    np.testing.assert_array_equal(inside,pairs['lookup_in_bounds']);np.testing.assert_array_equal(pairs['coarse_context'][~inside],0)
    replay=np.load(folder/'decoder-replay.npz',allow_pickle=False)
    np.testing.assert_array_equal(replay['coarse_context_gpu'],pairs['coarse_context'])
    audit=read(folder/'decoder-replay.audit.json');assert audit['status']=='PASS' and not audit['checkpoint_or_fine_payload_read']
    assert len(audit['allowed_artifact_reads'])==2
    assert digest(folder/'decoder_bundle/coarse_symbols.npy')==meta['coarse_symbols_sha256']
    study=ROOT/'research/experiment_bench/reference-study/table-8';g=read(study/'manifest.json')['grids']['xyz_encoding.embeddings']
    assert digest(study/g['payload']['file'])==g['payload']['sha256']
    saved=np.memmap(study/g['payload']['file'],dtype=np.uint8,mode='r',shape=tuple(g['shape']))
    np.testing.assert_array_equal(pairs['fine_symbols'],saved[125561:330940]);assert pairs['fine_symbols'].dtype==np.uint8
    assert array_sha(pairs['fine_symbols'])==manifest['fine_symbols_sha256']
    with (folder/'pairs.csv').open(encoding='utf-8') as f:
        for i,row in enumerate(csv.DictReader(f)):
            assert int(row['fine_slot_index'])==i
            assert [int(row['fine_symbol_0']),int(row['fine_symbol_1'])]==pairs['fine_symbols'][i].tolist()
            assert [float(row['coarse_context_0']),float(row['coarse_context_1'])]==pairs['coarse_context'][i].tolist()
        assert i+1==n
    hashes={str(f.relative_to(ROOT)):digest(f) for f in [folder/'pairs.npz',folder/'pairs.csv',folder/'manifest.json',folder/'validation.json',
        folder/'decoder_bundle/decoder_metadata.json',folder/'decoder_bundle/coarse_symbols.npy',folder/'decoder-replay.npz',folder/'decoder-replay.audit.json',study/'manifest.json',study/g['payload']['file']]}
    return pairs,manifest,hashes

def study(folder,out,seeds,kinds,bootstrap_reps):
    started=time.perf_counter();out.mkdir(parents=True,exist_ok=False)
    write(out/'config.json',{'input':str(folder),'output':str(out),'seeds':seeds,'splits':kinds,'bootstrap_reps':bootstrap_reps,
        'train_validation_test_fractions':[.64,.16,.20],'alpha':1,'class_counts':[4,8,16],'bins':['uniform','quantile'],
        'selection':'per-channel validation projected net bytes for each prespecified overhead scenario; final test never used to select',
        'primary_probability':'existing frequencies() minimum mass1, total65536; stored uint32 mass format',
        'tiny_class_train_threshold':100,'bootstrap':'conditional-on-fit cluster bootstrap, width=max(8,holdout-block-width); 95% percentile CI, no refitting',
        'scope':'L4 only; estimated rates, not actual bitstreams'})
    write(out/'manifest.json',{'status':'IN PROGRESS'});pairs,source,hashes=inputs(folder)
    n=len(pairs['fine_slot_index']);q=pairs['fine_symbols'];coarse=pairs['coarse_context'];inside=pairs['lookup_in_bounds'];v=pairs['vertex_indices']
    write(out/'input-validation.json',{'status':'PASS','rows':n,'in_bounds':int(inside.sum()),'out_of_bounds':int((~inside).sum()),
        'source_sha256':hashes,'coarse_context_source':'saved canonical decoder-available GPU float32; previous fresh-process replay exact',
        'GPU_indexing':'NOT RUN in this study; previous exhaustive PASS evidence reused','raw_float32_embeddings_read':False})
    rows=[];occupancy=[];overhead_rows=[];split_checks=[];selection=[];model_npz={};split_arrays={}
    for kind in kinds:
        for seed in seeds:
            tag=f'{kind}-seed{seed}';parts,groups=split_rows(v,seed,kind);train=parts['train'];val=parts['validation'];test=parts['test']
            repeat,again=split_rows(v,seed,kind)
            for key in parts:np.testing.assert_array_equal(parts[key],repeat[key]);split_arrays[tag+'_'+key]=parts[key]
            if kind!='random':
                sets=[set(groups[p]) for p in parts.values()];assert not (sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])
            split_checks.append({'split':kind,'seed':seed,'status':'PASS','train':len(train),'validation':len(val),'test':len(test),
                'train_sha256':array_sha(train),'validation_sha256':array_sha(val),'test_sha256':array_sha(test),
                'test_symbols_sha256':array_sha(q[test]),'spatial_groups_disjoint':kind!='random'})
            bootstrap_width=8 if kind=='random' else max(8,int(kind.split('-')[1]))
            plan=bootstrap_plan(v,test,10000+seed+sum(ord(c) for c in kind),bootstrap_reps,bootstrap_width)
            fitted={};cost_cache={}
            for channel in (0,1):
                target=q[:,channel]
                for name,method,k in MODELS:
                    model_id=name if method is None else method+'-'+name
                    prefix=f'{tag}__ch{channel}__{model_id}'
                    edges=None if method is None else fit_edges(coarse[:,channel],inside,train,k,method)
                    if edges is not None:
                        # Perturb every held-out context; fitted edges must remain bit-identical.
                        perturbed=coarse[:,channel].copy();perturbed[np.r_[val,test]]=np.float32(1e6)
                        np.testing.assert_array_equal(edges,fit_edges(perturbed,inside,train,k,method))
                        np.testing.assert_array_equal(edges,fit_edges(coarse[:,channel],inside,train,k,method))
                    classes,C=classify(coarse[:,channel],inside,name,k,edges)
                    if method is not None:assert np.all(classes[~inside]==k)
                    counts,masses,analytic,p,mi,interior_mi,weighted_mi=fit_histogram(target,classes,train,C)
                    model_npz[prefix+'_train_counts']=counts;model_npz[prefix+'_masses']=masses
                    model_npz[prefix+'_edges']=np.array([]) if edges is None else edges
                    h=overhead(masses,edges,name,k,method);baseinfo={'split':kind,'seed':seed,'model':name,'method':method or 'none','model_id':model_id,'channel':channel}
                    pred={partition:costs(target,classes,index,p) for partition,index in parts.items()}
                    analytic_test=costs(target,classes,test,analytic)
                    fitted[(channel,model_id)]={'counts':counts,'masses':masses,'edges':edges,'classes':classes,'overhead':h,'C':C,
                        'mi':mi,'interior_mi':interior_mi,'weighted_mi':weighted_mi,'prefix':prefix,'baseinfo':baseinfo,'analytic_test_bps':float(analytic_test.mean())}
                    cost_cache[(channel,model_id)]=pred
                    model_npz[prefix+'_test_cost_bits']=pred['test'];model_npz[prefix+'_validation_cost_bits']=pred['validation']
                    unconditional=(np.bincount(target[train],minlength=256)+1)/(len(train)+256)
                    for cls in range(C):
                        tr=int(counts[cls].sum());va=int(np.count_nonzero(classes[val]==cls));te=int(np.count_nonzero(classes[test]==cls))
                        dist=p[cls];middle=(dist+unconditional)/2
                        js=float(.5*np.sum(dist*np.log2(dist/middle))+.5*np.sum(unconditional*np.log2(unconditional/middle)))
                        occupancy.append({**baseinfo,'class':cls,'boundary_class':bool((name=='Boundary' and cls==1) or (method is not None and cls==k)),
                            'train_n':tr,'validation_n':va,'test_n':te,'empty_train':tr==0,'small_train':0<tr<100,
                            'tv_vs_training_iid':float(.5*np.abs(dist-unconditional).sum()),'js_bits_vs_training_iid':js,
                            'unique_bin_boundaries':0 if edges is None else len(np.unique(edges))})
                    assert counts.sum()==len(train) and np.isfinite(p).all() and np.all(p>0)
                    for scenario in ('dense_u32','packed_u16','sparse_default_u16','no_overhead'):
                        overhead_rows.append({**baseinfo,'scenario':scenario,'model_bytes':h[scenario],**h['components']})
            for channel in (0,1,'total'):
                for name,method,k in MODELS:
                    mid=name if method is None else method+'-'+name
                    channels=(0,1) if channel=='total' else (channel,)
                    # Per-row sum of both channel costs /2 reports bits per scalar symbol.
                    current=sum(cost_cache[(ch,mid)]['test'] for ch in channels)/len(channels)
                    baseline=sum(cost_cache[(ch,'IID')]['test'] for ch in channels)/len(channels)
                    boundary=sum(cost_cache[(ch,'Boundary')]['test'] for ch in channels)/len(channels)
                    gain_iid=baseline-current;gain_boundary=boundary-current
                    ci_iid=gain_interval(gain_iid,plan);ci_boundary=gain_interval(gain_boundary,plan)
                    entries=[fitted[(ch,mid)] for ch in channels];h={scenario:sum(e['overhead'][scenario] for e in entries) for scenario in ('dense_u32','packed_u16','sparse_default_u16','no_overhead')}
                    h_iid={s:sum(fitted[(ch,'IID')]['overhead'][s] for ch in channels) for s in h}
                    h_b={s:sum(fitted[(ch,'Boundary')]['overhead'][s] for ch in channels) for s in h}
                    record={'split':kind,'seed':seed,'model':name,'method':method or 'none','model_id':mid,'channel':channel,
                        'test_rows':len(test),'test_symbols':len(test)*len(channels),'heldout_bits_per_symbol':float(current.mean()),
                        'heldout_total_bits':float(current.sum()*len(channels)),'gain_vs_iid_bits_per_symbol':float(gain_iid.mean()),
                        'gain_vs_boundary_bits_per_symbol':float(gain_boundary.mean()),'gain_vs_iid_total_test_bits':float(gain_iid.sum()*len(channels)),
                        'gain_vs_boundary_total_test_bits':float(gain_boundary.sum()*len(channels)),
                        'gain_vs_iid_ci95_low':ci_iid[0],'gain_vs_iid_ci95_high':ci_iid[1],
                        'gain_vs_boundary_ci95_low':ci_boundary[0],'gain_vs_boundary_ci95_high':ci_boundary[1],
                        'bootstrap_blocks':plan[3],'bootstrap_reps':bootstrap_reps,'bootstrap_block_width':bootstrap_width,
                        'training_empirical_MI_bits':float(np.mean([e['mi'] for e in entries])),
                        'training_interior_MI_bits':float(np.mean([e['interior_mi'] for e in entries])),
                        'training_incremental_MI_given_bounds_bits':float(np.mean([e['weighted_mi'] for e in entries])),
                        'analytic_laplace_test_bps':float(np.mean([e['analytic_test_bps'] for e in entries])),
                        'primary_model_overhead_bytes':h['dense_u32'],'primary_extra_overhead_vs_iid_bytes':h['dense_u32']-h_iid['dense_u32'],
                        'primary_extra_overhead_vs_boundary_bytes':h['dense_u32']-h_b['dense_u32'],
                        'projected_payload_saving_vs_iid_bytes':float(gain_iid.mean()*n*len(channels)/8),
                        'projected_payload_saving_vs_boundary_bytes':float(gain_boundary.mean()*n*len(channels)/8),
                        'primary_estimated_net_vs_iid_bytes':float(gain_iid.mean()*n*len(channels)/8-(h['dense_u32']-h_iid['dense_u32'])),
                        'primary_estimated_net_vs_boundary_bytes':float(gain_boundary.mean()*n*len(channels)/8-(h['dense_u32']-h_b['dense_u32'])),
                        'break_even_vs_iid_bits_per_symbol':8*(h['dense_u32']-h_iid['dense_u32'])/(n*len(channels)),
                        'break_even_vs_boundary_bits_per_symbol':8*(h['dense_u32']-h_b['dense_u32'])/(n*len(channels)),
                        'actual_bitstream_bytes':None,'rate_type':'held-out prediction; full-L4 extrapolation estimated only',
                        'same_test_symbols_sha256':array_sha(q[test][:,list(channels)])}
                    for status,mask in (('in_bounds',inside[test]),('out_of_bounds',~inside[test])):
                        record[status+'_test_rows']=int(mask.sum())
                        record[status+'_bits_per_symbol']=float(current[mask].mean()) if mask.any() else None
                        record[status+'_gain_vs_boundary_bps']=float(gain_boundary[mask].mean()) if mask.any() else None
                    for scenario in h:
                        record[scenario+'_model_bytes']=h[scenario]
                        record[scenario+'_net_vs_iid_bytes']=record['projected_payload_saving_vs_iid_bytes']-(h[scenario]-h_iid[scenario])
                        record[scenario+'_net_vs_boundary_bytes']=record['projected_payload_saving_vs_boundary_bytes']-(h[scenario]-h_b[scenario])
                    assert abs(record['heldout_total_bits']-record['heldout_bits_per_symbol']*record['test_symbols'])<1e-6
                    rows.append(record)
            # Model selection is made only on validation costs for every prespecified storage scenario.
            for channel in (0,1):
                for scenario in ('dense_u32','packed_u16','sparse_default_u16'):
                    objective={mid:float(pred['validation'].mean()*n/8+fitted[(channel,mid)]['overhead'][scenario])
                        for (ch,mid),pred in cost_cache.items() if ch==channel}
                    chosen=min(objective,key=lambda key:(objective[key],key))
                    chosen_row=next(r for r in rows if r['split']==kind and r['seed']==seed and r['channel']==channel and r['model_id']==chosen)
                    selection.append({'split':kind,'seed':seed,'channel':channel,'scenario':scenario,'selected_model':chosen,'selection_partition':'validation',
                        'validation_projected_full_L4_payload_plus_model_bytes':objective[chosen],'all_validation_objectives':objective,
                        'test_gain_vs_iid_bps':chosen_row['gain_vs_iid_bits_per_symbol'],'test_gain_vs_boundary_bps':chosen_row['gain_vs_boundary_bits_per_symbol'],
                        'test_estimated_net_vs_iid_bytes':chosen_row[scenario+'_net_vs_iid_bytes'],
                        'test_estimated_net_vs_boundary_bytes':chosen_row[scenario+'_net_vs_boundary_bytes']})
            print('Evaluated',tag,'rows:',len(train),len(val),len(test),flush=True)
    np.savez_compressed(out/'fitted_histograms.npz',**model_npz);np.savez_compressed(out/'splits.npz',**split_arrays)
    csv_write(out/'per-split-results.csv',rows);csv_write(out/'class-occupancy.csv',occupancy);csv_write(out/'overhead-sensitivity.csv',overhead_rows)
    write(out/'split-validation.json',{'status':'PASS','splits':split_checks,'fine_slots_unique':True,'bins_train_only_perturbation_test':True,'same_test_targets_all_models':True})
    write(out/'model-selection.json',selection)
    summary=[]
    for kind in kinds:
        for channel in (0,1,'total'):
            for name,method,k in MODELS:
                mid=name if method is None else method+'-'+name;group=[r for r in rows if r['split']==kind and r['channel']==channel and r['model_id']==mid]
                s={'split':kind,'model':name,'method':method or 'none','model_id':mid,'channel':channel,'seeds':len(group)}
                fields=['heldout_bits_per_symbol','gain_vs_iid_bits_per_symbol','gain_vs_boundary_bits_per_symbol','heldout_total_bits',
                    'primary_model_overhead_bytes','primary_extra_overhead_vs_iid_bytes','primary_extra_overhead_vs_boundary_bytes',
                    'projected_payload_saving_vs_iid_bytes','projected_payload_saving_vs_boundary_bytes','primary_estimated_net_vs_iid_bytes','primary_estimated_net_vs_boundary_bytes',
                    'break_even_vs_iid_bits_per_symbol','break_even_vs_boundary_bits_per_symbol','training_empirical_MI_bits',
                    'training_incremental_MI_given_bounds_bits','analytic_laplace_test_bps']
                fields +=[scenario+'_net_vs_iid_bytes' for scenario in ('packed_u16','sparse_default_u16','no_overhead')]
                fields +=[scenario+'_net_vs_boundary_bytes' for scenario in ('packed_u16','sparse_default_u16','no_overhead')]
                for field in fields:
                    vals=[r[field] for r in group];s[field]=float(np.mean(vals));s[field+'_min']=float(min(vals));s[field+'_max']=float(max(vals));s[field+'_std']=float(np.std(vals,ddof=1))
                s['positive_incremental_gain_splits']=sum(r['gain_vs_boundary_bits_per_symbol']>0 for r in group)
                s['positive_primary_net_vs_boundary_splits']=sum(r['primary_estimated_net_vs_boundary_bytes']>0 for r in group)
                summary.append(s)
    csv_write(out/'summary.csv',summary)
    totals=[r for r in summary if r['channel']=='total' and r['method']!='none']
    # Prespecified practical criterion: positive incremental gain and net gain on every split;
    # clustered test CI lower bound positive in random and spatial regimes.
    promising=[];scenario_promising={scenario:[] for scenario in ('dense_u32','packed_u16','sparse_default_u16')}
    for mid in {r['model_id'] for r in totals}:
        entries=[r for r in rows if r['channel']=='total' and r['model_id']==mid]
        for scenario in scenario_promising:
            if all(r['gain_vs_boundary_ci95_low']>0 and r[scenario+'_net_vs_boundary_bytes']>0 and r[scenario+'_net_vs_iid_bytes']>0 for r in entries):scenario_promising[scenario].append(mid)
    promising=scenario_promising['dense_u32']
    stable_prediction=[mid for mid in {r['model_id'] for r in totals} if all(r['gain_vs_boundary_bits_per_symbol']>0 for r in rows if r['channel']=='total' and r['model_id']==mid)]
    verdict='PROMISING' if any(scenario_promising.values()) else ('WEAK / INCONCLUSIVE' if stable_prediction or any(r['gain_vs_boundary_bits_per_symbol']>0 for r in totals) else 'NOT PROMISING FOR THIS PAIR')
    result={'verdict':verdict,'checkpoint_sha256':source['checkpoint_sha256'],'quantization':'table-wise8','grid':'xyz','coarse_level':3,'fine_level':4,
        'rows':n,'in_bounds':int(inside.sum()),'out_of_bounds':int((~inside).sum()),'channels':2,'seeds':seeds,'split_regimes':kinds,
        'smoothing':'alpha1 then existing finite16-bit largest-remainder masses; analytical Laplace additionally reported',
        'rate_type':'estimated held-out predictive codelength and extrapolated full-L4 savings; actual_bitstream_bytes=null',
        'actual_bitstream_bytes':None,'scope':'only this L4 pair; no whole-scene compressed size prediction',
        'summary':summary,'per_split':rows,'validation_selected_models':selection,'stable_incremental_predictors':sorted(stable_prediction),
        'primary_overhead_promising_candidates':sorted(promising),'overhead_scenario_promising_candidates':{k:sorted(v) for k,v in scenario_promising.items()},'class_occupancy_file':'class-occupancy.csv',
        'uncertainty':'spatial bootstrap blocks width=max(8,holdout-block-width), conditional on fitted model; seeds are not independent scenes; no multiple-comparison significance claim',
        'input_hashes':hashes,'decision_rule':'PROMISING requires positive incremental CI lower bound and projected net gains vs both baselines across all 9 splits for at least one explicit feasible storage scenario; no winner chosen from final test'}
    write(out/'results.json',result)
    suite=unittest.defaultTestLoader.loadTestsFromName('research.hashgrid_analysis.xyz34_feasibility.tests')
    with (out/'tests.log').open('w',encoding='utf-8') as log:unit=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    assert unit.wasSuccessful()
    for path,expected in hashes.items():assert digest(ROOT/path)==expected
    checks=[{'test':name,'status':'PASS','input':input_name,'log':'validation.log'} for name,input_name in [
        ('all fine rows, target uint8, CSV/NPZ/source SHA integrity','input-validation.json'),
        ('decoder-available context + official OOB flag/zero, no raw embeddings','previous audited replay + saved pairs'),
        ('slot split coverage/disjointness/determinism, spatial groups disjoint','split-validation.json + splits.npz'),
        ('class bins fit training only, held-out perturbation invariant','fitted_histograms.npz'),
        ('probabilities normalized/strictly positive, empty classes uniform','fitted_histograms.npz'),
        ('all candidates score exactly same held-out uint8 targets','per-split-results.csv'),
        ('total bits = bits/symbol * N, overhead estimates distinct from actual','per-split-results.csv + overhead-sensitivity.csv'),
        ('validation-only selection; no final-test selection','model-selection.json'),
        ('input artifacts unchanged after analysis','input-validation.json')]]
    write(out/'validation.json',{'status':'PASS','unit_tests':{'tests':unit.testsRun,'failures':len(unit.failures),'errors':len(unit.errors)},'checks':checks,
        'reproducibility':'NOT RUN until separate repeated full CPU run','GPU_indexing':'NOT RUN; reused prior exhaustive PASS'})
    (out/'validation.log').write_text('\n'.join(r['status']+' '+r['test']+' input='+r['input'] for r in checks)+'\n',encoding='utf-8')
    write(out/'manifest.json',{'status':'COMPUTED','checkpoint_sha256':source['checkpoint_sha256'],'verdict':verdict,'seconds':time.perf_counter()-started,
        'environment':{'python':sys.version,'numpy':np.__version__,'GPU_used':False},'source_code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}})
    print(verdict,flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',default='research/interlevel_xyz34_results');parser.add_argument('--output',default='research/interlevel_xyz34_feasibility')
    parser.add_argument('--seeds',nargs='+',type=int,default=[0,1,2]);parser.add_argument('--splits',nargs='+',default=['random','block-8','block-16'])
    parser.add_argument('--bootstrap-reps',type=int,default=1000);args=parser.parse_args()
    folder=(ROOT/args.input).resolve();out=(ROOT/args.output).resolve()
    try:study(folder,out,args.seeds,args.splits,args.bootstrap_reps)
    except Exception:
        import traceback
        if out.exists():write(out/'failure.json',{'status':'FAIL','traceback':traceback.format_exc()})
        raise

if __name__=='__main__':main()
