"""Read existing research artifacts and compute measured/diagnostic data in pinned WSL env."""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
import numpy as np
import torch
from scipy.stats import rankdata
from PIL import Image
from research.grid4d.codec import KEYS,BUFFERS,_read_array,import_tables,load_checkpoint,validate_grid
from research.experiment_bench.cli import source_identity
from research.experiment_bench.entropy import parse,PREFIX
from research.experiment_bench.models import MODELS,context_class
from .common import ROOT,GRIDS,SHA,read,write,resolve,digest,csv_write
from .statistics import describe,histogram,entropy_counts,joint_metrics,pearson,sample_indices,joint_codes,conditional_error,average_ranks
from .mapping import slots,corners,lookup,vertex_sample,multiplicity

def selected_levels(config,meta):
    return [l for l in range(meta['levels']) if config['levels'] is None or l in config['levels']]

def gpu_mapping(config,states,runtime,out):
    from torch.utils.cpp_extension import load
    repo=resolve(config['repo']);sys.path.insert(0,str(repo))
    cuda=(repo/'hashencoder/src/hashencoder.cu').read_text()
    begin=cuda.index('template <uint32_t D>\n__device__ uint32_t fast_hash')
    end=cuda.index('template <uint32_t D>\n__device__ uint32_t get_grid_index(const uint32_t pos_grid[D])',begin)
    build=ROOT/'.tools/hashgrid-analysis-probe';build.mkdir(exist_ok=True)
    helper=cuda[begin:end]
    helper_path=build/'upstream_index.inc'
    if not helper_path.exists() or helper_path.read_text()!=helper:helper_path.write_text(helper)
    probe=load(name='grid4d_analysis_probe',sources=[str(Path(__file__).with_name('probe.cu'))],
        extra_include_paths=[str(build)],build_directory=str(build),extra_cflags=['-O2','-std=c++17'],
        extra_cuda_cflags=['-O2','-std=c++17','-allow-unsupported-compiler',
            '-U__CUDA_NO_HALF_OPERATORS__','-U__CUDA_NO_HALF_CONVERSIONS__','-U__CUDA_NO_HALF2_OPERATORS__'],verbose=True)
    from hashencoder.hashgrid import _hash_encode
    rng=np.random.default_rng(config['seed']);coordinates=rng.random((513,3),dtype=np.float32)
    coordinates[:3]=np.array([[0,0,0],[1,1,1],[.5,.5,.5]],dtype=np.float32)
    record={'status':'PASS','helper_source_sha256':hashlib.sha256(helper.encode()).hexdigest(),
        'upstream_cuda_sha256':digest(repo/'hashencoder/src/hashencoder.cu'),'coordinate_sha256':hashlib.sha256(coordinates.tobytes()).hexdigest(),
        'coordinates':coordinates.tolist(),'tolerance':{'atol':5e-6,'rtol':2e-5},'grids':{}}
    for g in GRIDS:
        key=g+'_encoding.embeddings';prefix=g+'_encoding';m=runtime['trainable_parameters'][key]
        q=states[0][prefix+'.per_level_scale'].cuda();base=states[0][prefix+'.base_resolution'].cuda()
        scale,res=probe.scales(torch.log2(q),base,m['levels']);scale=scale.cpu().numpy();res=res.cpu().numpy()
        assert res.tolist()==m['cuda_lookup_resolutions']
        actual=_hash_encode.apply(torch.from_numpy(coordinates).cuda(),states[0][key].cuda(),
            states[0][prefix+'.offsets'].cuda(),q,base,False).cpu().numpy().reshape(len(coordinates),m['levels'],2)
        errors=[];index_checks=[]
        for l,(a,b) in enumerate(zip(m['offsets'],m['offsets'][1:])):
            v=rng.integers(0,res[l],size=(257,3),dtype=np.int32)
            v[:2]=np.array([[0,0,0],res[l]-1])
            gpu=probe.indices(torch.from_numpy(v).cuda(),torch.from_numpy(res[l]).cuda(),b-a).cpu().numpy()
            cpu=slots(v,res[l],b-a)
            assert np.array_equal(cpu,gpu),(g,l,'indices')
            expected=lookup(coordinates,states[0][key][a:b].numpy(),scale[l],res[l])
            assert np.allclose(expected,actual[:,l],atol=5e-6,rtol=2e-5),(g,l,'interpolation',np.max(np.abs(expected-actual[:,l])))
            errors.append(float(np.max(np.abs(expected-actual[:,l]))));index_checks.append(len(v))
        record['grids'][g]={'scales':scale.tolist(),'resolutions':res.tolist(),'index_checks_by_level':index_checks,
            'interpolation_max_abs_errors':errors,'allocation_lookup_differ_at':[l for l in range(m['levels']) if m['allocation_resolutions'][l]!=res[l].tolist()]}
    torch.cuda.synchronize();write(out/'mapping-validation.json',record)
    return record

