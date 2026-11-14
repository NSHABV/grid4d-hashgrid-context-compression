"""Independent scalar class oracle: boundary/tie/fallback/channel causality tests."""
from bisect import bisect_right
import copy
import unittest
import numpy as np


ARMS = {'IID': 1, 'Geometry4': 4, 'Canonical8': 10, 'Mean8': 10,
        'Mean4': 6, 'Mean4Std2': 10}


def specification(name, tied=False):
    count = 7 if name in ('Canonical8', 'Mean8') else 3
    primary = ([0.0] * count if tied else list(np.linspace(-0.75, 0.75, count)))
    return {'name': name, 'C': ARMS[name], 'edges': {
        'primary': [primary, [-x for x in primary[::-1]]],
        'std': [[0.0 if tied else 0.25], [0.0 if tied else 0.5]],
    }}


def scalar_oracle(contexts, spec):
    """No calls to classifier/binning implementation; scalar bisect interval rule."""
    result = []
    for row, geometry in enumerate(contexts['geometry'].tolist()):
        channel_classes = []
        for channel in range(2):
            if spec['name'] == 'IID':
                cls = 0
            elif spec['name'] == 'Geometry4':
                cls = geometry
            elif geometry < 2:
                cls = geometry
            else:
                field = 'canonical_features' if spec['name'] == 'Canonical8' else 'mean'
                primary_bin = bisect_right(spec['edges']['primary'][channel],
                                           float(contexts[field][row, channel]))
                if spec['name'] == 'Mean4Std2':
                    dispersion_bin = bisect_right(spec['edges']['std'][channel],
                                                  float(contexts['std'][row, channel]))
                    cls = 2 + 2 * primary_bin + dispersion_bin
                else:
                    cls = 2 + primary_bin
            channel_classes.append(cls)
        result.append(channel_classes)
    return np.asarray(result, dtype=np.uint8).reshape((-1, 2))


def fixture():
    values = np.asarray([-2, -.75, -.5, -.25, 0, .25, .5, .75, 2], np.float64)
    tiled = np.tile(values, 4)
    return {'geometry': np.repeat(np.arange(4, dtype=np.uint8), len(values)),
            'canonical_features': np.column_stack((tiled, -tiled)).astype(np.float32),
            'mean': np.column_stack((tiled, -tiled)),
            'std': np.column_stack((np.abs(tiled), np.abs(tiled) / 2))}


class ClassContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from .core import classify
        cls.classify = staticmethod(classify)

    def compare(self, contexts, spec):
        actual = self.classify(contexts, spec)
        np.testing.assert_array_equal(actual, scalar_oracle(contexts, spec))
        self.assertEqual(actual.dtype, np.uint8)
        self.assertEqual(actual.shape, (len(contexts['geometry']), 2))
        self.assertTrue(np.all(actual < spec['C']))
        return actual

    def test_all_six_arms_independent_scalar_oracle(self):
        for name in ARMS:
            with self.subTest(name=name):
                self.compare(fixture(), specification(name))

    def test_iid_ignores_every_feature(self):
        context = fixture()
        for key in ('canonical_features', 'mean', 'std'):
            context[key][:] = np.nan
        np.testing.assert_array_equal(self.compare(context, specification('IID')), 0)

    def test_geometry_ignores_every_feature(self):
        context = fixture()
        for key in ('canonical_features', 'mean', 'std'):
            context[key][:] = np.nan
        expected = np.repeat(context['geometry'][:, None], 2, axis=1)
        np.testing.assert_array_equal(self.compare(context, specification('Geometry4')), expected)

    def test_empty_categories_stay_separate_and_ignore_sentinel_features(self):
        context = fixture()
        for key in ('canonical_features', 'mean', 'std'):
            context[key][context['geometry'] < 2] = np.nan
        for name in ('Canonical8', 'Mean8', 'Mean4', 'Mean4Std2'):
            self.compare(context, specification(name))

    def test_equal_threshold_goes_to_right_bin(self):
        context = fixture()
        for name in ('Canonical8', 'Mean8', 'Mean4', 'Mean4Std2'):
            self.compare(context, specification(name))

    def test_threshold_neighbors_are_not_rounded_together(self):
        context = {'geometry': np.full(3, 3, np.uint8)}
        values = np.asarray([np.nextafter(0.25, -np.inf), .25, np.nextafter(.25, np.inf)])
        context.update(mean=np.column_stack((values, values)),
                       canonical_features=np.column_stack((values, values)),
                       std=np.zeros((3, 2)))
        spec = specification('Mean8')
        ids = self.compare(context, spec)
        self.assertEqual(int(ids[1, 0])-int(ids[0, 0]), 1)
        self.assertEqual(int(ids[2, 0]), int(ids[1, 0]))

    def test_tied_edges_preserved_with_skipped_class_ids(self):
        context = fixture()
        for name in ('Canonical8', 'Mean8', 'Mean4', 'Mean4Std2'):
            self.compare(context, specification(name, tied=True))
        ids = self.compare(context, specification('Mean8', tied=True))
        self.assertEqual(set(ids[context['geometry'] >= 2].ravel().tolist()), {2, 9})

    def test_std_zero_median_right_interval(self):
        context = fixture()
        context['std'][:] = 0
        spec = specification('Mean4Std2', tied=True)
        ids = self.compare(context, spec)
        self.assertTrue(np.all(ids[context['geometry'] >= 2] % 2 == 1))

    def test_mean_std_cartesian_product_has_eight_main_classes(self):
        means = np.repeat([-2.0, -.5, .5, 2.0], 2)
        stds = np.tile([0.0, 1.0], 4)
        context = {'geometry': np.full(8, 3, np.uint8),
                   'mean': np.column_stack((means, means)),
                   'std': np.column_stack((stds, stds))}
        ids = self.compare(context, specification('Mean4Std2'))
        self.assertEqual(set(ids[:, 0].tolist()), set(range(2, 10)))

    def test_channels_use_their_own_thresholds(self):
        context = fixture()
        spec = specification('Mean4')
        spec['edges']['primary'][1] = [10., 11., 12.]
        ids = self.compare(context, spec)
        self.assertTrue(np.all(ids[context['geometry'] >= 2, 1] == 2))
        self.assertTrue(np.any(ids[:, 0] != ids[:, 1]))

    def test_canonical_and_mean_are_distinct_fields(self):
        context = fixture()
        context['mean'][:] = 2.
        context['canonical_features'][:] = -2.
        canonical = self.compare(context, specification('Canonical8'))
        mean = self.compare(context, specification('Mean8'))
        active = context['geometry'] >= 2
        self.assertTrue(np.all(canonical[active] == 2))
        self.assertTrue(np.all(mean[active] == 9))

    def test_slot_permutation_equivariance(self):
        context = fixture()
        order = np.random.default_rng(123).permutation(len(context['geometry']))
        permuted = {key: value[order] for key, value in context.items()}
        for name in ARMS:
            spec = specification(name)
            np.testing.assert_array_equal(self.classify(context, spec)[order],
                                          self.compare(permuted, spec))

    def test_arbitrary_chunk_boundaries_do_not_change_classes(self):
        context = fixture()
        for name in ARMS:
            spec = specification(name)
            pieces = [self.classify({k: v[a:b] for k, v in context.items()}, spec)
                      for a, b in ((0, 1), (1, 13), (13, 29), (29, 36))]
            np.testing.assert_array_equal(np.concatenate(pieces), self.compare(context, spec))

    def test_extra_fine_targets_do_not_affect_classes(self):
        context = fixture()
        first = dict(context, fine_symbols=np.zeros((36, 2), np.uint8))
        second = dict(context, fine_symbols=np.full((36, 2), 255, np.uint8))
        for name in ARMS:
            spec = specification(name)
            np.testing.assert_array_equal(self.classify(first, spec), self.classify(second, spec))

    def test_classifier_does_not_mutate_inputs_or_specs(self):
        context = fixture()
        saved = {key: value.copy() for key, value in context.items()}
        for name in ARMS:
            spec = specification(name)
            frozen = copy.deepcopy(spec)
            self.compare(context, spec)
            self.assertEqual(spec, frozen)
        for key in context:
            np.testing.assert_array_equal(context[key], saved[key])

    def test_singleton_can_share_main_bins_but_never_fallback(self):
        context = fixture()
        for name in ('Canonical8', 'Mean8', 'Mean4', 'Mean4Std2'):
            ids = self.compare(context, specification(name))
            self.assertTrue(np.all(ids[context['geometry'] == 2] >= 2))


if __name__ == '__main__':
    unittest.main()
