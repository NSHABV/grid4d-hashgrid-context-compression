"""Canonical CPU float32 context; no checkpoint, fine targets, or file I/O."""
import numpy as np
from research.grid4d.codec import dequantize
from research.hashgrid_analysis.xyz34.decoder import geometry

ARITHMETIC='cpu-f32-separate-ufuncs-corner-order-0-to-7-v1'

def context(meta,coarse):
    table=dequantize(coarse,meta['coarse']['quantization'])
    if coarse.dtype!=np.uint8 or list(coarse.shape)!=[meta['coarse']['rows'],2]:raise ValueError('Invalid L3')
    _,u,_,inside=geometry(meta)
    result=np.zeros((len(u),2),np.float32)
    pos=np.multiply(u[inside],np.asarray(meta['coarse']['scale'],np.float32),dtype=np.float32)
    base=np.floor(pos).astype(np.int64)
    f=np.subtract(pos,base.astype(np.float32),dtype=np.float32)
    s=np.multiply(np.multiply(f,f,dtype=np.float32),np.subtract(np.float32(3),np.multiply(np.float32(2),f,dtype=np.float32),dtype=np.float32),dtype=np.float32)
    out=np.zeros((len(pos),2),np.float32);r=meta['coarse']['lookup_resolution']
    for corner in range(8):
        bit=np.array([(corner>>d)&1 for d in range(3)])
        v=base+bit;index=v[:,0]+r[0]*v[:,1]+r[0]*r[1]*v[:,2]
        if index.min()<0 or index.max()>=len(table):raise ValueError('Non-dense coarse lookup')
        w=np.ones(len(pos),np.float32)
        for d in range(3):
            term=s[:,d] if bit[d] else np.subtract(np.float32(1),s[:,d],dtype=np.float32)
            w=np.multiply(w,term,dtype=np.float32)
        out=np.add(out,np.multiply(w[:,None],table[index],dtype=np.float32),dtype=np.float32)
    result[inside]=out
    return result,inside

def boundaries(values,inside):
    # np1.21 interpolation='linear' is the equivalent of later method='linear'.
    return np.stack([np.quantile(values[inside,ch].astype(np.float64),np.arange(1,8)/8,interpolation='linear') for ch in range(2)]).astype('<f8')

def classes(meta,coarse,model,edges=None):
    _,_,_,inside=geometry(meta);n=len(inside)
    if model=='iid':return np.zeros((n,2),np.uint8),inside,None
    if model=='boundary':return np.repeat((~inside)[:,None],2,axis=1).astype(np.uint8),inside,None
    if model!='spatial8' or edges is None or np.asarray(edges).shape!=(2,7):raise ValueError('Invalid context specification')
    edges=np.asarray(edges,np.float64)
    if not np.isfinite(edges).all() or np.any(np.diff(edges,axis=1)<0):raise ValueError('Invalid edges')
    values,inside=context(meta,coarse)
    result=np.column_stack([np.searchsorted(edges[ch],values[:,ch].astype(np.float64),side='right') for ch in range(2)]).astype(np.uint8)
    result[~inside]=8
    return result,inside,values
