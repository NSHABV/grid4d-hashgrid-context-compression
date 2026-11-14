"""Bounded G4DHPAIR V2 container: verified xyz L4/L5, scene table8 quantizer.

All inputs needed for independent decoding are transmitted. No saved context,
target or checkpoint file is read here. The canonical CPU context is reused;
IID and Geometry4 skip feature interpolation. Probability tables are fitted to
all scene symbols and paid in full, which is not held-out generalization.
"""
from __future__ import annotations

import copy
import hashlib
import struct
import time
import numpy as np

from research.hashgrid_analysis.hashed_context.core import (
    ARITHMETIC, compute_context, dequantize_symbols, slot_indices,
    vertices_from_ordinals)
from research.experiment_bench.hashed_interlevel import dry_model
from research.experiment_bench.hashed_interlevel.core import (
    fit_spec, classify, fit_masses)
from research.experiment_bench.hashed_pair import engine

MAGIC = b'G4DHPAIR'
VERSION = 2
PREFIX = struct.Struct('<8sH5Q')
NAMES = ('metadata', 'coarse_model', 'fine_model', 'coarse_payload', 'fine_payload')
BOUNDS = (64000, 1 << 20, 1 << 20, 4 << 20, 4 << 20)
ARMS = {'IID': 1, 'Geometry4': 4, 'Canonical8': 10, 'Mean8': 10}
STORAGES = tuple(dry_model.STORAGES)
ORDER = 'channel-major-slot-ascending-v1'
CONVENTION = 'nominal-v-in-[0,R);point-v<=floor(scale);u=f32(v)/f32(scale)'
HASH = {'name': 'grid4d-u32-stride-or-xor-v1', 'primes': [1, 2654435761, 805459861],
        'mask': 4294967295, 'modulo': 'allocated_rows'}
ENGINE = {'name': 'constriction-range', 'version': '0.4.2',
          'mass_precision': 16, 'coder_precision': 24, 'categorical_perfect': False}
RULES = {'quantile': 'linear-float64-all-G2-G3-per-channel', 'boundary': 'searchsorted-right',
         'empty': 'separate-G0-G1', 'fit': 'all-scene-symbols-laplace1-positive16'}
FALLBACK = {'features': [0, 0], 'ordinal': -1, 'vertex': [-1, -1, -1],
            'coordinates': [0, 0, 0], 'representative_valid': False}
GEOMETRY_KEYS = ('level', 'rows', 'offset_start', 'offset_end', 'lookup_resolution', 'scale')
EXPECTED = {
    'coarse': {'level': 4, 'rows': 205379, 'offset_start': 125561, 'offset_end': 330940,
               'lookup_resolution': [59, 59, 59], 'scale': [57.3502311706543] * 3},
    'fine': {'level': 5, 'rows': 524288, 'offset_start': 330940, 'offset_end': 855228,
            'lookup_resolution': [81, 81, 81], 'scale': [79.63493347167969] * 3},
}
QUANTIZER_KEYS = {'row_start', 'row_end', 'bits', 'min', 'max',
                  'step', 'rounding', 'reconstruction_dtype'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def array_sha(value):
    return sha(np.ascontiguousarray(value).tobytes())


def _geometry(meta):
    geometry = {'version': 1, 'grid': 'xyz', 'arithmetic': ARITHMETIC,
                'geometry_convention': CONVENTION, 'fallback': copy.deepcopy(FALLBACK),
                'hash': copy.deepcopy(HASH), 'interpolation': 'smoothstep-corners0to7'}
    for role in ('coarse', 'fine'):
        geometry[role] = {key: copy.deepcopy(meta[role][key]) for key in GEOMETRY_KEYS}
    geometry['coarse']['quantization'] = copy.deepcopy(meta['coarse']['quantization'])
    geometry['source_checkpoint_sha256'] = meta['source_checkpoint_sha256']
    geometry['source_symbols_sha256'] = meta['source_symbols_sha256']
    validate_geometry(geometry)
    return geometry


def _digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in '0123456789abcdef' for c in value))


