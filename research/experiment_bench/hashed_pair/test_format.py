"""Independent small fixtures for the new hashed-pair container and engine.

These tests use synthetic symbols and probability tables.  The separate
corruption command applies adversarial mutations to a real, completed stream.
"""
from __future__ import annotations

import copy
import unittest

import numpy as np

from research.experiment_bench.hashed_interlevel import dry_model
from research.experiment_bench.hashed_interlevel.core import fit_masses


class ProbabilityTransportTests(unittest.TestCase):
    def test_all_supported_storages_exact(self):
        rng = np.random.default_rng(491)
        for count in (1, 4, 10):
            q = rng.integers(0, 256, (417, 2), dtype=np.uint8)
            classes = rng.integers(0, count, q.shape, dtype=np.uint8)
            _, masses = fit_masses(q, classes, np.arange(len(q)), count)
            self.assertTrue(np.all(masses > 0))
            np.testing.assert_array_equal(masses.sum(axis=-1), 65536)
            # Repeated thresholds are legal and must survive bit-exactly.
            edges = {'primary': np.array([[0., 0., 1.], [-0., 2., 2.]])}
            for storage in dry_model.STORAGES:
                data = dry_model.serialize(masses, edges, {'C': count}, {}, storage)
                restored, limits, spec, metadata = dry_model.deserialize(data)
                np.testing.assert_array_equal(restored, masses)
                self.assertEqual(limits['primary'].tobytes(), edges['primary'].tobytes())
                self.assertEqual(spec, {'C': count})
                self.assertEqual(metadata, {})
                self.assertEqual(dry_model.section_sizes(data)['total'], len(data))
                self.assertEqual(data, dry_model.serialize(masses, edges, spec, metadata, storage))

    def test_zero_negative_wrong_sum_or_dtype_mass_rejected(self):
        valid = np.full((2, 4, 256), 256, dtype=np.uint32)
        variants = []
        bad = valid.copy(); bad[0, 0, 0] = 0; variants.append(bad)
        bad = valid.copy(); bad[0, 0, 0] += 1; variants.append(bad)
        variants.append(valid.astype(np.float64))
        variants.append(valid.astype(np.int32))
        for bad in variants:
            with self.assertRaises(ValueError):
                dry_model.serialize(bad, {}, {}, {}, 'packed_u16')

    def test_nonfinite_or_non_float64_threshold_rejected(self):
        masses = np.full((2, 1, 256), 256, dtype=np.uint32)
        for edges in (np.array([np.nan]), np.array([np.inf]), np.array([1.], np.float32)):
            with self.assertRaises(ValueError):
                dry_model.serialize(masses, {'primary': edges}, {}, {}, 'packed_u16')

    def test_oversized_mass_header_rejected_before_numpy_allocation(self):
        from unittest.mock import patch
        data = dry_model.HEADER.pack(b'HDPM', 1, 1, 2, 10, 256, 2**31, 0, 0, 0)
        with patch.object(np, 'empty', side_effect=AssertionError('allocation before bound check')):
            with self.assertRaises(ValueError):
                dry_model.deserialize(data)


