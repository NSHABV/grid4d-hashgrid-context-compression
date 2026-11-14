"""Independent scalar checks of the inherited Grid4D context contract.

The oracle deliberately does not call production hashing, interpolation,
dequantization, vertex traversal, aggregation, or searchsorted helpers.  Its
float32 operations round through struct, and its accumulation uses Python
float (IEEE binary64) in explicit x-fast lattice order.
"""
from __future__ import annotations

import copy
import math
import struct
import unittest

import numpy as np

from research.experiment_bench.pmf_clustering import geometry
from research.hashgrid_analysis.hashed_context import core


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _slot(vertex, resolution, rows):
    """Integer scalar transcription of the specified unsigned-32 lookup."""
    stride, index = 1, 0
    for axis in range(3):
        if stride > rows:
            break
        index = (index + int(vertex[axis]) * stride) & 0xffffffff
        stride = (stride * resolution[axis]) & 0xffffffff
    if stride > rows:
        index = (int(vertex[0]) ^ (int(vertex[1]) * 2654435761)
                 ^ (int(vertex[2]) * 805459861)) & 0xffffffff
    return index % rows


def _table(symbols, quantizer):
    lo, hi, step = (quantizer[key] for key in ('min', 'max', 'step'))
    return [[_f32(min(hi, max(lo, lo + int(q) * step))) for q in row]
            for row in symbols]


def _lookup(coordinates, table, scale, resolution):
    u = [_f32(value) for value in coordinates]
    if any(value < 0 or value > 1 for value in u):
        return [0.0, 0.0]
    position = [_f32(u[d] * _f32(scale[d])) for d in range(3)]
    base = [math.floor(value) for value in position]
    fraction = [_f32(position[d] - _f32(base[d])) for d in range(3)]
    smooth = [_f32(_f32(f * f) * _f32(3.0 - _f32(2.0 * f)))
              for f in fraction]
    accum = [0.0, 0.0]
    for corner in range(8):
        bits = [(corner >> d) & 1 for d in range(3)]
        index = _slot([base[d] + bits[d] for d in range(3)], resolution, len(table))
        weight = 1.0
        for d in range(3):
            term = smooth[d] if bits[d] else _f32(1.0 - smooth[d])
            weight = _f32(weight * term)
        for channel in range(2):
            accum[channel] = _f32(accum[channel] + _f32(weight * table[index][channel]))
    return accum


def _oracle(g, coarse, thresholds):
    c, fine = g['coarse'], g['fine']
    rows, res, scale = fine['rows'], fine['lookup_resolution'], fine['scale']
    table = _table(coarse, c['quantization'])
    nominal = [0] * rows
    point = [0] * rows
    ordinal = [-1] * rows
    vertex = [[-1] * 3 for _ in range(rows)]
    coordinates = [[0.0] * 3 for _ in range(rows)]
    anchor = [[0.0, 0.0] for _ in range(rows)]
    delta_sum = [[0.0, 0.0] for _ in range(rows)]
    delta_squared = [[0.0, 0.0] for _ in range(rows)]
    current = 0
    # z/y/x nesting makes x the fast coordinate, without the vector helper.
    for z in range(res[2]):
        for y in range(res[1]):
            for x in range(res[0]):
                v = [x, y, z]
                slot = _slot(v, res, rows)
                nominal[slot] += 1
                if all(v[d] <= math.floor(_f32(scale[d])) for d in range(3)):
                    u = [_f32(_f32(v[d]) / _f32(scale[d])) for d in range(3)]
                    feature = _lookup(u, table, c['scale'], c['lookup_resolution'])
                    if point[slot] == 0:
                        ordinal[slot], vertex[slot], coordinates[slot] = current, v, u
                        anchor[slot] = feature
                    point[slot] += 1
                    for channel in range(2):
                        delta = float(feature[channel]) - float(anchor[slot][channel])
                        delta_sum[slot][channel] += delta
                        delta_squared[slot][channel] += delta * delta
                current += 1
    kind = [0 if nominal[i] == 0 else 1 if point[i] == 0 else
            2 if point[i] == 1 else 3 for i in range(rows)]
    mean, std = [[0.0, 0.0] for _ in range(rows)], [[0.0, 0.0] for _ in range(rows)]
    classes = [[kind[i], kind[i]] for i in range(rows)]
    for i in range(rows):
        if point[i] == 0:
            continue
        for channel in range(2):
            centered = delta_sum[i][channel] / point[i]
            mean[i][channel] = anchor[i][channel] + centered
            variance = delta_squared[i][channel] / point[i] - centered * centered
            std[i][channel] = math.sqrt(max(0.0, variance)) if point[i] > 1 else 0.0
            # Counting <= is a scalar upper bound, including duplicate edges.
            classes[i][channel] = 2 + sum(edge <= mean[i][channel] for edge in thresholds[channel])
    return {
        'slot_index': np.arange(rows, dtype=np.int64),
        'global_embedding_row': np.arange(rows, dtype=np.int64) + fine['offset_start'],
        'nominal_count': np.array(nominal, np.int64),
        'point_count': np.array(point, np.int64),
        'geometry': np.array(kind, np.uint8),
        'canonical_ordinal': np.array(ordinal, np.int64),
        'canonical_vertex': np.array(vertex, np.int32),
        'canonical_coordinates': np.array(coordinates, np.float32),
        'canonical_features': np.array(anchor, np.float32),
        'mean': np.array(mean, np.float64),
        'std': np.array(std, np.float64),
        'representative_valid': np.array([n > 0 for n in point], bool),
    }, np.array(classes, np.uint8)


