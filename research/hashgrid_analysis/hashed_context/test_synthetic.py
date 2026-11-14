"""Independent tiny-grid oracles for decoder-available hashed contexts.

The expected indices implement uint32 C++ arithmetic with Python integers;
the expected lookup is scalar and does not use the production mapping helper.
No checkpoint, fine targets, or result directory is needed.
"""
import copy
import math
import unittest
from unittest.mock import patch

import numpy as np

from .core import ARITHMETIC, slot_indices, lookup_cpu, compute_context


MASK = (1 << 32) - 1
PRIMES = (1, 2654435761, 805459861)


def scalar_slot(vertex, resolution, rows):
    """Literal scalar get_grid_index<D=3>, including stride wraparound."""
    stride, index = 1, 0
    for axis in range(3):
        if stride > rows:
            break
        index = (index + (int(vertex[axis]) & MASK) * stride) & MASK
        stride = (stride * int(resolution[axis])) & MASK
    if stride > rows:
        index = 0
        for value, prime in zip(vertex, PRIMES):
            index ^= ((int(value) & MASK) * prime) & MASK
    return index % rows


def scalar_lookup(coordinate, table, scale, resolution):
    """Separate float32 operations in CUDA corner order; no fused arithmetic."""
    coordinate = np.asarray(coordinate, np.float32)
    if np.any(coordinate < 0) or np.any(coordinate > 1):
        return np.zeros(2, np.float32)
    base, smooth = [], []
    for axis in range(3):
        position = np.float32(coordinate[axis] * np.float32(scale[axis]))
        vertex = int(math.floor(float(position)))
        fraction = np.float32(position - np.float32(vertex))
        square = np.float32(fraction * fraction)
        twice = np.float32(np.float32(2) * fraction)
        value = np.float32(square * np.float32(np.float32(3) - twice))
        base.append(vertex)
        smooth.append(value)
    result = np.zeros(2, np.float32)
    for corner in range(8):
        weight = np.float32(1)
        vertex = []
        for axis in range(3):
            bit = (corner >> axis) & 1
            vertex.append(base[axis] + bit)
            term = smooth[axis] if bit else np.float32(np.float32(1) - smooth[axis])
            weight = np.float32(weight * term)
        index = scalar_slot(vertex, resolution, len(table))
        for channel in range(2):
            term = np.float32(weight * np.float32(table[index, channel]))
            result[channel] = np.float32(result[channel] + term)
    return result


def independent_dequantize(symbols, quantizer):
    lo, hi, step = quantizer['min'], quantizer['max'], quantizer['step']
    result = np.empty(symbols.shape, np.float32)
    for index in np.ndindex(symbols.shape):
        result[index] = np.float32(min(hi, max(lo, lo + int(symbols[index]) * step)))
    return result


def independent_context(fine, coarse, symbols):
    """Enumerate all tiny vertices; keep per-slot feature lists as an oracle."""
    rows, resolution = fine['rows'], fine['lookup_resolution']
    scale = np.asarray(fine['scale'], np.float32)
    coarse_table = independent_dequantize(symbols, coarse['quantization'])
    nominal = np.zeros(rows, np.int64)
    eligible = np.zeros(rows, np.int64)
    ordinal = np.full(rows, -1, np.int64)
    vertex = np.full((rows, 3), -1, np.int64)
    coordinate = np.zeros((rows, 3), np.float32)
    canonical = np.zeros((rows, 2), np.float32)
    features = [[] for _ in range(rows)]
    for z in range(resolution[2]):
        for y in range(resolution[1]):
            for x in range(resolution[0]):
                v = (x, y, z)
                j = scalar_slot(v, resolution, rows)
                nominal[j] += 1
                if any(v[axis] > math.floor(float(scale[axis])) for axis in range(3)):
                    continue
                eligible[j] += 1
                u = np.array([np.float32(np.float32(v[a]) / scale[a]) for a in range(3)])
                value = scalar_lookup(u, coarse_table, coarse['scale'], coarse['lookup_resolution'])
                features[j].append(value)
                if ordinal[j] == -1:
                    ordinal[j] = x + resolution[0] * y + resolution[0] * resolution[1] * z
                    vertex[j] = v
                    coordinate[j] = u
                    canonical[j] = value
    category = np.zeros(rows, np.uint8)
    category[(nominal > 0) & (eligible == 0)] = 1
    category[eligible == 1] = 2
    category[eligible > 1] = 3
    mean = np.zeros((rows, 2), np.float64)
    std = np.zeros((rows, 2), np.float64)
    for j, values in enumerate(features):
        if not values:
            continue
        for ch in range(2):
            mu = math.fsum(float(item[ch]) for item in values) / len(values)
            variance = math.fsum((float(item[ch]) - mu) ** 2 for item in values) / len(values)
            mean[j, ch] = mu
            std[j, ch] = math.sqrt(variance)
    return {'slot_index': np.arange(rows, dtype=np.int64),
            'nominal_count': nominal, 'point_count': eligible,
            'geometry': category, 'canonical_ordinal': ordinal,
            'canonical_vertex': vertex, 'canonical_coordinates': coordinate,
            'canonical_features': canonical, 'mean': mean, 'std': std}


