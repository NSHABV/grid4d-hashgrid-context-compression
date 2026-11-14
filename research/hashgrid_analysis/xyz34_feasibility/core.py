import json
import numpy as np
from research.experiment_bench.models import frequencies,TOTAL,validate_frequencies
from research.hashgrid_analysis.statistics import joint_metrics

MODELS=[('IID',None,0),('Boundary',None,0)]+[(f'Spatial-{k}',method,k) for method in ('uniform','quantile') for k in (4,8,16)]

def block_ids(vertices,width):
    v=np.asarray(vertices,dtype=np.int64)
    if v.ndim!=2 or v.shape[1]!=3 or width<1 or np.any(v<0):raise ValueError('Invalid vertices/width')
    shape=v.max(axis=0)//width+1;b=v//width
    return (b[:,0]+shape[0]*b[:,1]+shape[0]*shape[1]*b[:,2]).astype(np.int64)

def split_rows(vertices,seed,kind):
    n=len(vertices);rng=np.random.default_rng(seed)
    groups=np.arange(n) if kind=='random' else block_ids(vertices,int(kind.split('-')[1]))
    units=np.unique(groups);order=rng.permutation(units);nt=int(np.floor(.2*len(units)));nv=int(np.floor(.16*len(units)))
    if min(nt,nv)<1:raise ValueError('Not enough splitting units')
    test_units=order[:nt];val_units=order[nt:nt+nv]
    test=np.isin(groups,test_units);validation=np.isin(groups,val_units);train=~(test|validation)
    assert not np.any(test&validation) and not np.any(train&(test|validation))
    assert np.all(train|validation|test)
    return {'train':np.flatnonzero(train),'validation':np.flatnonzero(validation),'test':np.flatnonzero(test)},groups

def fit_edges(coarse,inside,train,k,method):
    x=np.asarray(coarse,dtype=np.float64)[train];x=x[np.asarray(inside)[train]]
    if not len(x) or not np.isfinite(x).all():raise ValueError('No finite training interior context')
    if method=='uniform':edges=np.linspace(x.min(),x.max(),k+1)[1:-1]
    elif method=='quantile':edges=np.quantile(x,np.arange(1,k)/k,method='linear')
    else:raise ValueError('Unknown bins')
    if np.any(np.diff(edges)<0):raise ValueError('Unordered bins')
    return edges.astype(np.float64)

def classify(coarse,inside,model,k=0,edges=None):
    inside=np.asarray(inside,dtype=bool)
    if model=='IID':return np.zeros(len(inside),np.int64),1
    if model=='Boundary':return (~inside).astype(np.int64),2
    if edges is None or len(edges)!=k-1:raise ValueError('Invalid spatial boundaries')
    result=np.searchsorted(edges,np.asarray(coarse,dtype=np.float64),side='right').astype(np.int64)
    result[~inside]=k
    return result,k+1

def fit_histogram(symbols,classes,train,nclasses):
    q=np.asarray(symbols)
    if q.dtype!=np.uint8 or q.ndim!=1 or len(classes)!=len(q):raise ValueError('uint8 single-channel symbols expected')
    counts=np.bincount(classes[train]*256+q[train].astype(np.int64),minlength=nclasses*256).reshape(nclasses,256)
    masses=np.stack([frequencies(row) for row in counts]);validate_frequencies(masses)
    analytic=(counts.astype(np.float64)+1)/(counts.sum(axis=1,keepdims=True)+256)
    finite=masses.astype(np.float64)/TOTAL
    assert np.all(finite>0) and np.allclose(finite.sum(axis=1),1,atol=0,rtol=0)
    mi=joint_metrics(counts)['mutual_information']
    interior_mi=0. if nclasses<=2 else joint_metrics(counts[:-1])['mutual_information']
    weighted_interior_mi=interior_mi*(counts[:-1].sum()/counts.sum()) if nclasses>2 else 0.
    return counts,masses,analytic,finite,mi,interior_mi,weighted_interior_mi

def costs(symbols,classes,rows,probabilities):
    p=probabilities[classes[rows],symbols[rows]]
    if not np.isfinite(p).all() or np.any(p<=0) or np.any(p>1):raise ValueError('Invalid predictive probability')
    return -np.log2(p)

def overhead(masses,edges,model,k,method):
    """Projected model bytes, using existing u32 mass format plus hypothetical metadata."""
    nclasses=len(masses);nb=0 if edges is None else len(edges)
    info={'model':model,'bin_method':method,'interior_classes':k,'alphabet':256,'mass_precision':16,
        'coarse_level':3,'fine_level':4,'rounding':'stored_float64_edges_searchsorted_right'}
    metadata=len(json.dumps(info,separators=(',',':'),sort_keys=True).encode('utf-8'))
    bounds=nb*8
    sparse=0
    for row in masses:
        values,count=np.unique(row,return_counts=True);default=values[np.argmax(count)]
        exceptions=int(np.count_nonzero(row!=default))
        # Proposed default u16 + exception count u16 + (symbol u8, mass u16) entries.
        assert row.max()<=65535
        sparse+=4+exceptions*3
    mass_bytes=nclasses*256*4
    return {'dense_u32':mass_bytes+bounds+metadata,'packed_u16':nclasses*256*2+bounds+metadata,
        'sparse_default_u16':sparse+bounds+metadata,'no_overhead':0,
        'components':{'unconditional_mass_bytes':mass_bytes if nclasses==1 else 0,
            'conditional_mass_bytes':mass_bytes if nclasses>1 else 0,'boundary_bytes':bounds,'metadata_bytes':metadata,
            'derived_CDF_in_memory_bytes':nclasses*257*4,'CDF_additional_file_bytes':0,
            'training_count_memory_bytes_not_transmitted':nclasses*256*8},
        'interpretation':'estimated candidate transport; no bitstream produced; CDF derived from masses, not charged twice'}

def bootstrap_plan(vertices,test,seed,reps=1000,width=8):
    blocks=block_ids(vertices,width)[test];ids,inverse=np.unique(blocks,return_inverse=True)
    counts=np.bincount(inverse).astype(np.float64);rng=np.random.default_rng(seed)
    weights=rng.multinomial(len(ids),np.full(len(ids),1/len(ids)),size=reps)
    denominators=weights@counts
    return inverse,weights,denominators,len(ids)

def gain_interval(gain,plan):
    inverse,weights,denominator,n=plan
    sums=np.bincount(inverse,weights=gain,minlength=n)
    draws=(weights@sums)/denominator
    return np.quantile(draws,[.025,.975]).tolist()