def validate_geometry(g):
    keys = {'version', 'grid', 'arithmetic', 'geometry_convention', 'fallback', 'hash',
            'interpolation', 'coarse', 'fine', 'source_checkpoint_sha256', 'source_symbols_sha256'}
    if (not isinstance(g, dict) or set(g) != keys or type(g['version']) is not int
            or g['version'] != 1 or g['grid'] != 'xyz' or g['arithmetic'] != ARITHMETIC
            or g['geometry_convention'] != CONVENTION
            or dry_model._json_bytes(g['fallback']) != dry_model._json_bytes(FALLBACK)
            or dry_model._json_bytes(g['hash']) != dry_model._json_bytes(HASH)
            or g['interpolation'] != 'smoothstep-corners0to7'
            or not _digest(g['source_checkpoint_sha256']) or not _digest(g['source_symbols_sha256'])):
        raise ValueError('Unsupported geometry/hash/domain specification')
    for role in ('coarse', 'fine'):
        level = g[role]
        expected_keys = set(GEOMETRY_KEYS) | ({'quantization'} if role == 'coarse' else set())
        if not isinstance(level, dict) or set(level) != expected_keys:
            raise ValueError('Invalid level fields')
        for key in GEOMETRY_KEYS:
            if level[key] != EXPECTED[role][key]:
                raise ValueError('Only the verified xyz L4/L5 runtime geometry is supported')
        for key in ('level', 'rows', 'offset_start', 'offset_end'):
            if type(level[key]) is not int:
                raise ValueError('Geometry integers required')
        if (any(type(v) is not int for v in level['lookup_resolution'])
                or any(type(v) not in (int, float) for v in level['scale'])):
            raise ValueError('Invalid resolution/scale type')
    validate_quantizer(g['coarse']['quantization'])


def validate_quantizer(q):
    """Validate one whole-xyz quantizer, shared by both transmitted levels.

    Row range expresses the full-table scope. Numeric extrema are transmitted;
    the decoder neither reads the original table nor recomputes extrema.
    The formula is exactly grid4d.codec.quantize: float64 step and nearest-even.
    """
    if (not isinstance(q, dict) or set(q) != QUANTIZER_KEYS
            or q['bits'] != 8 or type(q['bits']) is not int or q['row_start'] != 0
            or q['row_end'] != 6098108 or q['rounding'] != 'nearest-even'
            or type(q['row_start']) is not int or type(q['row_end']) is not int
            or q['reconstruction_dtype'] != 'float32'
            or any(type(q[k]) not in (int, float) for k in ('min', 'max', 'step'))):
        raise ValueError('Unsupported whole-xyz table-wise 8-bit quantizer')
    try:
        lo, hi, step = (float(q[k]) for k in ('min', 'max', 'step'))
    except OverflowError as exc:
        raise ValueError('Quantizer scalar exceeds finite float64 range') from exc
    if (not np.isfinite([lo, hi, step]).all() or hi < lo
            or step != (hi-lo)/255 or (lo != hi and step <= 0)):
        raise ValueError('Nonfinite or inconsistent table8 extrema/step')
    # The original table is float32. Bounds outside its finite range cannot be
    # legitimate extrema and could overflow decoder feature reconstruction.
    limit = float(np.finfo(np.float32).max)
    if abs(lo) > limit or abs(hi) > limit:
        raise ValueError('Quantizer extrema exceed finite float32 range')
    probe = np.zeros((1, 2), np.uint8) if step == 0 else np.array([[0, 255]], np.uint8)
    if not np.isfinite(dequantize_symbols(probe, q)).all():
        raise ValueError('Nonfinite float32 reconstruction')


def _constant_symbols(q, quantizer):
    if quantizer['step'] == 0 and np.any(q):
        raise ValueError('Constant whole-xyz table must have zero symbols in both levels')


def _contexts(g, coarse, name):
    rows = g['fine']['rows']
    if name == 'IID':
        return {'geometry': np.zeros(rows, np.uint8)}
    if name == 'Geometry4':
        r, s = g['fine']['lookup_resolution'], np.asarray(g['fine']['scale'], np.float32)
        nominal, point = np.zeros(rows, np.int64), np.zeros(rows, np.int64)
        total = int(np.prod(r))
        for start in range(0, total, 65536):
            v = vertices_from_ordinals(np.arange(start, min(start+65536, total)), r)
            index = slot_indices(v, r, rows)
            nominal += np.bincount(index, minlength=rows)
            inside = (v <= np.floor(s).astype(np.int64)).all(axis=1)
            point += np.bincount(index[inside], minlength=rows)
        geometry = np.zeros(rows, np.uint8)
        geometry[(nominal > 0) & (point == 0)] = 1
        geometry[point == 1] = 2
        geometry[point > 1] = 3
        return {'geometry': geometry}
    contexts = compute_context(g, coarse)
    if not all(np.isfinite(contexts[key]).all() for key in ('canonical_features', 'mean', 'std')):
        raise ValueError('Nonfinite canonical CPU feature arithmetic')
    return contexts