def make_fixture(coarse_hashed=False, anisotropic=False, zero=False):
    quantizer = {'bits': 8, 'min': -4., 'max': 4., 'step': 8. / 255,
                 'rounding': 'nearest-even', 'reconstruction_dtype': 'float32'}
    if zero:
        quantizer.update(min=0., max=0., step=0.)
    if anisotropic:
        coarse_r, coarse_scale, coarse_rows = [2, 3, 4], [1., 1.5, 2.6], 24
        fine_r, fine_scale, fine_rows = [3, 4, 5], [1.7, 2.3, 3.2], 29
    else:
        coarse_r = [4] * 3 if coarse_hashed else [3] * 3
        coarse_scale = [2.4] * 3 if coarse_hashed else [1.7] * 3
        coarse_rows = 31 if coarse_hashed else 27
        fine_r, fine_scale, fine_rows = [4] * 3, [2.5] * 3, 31
    coarse_level = 5 if coarse_hashed else 4
    coarse = {'level': coarse_level, 'rows': coarse_rows, 'offset_start': 7,
              'offset_end': 7 + coarse_rows, 'lookup_resolution': coarse_r,
              'scale': coarse_scale, 'quantization': quantizer}
    fine = {'level': coarse_level + 1, 'rows': fine_rows,
            'offset_start': coarse['offset_end'],
            'offset_end': coarse['offset_end'] + fine_rows,
            'lookup_resolution': fine_r, 'scale': fine_scale}
    meta = {'version': 1, 'arithmetic': ARITHMETIC, 'grid': 'xyz',
            'coarse': coarse, 'fine': fine}
    symbols = np.zeros((coarse_rows, 2), np.uint8) if zero else np.random.default_rng(39).integers(
        0, 256, (coarse_rows, 2), dtype=np.uint8)
    return meta, symbols


class IndependentIndexTests(unittest.TestCase):
    def test_dense_x_fast_anisotropic(self):
        vertices = np.array([[x, y, z] for z in range(5) for y in range(4) for x in range(3)])
        np.testing.assert_array_equal(slot_indices(vertices, [3, 4, 5], 60), np.arange(60))

    def test_hash_prime_and_uint32_products(self):
        vertices = np.array([[0, 0, 0], [1, 2, 3], [81, 111, 2048],
                             [65535, 65536, 99999], [MASK, MASK, MASK]], np.uint64)
        for rows in (1, 7, 31, 524288):
            expected = [scalar_slot(v, [1024] * 3, rows) for v in vertices]
            np.testing.assert_array_equal(slot_indices(vertices, [1024] * 3, rows), expected)

    def test_uint32_stride_overflow_remains_dense(self):
        resolution, rows = [65536, 65536, 2], MASK
        vertices = np.array([[65535, 65535, 1], [2, 3, 1], [0, 0, 1]], np.uint64)
        expected = [scalar_slot(v, resolution, rows) for v in vertices]
        np.testing.assert_array_equal(slot_indices(vertices, resolution, rows), expected)
        self.assertEqual(expected[-1], 0)

    def test_dense_hash_cutover_includes_equal_stride(self):
        vertices = np.array([[2, 3, 4], [9, 9, 9]])
        for rows in (9, 10, 99, 100, 101, 999, 1000):
            expected = [scalar_slot(v, [10] * 3, rows) for v in vertices]
            np.testing.assert_array_equal(slot_indices(vertices, [10] * 3, rows), expected)


