"""Rebuild every context using only public metadata and decoded L3 symbols."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
from research.grid4d.codec import dequantize
from research.hashgrid_analysis.mapping import lookup
from research.hashgrid_analysis.common import ROOT,read,digest

def dense_vertices(rows,resolution):
    r=np.asarray(resolution,dtype=np.int64)
    if r.shape!=(3,) or np.any(r<2) or int(np.prod(r))!=rows:
        raise ValueError('Only unpadded, collision-free dense 3D levels are supported')
    i=np.arange(rows,dtype=np.int64)
    return np.column_stack((i%r[0],(i//r[0])%r[1],i//(r[0]*r[1]))).astype(np.int32)

def geometry(meta):
    fine=meta['fine'];vertices=dense_vertices(fine['rows'],fine['lookup_resolution'])
    scale=np.asarray(fine['scale'],dtype=np.float32)
    if scale.shape!=(3,) or not np.isfinite(scale).all() or np.any(scale<=0):raise ValueError('Invalid scale')
    exact=vertices.astype(np.float64)/scale.astype(np.float64)
    coordinates=(vertices.astype(np.float32)/scale).astype(np.float32)
    valid=((coordinates>=0)&(coordinates<=1)).all(axis=1)
    return vertices,coordinates,exact,valid

def decoded_coarse(meta,symbols):
    if symbols.dtype!=np.uint8 or list(symbols.shape)!=[meta['coarse']['rows'],2]:raise ValueError('Invalid coarse symbols')
    return dequantize(symbols,meta['coarse']['quantization'])

def cpu_context(meta,symbols):
    table=decoded_coarse(meta,symbols)
    _,coordinates,_,valid=geometry(meta)
    result=np.zeros((len(coordinates),2),dtype=np.float32)
    c=meta['coarse']
    result[valid]=lookup(coordinates[valid],table,c['scale'],c['lookup_resolution'])
    return result

def gpu_context(meta,symbols):
    import torch
    sys.path.insert(0,str(ROOT/meta['implementation']['repo']))
    from hashencoder.hashgrid import _hash_encode
    table=decoded_coarse(meta,symbols)
    _,coordinates,_,_=geometry(meta)
    offsets=np.asarray(meta['implementation']['coarse_prefix_offsets'],dtype=np.int32)
    if offsets[-1]-offsets[-2]!=len(table) or len(offsets)!=5:raise ValueError('Invalid L3 offsets')
    # No L4 or later embeddings exist in this tensor. L0..L2 placeholders do not affect L3.
    prefix=torch.zeros((int(offsets[-1]),2),device='cuda',dtype=torch.float32)
    prefix[int(offsets[-2]):]=torch.from_numpy(table).cuda()
    offsets_gpu=torch.from_numpy(offsets).cuda()
    q=torch.tensor(meta['implementation']['per_level_scale'],device='cuda',dtype=torch.float32)
    base=torch.tensor(meta['implementation']['base_resolution'],device='cuda',dtype=torch.float32)
    output=[]
    with torch.no_grad():
        for a in range(0,len(coordinates),8192):
            u=torch.from_numpy(coordinates[a:a+8192]).cuda()
            result=_hash_encode.apply(u,prefix,offsets_gpu,q,base,False).reshape(len(u),4,2)
            output.append(result[:,3].cpu().numpy())
    return np.concatenate(output)

def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--output',required=True);p.add_argument('--gpu',action='store_true')
    args=p.parse_args();bundle=Path(args.bundle).resolve();destination=Path(args.output).resolve()
    allowed={bundle/'decoder_metadata.json',bundle/'coarse_symbols.npy'};reads=[];blocked=[]
    protected=[ROOT/'outputs',ROOT/'experiments',ROOT/'research/experiment_bench/reference-study',bundle.parent]
    def audit(event,values):
        if event!='open' or not isinstance(values[0],(str,bytes)):return
        path=Path(values[0]).resolve();mode=values[1]
        # Read audit after imports. Output writes and implementation/library loads are allowed.
        is_read=mode is None or ('r' in mode and '+' not in mode)
        if not is_read:return
        if any(path.is_relative_to(root.resolve()) for root in protected):
            if path not in allowed:
                blocked.append(str(path));raise PermissionError('Decoder attempted forbidden research-data read: '+str(path))
            reads.append(str(path))
    sys.addaudithook(audit)
    meta=read(bundle/'decoder_metadata.json');symbols=np.load(bundle/'coarse_symbols.npy',allow_pickle=False)
    if digest(bundle/'coarse_symbols.npy')!=meta['coarse_symbols_sha256']:raise ValueError('Coarse payload SHA mismatch')
    cpu=cpu_context(meta,symbols);arrays={'coarse_context_cpu':cpu}
    if args.gpu:arrays['coarse_context_gpu']=gpu_context(meta,symbols)
    np.savez_compressed(destination,**arrays)
    destination.with_suffix('.audit.json').write_text(json.dumps({'status':'PASS','pid':__import__('os').getpid(),
        'allowed_artifact_reads':sorted(set(reads)),'blocked_reads':blocked,'checkpoint_or_fine_payload_read':False,
        'rows':len(cpu),'GPU':args.gpu},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