def _spec_for_transport(spec):
    thresholds = {}
    if spec['name'] in ('Canonical8', 'Mean8'):
        thresholds['primary'] = np.asarray(spec['edges']['primary'], np.float64)
    return {'name': spec['name'], 'C': spec['C'], 'rules': copy.deepcopy(RULES)}, thresholds


def validate_spec(specification, thresholds, name):
    if (name not in ARMS or not isinstance(specification, dict)
            or dry_model._json_bytes(specification) != dry_model._json_bytes(
                {'name': name, 'C': ARMS[name], 'rules': RULES})):
        raise ValueError('Unsupported context model specification')
    edges = [[], []]
    if name in ('Canonical8', 'Mean8'):
        if set(thresholds) != {'primary'}:
            raise ValueError('Missing or extra threshold arrays')
        value = thresholds['primary']
        if (value.dtype != np.float64 or value.shape != (2, 7) or not np.isfinite(value).all()
                or np.any(np.diff(value, axis=1) < 0)):
            raise ValueError('Invalid finite sorted quantile thresholds')
        edges = value.tolist()
    elif thresholds:
        raise ValueError('Geometry/IID cannot have feature thresholds')
    return {'name': name, 'C': ARMS[name], 'edges': {'primary': edges, 'std': [[], []]}}


def _model_bytes(masses, spec, storage):
    specification, thresholds = _spec_for_transport(spec)
    choices = {key: dry_model.serialize(masses, thresholds, specification, {}, key)
               for key in STORAGES}
    for value in choices.values():
        f, e, s, m = dry_model.deserialize(value)
        if not np.array_equal(f, masses) or m != {}:
            raise AssertionError('Probability transport did not roundtrip')
        validate_spec(s, e, spec['name'])
    if storage == 'auto':
        storage = min(STORAGES, key=lambda key: len(choices[key]))
    if storage not in choices:
        raise ValueError('Unknown model storage')
    return choices[storage], storage, {key: len(value) for key, value in choices.items()}


def _load_model(data, name, storage):
    _, actual_storage, classes = dry_model._parts(data)
    masses, edges, spec, metadata = dry_model.deserialize(data)
    if actual_storage != storage or classes != ARMS[name] or metadata != {}:
        raise ValueError('Probability model header mismatch')
    return masses, validate_spec(spec, edges, name)


def _header_validate(h):
    keys = {'version', 'kind', 'engine', 'arithmetic', 'numpy', 'order', 'geometry', 'model', 'integrity'}
    if (set(h) != keys or h['version'] != VERSION or type(h['version']) is not int
            or h['kind'] != 'standalone-xyz-L4-L5'
            or dry_model._json_bytes(h['engine']) != dry_model._json_bytes(ENGINE)
            or h['arithmetic'] != ARITHMETIC or h['numpy'] != '1.26.4' or h['order'] != ORDER):
        raise ValueError('Unsupported container specification')
    validate_geometry(h['geometry'])
    model = h['model']
    if (not isinstance(model, dict) or set(model) != {'name', 'C', 'storage', 'coarse_storage'}
            or not isinstance(model['name'], str) or model['name'] not in ARMS
            or model['C'] != ARMS[model['name']]
            or type(model['C']) is not int or model['storage'] not in STORAGES
            or model['coarse_storage'] not in STORAGES):
        raise ValueError('Invalid model declaration')
    integrity = h['integrity']
    if (not isinstance(integrity, dict)
            or set(integrity) != {'q4', 'q5', 'classes', 'coarse_masses', 'fine_masses'}
            or not all(_digest(value) for value in integrity.values())):
        raise ValueError('Invalid integrity specification')


def pack(header, sections):
    """Pack even adversarial test headers; validation belongs to unpack/decode."""
    if set(sections) != set(NAMES):
        raise ValueError('Missing or extra sections')
    parts = [dry_model._json_bytes(header)] + [bytes(sections[name]) for name in NAMES[1:]]
    body = PREFIX.pack(MAGIC, VERSION, *(len(value) for value in parts)) + b''.join(parts)
    return body + hashlib.sha256(body).digest()