def inputs(config,out):
    checkpoint=resolve(config['checkpoint']);runtime=read(resolve(config['runtime']));study=resolve(config['study'])
    checkpoint_hash=digest(checkpoint)
    assert checkpoint_hash==runtime['checkpoint_sha256']
    states=load_checkpoint(checkpoint);tables,buffers,manifest=import_tables(study/'lossless')
    assert manifest['source_sha256']==checkpoint_hash and set(tables)==set(KEYS)
    assert sum(t.numel() for t in tables.values())==sum(m['scalar_count'] for m in runtime['trainable_parameters'].values())
    for key in KEYS:
        m=manifest['grids'][key];validate_grid(m)
        assert torch.equal(tables[key],states[0][key])
        assert m['levels']==(16 if key.startswith('xyz') else 32) and m['feature_dimension']==2
        for buf in BUFFERS:
            k=key.split('.')[0]+'.'+buf
            assert torch.equal(buffers[k],states[0][k])
    assert config['sampling_budget']>=256 and config['collision_budget']>=256 and config['enumeration_limit']>0
    assert set(config['grids']).issubset(GRIDS) and config['grids']
    if config['levels'] is not None:assert all(0<=l<32 for l in config['levels'])
    for g in config['grids']:
        if not selected_levels(config,manifest['grids'][g+'_encoding.embeddings']):
            raise ValueError(f'No selected levels exist in {g}; specify compatible grids/levels')
    core=source_identity(resolve(config['repo']))
    evidence={'status':'PASS','checkpoint_sha256':checkpoint_hash,'grids':len(tables),
        'levels':sum(m['levels'] for m in manifest['grids'].values()),'scalars':sum(t.numel() for t in tables.values()),
        'metadata_and_buffers_exact':True,'core_source_sha256':core}
    write(out/'input-validation.json',evidence)
    return states,{g:tables[g+'_encoding.embeddings'].numpy() for g in GRIDS},manifest,runtime,evidence

def memory_data(config,raw,manifest,out):
    total=sum(x.nbytes for x in raw.values());grids=[];levels=[]
    for g in config['grids']:
        x=raw[g];m=manifest['grids'][g+'_encoding.embeddings']
        grids.append({'grid':g,'rows':len(x),'scalars':x.size,'bytes':x.nbytes,'MiB':x.nbytes/2**20,'percent_total':100*x.nbytes/total})
        cumulative=0
        for l,(a,b) in enumerate(zip(m['offsets'],m['offsets'][1:])):
            cumulative+=(b-a)*8
            if l in selected_levels(config,m):levels.append({'grid':g,'level':l,'rows':b-a,'scalars':(b-a)*2,'bytes':(b-a)*8,
                'MiB':(b-a)*8/2**20,'percent_grid':100*(b-a)*8/x.nbytes,'cumulative_percent_grid':100*cumulative/x.nbytes})
    write(out/'memory/data.json',{'grids':grids,'levels':levels,'total_raw_bytes':total});csv_write(out/'memory/grids.csv',grids);csv_write(out/'memory/levels.csv',levels)

def distribution_data(config,raw,manifest,out):
    edges=np.linspace(min(x.min() for x in raw.values()),max(x.max() for x in raw.values()),config['histogram_bins']+1)
    records=[];data={}
    for g in config['grids']:
        x=raw[g];m=manifest['grids'][g+'_encoding.embeddings'];groups={}
        for label,a in [('pooled',x),('channel0',x[:,0]),('channel1',x[:,1])]:
            s=describe(a);groups[label]={**s,'counts':histogram(a,edges)};records.append({'grid':g,'level':'table','channel':label,**{k:v for k,v in s.items() if k not in ('box','top_values')}})
        levels=[]
        for l in selected_levels(config,m):
            a,b=m['offsets'][l:l+2]
            for ch in range(2):
                s=describe(x[a:b,ch]);levels.append({'level':l,'channel':ch,**s,'counts':histogram(x[a:b,ch],edges)})
                records.append({'grid':g,'level':l,'channel':ch,**{k:v for k,v in s.items() if k not in ('box','top_values')}})
        data[g]={'table':groups,'levels':levels}
    write(out/'distributions/raw.json',{'edges':edges.tolist(),'grids':data,'scale':'common full range; population std; exact counts/quantiles'})
    csv_write(out/'distributions/raw-statistics.csv',records)

