"""Replay saved small WSL lookup samples on another CPU/NumPy runtime."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

from . import core


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--results', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    results = Path(args.results).resolve()
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError('Cross-CPU output must be new')
    checks = []
    for pair in ['L4_to_L5', 'L5_to_L6']:
        bundle = results / pair / 'decoder_bundle'
        meta, q = core.load_bundle(bundle)
        gpu_dir = results / 'gpu_checks' / pair
        evidence = json.loads((gpu_dir / 'gpu-parity.json').read_text())
        with np.load(gpu_dir / 'gpu-parity-samples.npz', allow_pickle=False) as sample:
            u = sample['coordinates']
            expected = sample['cpu_features']
            actual = core.lookup_cpu(u, core.dequantize_symbols(q, meta['coarse']['quantization']),
                                    meta['coarse']['scale'], meta['coarse']['lookup_resolution'])
            features_equal = np.array_equal(actual, expected)
            indices_equal = []
            for role in ['coarse', 'fine']:
                level = meta[role]
                name = str(level['level'])
                actual_indices = core.slot_indices(sample['vertices_L' + name],
                    level['lookup_resolution'], level['rows'])
                indices_equal.append(bool(np.array_equal(actual_indices, sample['cpu_indices_L' + name])))
            checks.append({'pair': pair, 'queries': len(u),
                           'CPU_lookup_bitwise_equal': bool(features_equal),
                           'CPU_indices_exact': all(indices_equal),
                           'max_abs_error': float(np.max(np.abs(actual - expected))),
                           'source_environment': evidence['environment'],
                           'coarse_symbols_sha256': core.sha(bundle / 'coarse_symbols.npy'),
                           'metadata_sha256': core.sha(bundle / 'decoder_metadata.json'),
                           'samples_sha256': core.sha(gpu_dir / 'gpu-parity-samples.npz')})
    result = {'status': 'PASS' if all(c['CPU_lookup_bitwise_equal'] and c['CPU_indices_exact'] for c in checks) else 'FAIL',
              'checks': checks, 'environment': {'python': sys.version, 'numpy': np.__version__},
              'scope': '512 lookup samples per pair; not full aggregation portability or context-class proof'}
    with output.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({'status': result['status'], 'checks': [{k: c[k] for k in
        ['pair', 'queries', 'CPU_lookup_bitwise_equal', 'CPU_indices_exact', 'max_abs_error']} for c in checks]}))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