class IndependentLookupTests(unittest.TestCase):
    def test_dense_and_hashed_scalar_reference(self):
        rng = np.random.default_rng(451)
        points = np.concatenate((rng.random((37, 3)).astype(np.float32),
                                  np.array([[0, 0, 0], [1, 1, 1], [1, 0, 0],
                                            [-.01, .5, .5], [.5, 1.01, .5]], np.float32)))
        for resolution, rows, scale in (([3, 4, 5], 60, [2, 3, 4]),
                                        ([4, 5, 3], 29, [2.7, 3.2, 1.9])):
            table = rng.normal(size=(rows, 2)).astype(np.float32)
            expected = np.stack([scalar_lookup(u, table, scale, resolution) for u in points])
            np.testing.assert_array_equal(lookup_cpu(points, table, scale, resolution), expected)

    def test_smoothstep_is_not_linear_interpolation(self):
        table = np.repeat((np.arange(8) % 2)[:, None], 2, axis=1).astype(np.float32)
        out = lookup_cpu(np.array([[.25, .5, .75]], np.float32), table, [1] * 3, [2] * 3)
        np.testing.assert_array_equal(out, np.full((1, 2), np.float32(.15625)))
        self.assertNotEqual(float(out[0, 0]), .25)

    def test_exact_and_immediately_outside_boundaries(self):
        table = np.arange(16, dtype=np.float32).reshape(8, 2)
        lo = np.nextafter(np.float32(0), np.float32(-1))
        hi = np.nextafter(np.float32(1), np.float32(2))
        points = np.array([[lo, 0, 0], [hi, 0, 0], [0, 0, 0], [1, 1, 1]], np.float32)
        out = lookup_cpu(points, table, [1] * 3, [2] * 3)
        np.testing.assert_array_equal(out[:2], np.zeros((2, 2), np.float32))
        np.testing.assert_array_equal(out[2], table[0])
        np.testing.assert_array_equal(out[3], table[7])