def quantization_data(config,raw,manifest,out):
    variants=[];level_records=[];grid_records=[];hist={};quant={}
    setting=config['quantization']
    names=[f'{s}-{b}' for s in ('table','level') for b in (8,12,16) if setting=='all' or setting==f'{s}-{b}']
    # Channel/collision analysis always needs existing table-8, regardless of plotting filter.
    for name in dict.fromkeys(names+['table-8','level-8']):
        folder=resolve(config['study'])/name;qm=read(folder/'manifest.json');assert qm['source_sha256']==manifest['source_sha256']
        quant[name]={g:_read_array(folder,qm['grids'][g+'_encoding.embeddings']['payload']) for g in config['grids']}
        if name not in names:continue
        bits=qm['bits'];maxcode=(1<<bits)-1;edges=np.linspace(-.5,maxcode+.5,257)
        bygrid={}
        for g in config['grids']:
            q=quant[name][g];m=qm['grids'][g+'_encoding.embeddings'];full=np.bincount(q.reshape(-1),minlength=maxcode+1)
            h=entropy_counts(full);s=describe(q)
            grid_records.append({'variant':name,'grid':g,'bits':bits,'scope':qm['scope'],'n':q.size,'entropy_bits_per_symbol':h,'theoretical_bits':q.size*h,
                'fixed_bits':q.size*bits,'serialized_payload_bytes':q.nbytes,'mean':s['mean'],'std':s['std'],'min':s['min'],'max':s['max'],
                'unique':s['unique'],'zero_fraction':s['zero_fraction']})
            levels=[]
            for l in selected_levels(config,m):
                a,b=m['offsets'][l:l+2];ql=q[a:b];c=np.bincount(ql.reshape(-1),minlength=maxcode+1);hl=entropy_counts(c)
                row={'variant':name,'grid':g,'level':l,'bits':bits,'scope':qm['scope'],'n':ql.size,'entropy_bits_per_symbol':hl,'theoretical_bits':hl*ql.size,
                    'theoretical_bytes':hl*ql.size/8,'fixed_bits':ql.size*bits,'payload_bytes':ql.nbytes,'unique':int(np.count_nonzero(c))}
                level_records.append(row);levels.append({**row,'counts':histogram(ql,edges)})
            indices=np.flatnonzero(full)
            bygrid[g]={'statistics':s,'codes_nonzero':indices.tolist(),'counts_nonzero':full[indices].tolist(),
                'rebinned_counts':histogram(q,edges),'levels':levels,'quantization_params':m['quantization']}
        total=sum(p.stat().st_size for p in folder.iterdir() if p.is_file())
        variants.append({'variant':name,'bits':bits,'scope':qm['scope'],'real_serialized_bytes':total,
            'ideal_fixed_bits':sum(q.size for q in quant[name].values())*bits,'actual_entropy_bitstream_bytes':None,
            'note':'12-bit codes use uint16; level-wise numeric codes have different float ranges'})
        hist[name]={'edges':edges.tolist(),'grids':bygrid,'source':str(folder)}
    write(out/'distributions/quantized.json',hist);write(out/'entropy/data.json',{'levels':level_records,'grids':grid_records,'variants':variants})
    csv_write(out/'entropy/levels.csv',level_records);csv_write(out/'entropy/grids.csv',grid_records)
    csv_write(out/'entropy/priority-levels.csv',sorted(level_records,key=lambda r:-r['theoretical_bits']))
    return quant

