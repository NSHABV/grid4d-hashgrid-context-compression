"""Prespecified coarse-only classes and train-only finite histogram fitting."""
import numpy as np
from research.experiment_bench.models import frequencies, validate_frequencies

ARMS = {'IID':1,'Geometry4':4,'Canonical8':10,'Mean8':10,'Mean4':6,'Mean4Std2':10}


def split_slots(n, seed):
    order = np.random.Generator(np.random.PCG64(seed)).permutation(n)
    nt, nv = int(np.floor(.2*n)), int(np.floor(.16*n))
    return {'test':np.sort(order[:nt]), 'validation':np.sort(order[nt:nt+nv]),
            'train':np.sort(order[nt+nv:])}


def fit_spec(contexts, train, name):
    if name not in ARMS:
        raise ValueError(name)
    spec = {'name':name, 'C':ARMS[name], 'edges':{'primary':[[],[]], 'std':[[],[]]}}
    if name in ('IID','Geometry4'):
        return spec
    active = np.asarray(train)[contexts['geometry'][train] >= 2]
    if not len(active):
        raise ValueError('No active train slots')
    key = 'canonical_features' if name == 'Canonical8' else 'mean'
    k = 4 if name in ('Mean4','Mean4Std2') else 8
    for ch in range(2):
        spec['edges']['primary'][ch] = np.quantile(contexts[key][active,ch].astype(np.float64),
                                                  np.arange(1,k)/k, method='linear').tolist()
        if name == 'Mean4Std2':
            spec['edges']['std'][ch] = [float(np.quantile(contexts['std'][active,ch],.5,method='linear'))]
    return spec


def classify(contexts, spec):
    name, C = spec['name'], spec['C']
    if name not in ARMS or C != ARMS[name]:
        raise ValueError('Invalid model')
    g = np.asarray(contexts['geometry'])
    if g.ndim != 1 or np.any(g>3):
        raise ValueError('Invalid geometry')
    if name == 'IID':
        return np.zeros((len(g),2),np.uint8)
    if name == 'Geometry4':
        return np.repeat(g[:,None],2,axis=1).astype(np.uint8)
    key = 'canonical_features' if name == 'Canonical8' else 'mean'
    k = 4 if name in ('Mean4','Mean4Std2') else 8
    result = np.empty((len(g),2),np.uint8)
    for ch in range(2):
        edges = np.asarray(spec['edges']['primary'][ch],np.float64)
        if len(edges)!=k-1 or not np.isfinite(edges).all() or np.any(np.diff(edges)<0):
            raise ValueError('Invalid primary edges')
        bins = np.searchsorted(edges, contexts[key][:,ch],side='right')
        if name == 'Mean4Std2':
            e = np.asarray(spec['edges']['std'][ch],np.float64)
            if e.shape!=(1,) or not np.isfinite(e).all():
                raise ValueError('Invalid std edge')
            bins = 2*bins+np.searchsorted(e,contexts['std'][:,ch],side='right')
        result[:,ch] = 2+bins
        result[g<2,ch] = g[g<2]
    return result


def fit_masses(q, classes, train, C):
    if q.dtype != np.uint8 or q.shape != classes.shape:
        raise ValueError('Bad targets/classes')
    counts = np.stack([np.bincount(classes[train,ch].astype(np.int64)*256+q[train,ch],
                                  minlength=C*256).reshape(C,256) for ch in range(2)])
    masses = np.stack([[frequencies(row) for row in channel] for channel in counts])
    validate_frequencies(masses.reshape(-1,256))
    return counts,masses


def losses(q, classes, masses, rows):
    return np.column_stack([-np.log2(masses[ch,classes[rows,ch],q[rows,ch]].astype(np.float64)/65536.)
                            for ch in range(2)])


def strata(contexts, rows):
    g, n = contexts['geometry'][rows], contexts['point_count'][rows]
    return {'all':np.ones(len(rows),bool), **{f'G{k}':g==k for k in range(4)},
            'G3_K2':(g==3)&(n==2),'G3_K3':(g==3)&(n==3),'G3_K4plus':(g==3)&(n>=4)}
