"""Reproducible read-only artifact integrity audit for hashed-context diagnostics.

Only the new output directory is written. Existing validation directories are
never overwritten. Protected source files are read as bytes for SHA only; fine
symbols/checkpoints are never interpreted or used for context computation.
"""
import argparse
import csv
import ctypes
import hashlib
import json
from pathlib import Path
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = {'slot_index': 'int64', 'global_embedding_row': 'int64',
          'nominal_count': 'int64', 'point_count': 'int64', 'geometry': 'uint8',
          'canonical_ordinal': 'int64', 'canonical_vertex': 'int32',
          'canonical_coordinates': 'float32', 'canonical_features': 'float32',
          'mean': 'float64', 'std': 'float64', 'representative_valid': 'bool'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def peak_working_set():
    """Peak working set on Windows; unavailable measurements remain null."""
    class PMC(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong),
                    ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
    try:
        api = ctypes.windll.psapi.GetProcessMemoryInfo
        api.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
        api.restype = ctypes.c_int
        handle = ctypes.windll.kernel32.GetCurrentProcess
        handle.restype = ctypes.c_void_p
        p = PMC()
        p.cb = ctypes.sizeof(p)
        if api(handle(), ctypes.byref(p), p.cb):
            return int(p.PeakWorkingSetSize)
    except Exception:
        pass
    return None


def check_csv(run, pair):
    with np.load(run / pair / 'contexts.npz', allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    if set(data) != set(SCHEMA):
        raise AssertionError('Unexpected context schema')
    for key, dtype in SCHEMA.items():
        if data[key].dtype != np.dtype(dtype):
            raise AssertionError('NPZ dtype mismatch: ' + key)
    n = len(data['slot_index'])
    if n != 524288:
        raise AssertionError('Allocated row count mismatch')
    np.testing.assert_array_equal(data['slot_index'], np.arange(n, dtype=np.int64))
    np.testing.assert_array_equal(data['representative_valid'], data['point_count'] > 0)
    samples = (set(range(0, n, 1024)) | {0, 1, n - 2, n - 1} |
               set(np.random.default_rng(227).choice(n, 512, replace=False).tolist()))
    comparisons = floats = rows = 0
    with (run / pair / 'contexts.csv').open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if int(row['slot_index']) != i:
                raise AssertionError('Missing, repeated or unsorted CSV slot')
            if i >= n:
                raise AssertionError('Extra CSV row')
            rows += 1
            if i not in samples:
                continue
            for field, text in row.items():
                if field in data:
                    key, column = field, None
                else:
                    key, separator, tail = field.rpartition('_')
                    if not separator or not tail.isdigit() or key not in data:
                        raise AssertionError('Unexpected CSV field: ' + field)
                    column = int(tail)
                expected = data[key][i] if column is None else data[key][i, column]
                dtype = data[key].dtype
                if dtype.kind in 'iu':
                    if int(text) != int(expected):
                        raise AssertionError('Integer CSV roundtrip mismatch: ' + field)
                elif dtype.kind == 'f':
                    parsed = np.asarray(float(text), dtype=dtype)[()]
                    if parsed.tobytes() != expected.tobytes():
                        raise AssertionError('Float bit roundtrip mismatch: ' + field)
                    floats += 1
                else:
                    raise AssertionError('Unrecognized CSV dtype')
                comparisons += 1
    if rows != n:
        raise AssertionError('CSV row count mismatch')
    return {'pair': pair, 'status': 'PASS', 'rows_streamed': rows,
            'sorted_unique_slots': '0..524287 exact', 'sample_rows': len(samples),
            'sample_field_comparisons': comparisons,
            'sample_float_bit_roundtrip_comparisons': floats,
            'npz_schema_dtypes': SCHEMA}


def audit_run(run, output_name='integrity_checks'):
    run = Path(run).resolve()
    output = run / output_name
    if output.parent != run:
        raise ValueError('Output must be one direct child of the run directory')
    output.mkdir(exist_ok=False)
    started = time.perf_counter()
    protected = json.loads((run / 'protected-input-hashes.json').read_text(encoding='utf-8'))
    unchanged, mismatches, protected_bytes = [], [], 0
    for relative, expected in protected.items():
        path = ROOT / relative
        if not path.is_file():
            mismatches.append({'path': relative, 'error': 'MISSING'})
            continue
        actual = digest(path)
        protected_bytes += path.stat().st_size
        if actual != expected:
            mismatches.append({'path': relative, 'error': 'SHA_MISMATCH',
                               'actual': actual, 'expected': expected})
        else:
            unchanged.append(relative)
    if mismatches:
        raise AssertionError(str(mismatches[:20]))
    artifacts = json.loads((run / 'diagnostics/artifact_hashes.json').read_text(encoding='utf-8'))
    for relative, expected in artifacts.items():
        if digest(run / 'diagnostics' / relative) != expected:
            raise AssertionError('Diagnostic artifact SHA mismatch: ' + relative)
    summary = json.loads((run / 'diagnostics/summary.json').read_text(encoding='utf-8'))
    summary_sources = []
    for pair, details in summary['pairs'].items():
        source = details['sources']
        for name in ('contexts', 'metadata'):
            path = Path(source[name + '_path'])
            actual = digest(path)
            if actual != source[name + '_sha256']:
                raise AssertionError('Summary source SHA mismatch: ' + pair)
            summary_sources.append({'path': str(path), 'sha256': actual})
    csv_checks = [check_csv(run, pair) for pair in ('L4_to_L5', 'L5_to_L6')]
    result = {'status': 'PASS', 'protected_files_checked': len(protected),
              'protected_files_unchanged': len(unchanged),
              'protected_file_bytes_hashed': protected_bytes, 'protected_mismatches': mismatches,
              'diagnostic_artifacts_sha_verified': len(artifacts),
              'summary_source_hashes_verified': summary_sources, 'csv_checks': csv_checks,
              'elapsed_seconds': time.perf_counter() - started,
              'peak_process_working_set_bytes': peak_working_set(),
              'verifier_source_sha256': digest(__file__),
              'scope': 'Read-only artifact integrity; protected source bytes were hashed, '
                       'never interpreted as fine targets. No new contexts, models, coding or training.'}
    with (output / 'validation.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path, help='Existing hashed-context result directory')
    parser.add_argument('--output-name', default='integrity_checks',
                        help='Fresh direct child directory; existing output is rejected')
    args = parser.parse_args()
    result = audit_run(args.run, args.output_name)
    print(json.dumps({key: result[key] for key in ('status', 'protected_files_checked',
          'diagnostic_artifacts_sha_verified', 'elapsed_seconds', 'peak_process_working_set_bytes')}))


if __name__ == '__main__':
    main()