def channel_data(config,raw,manifest,quant,out):
    data={};summary=[];level_gain=[]
    raw_edges=np.linspace(min(float(x.min()) for x in raw.values()),max(float(x.max()) for x in raw.values()),129)
    zoom_edges=np.linspace(-.15,.15,129)
    np.testing.assert_array_equal(rankdata([3,1,1,2]),average_ranks([3,1,1,2]))
    for gi,g in enumerate(config['grids']):
        x=raw[g];q=quant['table-8'][g];idx=sample_indices(len(x),config['sampling_budget'],config['seed']+gi)
        joint=joint_codes(q[:,0],q[:,1]);conditional=joint_codes(context_class(q[:,0]),q[:,1],16)
        jm=joint_metrics(joint);cm=joint_metrics(conditional)
        means,error=conditional_error(conditional);class_n=conditional.sum(axis=1)
        iid=MODELS['iid'].fit(q);ctx=MODELS['channel_context'].fit(q)
        # Exact full-array codelength under the already transmitted 16-bit masses.
        pi=iid.distribution(1).astype(np.float64);pc=ctx.freq[1:].astype(np.float64)/65536
        saving=np.log2(pc[context_class(q[:,0]),q[:,1]])-np.log2(pi[q[:,1]])
        metrics={'grid':g,'rows':len(x),'pearson_full':pearson(x[:,0],x[:,1]),
            'spearman_full':pearson(rankdata(x[:,0]),rankdata(x[:,1])),
            'mutual_information_full_q0_q1':jm['mutual_information'],
            'mutual_information_16class_q1':cm['mutual_information'],'H_q1':cm['H_target'],'H_q1_given_class':cm['H_target_given_context'],
            'finite_model_gain_bits':float(saving.sum()),'diagnostic_prediction_mse_code_units':float((error*class_n).sum()/len(q))}
        summary.append(metrics)
        error_edges=np.linspace(-255,255,129);error_hist=np.zeros((16,128),dtype=np.int64)
        for c in range(16):
            values=np.arange(256)-means[c];error_hist[c],_=np.histogram(values,bins=error_edges,weights=conditional[c])
        raw_joint=np.histogram2d(x[:,0],x[:,1],bins=(raw_edges,raw_edges))[0].astype(np.int64)
        raw_zoom=np.histogram2d(x[:,0],x[:,1],bins=(zoom_edges,zoom_edges))[0].astype(np.int64)
        assert int(raw_joint.sum())==len(x)
        data[g]={'metrics':metrics,'scatter_values':x[idx].tolist(),'scatter_row_indices':idx.tolist(),
            'raw_joint_counts':raw_joint.tolist(),'raw_joint_edges':raw_edges.tolist(),
            'raw_zoom_counts':raw_zoom.tolist(),'raw_zoom_edges':zoom_edges.tolist(),'raw_zoom_included_rows':int(raw_zoom.sum()),
            'scatter_sampling':'uniform rows without replacement; exact full counts below',
            'joint_counts':joint.tolist(),'conditional_counts':conditional.tolist(),'class_rows':class_n.tolist(),
            'class_entropy':[entropy_counts(c) for c in conditional],'prediction_mean':means.tolist(),'prediction_mse':error.tolist(),
            'prediction_error_edges':error_edges.tolist(),'prediction_error_counts':error_hist.tolist()}
        m=manifest['grids'][g+'_encoding.embeddings']
        for l in selected_levels(config,m):
            a,b=m['offsets'][l:l+2];level_joint=joint_codes(q[a:b,0],q[a:b,1]);level_conditional=joint_codes(context_class(q[a:b,0]),q[a:b,1],16)
            row={'grid':g,'level':l,'n':(b-a)*2,'rows':b-a,
                'pearson_within_level':pearson(x[a:b,0],x[a:b,1]),
                'MI_q0_q1_within_level':joint_metrics(level_joint)['mutual_information'],
                'MI_class_q1_within_level':joint_metrics(level_conditional)['mutual_information'],
                'finite_diagnostic_gain_bits':float(saving[a:b].sum()),'gain_bits_per_original_scalar':float(saving[a:b].sum()/((b-a)*2)),
                'type':'diagnostic finite table-fitted model codelength; not actual per-level range stream; overhead not allocated'}
            level_gain.append(row)
    write(out/'channel_dependencies/data.json',data);csv_write(out/'channel_dependencies/summary.csv',summary)
    write(out/'context_gains/levels.json',level_gain);csv_write(out/'context_gains/levels.csv',level_gain)

