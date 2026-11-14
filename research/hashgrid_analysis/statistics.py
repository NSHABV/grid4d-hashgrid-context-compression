"""Pure NumPy referenceable estimators; full counts, explicit sampling elsewhere."""
import numpy as np

def entropy_counts(counts):
    c=np.asarray(counts,dtype=np.float64)
    if np.any(c<0) or not np.isfinite(c).all():raise ValueError('Invalid counts')
    if c.sum()==0:return 0.
    p=c[c>0]/c.sum()
    return float(-(p*np.log2(p)).sum())

def joint_metrics(counts):
    c=np.asarray(counts,dtype=np.float64)
    n=c.sum()
    h0=entropy_counts(c.sum(axis=1));h1=entropy_counts(c.sum(axis=0));hj=entropy_counts(c)
    return {'H_context':h0,'H_target':h1,'H_joint':hj,'H_target_given_context':hj-h0,
        'mutual_information':max(0.,h0+h1-hj),'observations':int(n)}

def pearson(a,b):
    a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64)
    if a.shape!=b.shape or not a.size or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('Invalid pairs')
    a=a-a.mean();b=b-b.mean();den=np.sqrt(np.dot(a,a)*np.dot(b,b))
    return float(np.dot(a,b)/den) if den else None

def histogram(values,edges):
    counts,_=np.histogram(values,bins=edges)
    if int(counts.sum())!=values.size:raise ValueError('Histogram lost observations')
    return counts.tolist()

def describe(values):
    x=np.asarray(values).reshape(-1)
    if not x.size or not np.isfinite(x).all():raise ValueError('Empty/nonfinite values')
    unique,counts=np.unique(x,return_counts=True);order=np.argsort(-counts,kind='stable')[:8]
    q=np.quantile(x,[0,.25,.5,.75,1])
    return {'n':int(x.size),'mean':float(x.mean(dtype=np.float64)),'std':float(x.std(dtype=np.float64)),
        'min':float(x.min()),'max':float(x.max()),'zero_fraction':float((x==0).mean()),'unique':int(unique.size),
        'top_values':[{'value':float(unique[i]),'count':int(counts[i])} for i in order],
        'box':dict(zip(('whislo','q1','med','q3','whishi'),map(float,q)))}

def sample_indices(n,budget,seed):
    return np.sort(np.random.default_rng(seed).choice(n,min(n,budget),replace=False))

def average_ranks(values):
    """Independent small-array rank reference, with average ranks for exact ties."""
    x=np.asarray(values);order=np.argsort(x,kind='stable');sorted_x=x[order]
    starts=np.r_[0,np.flatnonzero(np.diff(sorted_x)!=0)+1];ends=np.r_[starts[1:],len(x)]
    ranked=np.empty(len(x),dtype=np.float64)
    for a,b in zip(starts,ends):ranked[order[a:b]]=(a+b+1)/2
    return ranked

def joint_codes(q0,q1,classes=256):
    counts=np.bincount(q0.astype(np.int64)*256+q1,minlength=classes*256).reshape(classes,256)
    return counts

def conditional_error(counts):
    """Predict q1 by empirical E[q1|class]; diagnostic in-sample, not a coder."""
    c=np.asarray(counts,dtype=np.float64);n=c.sum(axis=1);values=np.arange(c.shape[1])
    means=np.divide(c@values,n,out=np.zeros_like(n),where=n>0)
    mse=np.divide((c*np.square(values[None,:]-means[:,None])).sum(axis=1),n,out=np.zeros_like(n),where=n>0)
    return means,mse
