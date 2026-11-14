"""Synthetic H4 optimizer/transport contracts; no scene data or benchmarks.

Run with the pinned interpreter from the repository root::

    .tools/phase2-plotting-env/Scripts/python.exe -B -m unittest \
        research.experiment_bench.pmf_clustering.test_optimizer
"""
from __future__ import annotations

from itertools import combinations
import math
import struct
import unittest
from unittest import mock

import numpy as np

from research.experiment_bench.hashed_pair.engine import decode_indexed, encode_indexed
from research.experiment_bench.models import frequencies
from . import optimizer, transport


def thresholds():
    return np.array([[0., 0., 1.5, 2., 9., 17., 255.],
                     [-2., 1., 2., 3., 4., 5., 6.]], dtype=np.float64)


def counts_for(spec):
    result = np.zeros((2, 10, 256), dtype=np.uint64)
    for source, bins in spec.items():
        for symbol, count in bins.items():
            result.reshape(20, 256)[source, symbol] = count
    return result


def originals(counts):
    return np.stack([frequencies(row) for row in counts.reshape(20, 256)]).reshape(2, 10, 256)


def model_for_partition(counts, original, partition, mode='C2'):
    """Independent small oracle: explicit source PMFs, then physical sharing."""
    source_rows = {}
    flat = counts.reshape(20, 256)
    for members in partition:
        if len(members) == 1:
            row = original.reshape(20, 256)[members[0]].copy()
        else:
            pooled = np.array([sum(int(flat[source, symbol]) for source in members)
                               for symbol in range(256)], dtype=np.uint64)
            row = frequencies(pooled)
        for source in members:
            source_rows[source] = row
    pool, mapping = [], np.full((2, 10), transport.UNUSED, dtype=np.uint8)
    for source, row in sorted(source_rows.items()):
        matches = [] if mode == 'C0' else [index for index, item in enumerate(pool)
                                          if np.array_equal(item, row)]
        index = matches[0] if matches else len(pool)
        if not matches:
            pool.append(row.copy())
        mapping.flat[source] = index
    return transport.Model(np.asarray(pool, dtype=np.uint32).reshape(-1, 256),
                           mapping, thresholds(), mode)


def measured_objective(counts, model, metadata_bytes=0):
    """Explicit complete wire sizes and a per-source entropy sum."""
    candidates = {storage: transport.serialize(model, storage)
                  for storage in transport.STORAGES}
    storage = min(transport.STORAGES, key=lambda key: len(candidates[key]))
    contributions = []
    for source, row in enumerate(counts.reshape(20, 256)):
        if any(row):
            pmf = model.pool[model.mapping.flat[source]].astype(np.float64)
            contributions.append(float(np.sum(row.astype(np.float64) *
                                               (16.0 - np.log2(pmf)), dtype=np.float64)))
    bits = math.fsum(contributions)
    return {'ideal_payload_bits': bits, 'ideal_payload_bytes': bits / 8.,
            'model_bytes': len(candidates[storage]), 'storage': storage,
            'J_bytes': math.fsum((bits / 8., len(candidates[storage]), metadata_bytes)),
            'transport_candidates': {key: len(value) for key, value in candidates.items()}}