def interlevel_data(config,raw,manifest,quant,mapping,out):
    rows=[];examples={};repro=[]
    qmanifest=read(resolve(config['study'])/'table-8/manifest.json')
    for gi,g in enumerate(config['grids']):
        m=manifest['grids'][g+'_encoding.embeddings'];scales=np.array(mapping['grids'][g]['scales'],dtype=np.float32)
        res=np.array(mapping['grids'][g]['resolutions']);x=raw[g];q=quant['table-8'][g]
        for fine in selected_levels(config,m):
            if fine==0:continue
            coarse=fine-1;a,b=m['offsets'][coarse:coarse+2];fa,fb=m['offsets'][fine:fine+2]
            valid=np.floor(scales[fine]).astype(int)+1
            v,mode,total=vertex_sample(valid,config['sampling_budget'],config['seed']+gi*100+fine,config['sampling_budget'])
            u=(v.astype(np.float32)/scales[fine]).astype(np.float32)
            fine_slots=slots(v,res[fine],fb-fa);targets=x[fa:fb][fine_slots];qs=q[fa:fb][fine_slots]
            interpolated=lookup(u,x[a:b],scales[coarse],res[coarse])
            nearest_vertices=np.rint(u*scales[coarse]).astype(np.int64);nearest=x[a:b][slots(nearest_vertices,res[coarse],b-a)]
            reproduced=vertex_sample(valid,config['sampling_budget'],config['seed']+gi*100+fine,config['sampling_budget'])[0]
            assert np.array_equal(v,reproduced)
            repro.append({'grid':g,'fine_level':fine,'vertices_sha256':hashlib.sha256(v.tobytes()).hexdigest(),'n':len(v),
                'unique_target_slots':int(np.unique(fine_slots).size),'nominal_eligible_vertices':total})
            for method,context in [('coarse_interpolation_at_fine_vertex',interpolated),('nearest_coarse_vertex',nearest)]:
                for ch in range(2):
                    lo,hi=float(x[a:b,ch].min()),float(x[a:b,ch].max())
                    classes=np.clip(np.floor((context[:,ch]-lo)/(hi-lo+1e-30)*16),0,15).astype(np.uint8)
                    counts=joint_codes(classes,qs[:,ch],16);jm=joint_metrics(counts)
                    train=np.arange(len(v))%5!=0;test=~train
                    traincounts=joint_codes(classes[train],qs[train,ch],16).astype(np.float64)+1
                    probs=traincounts/traincounts.sum(axis=1,keepdims=True)
                    heldout=float(-np.log2(probs[classes[test],qs[test,ch]]).mean())
                    baseline=np.bincount(qs[train,ch],minlength=256).astype(np.float64)+1;baseline/=baseline.sum()
                    heldout_iid=float(-np.log2(baseline[qs[test,ch]]).mean())
                    pred=np.full(16,float(targets[train,ch].mean()))
                    for c in range(16):
                        sel=train&(classes==c)
                        if sel.any():pred[c]=targets[sel,ch].mean(dtype=np.float64)
                    mse=float(np.square(targets[test,ch].astype(np.float64)-pred[classes[test]]).mean())
                    row={'grid':g,'coarse_level':coarse,'fine_level':fine,'channel':ch,'method':method,'pairs':len(v),
                        'sample_mode':mode,'pearson':pearson(context[:,ch],targets[:,ch]),
                        'spearman':pearson(rankdata(context[:,ch]),rankdata(targets[:,ch])),
                        'mutual_information':jm['mutual_information'],'conditional_entropy':jm['H_target_given_context'],
                        'heldout_cross_entropy':heldout,'heldout_iid_cross_entropy':heldout_iid,
                        'heldout_prediction_mse':mse,'type':'sampled vertex-domain diagnostic; not actual table coding'}
                    rows.append(row)
                    # A representative low/colliding pair for each grid, plus all per-pair histograms.
                    name=f'{g}-l{fine}-{method}-ch{ch}'
                    examples[name]={'joint_counts':counts.tolist(),'context_min':lo,'context_max':hi,
                        'scatter':np.column_stack((context[:,ch],targets[:,ch])).tolist() if fine in (1,5,m['levels']-1) else None,
                        'metadata':row}
    write(out/'interlevel/data.json',{'rows':rows,'examples':examples,'sample_reproducibility':repro,
        'status':'PASS diagnostic mapping; actual inter-level codec BLOCKED BY RESEARCH DESIGN'})
    csv_write(out/'interlevel/summary.csv',rows)