def _fixture(coarse_rows=40, fine_rows=69,
             coarse_scale=(1.5, 2.25, 1.75), fine_scale=(2.5, 3.25, 1.75)):
    quantizer = {'row_start': 0, 'row_end': 6098108, 'bits': 8,
                 'min': -2.125, 'max': 3.875, 'step': 6.0 / 255,
                 'rounding': 'nearest-even', 'reconstruction_dtype': 'float32'}

    def level(number, rows, start, scale):
        return {'level': number, 'rows': rows, 'offset_start': start,
                'offset_end': start + rows, 'lookup_resolution': [math.ceil(s) + 1 for s in scale],
                'scale': list(scale)}

    g = {'version': 1, 'grid': 'xyz',
         'arithmetic': 'cpu-f32-separate-ufunc-corner0to7-anchor-f64-addat-xfast-popstd-v1',
         'geometry_convention': 'nominal-v-in-[0,R);point-v<=floor(scale);u=f32(v)/f32(scale)',
         'fallback': {'features': [0, 0], 'ordinal': -1, 'vertex': [-1, -1, -1],
                      'coordinates': [0, 0, 0], 'representative_valid': False},
         'hash': {'name': 'grid4d-u32-stride-or-xor-v1', 'primes': [1, 2654435761, 805459861],
                  'mask': 4294967295, 'modulo': 'allocated_rows'},
         'interpolation': 'smoothstep-corners0to7',
         'coarse': level(4, coarse_rows, 0, coarse_scale),
         'fine': level(5, fine_rows, coarse_rows, fine_scale),
         'source_checkpoint_sha256': 'a' * 64, 'source_symbols_sha256': 'b' * 64}
    g['coarse']['quantization'] = quantizer
    symbols = np.array([[(37 * i + 13) % 256, (149 * i + 211) % 256]
                        for i in range(coarse_rows)], np.uint8)
    thresholds = np.array([[-1.75, -0.75, -0.125, 0.375, 0.875, 1.75, 2.75],
                           [-1.5, -0.625, 0.0, 0.5, 1.0, 1.875, 3.0]], np.float64)
    return g, symbols, thresholds


