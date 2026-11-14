"""Extract/check the one dense pair xyz L3 -> L4 without fitting any model."""
import argparse
import csv
import hashlib
import io
import subprocess
import sys
import time
import unittest
from pathlib import Path
import numpy as np
import torch
from research.grid4d.codec import load_checkpoint,_read_array,dequantize,quantize,validate_grid
from research.experiment_bench.cli import source_identity
from research.hashgrid_analysis.common import ROOT,read,write,digest,csv_write,SHA
from research.hashgrid_analysis.mapping import slots
from .decoder import geometry,dense_vertices,cpu_context,gpu_context

def probe(repo):
    from torch.utils.cpp_extension import load
    source=(repo/'hashencoder/src/hashencoder.cu').read_text()
    begin=source.index('template <uint32_t D>\n__device__ uint32_t fast_hash')
    end=source.index('template <uint32_t D>\n__device__ uint32_t get_grid_index(const uint32_t pos_grid[D])',begin)
    helper=source[begin:end];build=ROOT/'.tools/hashgrid-analysis-probe';build.mkdir(exist_ok=True)
    path=build/'upstream_index.inc'
    if not path.exists() or path.read_text()!=helper:path.write_text(helper)
    module=load(name='grid4d_analysis_probe',sources=[str(ROOT/'research/hashgrid_analysis/probe.cu')],
        extra_include_paths=[str(build)],build_directory=str(build),extra_cflags=['-O2','-std=c++17'],
        extra_cuda_cflags=['-O2','-std=c++17','-allow-unsupported-compiler','-U__CUDA_NO_HALF_OPERATORS__',
            '-U__CUDA_NO_HALF_CONVERSIONS__','-U__CUDA_NO_HALF2_OPERATORS__'],verbose=True)
    return module,hashlib.sha256(helper.encode()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True)
    p.add_argument('--scope',choices=('table','level'),default='table')
    args=p.parse_args();out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False);start=time.perf_counter()
    checkpoint=ROOT/'outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth'
    study=ROOT/f'research/experiment_bench/reference-study/{args.scope}-8'
    repo=ROOT/'external/Grid4D-audit-clean';source_hash=digest(checkpoint)
    write(out/'manifest.json',{'status':'IN PROGRESS','checkpoint_sha256':source_hash})
    write(out/'config.json',{'scope':args.scope,'seed':0,'sampling_budget':10000,'coarse_level':3,'fine_level':4,
        'checkpoint':str(checkpoint),'quantized_study':str(study),'output':str(out)})
    checks=[]
    def passed(name,inputs,**data):
        checks.append({'test':name,'status':'PASS','input':inputs,'log':'validation.log',**data})
        write(out/'checks-in-progress.json',checks)
        print('PASS',name,flush=True)
    original=load_checkpoint(checkpoint)[0];m=read(study/'manifest.json')
    assert source_hash==SHA==m['source_sha256']
    key='xyz_encoding.embeddings';g=m['grids'][key];validate_grid(g)
    for name in ('offsets','base_resolution','per_level_scale'):
        assert _read_array(study,g['buffers'][name]).tolist()==original['xyz_encoding.'+name].tolist()==g[name]
    raw=original[key].numpy();codes=_read_array(study,g['payload'])
    assert codes.dtype==np.uint8 and codes.shape==raw.shape and m['bits']==8
    offsets=g['offsets'];a,b,c=offsets[3:6];coarse_q=codes[a:b].copy();fine_q=codes[b:c].copy()
    if args.scope=='table':re_q,params=quantize(raw,8);assert np.array_equal(re_q,codes)
    else:
        params=None
        for l in (3,4):
            aa,bb=offsets[l:l+2];re_q,pp=quantize(raw[aa:bb],8)
            assert np.array_equal(re_q,codes[aa:bb]);assert all(g['quantization'][l][k]==v for k,v in pp.items())
    def qparams(level):
        result=dict(g['quantization'][0 if args.scope=='table' else level])
        if args.scope=='table':assert all(result[k]==v for k,v in params.items())
        return result
    core=source_identity(repo);passed('input integrity and existing 8-bit quantizer parity','checkpoint + existing quantized manifest/payload',checkpoint_sha256=source_hash,core_source_sha256=core)
    instrument,helper_sha=probe(repo)
    base=original['xyz_encoding.base_resolution'].cuda();q=original['xyz_encoding.per_level_scale'].cuda()
    scales,res=instrument.scales(torch.log2(q),base,5);scales=scales.cpu().numpy();res=res.cpu().numpy()
    meta={'version':1,'pair':'xyz L3 -> L4','quantization_scope':args.scope,'checkpoint_sha256':source_hash,
        'coordinate_rule':'float32(vertex) / actual CUDA float32 fine scale; never clamp; preserve upstream OOB zero',
        'context_arithmetic':'official Grid4D CUDA float32 is canonical; CPU arithmetic has measured tolerance',
        'coarse':{'level':3,'rows':b-a,'offset_start':a,'offset_end':b,'lookup_resolution':res[3].tolist(),
            'allocation_resolution':g['allocation_resolutions'][3],'scale':scales[3].tolist(),'quantization':qparams(3)},
        'fine':{'level':4,'rows':c-b,'offset_start':b,'offset_end':c,'lookup_resolution':res[4].tolist(),
            'allocation_resolution':g['allocation_resolutions'][4],'scale':scales[4].tolist()},
        'implementation':{'repo':'external/Grid4D-audit-clean','per_level_scale':g['per_level_scale'],'base_resolution':g['base_resolution'],
            'coarse_prefix_offsets':offsets[:5],'helper_sha256':helper_sha,'cuda_source_sha256':digest(repo/'hashencoder/src/hashencoder.cu')}}
    for l in (3,4):
        rows=offsets[l+1]-offsets[l];v=dense_vertices(rows,res[l]);assert g['allocation_resolutions'][l]==res[l].tolist()
        cpu=slots(v,res[l],rows);gpu=instrument.indices(torch.from_numpy(v).cuda(),torch.from_numpy(res[l]).cuda(),rows).cpu().numpy()
        np.testing.assert_array_equal(cpu,np.arange(rows));np.testing.assert_array_equal(gpu,cpu)
    passed('exhaustive GPU dense index parity for both levels','actual upstream get_grid_index<3,2>',coarse_indices=b-a,fine_indices=c-b,helper_sha256=helper_sha)
    bundle=out/'decoder_bundle';bundle.mkdir();np.save(bundle/'coarse_symbols.npy',coarse_q,allow_pickle=False)
    meta['coarse_symbols_sha256']=digest(bundle/'coarse_symbols.npy');write(bundle/'decoder_metadata.json',meta)
    vertex,u,exact,valid=geometry(meta);context_cpu=cpu_context(meta,coarse_q);context_gpu=gpu_context(meta,coarse_q)
    assert len(vertex)==len(fine_q)==c-b and np.unique(vertex,axis=0).shape[0]==c-b
    assert np.isfinite(context_gpu).all() and np.isfinite(context_cpu).all()
    np.testing.assert_allclose(context_cpu,context_gpu,atol=5e-6,rtol=2e-5)
    np.testing.assert_array_equal(context_gpu[~valid],0)
    passed('full-row CPU vs actual CUDA coarse interpolation','decoder bundle only',rows=len(vertex),in_bounds=int(valid.sum()),out_of_bounds=int((~valid).sum()),
        max_abs_error=float(np.max(np.abs(context_cpu-context_gpu))),atol=5e-6,rtol=2e-5,canonical_context='GPU float32')
    # Validate fine vertex locations against L4 interpolation without using L4 for context construction.
    sys.path.insert(0,str(repo));from hashencoder.hashgrid import _hash_encode
    fine_reconstructed=dequantize(fine_q,qparams(4));grid=torch.zeros((c,2),device='cuda');grid[b:c]=torch.from_numpy(fine_reconstructed).cuda()
    off=torch.tensor(offsets[:6],device='cuda',dtype=torch.int32);errors=[]
    with torch.no_grad():
        points=u[valid]
        for j in range(0,len(points),8192):
            actual=_hash_encode.apply(torch.from_numpy(points[j:j+8192]).cuda(),grid,off,q,base,False).reshape(-1,5,2)[:,4].cpu().numpy()
            expected=fine_reconstructed[valid][j:j+8192]
            errors.append(float(np.max(np.abs(actual-expected))))
            np.testing.assert_allclose(actual,expected,atol=1e-5,rtol=3e-5)
    passed('fine vertex feature lookup parity (validation only)','existing fine symbols and original L4 offsets',in_bounds=int(valid.sum()),max_abs_error=max(errors),atol=1e-5,rtol=3e-5)
    # Independent GPU fixtures exercise real upstream interpolation on small quantized grids.
    from .tests import metadata
    toy=metadata((5,5,5),(4.,4.,4.));v=dense_vertices(27,[3,3,3]);toy_raw=np.column_stack((v[:,0]+2*v[:,1]-3*v[:,2],np.full(27,7))).astype(np.float32)
    tq,tp=quantize(toy_raw,8);toy['coarse']['quantization']=tp
    toy['implementation']={'repo':'external/Grid4D-audit-clean','coarse_prefix_offsets':[0,27,54,81,108],
        'base_resolution':[3.,3.,3.],'per_level_scale':[1.,1.,1.]}
    toy_cpu=cpu_context(toy,tq);toy_gpu=gpu_context(toy,tq)
    np.testing.assert_allclose(toy_cpu,toy_gpu,atol=2e-6,rtol=2e-5)
    passed('small synthetic grid GPU lookup parity','known 3^3 coarse -> 5^3 fine fixture with existing quantizer',rows=125,max_abs_error=float(np.max(np.abs(toy_cpu-toy_gpu))))
    command=[sys.executable,'-m','research.hashgrid_analysis.xyz34.decoder','--bundle',str(bundle),'--output',str(out/'decoder-replay.npz'),'--gpu']
    with (out/'decoder-replay.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,check=True)
    replay=np.load(out/'decoder-replay.npz',allow_pickle=False)
    np.testing.assert_array_equal(replay['coarse_context_cpu'],context_cpu);np.testing.assert_array_equal(replay['coarse_context_gpu'],context_gpu)
    audit=read(out/'decoder-replay.audit.json');assert not audit['blocked_reads'] and not audit['checkpoint_or_fine_payload_read']
    passed('fresh-process decoder reproducibility and read audit','coarse_symbols.npy + decoder_metadata.json only',GPU_bitwise_equal=True,CPU_bitwise_equal=True,audit='decoder-replay.audit.json')
    # Build every target record after the context-only decoder has completed.
    local=np.arange(c-b,dtype=np.int64);global_rows=b+local
    arrays={'fine_slot_index':local,'fine_global_row_index':global_rows,'vertex_indices':vertex,'normalized_coordinates':u,
        'normalized_coordinates_float64':exact,'lookup_in_bounds':valid,'coarse_context':context_gpu,'coarse_context_cpu':context_cpu,
        'fine_symbols':fine_q,'fine_features_dequantized':fine_reconstructed}
    np.savez_compressed(out/'pairs.npz',**arrays)
    fields=['fine_slot_index','fine_global_row_index','vertex_x','vertex_y','vertex_z','u_x','u_y','u_z','lookup_in_bounds',
        'coarse_context_0','coarse_context_1','fine_symbol_0','fine_symbol_1','fine_feature_dequantized_0','fine_feature_dequantized_1']
    with (out/'pairs.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(fields)
        for i in local:
            writer.writerow([int(i),int(global_rows[i]),*vertex[i].tolist(),*u[i].tolist(),int(valid[i]),*context_gpu[i].tolist(),*fine_q[i].tolist(),*fine_reconstructed[i].tolist()])
    with (out/'pairs.csv').open() as f:
        reader=csv.DictReader(f);count=0
        for count,r in enumerate(reader,1):
            i=count-1;assert int(r['fine_slot_index'])==i and int(r['fine_global_row_index'])==b+i
            assert [float(r['coarse_context_0']),float(r['coarse_context_1'])]==context_gpu[i].tolist()
            assert [int(r['fine_symbol_0']),int(r['fine_symbol_1'])]==fine_q[i].tolist()
        assert count==c-b
    passed('all fine rows exactly once and CSV/NPZ parity','pairs.csv + pairs.npz',rows=c-b,no_padding=True,no_collisions=True)
    suite=unittest.defaultTestLoader.loadTestsFromName('research.hashgrid_analysis.xyz34.tests')
    with (out/'tests.log').open('w') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    assert result.wasSuccessful();passed('independent synthetic CPU/quantizer tests','xyz34/tests.py',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors))
    assert digest(checkpoint)==source_hash and digest(study/g['payload']['file'])==g['payload']['sha256']
    passed('source checkpoint and quantized artifacts unchanged','original checkpoint + quantized payload hashes')
    csv_write(out/'checks.csv',checks);write(out/'validation.json',{'status':'PASS','checks':checks,'tests':result.testsRun})
    (out/'validation.log').write_text('\n'.join(r['status']+' '+r['test']+' input='+r['input'] for r in checks)+'\n')
    examples=[0,1,59,3540,((29*59+29)*59+29),int(np.flatnonzero(~valid)[0]),len(local)-1]
    write(out/'examples.json',[{field:value for field,value in zip(fields,[int(i),int(global_rows[i]),*vertex[i].tolist(),*u[i].tolist(),int(valid[i]),*context_gpu[i].tolist(),*fine_q[i].tolist(),*fine_reconstructed[i].tolist()])} for i in examples])
    write(out/'manifest.json',{'status':'PAIRS VERIFIED','checkpoint_sha256':source_hash,'checkpoint':str(checkpoint),'scope':args.scope,
        'rows':c-b,'in_bounds':int(valid.sum()),'out_of_bounds':int((~valid).sum()),'coarse_rows':b-a,'seconds':time.perf_counter()-start,
        'pair_sha256':digest(out/'pairs.npz'),'csv_sha256':digest(out/'pairs.csv'),'fine_symbols_sha256':hashlib.sha256(fine_q.tobytes()).hexdigest(),
        'metadata':meta,'source_code_sha256':{f.name:digest(f) for f in Path(__file__).parent.glob('*.py')},
        'environment':{'python':sys.version,'torch':torch.__version__,'numpy':np.__version__,'GPU':torch.cuda.get_device_name()}})
    print('PAIRS VERIFIED:',c-b,'rows;',int(valid.sum()),'in-bounds;',int((~valid).sum()),'OOB',flush=True)

if __name__=='__main__':main()
