"""Versioned canonical CPU context from coarse uint8 symbols and public geometry.

No checkpoint/target loading, quantization, probability fitting or coding.
All aggregation updates follow ascending fine-lattice x-fast ordinal.
"""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ARITHMETIC = 'cpu-f32-separate-ufunc-corner0to7-anchor-f64-addat-xfast-popstd-v1'
DEQUANT_SOURCE = ROOT / 'research/grid4d/codec.py'

# Use the existing dequantizer body verbatim without importing its torch loader.
# This allows a lightweight decoder with no checkpoint-capable dependency.
_tree = ast.parse(DEQUANT_SOURCE.read_text(encoding='utf-8'))
_node = next(n for n in _tree.body if isinstance(n, ast.FunctionDef) and n.name == 'dequantize')
_ns = {'np': np}
exec(compile(ast.Module(body=[_node], type_ignores=[]), str(DEQUANT_SOURCE), 'exec'), _ns)
dequantize_symbols = _ns['dequantize']
del _tree, _node, _ns

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()

def load_bundle(folder):
    folder = Path(folder)
    meta = json.loads((folder / 'decoder_metadata.json').read_text(encoding='utf-8'))
    q = np.load(folder / 'coarse_symbols.npy', allow_pickle=False)
    if sha(folder / 'coarse_symbols.npy') != meta['coarse_symbols_sha256']:
        raise ValueError('Coarse bundle SHA mismatch')
    validate_meta(meta, q)
    return meta, q

def validate_meta(meta, q):
    if meta['version'] != 1 or meta['arithmetic'] != ARITHMETIC or meta['grid'] != 'xyz':
        raise ValueError('Unsupported context specification')
    for role in ('coarse', 'fine'):
        g = meta[role]
        scale = np.asarray(g['scale'], np.float32)
        r = np.asarray(g['lookup_resolution'], np.int64)
        if (scale.shape != (3,) or not np.isfinite(scale).all() or np.any(scale <= 0)
                or not np.array_equal(np.ceil(scale).astype(np.int64)+1, r)
                or g['offset_end']-g['offset_start'] != g['rows'] or g['rows'] < 1):
            raise ValueError('Invalid runtime geometry')
    if q.dtype != np.uint8 or list(q.shape) != [meta['coarse']['rows'], 2]:
        raise ValueError('Invalid coarse symbols')
    if meta['coarse']['quantization']['bits'] != 8:
        raise ValueError('Only existing table8 symbols allowed')

def slot_indices(vertices, resolution, rows):
    v = np.asarray(vertices, dtype=np.uint64)
    if v.ndim != 2 or v.shape[1] != 3 or rows < 1:
        raise ValueError('Invalid slot input')
    stride = 1
    index = np.zeros(len(v), np.uint64)
    for axis in range(3):
        if stride > rows:
            break
        index = (index + v[:,axis] * stride) & np.uint64(0xffffffff)
        stride = (stride * int(resolution[axis])) & 0xffffffff
    if stride > rows:
        index = (v[:,0] ^ (v[:,1]*np.uint64(2654435761))
                 ^ (v[:,2]*np.uint64(805459861))) & np.uint64(0xffffffff)
    return (index % rows).astype(np.int64)

def lookup_cpu(coordinates, table, scale, resolution):
    """Separate f32 operations, no FMA; CUDA OOB-zero and index modulo semantics."""
    u = np.asarray(coordinates, np.float32)
    table = np.asarray(table, np.float32)
    if u.ndim != 2 or u.shape[1] != 3 or not np.isfinite(u).all() or table.shape[1:] != (2,):
        raise ValueError('Invalid lookup data')
    result = np.zeros((len(u), 2), np.float32)
    valid = ((u >= 0) & (u <= 1)).all(axis=1)
    if not valid.any():
        return result
    position = np.multiply(u[valid], np.asarray(scale,np.float32), dtype=np.float32)
    base = np.floor(position).astype(np.int64)
    f = np.subtract(position,base.astype(np.float32),dtype=np.float32)
    s = np.multiply(np.multiply(f,f,dtype=np.float32),
        np.subtract(np.float32(3),np.multiply(np.float32(2),f,dtype=np.float32),dtype=np.float32),dtype=np.float32)
    accum = np.zeros((len(base),2),np.float32)
    for corner in range(8):
        bits = np.array([(corner >> d) & 1 for d in range(3)],np.int64)
        index = slot_indices(base+bits,resolution,len(table))
        weight = np.ones(len(base),np.float32)
        for d in range(3):
            term = s[:,d] if bits[d] else np.subtract(np.float32(1),s[:,d],dtype=np.float32)
            weight = np.multiply(weight,term,dtype=np.float32)
        accum = np.add(accum,np.multiply(weight[:,None],table[index],dtype=np.float32),dtype=np.float32)
    result[valid] = accum
    return result