class IndexedEngineTests(unittest.TestCase):
    @staticmethod
    def engine():
        from research.experiment_bench.hashed_pair import engine
        return engine

    def test_roundtrip_channel_and_row_boundaries(self):
        engine = self.engine()
        rng = np.random.default_rng(714)
        for count in (1, 4, 10):
            q = rng.integers(0, 256, (257, 2), dtype=np.uint8)
            q[0] = [0, 255]; q[-1] = [255, 0]
            c = rng.integers(0, count, q.shape, dtype=np.uint8)
            _, masses = fit_masses(q, c, np.arange(len(q)), count)
            reference = engine.encode_indexed(q, c, masses, chunk_rows=4096)
            for chunk in (1, 13, 256, 4096):
                encoded = engine.encode_indexed(q, c, masses, chunk_rows=chunk)
                self.assertEqual(encoded, reference)
                decoded = engine.decode_indexed(encoded, c, masses, chunk_rows=chunk)
                np.testing.assert_array_equal(decoded, q)

    def test_uniform_empty_fitted_classes_roundtrip(self):
        engine = self.engine()
        q = np.array([[0, 255], [255, 0], [128, 128]], np.uint8)
        classes = np.array([[0, 3], [2, 1], [3, 0]], np.uint8)
        masses = np.full((2, 4, 256), 256, np.uint32)
        payload = engine.encode_indexed(q, classes, masses)
        np.testing.assert_array_equal(engine.decode_indexed(payload, classes, masses), q)

    def test_invalid_classes_and_masses_rejected(self):
        engine = self.engine()
        q = np.zeros((5, 2), np.uint8)
        masses = np.full((2, 4, 256), 256, np.uint32)
        for classes in (np.full((5, 2), 4, np.uint8), np.full((5, 2), -1),
                        np.zeros((5, 2), np.float64), np.zeros((5, 1), np.uint8)):
            with self.assertRaises(ValueError):
                engine.encode_indexed(q, classes, masses)
        bad = masses.copy(); bad[1, 2, 128] = 0
        with self.assertRaises(ValueError):
            engine.encode_indexed(q, q, bad)

    def test_empty_and_unaligned_entropy_payload_rejected(self):
        engine = self.engine()
        classes = np.zeros((3, 2), np.uint8)
        masses = np.full((2, 1, 256), 256, np.uint32)
        for data in (b'', b'\x00', b'\x00' * 3, b'\x00' * 5):
            with self.assertRaises(ValueError):
                engine.decode_indexed(data, classes, masses)


def synthetic_header():
    """Valid structural metadata, but no source file or saved target dependency."""
    from research.experiment_bench.hashed_pair import format as fmt
    geometry = {'version': 1, 'grid': 'xyz', 'arithmetic': fmt.ARITHMETIC,
                'geometry_convention': fmt.CONVENTION, 'fallback': copy.deepcopy(fmt.FALLBACK),
                'hash': copy.deepcopy(fmt.HASH), 'interpolation': 'smoothstep-corners0to7',
                **copy.deepcopy(fmt.EXPECTED), 'source_checkpoint_sha256': '0' * 64,
                'source_symbols_sha256': '1' * 64}
    geometry['coarse']['quantization'] = {
        'row_start': 0, 'row_end': 6098108, 'bits': 8,
        'min': -5.548852920532227, 'max': 2.9999356269836426,
        'step': 0.03352466097065047, 'rounding': 'nearest-even',
        'reconstruction_dtype': 'float32'}
    return {'version': 1, 'kind': 'standalone-xyz-L4-L5', 'engine': copy.deepcopy(fmt.ENGINE),
            'arithmetic': fmt.ARITHMETIC, 'numpy': '1.26.4', 'order': fmt.ORDER,
            'geometry': geometry,
            'model': {'name': 'IID', 'C': 1, 'storage': 'packed_u16', 'coarse_storage': 'packed_u16'},
            'integrity': {key: '0' * 64 for key in ('q4', 'q5', 'classes', 'coarse_masses', 'fine_masses')}}