def collision_data(config,raw,manifest,quant,mapping,out):
    data={};summary=[]
    qmanifest=read(resolve(config['study'])/'table-8/manifest.json')
    for gi,g in enumerate(config['grids']):
        m=manifest['grids'][g+'_encoding.embeddings'];rng=np.random.default_rng(config['seed']+gi)
        q=quant['table-8'][g];model=MODELS['channel_context'].fit(q,m)
        full_classes=context_class(q[:,0]);conditional=joint_codes(full_classes,q[:,1],16)
        means,_=conditional_error(conditional)
        channel_prediction_error=np.square(q[:,1].astype(np.float64)-means[full_classes])
        finite_codelength=-np.log2(model.distribution(0)[q[:,0]].astype(np.float64))-np.log2(model.freq[1:].astype(np.float64)[full_classes,q[:,1]]/65536)
        queries=rng.random((config['sampling_budget'],3),dtype=np.float32)
        perlevel=[]
        for l in selected_levels(config,m):
            a,b=m['offsets'][l:l+2];res=np.array(mapping['grids'][g]['resolutions'][l]);scale=np.array(mapping['grids'][g]['scales'][l],np.float32)
            vertices,mode,total=vertex_sample(res,config['collision_budget'],config['seed']+gi*100+l,config['enumeration_limit'])
            unique,d=multiplicity(vertices,res,b-a)
            corner_v,_=corners(queries,scale);query_unique,query_d=multiplicity(corner_v.reshape(-1,3),res,b-a)
            assert int(d.sum())==len(unique) and int(query_d.sum())==len(query_unique)
            mult=np.bincount(d);query_mult=np.bincount(query_d)
            row={'grid':g,'level':l,'table_rows':b-a,'nominal_vertices':total,'nominal_vertices_per_slot':total/(b-a),
                'mode':mode,'enumerated_vertices':len(unique),'visited_slots':int((d>0).sum()),'colliding_slots':int((d>1).sum()),
                'colliding_fraction_all_slots':float((d>1).mean()),'colliding_fraction_visited_slots':float((d[d>0]>1).mean()),
                'max_multiplicity':int(d.max()),'query_unique_vertices':len(query_unique),'query_visited_slots':int((query_d>0).sum()),
                'query_colliding_fraction_all_slots':float((query_d>1).mean()),'query_max_multiplicity':int(query_d.max()),
                'hashed_lookup':int(np.prod(res))>b-a,'train_query_coverage':'not measured; these are seeded uniform diagnostic queries'}
            summary.append(row)
            features=raw[g][a:b];groups=[]
            for multiplicity_value in np.flatnonzero(mult):
                selected=d==multiplicity_value
                groups.append({'multiplicity':int(multiplicity_value),'slots':int(selected.sum()),
                    'mean_abs_feature':float(np.abs(features[selected]).mean(dtype=np.float64)),
                    'mean_l2_feature':float(np.linalg.norm(features[selected].astype(np.float64),axis=1).mean()),
                    'channel_predictor_mse_code_squared':float(channel_prediction_error[a:b][selected].mean()),
                    'channel_context_finite_bits_per_scalar':float(finite_codelength[a:b][selected].mean()/2)})
            perlevel.append({'summary':row,'nominal_multiplicity_counts':mult.tolist(),'query_multiplicity_counts':query_mult.tolist(),'feature_groups':groups})
        data[g]=perlevel
    write(out/'collisions/data.json',{'grids':data,'summary':summary,
        'prediction_error_and_interlevel_codelength_status':'BLOCKED BY RESEARCH DESIGN: one fine slot can have multiple vertex-derived contexts; no canonical slot correspondence chosen'})
    csv_write(out/'collisions/summary.csv',summary)