def vertices_from_ordinals(linear, resolution):
    r = np.asarray(resolution,np.int64)
    linear = np.asarray(linear,np.int64)
    return np.column_stack((linear % r[0],(linear//r[0]) % r[1],linear//(r[0]*r[1])))

def compute_context(meta, coarse_symbols, chunk=65536, vertex_limit=None):
    """All stored slots, optionally an ascending prefix for cost pilot only.

    Moments use canonical-feature anchored differences in f64. This reduces
    cancellation, makes exact constant/singleton Std zero, and keeps updates in
    the same order independent of chunks. The arrays never contain fine labels.
    """
    validate_meta(meta,coarse_symbols)
    if not isinstance(chunk,int) or chunk < 1:
        raise ValueError('Invalid chunk')
    c,g = meta['coarse'],meta['fine']
    table = dequantize_symbols(coarse_symbols,c['quantization'])
    rows = g['rows']
    r = np.asarray(g['lookup_resolution'],np.int64)
    scale = np.asarray(g['scale'],np.float32)
    eligible_r = np.floor(scale).astype(np.int64)+1
    total = int(np.prod(r,dtype=np.int64))
    if vertex_limit is not None:
        total = min(total,int(vertex_limit))
    nominal = np.zeros(rows,np.int64)
    eligible = np.zeros(rows,np.int64)
    ordinal = np.full(rows,np.iinfo(np.int64).max,np.int64)
    canonical = np.zeros((rows,2),np.float32)
    delta_sum = np.zeros((rows,2),np.float64)
    delta_squared = np.zeros((rows,2),np.float64)
    for start in range(0,total,chunk):
        linear = np.arange(start,min(start+chunk,total),dtype=np.int64)
        v = vertices_from_ordinals(linear,r)
        slots = slot_indices(v,r,rows)
        nominal += np.bincount(slots,minlength=rows)
        valid = (v < eligible_r).all(axis=1)
        if not valid.any():
            continue
        v,linear,index = v[valid],linear[valid],slots[valid]
        eligible += np.bincount(index,minlength=rows)
        coordinates = np.divide(v.astype(np.float32),scale,dtype=np.float32)
        features = lookup_cpu(coordinates,table,c['scale'],c['lookup_resolution'])
        np.minimum.at(ordinal,index,linear)
        first = ordinal[index] == linear
        canonical[index[first]] = features[first]
        delta = features.astype(np.float64)-canonical[index].astype(np.float64)
        for channel in range(2):
            np.add.at(delta_sum[:,channel],index,delta[:,channel])
            np.add.at(delta_squared[:,channel],index,delta[:,channel]*delta[:,channel])
    inside = eligible > 0
    geometry = np.zeros(rows,np.uint8)
    geometry[(nominal > 0) & ~inside] = 1
    geometry[eligible == 1] = 2
    geometry[eligible > 1] = 3
    ordinal[~inside] = -1
    vertex = np.full((rows,3),-1,np.int32)
    vertex[inside] = vertices_from_ordinals(ordinal[inside],r).astype(np.int32)
    coordinates = np.zeros((rows,3),np.float32)
    coordinates[inside] = np.divide(vertex[inside].astype(np.float32),scale,dtype=np.float32)
    mean,std = np.zeros((rows,2),np.float64),np.zeros((rows,2),np.float64)
    centered_mean = delta_sum[inside] / eligible[inside,None]
    mean[inside] = canonical[inside].astype(np.float64)+centered_mean
    variance = delta_squared[inside]/eligible[inside,None] - centered_mean*centered_mean
    if np.any(variance < -1e-12):
        raise ArithmeticError('Unexpected negative population variance')
    std[inside] = np.sqrt(np.maximum(variance,0))
    std[eligible == 1] = 0
    return {'slot_index':np.arange(rows,dtype=np.int64),
        'global_embedding_row':np.arange(rows,dtype=np.int64)+g['offset_start'],
        'nominal_count':nominal,'point_count':eligible,'geometry':geometry,
        'canonical_ordinal':ordinal,'canonical_vertex':vertex,'canonical_coordinates':coordinates,
        'canonical_features':canonical,'mean':mean,'std':std,'representative_valid':inside}

def arrays_sha(arrays):
    h = hashlib.sha256()
    for key in sorted(arrays):
        x = np.ascontiguousarray(arrays[key])
        h.update(key.encode());h.update(x.dtype.str.encode());h.update(str(x.shape).encode());h.update(x.tobytes())
    return h.hexdigest()
