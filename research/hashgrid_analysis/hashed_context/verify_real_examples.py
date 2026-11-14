"""Read-only independent scalar verification of selected real colliding slots.

Bounded vector indexing prefilters all nominal vertices. Only selected matches
are verified with the independent scalar indexing/interpolation test oracles.
Coarse uint8 symbols are reconstructed, never requantized. Fine targets and
checkpoints are blocked by a Python file-open audit hook.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

from .core import load_bundle, sha, slot_indices
from .test_synthetic import scalar_slot, scalar_lookup


def install_audit():
    opened = []
    blocked = {'fine_symbols.npy', 'deform.pth', 'xyz_encoding.u8.bin'}

    def hook(event, args):
        if event != 'open' or not isinstance(args[0], (str, bytes)):
            return
        path = Path(args[0]).resolve()
        if path.name in blocked:
            raise PermissionError(f'Forbidden target/checkpoint read: {path}')
        mode = args[1]
        opened.append({'path': str(path), 'mode': mode})

    sys.addaudithook(hook)
    return opened


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output-name', default='example_verification')
    args = parser.parse_args()
    run = args.run_dir.resolve()
    output = run / args.output_name
    if output.parent != run:
        raise ValueError('Output must be one direct child of the run directory')
    output.mkdir(exist_ok=False)
    opened = install_audit()
    started = time.perf_counter()
    source_paths = [run / 'diagnostics/examples.json', Path(__file__).resolve(),
                    Path(__file__).with_name('test_synthetic.py'), Path(__file__).with_name('core.py')]
    examples = json.loads(source_paths[0].read_text(encoding='utf-8'))
    if len(examples) != 6:
        raise AssertionError('Expected six pairs of examples')
    validations, vertex_rows = [], []
    maximum_mean_error = maximum_std_error = 0.
    for pair in ('L4_to_L5', 'L5_to_L6'):
        pair_path = run / pair
        bundle = pair_path / 'decoder_bundle'
        source_paths.extend([bundle / 'decoder_metadata.json', bundle / 'coarse_symbols.npy',
                             pair_path / 'contexts.npz'])
    before = {str(path): sha(path) for path in source_paths}
    for pair in ('L4_to_L5', 'L5_to_L6'):
        meta, q = load_bundle(run / pair / 'decoder_bundle')
        quantizer = meta['coarse']['quantization']
        # Independent vector expression equivalent to the exported affine
        # reconstruction specification; no quantization or parameter fitting.
        coarse_table = np.minimum(quantizer['max'], np.maximum(quantizer['min'],
            quantizer['min'] + q.astype(np.float64) * quantizer['step'])).astype(np.float32)
        selected_examples = [item for item in examples if item['pair'] == pair]
        selected = sorted({int(item[f'{role}_slot']) for item in selected_examples
                           for role in ('low', 'high')})
        if len(selected) != 6:
            raise AssertionError('Expected six distinct slots per level')
        matches = {j: [] for j in selected}
        fine = meta['fine']
        resolution = fine['lookup_resolution']
        scale = np.asarray(fine['scale'], np.float32)
        eligible_maximum = np.floor(scale).astype(np.int64)
        total = math.prod(resolution)
        for start in range(0, total, 65536):
            ordinal = np.arange(start, min(start + 65536, total), dtype=np.int64)
            vertices = np.column_stack((ordinal % resolution[0],
                (ordinal // resolution[0]) % resolution[1],
                ordinal // (resolution[0] * resolution[1])))
            indexes = slot_indices(vertices, resolution, fine['rows'])
            keep = np.isin(indexes, selected)
            for o, v, j in zip(ordinal[keep], vertices[keep], indexes[keep]):
                j, o = int(j), int(o)
                if scalar_slot(v, resolution, fine['rows']) != j:
                    raise AssertionError('Independent uint32 index mismatch')
                allowed = bool(np.all(v <= eligible_maximum))
                u = np.array([np.float32(np.float32(v[a]) / scale[a]) for a in range(3)])
                features = scalar_lookup(u, coarse_table, meta['coarse']['scale'],
                                         meta['coarse']['lookup_resolution']) if allowed else np.zeros(2, np.float32)
                matches[j].append((o, v.copy(), u, allowed, features))
                vertex_rows.append({'pair': pair, 'fine_slot': j,
                    'global_embedding_row': fine['offset_start'] + j, 'ordinal': o,
                    'vertex_x': int(v[0]), 'vertex_y': int(v[1]), 'vertex_z': int(v[2]),
                    'normalized_x': float(u[0]), 'normalized_y': float(u[1]), 'normalized_z': float(u[2]),
                    'point_eligible': int(allowed), 'feature_available': int(allowed),
                    'coarse_feature_0': float(features[0]), 'coarse_feature_1': float(features[1])})
        with np.load(run / pair / 'contexts.npz', allow_pickle=False) as stored:
            for j in selected:
                nominal = matches[j]
                eligible = [item for item in nominal if item[3]]
                if len(nominal) != int(stored['nominal_count'][j]) or len(eligible) != int(stored['point_count'][j]):
                    raise AssertionError('Correspondence count mismatch')
                if not eligible:
                    raise AssertionError('Selected example unexpectedly lacks a point context')
                canonical = min(eligible, key=lambda item: item[0])
                if canonical[0] != int(stored['canonical_ordinal'][j]):
                    raise AssertionError('Canonical ordinal mismatch')
                np.testing.assert_array_equal(canonical[1], stored['canonical_vertex'][j])
                np.testing.assert_array_equal(canonical[2], stored['canonical_coordinates'][j])
                np.testing.assert_array_equal(canonical[4], stored['canonical_features'][j])
                mean, std = [], []
                for channel in range(2):
                    values = [float(item[4][channel]) for item in eligible]
                    mu = math.fsum(values) / len(values)
                    sigma = math.sqrt(math.fsum((value - mu) ** 2 for value in values) / len(values))
                    mean.append(mu)
                    std.append(sigma)
                np.testing.assert_allclose(mean, stored['mean'][j], rtol=0, atol=1e-14)
                np.testing.assert_allclose(std, stored['std'][j], rtol=0, atol=1e-14)
                mean_error = float(np.max(np.abs(np.asarray(mean) - stored['mean'][j])))
                std_error = float(np.max(np.abs(np.asarray(std) - stored['std'][j])))
                maximum_mean_error, maximum_std_error = max(maximum_mean_error, mean_error), max(maximum_std_error, std_error)
                for item in selected_examples:
                    for role in ('low', 'high'):
                        if item[f'{role}_slot'] != j:
                            continue
                        for suffix, field in (('nominal_count', 'nominal_count'), ('point_count', 'point_count'),
                                              ('canonical_ordinal', 'canonical_ordinal')):
                            if item[f'{role}_{suffix}'] != int(stored[field][j]):
                                raise AssertionError(f'Example JSON {suffix} mismatch')
                        for suffix, field in (('canonical_vertex', 'canonical_vertex'), ('mean', 'mean'), ('std', 'std')):
                            np.testing.assert_array_equal(item[f'{role}_{suffix}'], stored[field][j])
                        norm = float(np.linalg.norm(stored['std'][j]))
                        if item[f'{role}_sigma_norm'] != norm:
                            raise AssertionError('Example sigma norm mismatch')
                validations.append({'pair': pair, 'slot': j, 'status': 'PASS',
                    'nominal_count': len(nominal), 'point_count': len(eligible),
                    'canonical_ordinal': canonical[0], 'mean': mean, 'std': std,
                    'maximum_mean_error': mean_error, 'maximum_std_error': std_error})
            for item in selected_examples:
                low, high = int(item['low_slot']), int(item['high_slot'])
                distance = float(np.linalg.norm(stored['mean'][low] - stored['mean'][high]))
                norm_difference = float(np.linalg.norm(stored['std'][high]) - np.linalg.norm(stored['std'][low]))
                if distance != item['mean_l2_distance'] or norm_difference != item['sigma_norm_difference']:
                    raise AssertionError('Example distance or norm difference mismatch')
                if norm_difference / quantizer['step'] != item['sigma_difference_in_quantization_steps']:
                    raise AssertionError('Example quantization-step comparison mismatch')
                if distance > item['mean_tolerance']:
                    raise AssertionError('Selected means exceed the recorded tolerance')
    after = {str(path): sha(path) for path in source_paths}
    if before != after:
        raise AssertionError('An input source changed during verification')
    with (output / 'selected-correspondences.csv').open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(vertex_rows[0]))
        writer.writeheader()
        writer.writerows(vertex_rows)
    summary = {'status': 'PASS', 'selected_slots_verified': len(validations),
        'example_pairs_verified': len(examples), 'nominal_vertices_scalar_verified': len(vertex_rows),
        'maximum_mean_error': maximum_mean_error, 'maximum_std_error': maximum_std_error,
        'moment_absolute_tolerance': 1e-14, 'index_and_canonical_features_comparison': 'exact',
        'source_hashes_unchanged': before == after, 'source_sha256': before,
        'fine_targets_and_checkpoint_open_blocked': True,
        'feature_sentinel_for_noneligible': [0., 0.],
        'slots': validations, 'elapsed_seconds': time.perf_counter() - started}
    summary['file_open_events'] = opened.copy()
    with (output / 'validation.json').open('x', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps({key: summary[key] for key in ('status', 'selected_slots_verified',
        'nominal_vertices_scalar_verified', 'maximum_mean_error', 'maximum_std_error', 'elapsed_seconds')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
