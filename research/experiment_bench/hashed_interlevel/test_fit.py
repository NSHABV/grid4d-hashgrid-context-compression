"""Synthetic held-out causality and scoring tests, independent of real targets."""
import copy
import math
import unittest

import numpy as np

from research.experiment_bench.hashed_interlevel.core import (
    ARMS, classify, fit_masses, fit_spec, losses, split_slots, strata,
)


class HeldoutFitTests(unittest.TestCase):
    @staticmethod
    def fixture(n=400):
        rng = np.random.default_rng(731)
        geometry = (np.arange(n) % 4).astype(np.uint8)
        point_count = np.where(geometry == 2, 1, np.where(geometry == 3, 2 + np.arange(n) % 3, 0))
        context = {
            'geometry': geometry,
            'point_count': point_count,
            'mean': rng.normal(size=(n, 2)),
            'canonical_features': rng.normal(size=(n, 2)).astype(np.float32),
            'std': rng.uniform(0.1, 1.0, size=(n, 2)),
        }
        context['std'][geometry < 3] = 0.
        q = rng.integers(0, 256, size=(n, 2), dtype=np.uint8)
        return context, q

    def test_splits_disjoint_cover_all_slots_and_preserve_channel_groups(self):
        _, q = self.fixture()
        seen = []
        for seed in (0, 1, 2):
            parts = split_slots(len(q), seed)
            self.assertEqual({key: len(value) for key, value in parts.items()},
                             {'train': 256, 'validation': 64, 'test': 80})
            flattened = np.concatenate(list(parts.values()))
            np.testing.assert_array_equal(np.sort(flattened), np.arange(len(q)))
            self.assertEqual(len(np.unique(flattened)), len(q))
            for name, rows in parts.items():
                self.assertEqual(q[rows].shape, (len(rows), 2))
                np.testing.assert_array_equal(rows, np.sort(rows))
                np.testing.assert_array_equal(rows, split_slots(len(q), seed)[name])
            seen.append(parts['test'])
        self.assertFalse(np.array_equal(seen[0], seen[1]))
        self.assertFalse(np.array_equal(seen[1], seen[2]))

    def test_split_real_size_rounding_is_explicit(self):
        split = split_slots(524288, 0)
        self.assertEqual(len(split['test']), 104857)
        self.assertEqual(len(split['validation']), 83886)
        self.assertEqual(len(split['train']), 335545)

    def test_fit_ignores_every_nontrain_target_and_feature(self):
        ctx, q = self.fixture()
        split = split_slots(len(q), 1)
        train = split['train']
        other = np.concatenate((split['validation'], split['test']))
        modified = {key: arr.copy() for key, arr in ctx.items()}
        modified['geometry'][other] = 3
        modified['point_count'][other] = 10000
        for key in ('mean', 'canonical_features', 'std'):
            modified[key][other] = 1e6
        changed_q = q.copy()
        changed_q[other] = 255 - changed_q[other]
        for name, C in ARMS.items():
            with self.subTest(model=name):
                spec = fit_spec(ctx, train, name)
                changed_spec = fit_spec(modified, train, name)
                self.assertEqual(spec, changed_spec)
                cls = classify(ctx, spec)
                changed_cls = classify(modified, changed_spec)
                np.testing.assert_array_equal(cls[train], changed_cls[train])
                counts, masses = fit_masses(q, cls, train, C)
                new_counts, new_masses = fit_masses(changed_q, changed_cls, train, C)
                np.testing.assert_array_equal(counts, new_counts)
                np.testing.assert_array_equal(masses, new_masses)

    def test_target_changes_never_change_context_spec_or_classes(self):
        ctx, q = self.fixture()
        train = split_slots(len(q), 0)['train']
        for name in ARMS:
            spec = fit_spec(ctx, train, name)
            original = classify(ctx, spec)
            q[:] = 0  # all targets can change: neither API receives q
            self.assertEqual(spec, fit_spec(ctx, train, name))
            np.testing.assert_array_equal(original, classify(ctx, spec))

    def test_thresholds_train_active_only_manual_quantiles(self):
        ctx, _ = self.fixture(16)
        train = np.arange(12)
        active = np.array([2, 3, 6, 7, 10, 11])
        self.assertTrue(np.all(ctx['geometry'][active] >= 2))
        ctx['mean'][:] = 9999.
        ctx['mean'][active, 0] = np.arange(6)
        ctx['mean'][active, 1] = 2 * np.arange(6)
        spec = fit_spec(ctx, train, 'Mean4')
        np.testing.assert_array_equal(spec['edges']['primary'][0], [1.25, 2.5, 3.75])
        np.testing.assert_array_equal(spec['edges']['primary'][1], [2.5, 5., 7.5])

    def test_finite_unseen_classes_and_symbols(self):
        q = np.full((6, 2), 17, np.uint8)
        classes = np.zeros((6, 2), np.uint8)
        counts, masses = fit_masses(q, classes, np.arange(4), 10)
        np.testing.assert_array_equal(counts[:, 1:], 0)
        np.testing.assert_array_equal(masses[:, 1:], 256)
        self.assertTrue(np.all(masses >= 1))
        self.assertEqual(masses.dtype, np.uint32)
        np.testing.assert_array_equal(masses.sum(axis=2, dtype=np.uint64), 65536)
        cdf = np.concatenate((np.zeros((2, 10, 1), np.uint64),
                              np.cumsum(masses, axis=2, dtype=np.uint64)), axis=2)
        self.assertTrue(np.all(np.diff(cdf, axis=2) > 0))
        q[4:] = 255
        classes[4:] = 9
        np.testing.assert_array_equal(losses(q, classes, masses, np.array([4, 5])), 8.)

    def test_losses_match_scalar_oracle_per_slot_channel(self):
        masses = np.ones((2, 4, 256), np.uint32)
        masses[:, :, 255] = 65281
        masses[0, 0] = 256
        q = np.array([[0, 255], [255, 7], [1, 2]], np.uint8)
        classes = np.array([[0, 3], [1, 2], [3, 0]], np.uint8)
        rows = np.array([2, 0, 1])
        expected = np.array([
            [-math.log2(int(masses[channel, int(classes[row, channel]), int(q[row, channel])]) / 65536.)
             for channel in range(2)]
            for row in rows
        ])
        np.testing.assert_allclose(losses(q, classes, masses, rows), expected, rtol=0, atol=1e-15)

    def test_duplicate_edges_right_closed_equality_and_geometry_fallback(self):
        ctx, _ = self.fixture(8)
        ctx['mean'][:] = np.array([-1., 0., 0., 1., 2., 2., 3., 4.])[:, None]
        ctx['geometry'][:] = 3
        ctx['geometry'][:2] = [0, 1]
        spec = {'name': 'Mean4', 'C': 6,
                'edges': {'primary': [[0., 0., 2.], [0., 0., 2.]], 'std': [[], []]}}
        result = classify(ctx, spec)
        expected = np.array([0, 1, 4, 4, 5, 5, 5, 5], np.uint8)
        np.testing.assert_array_equal(result, np.repeat(expected[:, None], 2, axis=1))

    def test_zero_std_collapses_to_relabelled_mean4(self):
        ctx, q = self.fixture()
        ctx['std'][:] = 0.
        split = split_slots(len(q), 2)
        plain = fit_spec(ctx, split['train'], 'Mean4')
        extended = fit_spec(ctx, split['train'], 'Mean4Std2')
        self.assertEqual(plain['edges']['primary'], extended['edges']['primary'])
        self.assertEqual(extended['edges']['std'], [[0.], [0.]])
        a = classify(ctx, plain)
        b = classify(ctx, extended)
        active = ctx['geometry'] >= 2
        np.testing.assert_array_equal(b[active], 2 * a[active] - 1)
        np.testing.assert_array_equal(b[~active], a[~active])
        _, ma = fit_masses(q, a, split['train'], 6)
        _, mb = fit_masses(q, b, split['train'], 10)
        np.testing.assert_array_equal(losses(q, a, ma, split['test']),
                                      losses(q, b, mb, split['test']))

    def test_arms_have_fixed_class_budgets(self):
        ctx, _ = self.fixture()
        train = split_slots(len(ctx['geometry']), 0)['train']
        self.assertEqual(ARMS, {'IID': 1, 'Geometry4': 4, 'Canonical8': 10,
                               'Mean8': 10, 'Mean4': 6, 'Mean4Std2': 10})
        for name, C in ARMS.items():
            classes = classify(ctx, fit_spec(ctx, train, name))
            self.assertEqual(classes.shape, (400, 2))
            self.assertEqual(classes.dtype, np.uint8)
            self.assertTrue(np.all(classes < C))

    def test_strata_are_slot_masks_and_partition(self):
        ctx, _ = self.fixture()
        rows = split_slots(400, 0)['test']
        groups = strata(ctx, rows)
        combined = np.stack([groups[f'G{k}'] for k in range(4)])
        np.testing.assert_array_equal(combined.sum(axis=0), 1)
        k_groups = np.stack([groups['G3_K2'], groups['G3_K3'], groups['G3_K4plus']])
        np.testing.assert_array_equal(k_groups.sum(axis=0), groups['G3'].astype(int))


if __name__ == '__main__':
    unittest.main(verbosity=2)