def experiments_data(config,manifest,out):
    rows=[];fairness=[];coded={};experiment_root=resolve(config['experiments'])
    for path in sorted(experiment_root.glob('*/manifest.json')):
        record=read(path)
        if record['checkpoint_sha256']!=manifest['source_sha256']:continue
        folder=path.parent;verify=read(folder/'verification.json');assert verify['passed'] and verify['frames']==20
        assert record['iteration']==50000
        comp=read(folder/'compression.json');metrics=read(folder/'metrics.json')['values'];cfg=read(folder/'config.json')
        perview=read(folder/'model/per_view.json')['ours_50000'];inference=read(folder/'inference.json')
        assert inference['strict_load'] and inference['all_non_embeddings_unchanged'] and len(inference['frames'])==20
        rows.append({'variant':record['id'].replace('reference-',''),'model':comp['model'],'bits':comp['quantization_bits'],
            'scope':comp['quantization_scope'],'bytes':comp['total_compressed_bytes'],'MiB':comp['total_compressed_bytes']/2**20,
            'bits_per_scalar':comp['bits_per_symbol'],**metrics,'size_type':'actual bitstream' if comp['actual_bitstream_bytes'] else 'real raw serialized directory',
            'ideal_fixed_bytes':comp['fixed_ideal_bytes_without_metadata']})
        fairness.append({'id':record['id'],'checkpoint_sha256':record['checkpoint_sha256'],'config':cfg,
            'float_frame_hashes':[r['float32_rgb_sha256'] for r in inference['frames']],'per_view':perview,'folder':str(folder)})
        if comp['actual_bitstream_bytes'] is not None:
            stream=folder/'bitstream.bin';assert digest(stream)==record['bitstream_sha256'] and stream.stat().st_size==comp['actual_bitstream_bytes']
            assert verify['symbols_exact'] and verify['float_render_png_metrics_equal_reference']
            header,models,payload=parse(stream)
            model={**comp,'header':header,'total_json_bytes':comp['metadata_framing_bytes']-PREFIX.size-32,
                'prefix_bytes':PREFIX.size,'integrity_bytes':32,
                'quantization_metadata_and_buffers_split':'combined JSON section; exact independent semantic split unavailable'}
            assert len(models)==comp['model_overhead_bytes'] and len(payload)==comp['coded_payload_bytes']
            coded[comp['model']]=model
    assert rows and {'float32','fixed8','iid','channel_context'}.issubset({r['model'] for r in rows})
    originals=[r for r in fairness if r['id']=='reference-float32'];assert len(originals)==1
    reference_frames=sorted(originals[0]['per_view']['PSNR'])
    for r in fairness:
        assert sorted(r['per_view']['PSNR'])==reference_frames
        c=r['config'];base=originals[0]['config']
        assert all(c[k]==base[k] for k in ('checkpoint','iteration','repo','dataset','seed','evaluation'))
        gt=Path(r['folder'])/'model/test/ours_50000/gt'
        gt0=Path(originals[0]['folder'])/'model/test/ours_50000/gt'
        assert all(digest(gt/n)==digest(gt0/n) for n in reference_frames)
    for k in KEYS:
        assert coded['iid']['header']['components'][k]['symbols_sha256']==coded['channel_context']['header']['components'][k]['symbols_sha256']==coded['fixed8']['header']['components'][k]['symbols_sha256']
    gains=[]
    for model_name in coded:
        if model_name in ('fixed8','iid'):continue
        for g in config['grids']:
            key=g+'_encoding.embeddings';a=coded['iid']['header']['components'][key];b=coded[model_name]['header']['components'][key]
            gains.append({'model':model_name,'baseline':'iid','grid':g,'payload_gain_bits':8*(a['coded_bytes']-b['coded_bytes']),
                'model_extra_bits':8*(b['model_bytes']-a['model_bytes']),
                'payload_plus_model_gain_bits':8*(a['coded_bytes']+a['model_bytes']-b['coded_bytes']-b['model_bytes']),
                'n':a['symbols'],'gain_payload_bits_per_scalar':8*(a['coded_bytes']-b['coded_bytes'])/a['symbols'],
                'global_json_prefix_trailer':'not arbitrarily allocated to grids'})
    write(out/'rate_distortion/data.json',rows);csv_write(out/'rate_distortion/data.csv',rows)
    write(out/'bitstream/data.json',coded);write(out/'context_gains/grids.json',gains);csv_write(out/'context_gains/grids.csv',gains)
    write(out/'experiment-fairness.json',{'status':'PASS','experiments':fairness,'views':reference_frames,
        'checkpoint_and_settings_same':True,'quantized_symbols_same':True,'actual_stream_hashes_sizes_verified':True})
    return fairness

