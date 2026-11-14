"""Small deterministic unit tests; checkpoint/GPU integration is checked separately."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import torch
from .codec import (KEYS, dequantize, empirical_entropy, export_lossless,
                    export_quantized, import_tables, quantize, sha, validate_grid, write_json)


class CodecTests(unittest.TestCase):
    def test_quantization_bounds_and_error(self):
        x = np.array([-2., -1., 0., 1., 3.], dtype=np.float32)
        for bits in (8, 12, 16):
            codes, params = quantize(x, bits)
            restored = dequantize(codes, json.loads(json.dumps(params)))
            self.assertEqual(restored[0], x[0])
            self.assertEqual(restored[-1], x[-1])
            self.assertLessEqual(float(np.abs(x - restored).max()), params['step'] / 2 + 1e-6)
            self.assertEqual(codes[0], 0)
            self.assertEqual(codes[-1], (1 << bits) - 1)

    def test_constant_and_extremes(self):
        for x in (np.full((3, 2), 1.25, dtype=np.float32),
                  np.zeros((2, 2), dtype=np.float32),
                  np.array([-np.finfo(np.float32).max, 0, np.finfo(np.float32).max], dtype=np.float32),
                  np.array([0, np.nextafter(np.float32(0), np.float32(1))], dtype=np.float32)):
            for bits in (8, 12, 16):
                q, p = quantize(x, bits)
                y = dequantize(q, p)
                self.assertTrue(np.isfinite(y).all())
                if np.all(x == x.flat[0]):
                    np.testing.assert_array_equal(x, y)

    def test_invalid_quantization(self):
        for x in (np.array([], dtype=np.float32), np.array([np.nan], dtype=np.float32),
                  np.array([np.inf], dtype=np.float32), np.array([1], dtype=np.float64)):
            with self.assertRaises(ValueError):
                quantize(x, 8)
        with self.assertRaises(ValueError):
            quantize(np.array([1], dtype=np.float32), 7)
        with self.assertRaises(ValueError):
            dequantize(np.array([256], dtype=np.int32), quantize(np.array([0, 1], dtype=np.float32), 8)[1])

    def test_entropy_known(self):
        self.assertAlmostEqual(empirical_entropy([7, 7, 7])['bits_per_symbol'], 0)
        self.assertAlmostEqual(empirical_entropy([0, 0, 1, 1])['bits_per_symbol'], 1)
        self.assertAlmostEqual(empirical_entropy([0, 1, 2, 3])['bits_per_symbol'], 2)
        self.assertAlmostEqual(empirical_entropy([0, 0, 0, 1])['bits_per_symbol'], .8112781244591328)
        with self.assertRaises(ValueError):
            empirical_entropy([])

    def test_interchange_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            grid, records = {}, {}
            for key in KEYS:
                prefix = key.split('.')[0]
                # Include signed zero and smallest positive subnormal.
                grid[key] = torch.tensor([[-0., 0.], [1., -1.], [2., 3.]], dtype=torch.float32)
                grid[f'{prefix}.offsets'] = torch.tensor([0, 1, 3], dtype=torch.int32)
                grid[f'{prefix}.base_resolution'] = torch.tensor([1., 1., 1.])
                grid[f'{prefix}.per_level_scale'] = torch.tensor([2., 2., 2.])
                records[key] = {'shape': [3, 2], 'levels': 2, 'feature_dimension': 2,
                    'offsets': [0, 1, 3], 'table_rows_per_level': [1, 2],
                    'scalar_count': 6, 'bytes': 24, 'allocation_resolutions': [[1]*3, [2]*3],
                    'cuda_lookup_resolutions': [[1]*3, [2]*3],
                    'base_resolution': [1.]*3, 'per_level_scale': [2.]*3}
            cp = root / 'source.pth'
            torch.save((grid, {}), cp)
            runtime = root / 'runtime.json'
            write_json(runtime, {'checkpoint_sha256': sha(cp), 'grid_args': {}, 'network_args': {},
                                 'trainable_parameters': records})
            export_lossless(cp, runtime, root / 'lossless')
            restored, _, meta = import_tables(root / 'lossless')
            for key in KEYS:
                self.assertTrue(torch.equal(grid[key], restored[key]))
                self.assertEqual(grid[key].numpy().tobytes(), restored[key].numpy().tobytes())
                self.assertEqual(meta['grids'][key]['offsets'], [0, 1, 3])
            for scope in ('table', 'level'):
                for bits in (8, 12, 16):
                    path = root / f'{scope}-{bits}'
                    export_quantized(root / 'lossless', path, bits, scope)
                    decoded, _, _ = import_tables(path)
                    self.assertTrue(all(torch.isfinite(x).all() for x in decoded.values()))
            bad = copy.deepcopy(records[KEYS[0]])
            bad['offsets'] = [0, 2, 2]
            with self.assertRaises(ValueError):
                validate_grid(bad)
            payload = root / 'lossless/xyz_encoding.f32.bin'
            payload.write_bytes(payload.read_bytes()[:-1])
            with self.assertRaises(ValueError):
                import_tables(root / 'lossless')


if __name__ == '__main__':
    unittest.main()
