"""CUDA-verified vertex indexing and smoothstep interpolation for diagnostics."""
import numpy as np

def slots(vertices,resolution,rows):
    v=np.asarray(vertices,dtype=np.uint64)
    if v.ndim!=2 or v.shape[1]!=3 or rows<1:raise ValueError('Invalid vertices/table')
    stride=1;index=np.zeros(len(v),dtype=np.uint64)
    for d in range(3):
        if stride>rows:break
        index=(index+v[:,d]*stride)&np.uint64(0xffffffff)
        stride=(stride*int(resolution[d]))&0xffffffff
    if stride>rows:
        index=(v[:,0]^(v[:,1]*np.uint64(2654435761))^(v[:,2]*np.uint64(805459861)))&np.uint64(0xffffffff)
    return (index%rows).astype(np.int64)

def corners(coordinates,scale):
    u=np.asarray(coordinates,dtype=np.float32)
    if u.ndim!=2 or u.shape[1]!=3 or not np.isfinite(u).all() or np.any(u<0) or np.any(u>1):raise ValueError('Normalized [0,1]^3 expected')
    position=u*np.asarray(scale,dtype=np.float32)
    base=np.floor(position).astype(np.int64);fraction=position-base.astype(np.float32)
    smooth=fraction*fraction*(np.float32(3)-np.float32(2)*fraction)
    vertices=[];weights=[]
    for i in range(8):
        bits=np.array([(i>>d)&1 for d in range(3)])
        vertices.append(base+bits)
        weights.append(np.prod(np.where(bits,smooth,np.float32(1)-smooth),axis=1,dtype=np.float32))
    return np.stack(vertices,axis=1),np.stack(weights,axis=1)

def lookup(coordinates,table,scale,resolution):
    vertices,weights=corners(coordinates,scale)
    indices=slots(vertices.reshape(-1,3),resolution,len(table)).reshape(-1,8)
    # Match CUDA accumulation order; tolerances allow fused CUDA arithmetic.
    result=np.zeros((len(coordinates),2),dtype=np.float32)
    for i in range(8):result+=weights[:,i,None]*table[indices[:,i]]
    return result

def vertex_sample(resolution,budget,seed,enumeration_limit):
    total=int(np.prod(resolution,dtype=np.int64))
    if total<=enumeration_limit:linear=np.arange(total,dtype=np.int64);mode='exact full nominal vertex lattice'
    else:linear=np.sort(np.random.default_rng(seed).choice(total,min(total,budget),replace=False));mode='uniform nominal vertices without replacement; observed lower bound'
    r=np.asarray(resolution,dtype=np.int64)
    vertices=np.column_stack((linear%r[0],(linear//r[0])%r[1],linear//(r[0]*r[1])))
    return vertices,mode,total

def multiplicity(vertices,resolution,rows):
    unique=np.unique(vertices,axis=0)
    counts=np.bincount(slots(unique,resolution,rows),minlength=rows)
    return unique,counts
