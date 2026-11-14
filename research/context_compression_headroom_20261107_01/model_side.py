"""Model-only diagnostic transport; no entropy payload or PMF optimization."""
from __future__ import annotations
import hashlib
import struct
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
import numpy as np
from research.experiment_bench.models import validate_frequencies
from research.experiment_bench.pmf_clustering.transport import _mass_bytes
from research.experiment_bench.hashed_interlevel.dry_model import (
    _json_bytes, _json_load, _threshold_bytes, _threshold_load,
)

STORAGES = ('dense_u32', 'packed_u16', 'sparse_default_u16')
HEADER = struct.Struct('<4sBBH4I')
MAGIC = b'HCDM'


def serialize(masses, thresholds, specification, row_counts, storage):
    f = np.asarray(masses)
    if f.dtype != np.uint32 or f.ndim != 2 or not 2 <= len(f) <= 20:
        raise ValueError('Expected uint32 PMFs with2..20 rows')
    validate_frequencies(f)
    if storage not in STORAGES or len(row_counts) != 2 or sum(row_counts) != len(f):
        raise ValueError('Invalid model transport/mapping')
    if any(type(c) is not int or not 1 <= c <= 10 for c in row_counts):
        raise ValueError('Invalid channel class count')
    mapping = bytes(row_counts) + bytes(range(len(f)))
    parts = (_mass_bytes(f, storage), _threshold_bytes(thresholds), mapping,
             _json_bytes(specification))
    body = HEADER.pack(MAGIC, 1, STORAGES.index(storage) + 1, len(f),
                       *(len(p) for p in parts)) + b''.join(parts)
    return body + hashlib.sha256(body).digest()


def deserialize(data):
    if not isinstance(data, bytes) or len(data) < HEADER.size + 32:
        raise ValueError('Truncated model-only file')
    if hashlib.sha256(data[:-32]).digest() != data[-32:]:
        raise ValueError('Model integrity mismatch')
    magic, version, sid, rows, *lengths = HEADER.unpack_from(data)
    if magic != MAGIC or version != 1 or sid not in (1, 2, 3) or not 2 <= rows <= 20:
        raise ValueError('Invalid model-only header')
    if any(n > 1048576 for n in lengths) or HEADER.size + sum(lengths) + 32 != len(data):
        raise ValueError('Invalid model-only section lengths')
    parts = []; pos = HEADER.size
    for n in lengths:
        parts.append(data[pos:pos+n]); pos += n
    raw, thresholds, mapping, spec = parts
    storage = STORAGES[sid-1]
    if len(mapping) != 2 + rows or mapping[2:] != bytes(range(rows)):
        raise ValueError('Noncanonical mapping')
    row_counts = list(mapping[:2])
    if any(not 1 <= c <= 10 for c in row_counts) or sum(row_counts) != rows:
        raise ValueError('Invalid mapping counts')
    if sid in (1, 2):
        width = 4 if sid == 1 else 2
        if len(raw) != rows * 256 * width:
            raise ValueError('Dense model length')
        f = np.frombuffer(raw, dtype='<u4' if width == 4 else '<u2').reshape(rows, 256).astype(np.uint32)
    else:
        f = np.empty((rows, 256), np.uint32); pos = 0
        for row in f:
            if pos + 4 > len(raw): raise ValueError('Sparse header truncated')
            default, count = struct.unpack_from('<HH', raw, pos); pos += 4
            if not default or count > 255 or pos + count * 3 > len(raw):
                raise ValueError('Sparse row invalid')
            row.fill(default); previous = -1
            for _ in range(count):
                symbol, mass = struct.unpack_from('<BH', raw, pos); pos += 3
                if symbol <= previous or mass == 0 or mass == default:
                    raise ValueError('Sparse exception invalid')
                previous = symbol; row[symbol] = mass
        if pos != len(raw): raise ValueError('Extra sparse bytes')
    validate_frequencies(f)
    t = _threshold_load(thresholds); s = _json_load(spec)
    if serialize(f, t, s, row_counts, storage) != data:
        raise ValueError('Noncanonical model-only representation')
    return f, t, s, row_counts, storage


def sizes(data):
    _, _, _, row_counts, storage = deserialize(data)
    *_, nm, ne, nmap, ns = HEADER.unpack_from(data)
    return {'storage': storage, 'pmf_rows': sum(row_counts), 'pmf_bytes': nm,
            'threshold_bytes': ne, 'mapping_bytes': nmap, 'specification_bytes': ns,
            'framing_bytes': HEADER.size + 32, 'side_information_bytes': len(data)}


def choose(masses, thresholds, specification, row_counts):
    candidates = {s: serialize(masses, thresholds, specification, row_counts, s) for s in STORAGES}
    measured = {s: sizes(b) for s, b in candidates.items()}
    selected = min(STORAGES, key=lambda s: len(candidates[s]))
    return candidates[selected], measured
