"""Frozen GLOBAL8 inputs; no checkpoint loading or quantization.

Only discovery is metadata-only.  ``audit_source`` is the explicitly authorized
input audit, and streams one allocated level at a time from the sealed archive.
The small NumPy reconstruction below preserves codec.dequantize arithmetic while
avoiding that module's unrelated torch import.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys
import time

R = Path(__file__).resolve().parent
ROOT = R.parents[1]
NUMPY_DEPS = ROOT / 'research/mean8_hellwarrior_validation_20261020_01/.deps/numpy126'
if sys.platform != 'win32':
    sys.path.insert(0, str(NUMPY_DEPS))
import numpy as np

if np.__version__ != '1.26.4':
    raise RuntimeError('Pinned NumPy1.26.4 is required')

SOURCE_RUN = ROOT / 'research/full_spatial_hashgrid_audit_20261029_01'
SCENES = ('bouncingballs', 'hellwarrior')
EXPECTED = {
    'bouncingballs': {
        'archive_sha256': '055d02308166111d7f4edfe4f2f5cd5fc3b67a366d43b4564e14ed4c1261eef5',
        'symbols_sha256': 'b6f2676efa4c33d0cf2506271bafe0db0b133d05baeabaeb07eca8e47e939de8',
        'restored_sha256': 'f4bb5aa577e232e1caa89c67125b261169b0fa77fecdebc1609ae2e25cb47c38',
    },
    'hellwarrior': {
        'archive_sha256': '4a7ee63b7dc926b4de7f1b3088122cb38129969eb90325f32a5f0a619a9c8f6b',
        'symbols_sha256': 'acd04fe37fcf727d3323c3fb9813ca04777381eaba8bbdf57039187de01e00ea',
        'restored_sha256': 'aeefc00dbbc1d785967341854c9c63358c598e83f71ad476838996b1baee6efa',
    },
}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def arrsha(x):
    return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()


def put(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, allow_nan=False, indent=2)
        f.write('\n')


def canonical_dequantize(codes, params):
    # Same operations and operation order as research/grid4d/codec.py:dequantize.
    bits = params['bits']
    lo, hi, step = params['min'], params['max'], params['step']
    if (bits not in (8, 12, 16) or not np.isfinite([lo, hi, step]).all() or hi < lo or
            step != (hi - lo) / ((1 << bits) - 1) or
            not np.issubdtype(codes.dtype, np.integer) or codes.size == 0 or
            codes.min() < 0 or codes.max() > (1 << bits) - 1):
        raise ValueError('Invalid quantization data')
    if step == 0 and np.any(codes != 0):
        raise ValueError('Constant array must have zero symbols')
    return np.clip(lo + codes.astype(np.float64) * step, lo, hi).astype(np.float32)


def source_paths(scene):
    check(scene in SCENES, 'Only the two registered development scenes are allowed')
    s = SOURCE_RUN / scene
    return {
        'archive': s / 'ZLIB8.npz',
        'metadata': s / 'ZLIB8_decoded/metadata.json',
        'validation': s / 'ZLIB8_decoded/validation.json',
        'symbols': s / 'ZLIB8_decoded/symbols.npy',
        'budget': s / 'ZLIB8_budget.json',
        'levels': s / 'levels.csv',
        'inventory': s / 'inventory.json',
        'seal': SOURCE_RUN / 'FINAL_VALIDATION.json',
    }


def inspect_source(scene):
    """Read only existing metadata, not code arrays or model tensors."""
    p = source_paths(scene)
    m, v, b = read_json(p['metadata']), read_json(p['validation']), read_json(p['budget'])
    check(v['status'] == 'PASS' and v['all_levels'] == 16, 'Frozen decoder did not pass')
    check(m['symbols_sha256'] == v['symbols_sha256'] == EXPECTED[scene]['symbols_sha256'],
          'Historical symbol identities disagree')
    check(v['restored_sha256'] == EXPECTED[scene]['restored_sha256'], 'Historical reconstruction identity')
    check(b['sha256'] == EXPECTED[scene]['archive_sha256'], 'Historical archive identity')
    check(m['shape'] == [6098108, 2] and m['dtype'] == 'uint8', 'Unexpected frozen shape/dtype')
    check(len(m['offsets']) == 17 and m['offsets'][0] == 0 and m['offsets'][-1] == m['shape'][0],
          'Frozen offsets')
    check(m['quantizer']['bits'] == 8 and
          m['quantization_scope'] == 'entire xyz table shared across all levels/channels',
          'Not unchanged GLOBAL8')
    return {'scene': scene, 'paths': {k: str(v) for k, v in p.items()},
            'metadata': m, 'historical_validation': v, 'historical_budget': b,
            'expected': EXPECTED[scene].copy()}


def iter_source_levels(scene):
    """Yield old frozen uint8 arrays, one at a time. Never quantize."""
    m = inspect_source(scene)['metadata']
    with np.load(source_paths(scene)['archive'], allow_pickle=False) as z:
        check(set(z.files) == {'metadata'} | {f'level_{i:02d}' for i in range(16)}, 'Frozen archive members')
        check(json.loads(z['metadata'].tobytes()) == m, 'Archive/source metadata mismatch')
        for i, (lo, hi) in enumerate(zip(m['offsets'], m['offsets'][1:])):
            q = z[f'level_{i:02d}']
            check(q.dtype == np.uint8 and q.shape == (hi - lo, 2) and q.flags.c_contiguous,
                  'Frozen code layout')
            yield i, q


def load_codes(scene):
    """Read-only mmap of already decoded frozen codes; audit_source verifies it."""
    q = np.load(source_paths(scene)['symbols'], mmap_mode='r', allow_pickle=False)
    check(q.dtype == np.uint8 and q.shape == (6098108, 2) and q.flags.c_contiguous,
          'Frozen mmap shape/dtype/layout')
    return q


def audit_source(scene):
    """Stream frozen inputs and validate the previous exact hashes. No re-fit."""
    t = time.perf_counter()
    s = inspect_source(scene)
    p = source_paths(scene)
    hashing = time.perf_counter()
    check(sha(p['archive']) == EXPECTED[scene]['archive_sha256'], 'INPUT_BLOCKED: frozen archive hash')
    source_hashes = {k: sha(v) for k, v in p.items() if k != 'archive'}
    source_hashes['archive'] = EXPECTED[scene]['archive_sha256']
    sealed = read_json(p['seal'])
    check(sealed['status'] == 'PASS_COMPLETED', 'Historical final seal status')
    verified_sealed_entries = {}
    for key, path in p.items():
        if key == 'seal':
            continue
        rel = path.relative_to(SOURCE_RUN).as_posix()
        entry = sealed['artifacts'][rel]
        check(source_hashes[key] == entry['sha256'] and path.stat().st_size == entry['bytes'],
              'INPUT_BLOCKED: frozen file differs from historical final seal: ' + rel)
        verified_sealed_entries[rel] = entry
    hash_seconds = time.perf_counter() - hashing
    with p['levels'].open(newline='', encoding='utf-8') as f:
        old_levels = list(csv.DictReader(f))
    check(len(old_levels) == 16, 'Frozen level records')
    codes_hash, restored_hash = hashlib.sha256(), hashlib.sha256()
    qfull = load_codes(scene)
    rows = []
    for i, q in iter_source_levels(scene):
        lo, hi = s['metadata']['offsets'][i:i + 2]
        digest = arrsha(q)
        check(digest == old_levels[i]['symbols_sha256'], 'INPUT_BLOCKED: per-level frozen hash')
        check(np.array_equal(qfull[lo:hi], q), 'INPUT_BLOCKED: prior mmap != sealed decoded archive')
        codes_hash.update(q.tobytes())
        y = canonical_dequantize(q, s['metadata']['quantizer'])
        restored_hash.update(y.tobytes())
        rows.append({'level': i, 'offset_start': lo, 'offset_end': hi, 'rows': hi - lo,
                     'shape': [hi - lo, 2], 'dtype': '|u1', 'symbols': int(q.size),
                     'raw_bytes': q.nbytes, 'symbols_sha256': digest, 'restored_sha256': arrsha(y)})
    check(codes_hash.hexdigest() == EXPECTED[scene]['symbols_sha256'], 'INPUT_BLOCKED: full symbols SHA')
    check(restored_hash.hexdigest() == EXPECTED[scene]['restored_sha256'], 'INPUT_BLOCKED: canonical FP32 SHA')
    return {**s, 'status': 'PASS', 'source_file_sha256': source_hashes, 'levels': rows,
            'historical_seal_entries_verified': verified_sealed_entries,
            'decoded_codes_exact': True, 'canonical_dequantization_exact': True,
            'no_checkpoint_read_no_quantization': True, 'hashing_seconds': hash_seconds,
            'input_audit_seconds': time.perf_counter() - t}