class GeometryScalarOracleTests(unittest.TestCase):
    def _check_context(self, g, symbols, thresholds):
        expected, classes = _oracle(g, symbols, thresholds)
        # Small chunks cross collision groups and anchor boundaries.
        for chunk in (1, 7, 65536):
            actual = core.compute_context(g, symbols, chunk=chunk)
            self.assertEqual(set(actual), set(expected))
            for key in expected:
                with self.subTest(chunk=chunk, field=key):
                    self.assertEqual(actual[key].dtype, expected[key].dtype)
                    np.testing.assert_array_equal(actual[key], expected[key])
        actual_classes = geometry.contexts(g, symbols, thresholds, profile=geometry.SYNTHETIC)
        self.assertEqual(actual_classes.dtype, np.uint8)
        np.testing.assert_array_equal(actual_classes, classes)
        return expected, classes

    def test_dense_slots_empty_and_boundary_only(self):
        g, symbols, thresholds = _fixture()
        expected, classes = self._check_context(g, symbols, thresholds)
        self.assertEqual(np.bincount(expected['geometry'], minlength=4).tolist(), [9, 36, 24, 0])
        for kind in (0, 1):
            mask = expected['geometry'] == kind
            np.testing.assert_array_equal(classes[mask], np.full((int(mask.sum()), 2), kind, np.uint8))
            np.testing.assert_array_equal(expected['canonical_vertex'][mask], -1)
            np.testing.assert_array_equal(expected['mean'][mask], 0.0)

    def test_hash_collisions_anchor_and_population_moments(self):
        g, symbols, thresholds = _fixture(coarse_rows=7, fine_rows=11,
                                          fine_scale=(3.25, 2.5, 2.75))
        expected, _ = self._check_context(g, symbols, thresholds)
        self.assertTrue(np.any(expected['point_count'] > 1))
        self.assertTrue(np.any(expected['std'] > 0))
        self.assertEqual(int(expected['nominal_count'].sum()), 80)
        self.assertEqual(int(expected['point_count'].sum()), 36)
        # Collision anchors are the first eligible x-fast ordinal, not a last write.
        self.assertGreater(len(np.unique(expected['canonical_ordinal'])), 1)

    def test_mean8_duplicate_edges_use_right_boundary(self):
        g, symbols, _ = _fixture(coarse_rows=7, fine_rows=11)
        q = g['coarse']['quantization']
        q.update(min=0.0, max=0.0, step=0.0)
        symbols.fill(0)
        thresholds = np.array([[-1, 0, 0, 0, 0, 0, 1], [0, 0, 0, 0, 0, 0, 0]], np.float64)
        expected, classes = self._check_context(g, symbols, thresholds)
        inside = expected['geometry'] >= 2
        self.assertTrue(inside.any())
        np.testing.assert_array_equal(classes[inside, 0], 8)
        np.testing.assert_array_equal(classes[inside, 1], 9)
        np.testing.assert_array_equal(expected['std'], 0.0)

    def test_uint32_hash_and_dense_index_match_scalar(self):
        vertices = np.array([[0, 0, 0], [1, 2, 3], [0xffffffff, 2, 7],
                             [0xfffffffe, 0xffffffff, 0xffffffff]], np.uint64)
        for resolution, rows in (([4, 5, 6], 120), ([4, 5, 6], 121),
                                 ([4, 5, 6], 119), ([32, 32, 32], 17),
                                 ([2, 2, 2], 1)):
            with self.subTest(resolution=resolution, rows=rows):
                expected = [_slot(v, resolution, rows) for v in vertices]
                np.testing.assert_array_equal(core.slot_indices(vertices, resolution, rows), expected)
        # Fixed known integer expectations also keep the oracle's constants honest.
        self.assertEqual(_slot([1, 2, 3], [4, 5, 6], 120), 69)
        self.assertEqual(_slot([0, 1, 0], [32, 32, 32], 17), (2654435761 & 0xffffffff) % 17)

    def test_float32_lookup_corner_order_endpoints_and_oob(self):
        g, symbols, _ = _fixture(coarse_rows=7)
        c = g['coarse']
        table = _table(symbols, c['quantization'])
        # Non-dyadic coordinates force rounding at smoothstep and corner sums.
        points = [[0, 0, 0], [1, 1, 1], [1 / 7, 2 / 3, 5 / 11],
                  [0.99999994, 0.50000006, 0.125], [-0.001, 0, 0], [0, 1.00001, 0]]
        expected = np.array([_lookup(p, table, c['scale'], c['lookup_resolution'])
                             for p in points], np.float32)
        actual = core.lookup_cpu(points, np.array(table, np.float32), c['scale'], c['lookup_resolution'])
        np.testing.assert_array_equal(actual, expected)
        np.testing.assert_array_equal(actual[-2:], 0.0)

    def test_exact_integer_scale_includes_upper_endpoint(self):
        g, symbols, thresholds = _fixture(coarse_scale=(2.0, 2.0, 2.0),
                                          fine_scale=(3.0, 2.0, 1.0), fine_rows=29)
        expected, _ = self._check_context(g, symbols, thresholds)
        self.assertEqual(np.bincount(expected['geometry'], minlength=4).tolist(), [5, 0, 24, 0])
        np.testing.assert_array_equal(expected['canonical_coordinates'][23], [1, 1, 1])

    def test_synthetic_profile_does_not_relax_production_geometry(self):
        g, symbols, thresholds = _fixture()
        with self.assertRaises(ValueError):
            geometry.contexts(g, symbols, thresholds)
        geometry.validate(g, geometry.SYNTHETIC)
        mutations = [
            lambda value: value['fine'].update(rows=4097),
            lambda value: value['fine'].update(lookup_resolution=[33, 5, 3]),
            lambda value: value['fine'].update(scale=[2.1, 3.25, 1.75]),
            lambda value: value['fine'].update(level=7),
            lambda value: value['fine'].update(offset_start=41),
            lambda value: value['coarse']['quantization'].update(row_end=40),
        ]
        for mutation in mutations:
            bad = copy.deepcopy(g)
            mutation(bad)
            with self.subTest(geometry=bad), self.assertRaises(ValueError):
                geometry.contexts(bad, symbols, thresholds, profile=geometry.SYNTHETIC)

    def test_frozen_thresholds_validation(self):
        g, symbols, thresholds = _fixture()
        for bad in (thresholds.astype(np.float32), thresholds[:, :6], thresholds[:, ::-1],
                    np.full((2, 7), np.nan, np.float64), np.full((2, 7), np.inf, np.float64)):
            with self.subTest(dtype=bad.dtype, shape=bad.shape), self.assertRaises(ValueError):
                geometry.contexts(g, symbols, bad, profile=geometry.SYNTHETIC)


if __name__ == '__main__':
    unittest.main()