class ContainerStructureTests(unittest.TestCase):
    def setUp(self):
        from research.experiment_bench.hashed_pair import format as fmt
        self.fmt = fmt
        self.header = synthetic_header()
        self.sections = dict.fromkeys(fmt.NAMES, b'\x00' * 4)

    def test_structure_roundtrip_and_exact_accounting(self):
        data = self.fmt.pack(self.header, self.sections)
        header, sections = self.fmt.unpack(data)
        self.assertEqual(header, self.header)
        self.assertEqual(self.fmt.pack(header, sections), data)
        self.assertEqual(len(data), self.fmt.PREFIX.size + sum(map(len, sections.values())) + 32)

    def test_geometry_hash_domain_rules_rejected(self):
        changes = [(('geometry', 'fine', 'rows'), 2**50),
                   (('geometry', 'fine', 'rows'), 524288.0),
                   (('geometry', 'coarse', 'offset_start'), 125562),
                   (('geometry', 'fine', 'scale'), [79., 79., 79.]),
                   (('geometry', 'fine', 'lookup_resolution'), [81, 81, 80]),
                   (('geometry', 'hash', 'primes'), [1, 3, 5]),
                   (('geometry', 'hash', 'mask'), 2**64-1),
                   (('geometry', 'geometry_convention'), 'clamp-to-boundary'),
                   (('geometry', 'interpolation'), 'linear'),
                   (('geometry', 'fallback', 'features'), [1, 1]),
                   (('geometry', 'coarse', 'quantization', 'step'), -1.),
                   (('geometry', 'coarse', 'quantization', 'bits'), 7),
                   (('geometry', 'coarse', 'quantization', 'rounding'), 'floor'),
                   (('geometry', 'coarse', 'quantization', 'min'), 100.)]
        from unittest.mock import patch
        for path, value in changes:
            with self.subTest(path=path, value=value):
                h = copy.deepcopy(self.header); cursor = h
                for key in path[:-1]: cursor = cursor[key]
                cursor[path[-1]] = value
                data = self.fmt.pack(h, self.sections)
                with patch.object(self.fmt, '_contexts', side_effect=AssertionError('context allocated before validation')):
                    with self.assertRaises(ValueError): self.fmt.unpack(data)

    def test_model_rules_and_threshold_semantics(self):
        spec = {'name': 'Mean8', 'C': 10, 'rules': copy.deepcopy(self.fmt.RULES)}
        limits = {'primary': np.zeros((2, 7), np.float64)}
        self.fmt.validate_spec(spec, limits, 'Mean8')  # Repeated zero quantiles legal.
        cases = []
        bad = copy.deepcopy(spec); bad['rules']['boundary'] = 'searchsorted-left'; cases.append((bad, limits))
        bad = copy.deepcopy(spec); bad['C'] = 8; cases.append((bad, limits))
        cases.extend((spec, {'primary': x}) for x in
                     (np.zeros((2, 8)), np.zeros((1, 7)), np.full((2, 7), np.inf),
                      np.array([[1., 0, 0, 0, 0, 0, 0]] * 2), np.zeros((2, 7), np.float32)))
        cases.append((spec, {'primary': limits['primary'], 'extra': np.zeros(1)}))
        for model, edges in cases:
            with self.assertRaises(ValueError): self.fmt.validate_spec(model, edges, 'Mean8')

    def test_length_bound_checked_before_digest_or_model_allocation(self):
        from unittest.mock import patch
        prefix = self.fmt.PREFIX.pack(self.fmt.MAGIC, 1, 2**50, 0, 0, 0, 0) + bytes(32)
        with patch.object(self.fmt.hashlib, 'sha256', side_effect=AssertionError('digest before length bound')):
            with self.assertRaises(ValueError): self.fmt.unpack(prefix)

    def test_corrupt_version_magic_digest_and_truncation(self):
        original = self.fmt.pack(self.header, self.sections)
        candidates = [b'', original[:-1], original + bytes(4)]
        for offset in (0, 8, len(original)-1):
            bad = bytearray(original); bad[offset] ^= 1; candidates.append(bytes(bad))
        for bad in candidates:
            with self.assertRaises(ValueError): self.fmt.unpack(bad)

    def test_invalid_payload_lengths(self):
        for key in ('coarse_payload', 'fine_payload'):
            for value in (b'', bytes(3), bytes(5)):
                sections = dict(self.sections); sections[key] = value
                with self.assertRaises(ValueError):
                    self.fmt.unpack(self.fmt.pack(self.header, sections))

    def test_engine_assertion_becomes_controlled_payload_error(self):
        from unittest.mock import patch
        message = 'Tried to decode from compressed data that is invalid for the employed entropy model.'
        with patch.object(self.fmt.engine, 'decode_indexed', side_effect=AssertionError(message)):
            with self.assertRaisesRegex(ValueError, 'Invalid range payload'):
                self.fmt._decode_payload(b'\x00' * 4, np.zeros((1, 2), np.uint8),
                                         np.full((2, 1, 256), 256, np.uint32))


if __name__ == '__main__':
    unittest.main()
