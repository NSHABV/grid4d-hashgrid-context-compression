"""H4G4PAIR v1 standalone codec; no optimizer or histogram dependency here."""
from __future__ import annotations

import copy
import hashlib
import struct
import time
import numpy as np
from research.experiment_bench.hashed_pair import engine
from research.experiment_bench.hashed_pair_v3 import format as legacy
from research.experiment_bench.hashed_interlevel import dry_model as dm
from . import geometry, transport

MAGIC = b'H4G4PAIR'
PREFIX = struct.Struct('<8sH5Q')
NAMES = ('metadata', 'coarse_model', 'fine_model', 'coarse_payload', 'fine_payload')
BOUNDS = (64000, 1 << 20, transport.MAX_BYTES, 4 << 20, 4 << 20)
MAX_BYTES = PREFIX.size + sum(BOUNDS) + 32
DIGEST_KEYS = ('coarse_symbols', 'fine_symbols', 'context_ids', 'cluster_ids',
               'coarse_masses', 'fine_masses', 'mapping')
ROUTING = 'Mean8-local0to9-per-channel-to-global-pool-v1'


def header(g, profile, coarse_storage, digests):
    geometry.validate(g, profile)
    if not isinstance(coarse_storage, str) or coarse_storage not in dm.STORAGES:
        raise ValueError('Unsupported coarse storage')
    return {'version': 1, 'geometry': copy.deepcopy(g), 'geometry_profile': profile,
            'arithmetic': legacy.ARITHMETIC, 'numpy': '1.26.4', 'order': legacy.ORDER,
            'engine': copy.deepcopy(legacy.ENGINE),
            'model': {'name': 'Mean8-clustered', 'coarse_storage': coarse_storage, 'routing': ROUTING},
            'integrity': dict(digests)}


def outer_side_bytes(g, profile, coarse_storage):
    """Exact metadata/framing size; all digest contents have fixed ASCII width."""
    h = header(g, profile, coarse_storage, {k: '0' * 64 for k in DIGEST_KEYS})
    return len(dm._json_bytes(h)) + PREFIX.size + 32


def pack(h, sections):
    """Raw framing also permits adversarial test fixtures; unpack validates."""
    if set(sections) != set(NAMES):
        raise ValueError('Missing/extra sections')
    parts = [dm._json_bytes(h)] + [bytes(sections[name]) for name in NAMES[1:]]
    body = PREFIX.pack(MAGIC, 1, *(len(p) for p in parts)) + b''.join(parts)
    return body + hashlib.sha256(body).digest()


def _validate_header(h):
    if (not isinstance(h, dict) or set(h) != {'version', 'geometry', 'geometry_profile',
            'arithmetic', 'numpy', 'order', 'engine', 'model', 'integrity'}
            or type(h['version']) is not int or h['version'] != 1
            or h['arithmetic'] != legacy.ARITHMETIC or h['numpy'] != '1.26.4'
            or h['order'] != legacy.ORDER or dm._json_bytes(h['engine']) != dm._json_bytes(legacy.ENGINE)):
        raise ValueError('Unsupported H4 contract')
    geometry.validate(h['geometry'], h['geometry_profile'])
    m = h['model']
    if (not isinstance(m, dict) or set(m) != {'name', 'coarse_storage', 'routing'}
            or m['name'] != 'Mean8-clustered' or m['routing'] != ROUTING
            or not isinstance(m['coarse_storage'], str) or m['coarse_storage'] not in dm.STORAGES):
        raise ValueError('Invalid model contract')
    d = h['integrity']
    if not isinstance(d, dict) or set(d) != set(DIGEST_KEYS) or not all(legacy._digest(v) for v in d.values()):
        raise ValueError('Invalid integrity fields')


def unpack(data):
    if not isinstance(data, (bytes, bytearray)) or not PREFIX.size + 32 <= len(data) <= MAX_BYTES:
        raise ValueError('Invalid H4 container byte buffer/size')
    magic, version, *lengths = PREFIX.unpack_from(data)
    if (magic != MAGIC or version != 1 or any(n > b for n, b in zip(lengths, BOUNDS))
            or PREFIX.size + sum(lengths) + 32 != len(data)):
        raise ValueError('Invalid magic/version/lengths')
    if hashlib.sha256(data[:-32]).digest() != data[-32:]:
        raise ValueError('Container checksum mismatch')
    sections, pos = {}, PREFIX.size
    for name, length in zip(NAMES, lengths):
        sections[name] = bytes(data[pos:pos + length])
        pos += length
    try:
        h = dm._json_load(sections['metadata'])
        _validate_header(h)
    except (KeyError, TypeError, IndexError, OverflowError, RecursionError) as exc:
        raise ValueError('Malformed metadata') from exc
    transport.deserialize(sections['fine_model'])
    for key in ('coarse_payload', 'fine_payload'):
        if not sections[key] or len(sections[key]) % 4:
            raise ValueError('Invalid range payload length')
    return h, sections


def sizes(data):
    h, s = unpack(data)
    result = transport.sizes(s['fine_model'])
    result.update(total_bytes=len(data), coarse_bytes=len(s['coarse_model']) + len(s['coarse_payload']),
                  fine_payload_bytes=len(s['fine_payload']), outer_metadata_bytes=len(s['metadata']) + PREFIX.size + 32)
    if result['total_bytes'] != sum(result[k] for k in ('coarse_bytes', 'fine_payload_bytes', 'model_bytes', 'outer_metadata_bytes')):
        raise AssertionError('Container accounting mismatch')
    if result['outer_metadata_bytes'] != outer_side_bytes(h['geometry'], h['geometry_profile'], h['model']['coarse_storage']):
        raise AssertionError('Measured side bytes differ from dry evaluator')
    return result


