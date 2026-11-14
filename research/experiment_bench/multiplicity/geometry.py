"""Geometry-only Count6 contract. No symbols, feature values or occupancy inputs."""
import numpy as np

HASH = {'name':'grid4d-u32-stride-or-xor-v1','primes':[1,2654435761,805459861],
        'mask':4294967295,'modulo':'allocated_rows'}
CONVENTION = 'nominal-v-in-[0,R);point-v<=floor(scale);u=f32(v)/f32(scale)'

def specification(meta):
    return {'version':1,'fine':meta['fine'],'hash':HASH,'geometry_convention':CONVENTION}

def slots(vertices, resolution, rows):
    v=np.asarray(vertices,np.uint64)
    if v.ndim!=2 or v.shape[1]!=3 or rows<1: raise ValueError('Bad vertices/rows')
    stride=1; index=np.zeros(len(v),np.uint64)
    for axis in range(3):
        if stride>rows: break
        index=(index+v[:,axis]*stride)&np.uint64(0xffffffff)
        stride=(stride*int(resolution[axis]))&0xffffffff
    if stride>rows:
        index=(v[:,0] ^ v[:,1]*np.uint64(2654435761) ^ v[:,2]*np.uint64(805459861))&np.uint64(0xffffffff)
    return (index%rows).astype(np.int64)

def count6_classes(nominal_count,point_count):
    n,p=np.asarray(nominal_count),np.asarray(point_count)
    if (n.ndim!=1 or n.shape!=p.shape or not np.issubdtype(n.dtype,np.integer)
        or not np.issubdtype(p.dtype,np.integer) or np.any(p<0) or np.any(n<p)):
        raise ValueError('Invalid integer correspondence counts')
    c=np.where(n==0,0,np.where(p==0,1,np.minimum(p+1,5))).astype(np.uint8)
    return np.repeat(c[:,None],2,axis=1)

def geometry4_classes(nominal_count,point_count):
    c=count6_classes(nominal_count,point_count)
    return np.minimum(c,3).astype(np.uint8)

def compute_geometry(spec,chunk=65536,vertex_limit=None):
    if spec.get('version')!=1 or spec.get('hash')!=HASH or spec.get('geometry_convention')!=CONVENTION:
        raise ValueError('Unsupported geometry specification')
    g=spec['fine']; r=np.asarray(g['lookup_resolution'],np.int64); s=np.asarray(g['scale'],np.float32)
    rows=g['rows']
    if (r.shape!=(3,) or s.shape!=(3,) or not np.isfinite(s).all() or np.any(s<=0)
        or not np.array_equal(np.ceil(s).astype(np.int64)+1,r) or rows<1
        or g['offset_end']-g['offset_start']!=rows or chunk<1): raise ValueError('Bad geometry')
    total=int(np.prod(r)); total=min(total,vertex_limit) if vertex_limit is not None else total
    nominal=np.zeros(rows,np.int64); point=np.zeros(rows,np.int64)
    for start in range(0,total,chunk):
        i=np.arange(start,min(start+chunk,total),dtype=np.int64)
        v=np.column_stack((i%r[0],i//r[0]%r[1],i//(r[0]*r[1])))
        h=slots(v,r,rows); e=np.all(v<=np.floor(s).astype(np.int64),axis=1)
        nominal+=np.bincount(h,minlength=rows)
        point+=np.bincount(h[e],minlength=rows)
    return {'slot_index':np.arange(rows,dtype=np.int64),'nominal_count':nominal,'point_count':point,
            'Geometry4':geometry4_classes(nominal,point),'Count6':count6_classes(nominal,point)}