def exhaustive_oracle(counts, original, metadata_bytes=0):
    """Enumerate every admissible next partition, including the stopping pass."""
    state = tuple((source,) for source, row in enumerate(counts.reshape(20, 256)) if any(row))
    current = model_for_partition(counts, original, state)
    cost = measured_objective(counts, current, metadata_bytes)
    steps = []
    while True:
        proposals = []
        for left, right in combinations(state, 2):
            union = tuple(sorted(left + right))
            if any(source % 10 < 2 for source in union) or len({source // 10 for source in union}) != 1:
                continue
            partition = tuple(sorted([item for item in state if item not in (left, right)] + [union]))
            model = model_for_partition(counts, original, partition)
            score = measured_objective(counts, model, metadata_bytes)
            proposals.append((left, right, partition, model, score))
        best = min(proposals, key=lambda proposal: (proposal[4]['J_bytes'], proposal[0], proposal[1]),
                   default=None)
        accepted = best is not None and best[4]['J_bytes'] < cost['J_bytes']
        steps.append({'proposals': proposals, 'best': best, 'accepted': accepted, 'before': cost})
        if not accepted:
            return current, cost, steps
        state, current, cost = best[2], best[3], best[4]


class OptimizerContracts(unittest.TestCase):
    def assert_same_model(self, left, right):
        self.assertEqual(left.mode, right.mode)
        np.testing.assert_array_equal(left.pool, right.pool)
        np.testing.assert_array_equal(left.mapping, right.mapping)
        np.testing.assert_array_equal(left.thresholds, right.thresholds)

    def test_c0_copies_original_pmfs_without_refitting_or_mutation(self):
        counts = counts_for({0: {250: 3}, 2: {240: 7}, 9: {230: 4}, 10: {220: 2}, 19: {210: 1}})
        original = originals(counts_for({0: {1: 20}, 2: {1: 20}, 9: {3: 40},
                                         10: {1: 20}, 19: {7: 60}}))
        saved_counts, saved_original, edges = counts.copy(), original.copy(), thresholds()
        saved_edges = edges.copy()
        with mock.patch.object(optimizer, 'frequencies', side_effect=AssertionError('C0 refitted')):
            result = optimizer.optimize(counts, original, edges, 'C0', 37)
        expected = model_for_partition(counts, original, ((0,), (2,), (9,), (10,), (19,)), 'C0')
        self.assert_same_model(result.model, expected)
        self.assertEqual(len(result.model.pool), 5)
        self.assertEqual(result.history, [])
        self.assertEqual(result.candidates_evaluated, 0)
        self.assertEqual(result.initial, result.final)
        self.assertEqual(result.final['outer_metadata_bytes'], 37)
        self.assertFalse(np.shares_memory(result.model.pool, original))
        self.assertFalse(np.shares_memory(result.model.thresholds, edges))
        np.testing.assert_array_equal(counts, saved_counts)
        np.testing.assert_array_equal(original, saved_original)
        np.testing.assert_array_equal(edges, saved_edges)

    def test_c1_preserves_every_symbol_probability_and_raw_entropy_payload(self):
        rng = np.random.default_rng(4821)
        symbols = rng.integers(0, 256, size=(173, 2), dtype=np.uint8)
        classes = np.column_stack((np.resize([0, 2, 7, 9], len(symbols)),
                                   np.resize([0, 2, 4, 8], len(symbols)))).astype(np.uint8)
        counts = optimizer.histogram(symbols, classes)
        original = np.stack([frequencies(rng.integers(0, 100, 256))
                             for _ in range(20)]).reshape(2, 10, 256)
        for source in (2, 10, 14):
            original.reshape(20, 256)[source] = original[0, 0]
        with mock.patch.object(optimizer, 'frequencies', side_effect=AssertionError('C0/C1 refitted')):
            baseline = optimizer.optimize(counts, original, thresholds(), 'C0')
            shared = optimizer.optimize(counts, original, thresholds(), 'C1')
        self.assertLess(len(shared.model.pool), len(baseline.model.pool))
        self.assertEqual(shared.history, [])
        self.assertEqual(shared.candidates_evaluated, 0)
        self.assertEqual(shared.final['ideal_payload_bits'], baseline.final['ideal_payload_bits'])
        self.assertLess(shared.final['model_bytes'], baseline.final['model_bytes'])
        reference_payload = encode_indexed(symbols, classes, original, chunk_rows=19)
        for result in (baseline, shared):
            routes = transport.route(classes, result.model)
            for channel in range(2):
                np.testing.assert_array_equal(result.model.pool[routes[:, channel]],
                                              original[channel, classes[:, channel]])
            physical = np.broadcast_to(result.model.pool, (2, len(result.model.pool), 256))
            payload = encode_indexed(symbols, routes, physical, chunk_rows=19)
            self.assertEqual(payload, reference_payload)
            np.testing.assert_array_equal(decode_indexed(payload, routes, physical, chunk_rows=7), symbols)

    def test_beneficial_nonidentical_histograms_are_merged(self):
        counts = counts_for({2: {1: 100}, 3: {1: 101}})
        original = originals(counts)
        self.assertFalse(np.array_equal(counts[0, 2], counts[0, 3]))
        self.assertFalse(np.array_equal(original[0, 2], original[0, 3]))
        result = optimizer.optimize(counts, original, thresholds(), 'C2')
        self.assertEqual([(item['left'], item['right']) for item in result.history], [([2], [3])])
        self.assertEqual(result.final['pool_rows'], 1)
        self.assertLess(result.final['J_bytes'], result.initial['J_bytes'])
        self.assertEqual(result.candidates_evaluated, 1)

    def test_identical_histograms_can_merge_after_exact_physical_sharing(self):
        counts = counts_for({2: {1: 100000}, 3: {1: 100000}})
        result = optimizer.optimize(counts, originals(counts), thresholds(), 'C2')
        self.assertEqual(result.initial['pool_rows'], 1)
        self.assertEqual(result.final['pool_rows'], 1)
        self.assertEqual(len(result.history), 1)
        self.assertLess(result.final['ideal_payload_bits'], result.initial['ideal_payload_bits'])
        self.assertLess(result.final['J_bytes'], result.initial['J_bytes'])

    def test_identical_histograms_are_not_forced_to_merge_when_cost_increases(self):
        counts = counts_for({2: {1: 1}, 3: {1: 1}, 4: {1: 1}})
        result = optimizer.optimize(counts, originals(counts), thresholds(), 'C2')
        self.assertEqual(result.history, [])
        self.assertEqual(result.candidates_evaluated, 3)
        self.assertEqual(result.initial, result.final)

    def test_incompatible_histograms_reject_the_only_candidate(self):
        counts = counts_for({2: {1: 100000}, 3: {2: 100000}})
        original = originals(counts)
        result = optimizer.optimize(counts, original, thresholds(), 'C2')
        merged = model_for_partition(counts, original, ((2, 3),))
        self.assertGreater(measured_objective(counts, merged)['J_bytes'], result.initial['J_bytes'])
        self.assertEqual(result.history, [])
        self.assertEqual(result.candidates_evaluated, 1)
        for source in (2, 3):
            np.testing.assert_array_equal(result.model.pool[result.model.mapping.flat[source]],
                                          original.reshape(20, 256)[source])

    def test_pooled_raw_counts_receive_smoothing_once(self):
        counts = counts_for({2: {1: 100}, 3: {1: 101}})
        raw_pool = counts[0, 2] + counts[0, 3]
        original = originals(counts)
        calls = []
        def inspect(raw):
            calls.append(raw.copy())
            return frequencies(raw)
        with mock.patch.object(optimizer, 'frequencies', side_effect=inspect):
            result = optimizer.optimize(counts, original, thresholds(), 'C2')
        self.assertEqual(len(calls), 1)
        np.testing.assert_array_equal(calls[0], raw_pool)
        np.testing.assert_array_equal(result.model.pool[0], frequencies(raw_pool))
        self.assertFalse(np.array_equal(result.model.pool[0], frequencies(raw_pool + 1)))
        self.assertFalse(np.array_equal(result.model.pool[0], frequencies(original[0, 2] + original[0, 3])))

    def test_fallback_and_cross_channel_statistical_restrictions_allow_exact_sharing(self):
        counts = counts_for({source: {7: 100000} for source in (0, 1, 2, 10, 11, 12)})
        original = originals(counts)
        for mode, expected_rows in (('C0', 6), ('C1', 1), ('C2', 1)):
            with self.subTest(mode=mode):
                result = optimizer.optimize(counts, original, thresholds(), mode)
                self.assertEqual(result.final['pool_rows'], expected_rows)
                self.assertEqual(result.history, [])
                self.assertEqual(result.candidates_evaluated, 0)
                for source in (0, 1, 2, 10, 11, 12):
                    np.testing.assert_array_equal(result.model.pool[result.model.mapping.flat[source]],
                                                  original.reshape(20, 256)[source])

    def test_fallback_rows_stay_original_while_feature_bins_merge(self):
        counts = counts_for({0: {9: 3}, 1: {8: 4}, 2: {1: 100}, 3: {1: 101},
                             10: {7: 8}, 11: {6: 9}, 12: {2: 100}, 13: {2: 101}})
        original = originals(counts)
        original[0, 0] = original[0, 2]
        original[1, 1] = original[1, 2]
        result = optimizer.optimize(counts, original, thresholds(), 'C2')
        self.assertGreaterEqual(len(result.history), 2)
        for step in result.history:
            sources = step['left'] + step['right']
            self.assertTrue(all(source % 10 >= 2 for source in sources))
            self.assertEqual(len({source // 10 for source in sources}), 1)
        for source in (0, 1, 10, 11):
            np.testing.assert_array_equal(result.model.pool[result.model.mapping.flat[source]],
                                          original.reshape(20, 256)[source])

    def test_exhaustive_greedy_each_step_final_stop_and_every_full_serialized_objective(self):
        counts = counts_for({2: {1: 30, 2: 3}, 3: {1: 31, 2: 3}, 4: {1: 29, 2: 3},
                             5: {200: 100000}, 12: {50: 2}, 13: {51: 3}})
        original, metadata = originals(counts), 123
        expected_model, expected_score, steps = exhaustive_oracle(counts, original, metadata)
        evaluated = []
        real_objective = optimizer.objective
        def inspect(hist, model, metadata_bytes=0):
            score = real_objective(hist, model, metadata_bytes)
            evaluated.append((transport.serialize(model, 'dense_u32'), score, metadata_bytes))
            return score
        with mock.patch.object(optimizer, 'objective', side_effect=inspect):
            result = optimizer.optimize(counts, original, thresholds(), 'C2', metadata)
        self.assertGreaterEqual(len(result.history), 2)
        self.assertFalse(steps[-1]['accepted'])
        self.assertGreater(len(steps[-1]['proposals']), 0, 'Final rejected proposals must actually be evaluated')
        self.assert_same_model(result.model, expected_model)
        self.assertEqual(result.final['J_bytes'], expected_score['J_bytes'])
        self.assertEqual(result.candidates_evaluated, sum(len(step['proposals']) for step in steps))
        self.assertEqual(len(evaluated), 1 + result.candidates_evaluated)
        offset, accepted = 1, 0
        for step in steps:
            count = len(step['proposals'])
            actual_batch = evaluated[offset:offset + count]
            expected_blobs = sorted(transport.serialize(proposal[3], 'dense_u32')
                                    for proposal in step['proposals'])
            self.assertEqual(sorted(item[0] for item in actual_batch), expected_blobs)
            by_blob = {transport.serialize(proposal[3], 'dense_u32'): proposal[4]
                       for proposal in step['proposals']}
            for blob, score, measured_metadata in actual_batch:
                expected = by_blob[blob]
                self.assertEqual(measured_metadata, metadata)
                for key, value in expected.items():
                    self.assertEqual(score[key], value, key)
                self.assertEqual(score['model_bytes'], score['header_bytes'] + score['pmf_bytes'] +
                                 score['mapping_bytes'] + score['threshold_bytes'])
                self.assertEqual(score['mode_identifier_bytes'], 1)
                self.assertEqual(score['storage_identifier_bytes'], 1)
            if step['accepted']:
                history, best = result.history[accepted], step['best']
                self.assertEqual((history['left'], history['right']), (list(best[0]), list(best[1])))
                self.assertEqual(history['J_before'], step['before']['J_bytes'])
                self.assertEqual(history['J_after'], best[4]['J_bytes'])
                self.assertLess(history['J_after'], history['J_before'])
                self.assertEqual(history['side_delta_bytes'], best[4]['model_bytes'] - step['before']['model_bytes'])
                self.assertEqual(history['ideal_delta_bytes'],
                                 best[4]['ideal_payload_bytes'] - step['before']['ideal_payload_bytes'])
                accepted += 1
            else:
                self.assertTrue(all(proposal[4]['J_bytes'] >= step['before']['J_bytes']
                                    for proposal in step['proposals']))
            offset += count
        self.assertEqual(accepted, len(result.history))

    def test_equal_objective_uses_lexicographic_members_and_is_deterministic(self):
        counts = counts_for({source: {1: 1000000} for source in (2, 3, 4)})
        original = originals(counts)
        _, _, steps = exhaustive_oracle(counts, original)
        costs = [proposal[4]['J_bytes'] for proposal in steps[0]['proposals']]
        self.assertEqual(len(set(costs)), 1)
        self.assertTrue(steps[0]['accepted'])
        first = optimizer.optimize(counts, original, thresholds(), 'C2')
        self.assertEqual((first.history[0]['left'], first.history[0]['right']), ([2], [3]))
        self.assertEqual((first.history[1]['left'], first.history[1]['right']), ([2, 3], [4]))
        for _ in range(3):
            repeated = optimizer.optimize(counts.copy(), original.copy(), thresholds(), 'C2')
            self.assertEqual(repeated.history, first.history)
            self.assertEqual(repeated.final, first.final)
            self.assertEqual(repeated.candidates_evaluated, first.candidates_evaluated)
            self.assert_same_model(repeated.model, first.model)

    def test_exact_objective_tie_is_not_accepted(self):
        counts = counts_for({2: {1: 100}, 3: {1: 101}})
        real_objective = optimizer.objective
        def tied(hist, model, metadata_bytes=0):
            result = real_objective(hist, model, metadata_bytes)
            result['J_bytes'] = 500.
            return result
        with mock.patch.object(optimizer, 'objective', side_effect=tied):
            result = optimizer.optimize(counts, originals(counts), thresholds(), 'C2')
        self.assertEqual(result.history, [])
        self.assertEqual(result.candidates_evaluated, 1)
        self.assertEqual(result.final['pool_rows'], 2)

    def test_empty_and_single_observation_histograms(self):
        counts = counts_for({})
        for mode in transport.MODES:
            result = optimizer.optimize(counts, originals(counts), thresholds(), mode, 29)
            self.assertEqual(result.model.pool.shape, (0, 256))
            self.assertTrue(np.all(result.model.mapping == transport.UNUSED))
            self.assertEqual(result.final['ideal_payload_bits'], 0.)
            self.assertEqual(result.final['J_bytes'], transport.HEADER.size + 112 + 20 + 29)
            self.assertEqual(result.candidates_evaluated, 0)
            self.assertEqual(result.history, [])
            self.assertEqual(transport.route(np.empty((0, 2), np.uint8), result.model).shape, (0, 2))
        counts = counts_for({2: {255: 1}, 19: {0: 1}})
        result = optimizer.optimize(counts, originals(counts), thresholds(), 'C2')
        self.assertTrue(np.all(result.model.pool > 0))
        np.testing.assert_array_equal(result.model.pool.sum(axis=1), [65536, 65536])
        self.assertTrue(math.isfinite(result.final['J_bytes']))
        self.assertEqual(result.candidates_evaluated, 0)

    def test_histogram_preserves_channel_local_ids_and_empty_inputs(self):
        symbols = np.array([[9, 7], [9, 8], [4, 7]], np.uint8)
        classes = np.array([[2, 9], [2, 9], [0, 1]], np.uint8)
        expected = counts_for({2: {9: 2}, 0: {4: 1}, 19: {7: 1, 8: 1}, 11: {7: 1}})
        np.testing.assert_array_equal(optimizer.histogram(symbols, classes), expected)
        np.testing.assert_array_equal(optimizer.histogram(np.empty((0, 2), np.uint8),
                                                        np.empty((0, 2), np.uint8)), counts_for({}))
        invalid = [(symbols.astype(np.int16), classes), (symbols, classes.astype(np.int16)),
                   (symbols[:, 0], classes), (symbols, classes[:, 0]),
                   (symbols, np.full_like(classes, 10))]
        for q, c in invalid:
            with self.subTest(q_shape=q.shape, c_shape=c.shape, q_type=q.dtype, c_type=c.dtype):
                with self.assertRaises(ValueError):
                    optimizer.histogram(q, c)

    def test_raw_count_validation_rejects_overflow_before_numpy_sums(self):
        counts = counts_for({2: {0: optimizer.MAX_COUNT_SUM}})
        checked = optimizer.validate_counts(counts)
        self.assertEqual(int(checked.sum()), optimizer.MAX_COUNT_SUM)
        self.assertFalse(np.shares_memory(checked, counts))
        result = optimizer.optimize(counts, originals(counts), thresholds(), 'C2')
        self.assertTrue(math.isfinite(result.final['J_bytes']))
        invalid = [np.zeros((2, 10, 255), np.uint64), counts.astype(np.float64), counts.astype(object),
                   np.zeros((2, 10, 256), bool), counts_for({2: {0: optimizer.MAX_COUNT_SUM + 1}}),
                   counts_for({2: {0: 1 << 63}, 3: {0: 1 << 63}})]
        negative = np.zeros((2, 10, 256), np.int64)
        negative[0, 0, 0] = -1
        invalid.append(negative)
        for index, value in enumerate(invalid):
            with self.subTest(case=index):
                with self.assertRaises(ValueError):
                    optimizer.validate_counts(value)

    def test_original_and_objective_input_validation(self):
        counts = counts_for({2: {1: 2}})
        original = originals(counts)
        bad_sum, bad_zero = original.copy(), original.copy()
        bad_sum[0, 0, 0] += 1
        bad_zero[0, 0, 0] = 0
        for value in (original.astype(np.uint16), original[:, :9], bad_sum, bad_zero):
            with self.assertRaises(ValueError):
                optimizer.optimize(counts, value, thresholds(), 'C0')
        for mode in ('C3', 0, None):
            with self.assertRaises(ValueError):
                optimizer.optimize(counts, original, thresholds(), mode)
        result = optimizer.optimize(counts, original, thresholds(), 'C0')
        for metadata in (-1, 1.5, True, np.int64(1), (1 << 53) + 1):
            with self.subTest(metadata=metadata):
                with self.assertRaises(ValueError):
                    optimizer.objective(counts, result.model, metadata)
        with self.assertRaises(ValueError):
            optimizer.objective(counts_for({3: {1: 2}}), result.model)
        with self.assertRaises(ValueError):
            optimizer.objective(counts_for({}), result.model)


class TransportContracts(unittest.TestCase):
    def fixture(self, mode='C1'):
        counts = counts_for({2: {17: 100}, 9: {200: 70}, 12: {17: 100}})
        return model_for_partition(counts, originals(counts), ((2,), (9,), (12,)), mode)

    def assert_roundtrip(self, model, storage):
        encoded = transport.serialize(model, storage)
        decoded, chosen = transport.deserialize(encoded)
        self.assertEqual(chosen, storage)
        self.assertEqual(decoded.mode, model.mode)
        np.testing.assert_array_equal(decoded.pool, model.pool)
        np.testing.assert_array_equal(decoded.mapping, model.mapping)
        np.testing.assert_array_equal(decoded.thresholds, model.thresholds)
        self.assertEqual(transport.serialize(decoded, storage), encoded)
        decoded_mutable, _ = transport.deserialize(bytearray(encoded))
        np.testing.assert_array_equal(decoded_mutable.pool, model.pool)
        return encoded

    def test_all_three_transports_roundtrip_each_mode_and_empty_pool(self):
        for mode in transport.MODES:
            for storage in transport.STORAGES:
                with self.subTest(mode=mode, storage=storage):
                    self.assert_roundtrip(self.fixture(mode), storage)
                    empty = model_for_partition(counts_for({}), originals(counts_for({})), (), mode)
                    self.assert_roundtrip(empty, storage)

    def test_positive_extreme_mass_fits_packed_u16_exactly(self):
        pool = np.ones((1, 256), np.uint32)
        pool[0, 255] = 65281
        mapping = np.full((2, 10), 255, np.uint8)
        mapping[0, 9] = 0
        model = transport.Model(pool, mapping, thresholds(), 'C1')
        for storage in transport.STORAGES:
            self.assert_roundtrip(model, storage)
        packed = transport.serialize(model, 'packed_u16')
        masses = packed[transport.HEADER.size:transport.HEADER.size + 512]
        self.assertEqual(struct.unpack_from('<H', masses, 255 * 2)[0], 65281)

    def test_choose_measures_all_full_serializations_and_deterministic_storage_ties(self):
        uniform = np.full((1, 256), 256, np.uint32)
        diverse = (np.arange(1, 257, dtype=np.uint32) + 127)[None, :]
        diverse[0, :128] += 1
        mapping = np.full((2, 10), 255, np.uint8)
        mapping[0, 2] = 0
        for pool, expected in ((uniform, 'sparse_default_u16'), (diverse, 'packed_u16')):
            model = transport.Model(pool, mapping, thresholds(), 'C1')
            real_serialize = transport.serialize
            with mock.patch.object(transport, 'serialize', wraps=real_serialize) as serialize:
                data, sizes = transport.choose(model)
            self.assertEqual([call.args[1] for call in serialize.call_args_list], list(transport.STORAGES))
            for storage in transport.STORAGES:
                self.assertEqual(sizes[storage], len(real_serialize(model, storage)))
            self.assertEqual(transport.deserialize(data)[1], expected)
            self.assertEqual(len(data), min(sizes.values()))
            reported = transport.sizes(data)
            self.assertEqual(reported['model_bytes'], reported['pmf_bytes'] + reported['mapping_bytes'] +
                             reported['threshold_bytes'] + reported['header_bytes'])
        empty = model_for_partition(counts_for({}), originals(counts_for({})), (), 'C1')
        data, sizes = transport.choose(empty)
        self.assertEqual(len(set(sizes.values())), 1)
        self.assertEqual(transport.deserialize(data)[1], 'dense_u32')

    def test_sparse_default_uses_smallest_modal_mass_on_tie(self):
        pool = np.full((1, 256), 255, np.uint32)
        pool[0, 128:] = 257
        mapping = np.full((2, 10), 255, np.uint8)
        mapping[0, 2] = 0
        data = self.assert_roundtrip(transport.Model(pool, mapping, thresholds(), 'C1'), 'sparse_default_u16')
        self.assertEqual(struct.unpack_from('<HH', data, transport.HEADER.size), (255, 128))

    def test_route_uses_local_source_ids_not_physical_pool_ids(self):
        model = self.fixture('C1')
        classes = np.array([[2, 2], [9, 2], [2, 2]], np.uint8)
        routes = transport.route(classes, model)
        np.testing.assert_array_equal(routes, np.array([[0, 0], [1, 0], [0, 0]], np.uint8))
        self.assertFalse(np.array_equal(classes, routes))
        for invalid in (routes, classes.astype(np.int64), classes[:, :1],
                        np.full_like(classes, 10), np.array([[2, 2]], np.uint8)):
            with self.assertRaises(ValueError):
                transport.route(invalid, model)

    @staticmethod
    def with_header(data, index, value):
        fields = list(transport.HEADER.unpack_from(data))
        fields[index] = value
        return transport.HEADER.pack(*fields) + data[transport.HEADER.size:]

    def test_malformed_headers_lengths_and_input_types_are_rejected_for_all_transports(self):
        for storage in transport.STORAGES:
            data = transport.serialize(self.fixture(), storage)
            mutations = [(0, b'FAIL'), (1, 2), (2, 0), (2, 4), (3, 3), (4, 1),
                         (5, 21), (6, 999999), (7, 111), (8, 19)]
            for index, value in mutations:
                with self.subTest(storage=storage, field=index, value=value):
                    with self.assertRaises(ValueError):
                        transport.deserialize(self.with_header(data, index, value))
            for malformed in (b'', data[:-1], data + b'X', data[:transport.HEADER.size - 1],
                              memoryview(data), 'not bytes', b'x' * (transport.MAX_BYTES + 1)):
                with self.subTest(storage=storage, malformed_type=type(malformed), size=len(malformed)):
                    with self.assertRaises(ValueError):
                        transport.deserialize(malformed)

    def test_invalid_masses_thresholds_and_mappings_in_wire_data_are_rejected(self):
        model = self.fixture('C0')
        for storage in transport.STORAGES[:2]:
            original = transport.serialize(model, storage)
            width = 4 if storage == 'dense_u32' else 2
            mass_bytes = transport.HEADER.unpack_from(original)[6]
            threshold_start = transport.HEADER.size + mass_bytes
            mapping_start = threshold_start + transport.THRESHOLD_BYTES
            for mass in (0, 1):
                bad = bytearray(original)
                struct.pack_into('<I' if width == 4 else '<H', bad, transport.HEADER.size, mass)
                with self.subTest(storage=storage, mass=mass):
                    with self.assertRaises(ValueError):
                        transport.deserialize(bad)
            for threshold_value in (float('nan'), float('inf'), 999.):
                bad = bytearray(original)
                struct.pack_into('<d', bad, threshold_start, threshold_value)
                with self.assertRaises(ValueError):
                    transport.deserialize(bad)
            for position, value in ((2, 250), (2, 255), (9, 0), (0, 0)):
                bad = bytearray(original)
                bad[mapping_start + position] = value
                with self.subTest(storage=storage, mapping_position=position, mapping_value=value):
                    with self.assertRaises(ValueError):
                        transport.deserialize(bad)
            # All mapping references remain valid but first-use row order is reversed.
            bad = bytearray(original)
            bad[mapping_start + 2], bad[mapping_start + 9] = 1, 0
            with self.assertRaises(ValueError):
                transport.deserialize(bad)
            # Two distinct active classes may not transmit equal rows twice in C1.
            duplicate = bytearray(original)
            duplicate[6] = transport.MODES.index('C1')
            with self.assertRaises(ValueError):
                transport.deserialize(duplicate)

    @staticmethod
    def sparse_blob(raw):
        mapping = np.full((2, 10), 255, np.uint8)
        mapping[0, 2] = 0
        return (transport.HEADER.pack(transport.MAGIC, transport.VERSION, 3, 1, 2, 1,
                                      len(raw), transport.THRESHOLD_BYTES, transport.MAPPING_BYTES)
                + raw + thresholds().astype('<f8').tobytes() + mapping.tobytes())

    def test_noncanonical_sparse_encodings_are_rejected(self):
        valid_raw = struct.pack('<HHBHBH', 256, 2, 0, 255, 1, 257)
        transport.deserialize(self.sparse_blob(valid_raw))
        malformed = {
            'truncated header': b'\x00\x01',
            'zero default': struct.pack('<HH', 0, 0),
            'too many exceptions': struct.pack('<HH', 256, 256),
            'truncated exception': struct.pack('<HHBH', 256, 2, 0, 255),
            'zero mass': struct.pack('<HHBHBH', 256, 2, 0, 0, 1, 257),
            'default as exception': struct.pack('<HHBH', 256, 1, 0, 256),
            'duplicate symbol': struct.pack('<HHBHBH', 256, 2, 0, 255, 0, 257),
            'unsorted symbols': struct.pack('<HHBHBH', 256, 2, 1, 257, 0, 255),
            'wrong total': struct.pack('<HHBH', 256, 1, 0, 257),
            'trailing mass bytes': valid_raw + b'\x00',
            'nonmodal default': struct.pack('<HH', 255, 255) + b''.join(
                struct.pack('<BH', symbol, 257 if symbol == 1 else 256) for symbol in range(1, 256)),
            'larger tied modal default': struct.pack('<HH', 257, 128) + b''.join(
                struct.pack('<BH', symbol, 255) for symbol in range(128)),
        }
        for name, raw in malformed.items():
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    transport.deserialize(self.sparse_blob(raw))

    def test_public_model_validation_and_unknown_storage(self):
        good = self.fixture()
        bad_models = [None, transport.Model(good.pool, good.mapping, good.thresholds, 'C3'),
                      transport.Model(good.pool.astype(np.uint16), good.mapping, good.thresholds, 'C1'),
                      transport.Model(good.pool[:, :255], good.mapping, good.thresholds, 'C1'),
                      transport.Model(good.pool, good.mapping.astype(np.int16), good.thresholds, 'C1'),
                      transport.Model(good.pool, good.mapping[:, :9], good.thresholds, 'C1'),
                      transport.Model(good.pool, good.mapping, good.thresholds.astype(np.float32), 'C1'),
                      transport.Model(good.pool, good.mapping, good.thresholds[:, :6], 'C1'),
                      transport.Model(good.pool, good.mapping, good.thresholds, 'C0')]
        for index, model in enumerate(bad_models):
            with self.subTest(case=index):
                with self.assertRaises(ValueError):
                    transport.validate(model)
        for storage in ('bad', None, 1):
            with self.assertRaises(ValueError):
                transport.serialize(good, storage)


if __name__ == '__main__':
    unittest.main()