def _masses(pool):
    return np.stack((pool, pool))  # Engine channel axis; shared pool transmitted once.


def decode_coarse(model_bytes, payload, g, storage):
    if not isinstance(payload, bytes) or not payload or len(payload) % 4 or len(payload) > BOUNDS[3]:
        raise ValueError('Malformed coarse payload')
    if not isinstance(model_bytes, bytes) or len(model_bytes) > BOUNDS[1]:
        raise ValueError('Malformed coarse model')
    fc, _ = legacy._load_model(model_bytes, 'IID', storage)
    ids = np.zeros((g['coarse']['rows'], 2), np.uint8)
    q = legacy._decode_payload(payload, ids, fc)
    legacy._constant_symbols(q, g['coarse']['quantization'])
    return q, fc, ids


def validate_original(model, original_masses, original_thresholds):
    """Encoder-side source invariants, deliberately absent from decoder inputs."""
    transport.validate(model)
    e = geometry.validate_thresholds(original_thresholds)
    if model.thresholds.astype('<f8').tobytes() != e.astype('<f8').tobytes():
        raise ValueError('Original Mean8 thresholds changed')
    f = np.asarray(original_masses)
    if (f.dtype != np.uint32 or f.shape != (2, 10, 256) or np.any(f < 1)
            or np.any(f.sum(2, dtype=np.uint64) != 65536)):
        raise ValueError('Invalid original transmitted PMFs')
    for channel, cls in np.argwhere(model.mapping != transport.UNUSED):
        if model.mode in ('C0', 'C1') or cls < 2:
            if not np.array_equal(model.pool[model.mapping[channel, cls]], f[channel, cls]):
                raise ValueError('Original probability changed in C0/C1 or G0/G1')


def encode(g, coarse, fine, classes, model, coarse_model, coarse_payload, coarse_storage,
           *, original_masses, original_thresholds, profile=geometry.PRODUCTION):
    engine.check_runtime()
    started = time.perf_counter()
    geometry.validate(g, profile)
    validate_original(model, original_masses, original_thresholds)
    for q, role in ((coarse, 'coarse'), (fine, 'fine')):
        if not isinstance(q, np.ndarray) or q.dtype != np.uint8 or q.shape != (g[role]['rows'], 2):
            raise ValueError('Complete frozen uint8 symbol arrays required')
        legacy._constant_symbols(q, g['coarse']['quantization'])
    rebuilt = geometry.contexts(g, coarse, model.thresholds, profile)
    if not isinstance(classes, np.ndarray) or classes.dtype != np.uint8 or not np.array_equal(classes, rebuilt):
        raise ValueError('Supplied contexts differ from coarse-only reconstruction')
    ids = transport.route(rebuilt, model)
    c, fc, coarse_ids = decode_coarse(coarse_model, coarse_payload, g, coarse_storage)
    if not np.array_equal(c, coarse) or engine.encode_indexed(c, coarse_ids, fc) != coarse_payload:
        raise ValueError('Coarse prerequisite differs or has noncanonical trailing words')
    wire, choices = transport.choose(model)
    payload = engine.encode_indexed(fine, ids, _masses(model.pool))
    digests = {key: legacy.array_sha(value) for key, value in zip(DIGEST_KEYS,
               (coarse, fine, rebuilt, ids, fc, model.pool, model.mapping))}
    h = header(g, profile, coarse_storage, digests)
    data = pack(h, dict(metadata=b'', coarse_model=coarse_model, fine_model=wire,
                        coarse_payload=coarse_payload, fine_payload=payload))
    return data, {'sizes': sizes(data), 'encode_seconds': time.perf_counter() - started,
                  'coarse_payload_reused_and_verified': True, 'transport_candidates': choices}


def decode(data, strict=True):
    if type(strict) is not bool:
        raise ValueError('Strict flag must be bool')
    engine.check_runtime()
    started = time.perf_counter()
    h, s = unpack(data)
    g, d = h['geometry'], h['integrity']
    model, _ = transport.deserialize(s['fine_model'])
    if legacy.array_sha(model.pool) != d['fine_masses'] or legacy.array_sha(model.mapping) != d['mapping']:
        raise ValueError('Model integrity mismatch')
    coarse, fc, coarse_ids = decode_coarse(s['coarse_model'], s['coarse_payload'], g, h['model']['coarse_storage'])
    if legacy.array_sha(fc) != d['coarse_masses'] or legacy.array_sha(coarse) != d['coarse_symbols']:
        raise ValueError('Coarse integrity mismatch')
    classes = geometry.contexts(g, coarse, model.thresholds, h['geometry_profile'])
    if legacy.array_sha(classes) != d['context_ids']:
        raise ValueError('Reconstructed Mean8 IDs differ')
    ids = transport.route(classes, model)
    if legacy.array_sha(ids) != d['cluster_ids']:
        raise ValueError('Reconstructed pool IDs differ')
    fine = legacy._decode_payload(s['fine_payload'], ids, _masses(model.pool))
    if legacy.array_sha(fine) != d['fine_symbols']:
        raise ValueError('Fine reconstruction mismatch')
    legacy._constant_symbols(fine, g['coarse']['quantization'])
    if strict and (engine.encode_indexed(coarse, coarse_ids, fc) != s['coarse_payload']
                   or engine.encode_indexed(fine, ids, _masses(model.pool)) != s['fine_payload']):
        raise ValueError('Noncanonical payload or trailing words')
    return coarse, fine, classes, ids, {'status': 'PASS', 'strict': strict,
                                      'decode_seconds': time.perf_counter() - started, 'sizes': sizes(data)}