def unpack(data):
    if not isinstance(data, (bytes, bytearray, memoryview)) or len(data) < PREFIX.size+32:
        raise ValueError('Truncated container')
    magic, version, *lengths = PREFIX.unpack_from(data)
    if (magic != MAGIC or version != VERSION
            or any(n > bound for n, bound in zip(lengths, BOUNDS))
            or PREFIX.size+sum(lengths)+32 != len(data)):
        raise ValueError('Invalid magic/version/lengths or trailing bytes')
    if hashlib.sha256(data[:-32]).digest() != bytes(data[-32:]):
        raise ValueError('Container checksum mismatch')
    sections, offset = {}, PREFIX.size
    for name, length in zip(NAMES, lengths):
        sections[name] = bytes(data[offset:offset+length])
        offset += length
    header = dry_model._json_load(sections['metadata'])
    try:
        _header_validate(header)
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError('Malformed container metadata') from exc
    for name in ('coarse_payload', 'fine_payload'):
        if not sections[name] or len(sections[name]) % 4:
            raise ValueError('Invalid range payload length')
    return header, sections


def section_sizes(data):
    _, sections = unpack(data)
    fine = dry_model.section_sizes(sections['fine_model'])
    coarse_bytes = len(sections['coarse_model']) + len(sections['coarse_payload'])
    payload = len(sections['fine_payload'])
    probability = fine['probability_masses']
    framing = len(data)-coarse_bytes-payload-probability
    return {'total_bytes': len(data), 'coarse_bytes': coarse_bytes, 'fine_payload_bytes': payload,
            'model_bytes': probability, 'metadata_framing_bytes': framing,
            'coarse_payload_bytes': len(sections['coarse_payload']),
            'coarse_model_bytes': len(sections['coarse_model']),
            'fine_model_bytes': len(sections['fine_model']),
            'threshold_bytes': fine['context_thresholds'],
            'fine_specification_bytes': fine['model_specification'],
            'fine_model_header_bytes': fine['header'],
            'fine_model_metadata_bytes': fine['mandatory_metadata'],
            'central_metadata_bytes': len(sections['metadata']),
            'prefix_bytes': PREFIX.size, 'integrity_bytes': 32}


def encode_pair(meta, q4, q5, name, storage='auto'):
    engine.check_runtime()
    started, cpu_started = time.perf_counter(), time.process_time()
    if name not in ARMS:
        raise ValueError('Unsupported arm')
    g = _geometry(meta)
    for q, role in ((q4, 'coarse'), (q5, 'fine')):
        if not isinstance(q, np.ndarray) or q.dtype != np.uint8 or q.shape != (g[role]['rows'], 2):
            raise ValueError('Expected complete frozen uint8 [rows,2] symbols')
        _constant_symbols(q, g['coarse']['quantization'])
    timing = {}
    t = time.perf_counter()
    contexts = _contexts(g, q4, name)
    rows = np.arange(len(q5), dtype=np.int64)
    spec = fit_spec(contexts, rows, name)
    classes = classify(contexts, spec)
    timing['context_seconds'] = time.perf_counter()-t
    t = time.perf_counter()
    coarse_classes = np.zeros(q4.shape, np.uint8)
    coarse_spec = fit_spec({'geometry': np.zeros(len(q4), np.uint8)}, np.arange(len(q4)), 'IID')
    _, f4 = fit_masses(q4, coarse_classes, np.arange(len(q4)), 1)
    _, f5 = fit_masses(q5, classes, rows, ARMS[name])
    timing['fit_seconds'] = time.perf_counter()-t
    t = time.perf_counter()
    coarse_model, coarse_storage, coarse_candidates = _model_bytes(f4, coarse_spec, 'auto')
    fine_model, selected_storage, candidates = _model_bytes(f5, spec, storage)
    timing['serialization_seconds'] = time.perf_counter()-t
    t = time.perf_counter()
    coarse_payload = engine.encode_indexed(q4, coarse_classes, f4)
    timing['coarse_entropy_seconds'] = time.perf_counter()-t
    t = time.perf_counter()
    fine_payload = engine.encode_indexed(q5, classes, f5)
    timing['fine_entropy_seconds'] = time.perf_counter()-t
    t = time.perf_counter()
    header = {'version': VERSION, 'kind': 'standalone-xyz-L4-L5', 'engine': copy.deepcopy(ENGINE),
              'arithmetic': ARITHMETIC, 'numpy': '1.26.4', 'order': ORDER, 'geometry': g,
              'model': {'name': name, 'C': ARMS[name], 'storage': selected_storage,
                        'coarse_storage': coarse_storage},
              'integrity': {'q4': array_sha(q4), 'q5': array_sha(q5), 'classes': array_sha(classes),
                            'coarse_masses': array_sha(f4), 'fine_masses': array_sha(f5)}}
    sections = {'metadata': b'', 'coarse_model': coarse_model, 'fine_model': fine_model,
                'coarse_payload': coarse_payload, 'fine_payload': fine_payload}
    data = pack(header, sections)
    sizes = section_sizes(data)
    timing['framing_seconds'] = time.perf_counter()-t
    timing['encode_total_seconds'] = time.perf_counter()-started
    timing['cpu_seconds'] = time.process_time()-cpu_started
    probability = f5[np.arange(2)[None, :], classes, q5].astype(np.float64)/65536
    return data, {'model': name, 'storage': selected_storage, 'coarse_storage': coarse_storage,
                  'candidate_model_bytes': candidates, 'candidate_coarse_model_bytes': coarse_candidates,
                  'sizes': sizes, 'timing': timing, 'classes_sha256': array_sha(classes),
                  'coarse_masses_sha256': array_sha(f4), 'fine_masses_sha256': array_sha(f5),
                  'q4_sha256': array_sha(q4), 'q5_sha256': array_sha(q5),
                  'finite_fine_bits': float(-np.log2(probability).sum()),
                  'engine_source_sha256': engine.SOURCE_SHA256,
                  'class_counts': [np.bincount(classes[:, ch], minlength=ARMS[name]).tolist() for ch in range(2)]}