class IndependentAggregationTests(unittest.TestCase):
    def compare_oracle(self, meta, symbols, chunk=17):
        expected = independent_context(meta['fine'], meta['coarse'], symbols)
        actual = compute_context(meta, symbols, chunk=chunk)
        for key, values in expected.items():
            if key in ('mean', 'std'):
                np.testing.assert_allclose(actual[key], values, rtol=2e-14, atol=2e-14,
                                           err_msg=key)
            else:
                np.testing.assert_array_equal(actual[key], values, err_msg=key)
        np.testing.assert_array_equal(actual['global_embedding_row'],
                                      actual['slot_index'] + meta['fine']['offset_start'])
        np.testing.assert_array_equal(actual['representative_valid'], actual['point_count'] > 0)
        return actual

    def test_dense_coarse_collision_counts_and_canonical(self):
        meta, symbols = make_fixture()
        data = self.compare_oracle(meta, symbols)
        np.testing.assert_array_equal(np.bincount(data['geometry'], minlength=4), [1, 10, 13, 7])
        self.assertEqual(int(data['nominal_count'].sum()), 64)
        self.assertEqual(int(data['point_count'].sum()), 27)
        self.assertEqual(len(np.unique(data['slot_index'])), 31)
        self.assertTrue(np.any(data['nominal_count'] > 1))
        # The canonical ordinal is the minimum eligible preimage, not a nominal boundary point.
        resolution = meta['fine']['lookup_resolution']
        for j in np.flatnonzero(data['point_count'] > 0):
            v = data['canonical_vertex'][j]
            self.assertEqual(scalar_slot(v, resolution, 31), int(j))
            self.assertTrue(np.all(v <= np.floor(meta['fine']['scale'])))

    def test_hashed_coarse_independent_lookup_and_moments(self):
        meta, symbols = make_fixture(coarse_hashed=True)
        data = self.compare_oracle(meta, symbols, chunk=3)
        self.assertTrue(np.any(data['std'][data['geometry'] == 3] > 0))

    def test_anisotropic_coarse_and_fine_geometry(self):
        self.compare_oracle(*make_fixture(anisotropic=True), chunk=11)

    def test_mean_population_std_empty_and_singleton(self):
        meta, symbols = make_fixture(coarse_hashed=True)
        data = self.compare_oracle(meta, symbols)
        empty = data['point_count'] == 0
        singleton = data['point_count'] == 1
        for key in ('canonical_features', 'mean', 'std', 'canonical_coordinates'):
            np.testing.assert_array_equal(data[key][empty], np.zeros_like(data[key][empty]))
        np.testing.assert_array_equal(data['canonical_ordinal'][empty], -np.ones(empty.sum(), np.int64))
        np.testing.assert_array_equal(data['canonical_vertex'][empty], -np.ones((empty.sum(), 3), np.int32))
        np.testing.assert_array_equal(data['std'][singleton], np.zeros((singleton.sum(), 2)))
        np.testing.assert_array_equal(data['mean'][singleton], data['canonical_features'][singleton])

    def test_chunk_invariance_all_arrays_exact(self):
        meta, symbols = make_fixture(coarse_hashed=True)
        expected = compute_context(meta, symbols, chunk=1)
        for chunk in (2, 3, 7, 17, 64, 4096):
            actual = compute_context(meta, symbols, chunk=chunk)
            self.assertEqual(set(actual), set(expected))
            for key in expected:
                np.testing.assert_array_equal(actual[key], expected[key], err_msg=f'{key}, chunk={chunk}')

    def test_exact_zero_coarse_constant_all_aggregates(self):
        meta, symbols = make_fixture(coarse_hashed=True, zero=True)
        data = self.compare_oracle(meta, symbols, chunk=1)
        for key in ('canonical_features', 'mean', 'std'):
            np.testing.assert_array_equal(data[key], np.zeros_like(data[key]))

    def test_nonzero_constant_table_respects_lookup_rounding(self):
        # Finite-precision sums of eight weights need not be exactly one.
        # A constant source table therefore does not imply bit-exact constant
        # lookup outputs; any resulting tiny Std must match the scalar oracle.
        meta, symbols = make_fixture(coarse_hashed=True, zero=True)
        meta['coarse']['quantization'].update(min=7., max=7., step=0.)
        data = self.compare_oracle(meta, symbols, chunk=3)
        active = data['representative_valid']
        np.testing.assert_allclose(data['mean'][active], 7., rtol=0, atol=2e-6)
        self.assertTrue(np.all(data['std'][active] < 2e-6))

    def test_inputs_not_mutated_and_no_file_reads_during_context(self):
        meta, symbols = make_fixture(coarse_hashed=True)
        old_meta, old_symbols = copy.deepcopy(meta), symbols.copy()
        with (patch('builtins.open', side_effect=AssertionError('Unexpected file read')),
                patch('pathlib.Path.open', side_effect=AssertionError('Unexpected path read')),
                patch('numpy.load', side_effect=AssertionError('Unexpected array load'))):
            compute_context(meta, symbols, chunk=3)
        self.assertEqual(meta, old_meta)
        np.testing.assert_array_equal(symbols, old_symbols)

    def test_metadata_dtype_shape_scale_rejection(self):
        meta, symbols = make_fixture()
        with self.assertRaises(ValueError):
            compute_context(meta, symbols.astype(np.uint16))
        with self.assertRaises(ValueError):
            compute_context(meta, symbols[:-1])
        broken = copy.deepcopy(meta)
        broken['fine']['lookup_resolution'][0] += 1
        with self.assertRaises(ValueError):
            compute_context(broken, symbols)
        with self.assertRaises(ValueError):
            compute_context(meta, symbols, chunk=0)


if __name__ == '__main__':
    unittest.main()