def rendering_data(config,fairness,out):
    original=next(r for r in fairness if r['id']=='reference-float32');frames=sorted(original['per_view']['PSNR'])
    timestamps=read(resolve(original['config']['dataset'])/'transforms_test.json')['frames']
    rows=[];worst=[]
    for e in fairness:
        for i,n in enumerate(frames):
            rows.append({'variant':e['id'].replace('reference-',''),'frame':n,'index':i,'timestamp':timestamps[i]['time'],
                **{k:e['per_view'][k][n] for k in ('PSNR','SSIM','LPIPS','MS-SSIM')},
                'delta_PSNR':e['per_view']['PSNR'][n]-original['per_view']['PSNR'][n],
                'delta_SSIM':e['per_view']['SSIM'][n]-original['per_view']['SSIM'][n],
                'delta_LPIPS':e['per_view']['LPIPS'][n]-original['per_view']['LPIPS'][n]})
    for name in ('table-8','level-8'):
        candidates=[r for r in rows if r['variant']==name]
        worst.extend(sorted(candidates,key=lambda r:r['delta_PSNR'])[:3])
    checks=[]
    sys.path.insert(0,str(resolve(config['repo'])))
    from utils.loss_utils import ssim
    from pytorch_msssim import ms_ssim
    import lpips
    network=lpips.LPIPS(net='vgg').cuda()
    recomputed=[]
    for e in fairness:
        test=Path(e['folder'])/'model/test/ours_50000'
        for n in frames:
            rgb=np.asarray(Image.open(test/'renders'/n).convert('RGB'),np.float64)/255
            gt=np.asarray(Image.open(test/'gt'/n).convert('RGB'),np.float64)/255
            assert rgb.shape==gt.shape==(800,800,3) and np.isfinite(rgb).all()
            mse=np.square(rgb-gt).mean();psnr=-10*math.log10(mse)
            assert abs(psnr-e['per_view']['PSNR'][n])<1e-4
            with torch.no_grad():
                a=torch.from_numpy(rgb.astype(np.float32).transpose(2,0,1).copy()).unsqueeze(0).cuda()
                b=torch.from_numpy(gt.astype(np.float32).transpose(2,0,1).copy()).unsqueeze(0).cuda()
                values={'SSIM':float(ssim(a,b)),'LPIPS':float(network(a,b)),'MS-SSIM':float(ms_ssim(a,b,data_range=1,size_average=True))}
                for metric,value in values.items():assert np.isfinite(value) and abs(value-e['per_view'][metric][n])<1e-6,(e['id'],n,metric,value)
                recomputed.append({'variant':e['id'],'frame':n,'PSNR_cpu':psnr,**values})
            for sub in ('gt','renders','depth'):assert Image.open(test/sub/n).size==(800,800)
        checks.append({'variant':e['id'],'frames':len(frames),'independent_cpu_psnr_matches':True,
            'recomputed_ssim_lpips_msssim_match':True,'image_shapes':'800x800'})
    write(out/'rendering/data.json',{'per_frame':rows,'worst_frames':worst,'experiments':fairness,'checks':checks,
        'error_metric':'mean absolute RGB error in [0,1] PNG space','colormap_range':[0,1],
        'encoder_equivalence':'IID and channel context have identical float renders; quantization creates differences'})
    csv_write(out/'rendering/per-frame.csv',rows);csv_write(out/'rendering/worst-frames.csv',worst)
    csv_write(out/'rendering/recomputed-metrics.csv',recomputed)

def main():
    p=argparse.ArgumentParser();p.add_argument('config');args=p.parse_args();config=read(args.config)
    out=resolve(config['output']);out.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    section=config['section'];states,raw,manifest,runtime,evidence=inputs(config,out)
    memory_data(config,raw,manifest,out)
    if section in ('all','histograms'):distribution_data(config,raw,manifest,out)
    quant=None
    if section in ('all','histograms','entropy','channels','interlevel','collisions'):
        quant=quantization_data(config,raw,manifest,out)
    if section in ('all','channels'):channel_data(config,raw,manifest,quant,out)
    if section in ('all','interlevel','collisions'):
        mapping=gpu_mapping(config,states,runtime,out)
        if section in ('all','interlevel'):interlevel_data(config,raw,manifest,quant,mapping,out)
        if section in ('all','collisions'):collision_data(config,raw,manifest,quant,mapping,out)
    if section in ('all','rate-distortion','rendering','channels'):
        fairness=experiments_data(config,manifest,out)
        if section in ('all','rendering'):rendering_data(config,fairness,out)
    assert digest(resolve(config['checkpoint']))==evidence['checkpoint_sha256']
    write(out/'computation.json',{'status':'PASS','seconds':time.perf_counter()-start,'section':section,
        'python':sys.version,'torch':torch.__version__,'numpy':np.__version__,'source_checkpoint_unchanged':True})
    print('Analysis computation PASS',section,time.perf_counter()-start)

if __name__=='__main__':main()