def _decode_payload(payload, classes, masses):
    """Normalize constriction's invalid-stream assertion to a format error."""
    try:
        return engine.decode_indexed(payload, classes, masses)
    except AssertionError as exc:
        raise ValueError('Invalid range payload for transmitted probability model') from exc


def decode_bytes(data, verify_canonical=True):
    engine.check_runtime()
    started, cpu_started = time.perf_counter(), time.process_time()
    timing = {}
    header, sections = unpack(data)
    g, model, integrity = header['geometry'], header['model'], header['integrity']
    t = time.perf_counter()
    f4, _ = _load_model(sections['coarse_model'], 'IID', model['coarse_storage'])
    f5, spec = _load_model(sections['fine_model'], model['name'], model['storage'])
    if array_sha(f4) != integrity['coarse_masses'] or array_sha(f5) != integrity['fine_masses']:
        raise ValueError('Probability mass digest mismatch')
    timing['model_restore_seconds'] = time.perf_counter()-t
    coarse_classes = np.zeros((g['coarse']['rows'], 2), np.uint8)
    t = time.perf_counter()
    q4 = _decode_payload(sections['coarse_payload'], coarse_classes, f4)
    timing['coarse_entropy_seconds'] = time.perf_counter()-t
    if array_sha(q4) != integrity['q4']:
        raise ValueError('Coarse symbols digest mismatch')
    _constant_symbols(q4, g['coarse']['quantization'])
    dequantize_symbols(q4, g['coarse']['quantization'])
    t = time.perf_counter()
    contexts = _contexts(g, q4, model['name'])
    classes = classify(contexts, spec)
    timing['context_seconds'] = time.perf_counter()-t
    if array_sha(classes) != integrity['classes']:
        raise ValueError('Reconstructed context classes digest mismatch')
    t = time.perf_counter()
    q5 = _decode_payload(sections['fine_payload'], classes, f5)
    timing['fine_entropy_seconds'] = time.perf_counter()-t
    if array_sha(q5) != integrity['q5']:
        raise ValueError('Fine symbols digest mismatch')
    _constant_symbols(q5, g['coarse']['quantization'])
    t = time.perf_counter()
    if verify_canonical:
        if (engine.encode_indexed(q4, coarse_classes, f4) != sections['coarse_payload']
                or engine.encode_indexed(q5, classes, f5) != sections['fine_payload']):
            raise ValueError('Noncanonical range payload or unused trailing words')
    timing['canonical_validation_seconds'] = time.perf_counter()-t
    timing['decode_total_seconds'] = time.perf_counter()-started
    timing['cpu_seconds'] = time.process_time()-cpu_started
    return q4, q5, classes, {'status': 'PASS', 'model': model['name'], 'storage': model['storage'],
                           'timing': timing, 'sizes': section_sizes(data),
                           'q4_sha256': array_sha(q4), 'q5_sha256': array_sha(q5),
                           'classes_sha256': array_sha(classes), 'fine_masses_sha256': array_sha(f5),
                           'coarse_masses_sha256': array_sha(f4),
                           'canonical_payload_verified': bool(verify_canonical)}
