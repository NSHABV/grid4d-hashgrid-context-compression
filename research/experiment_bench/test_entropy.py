import copy
import hashlib
import inspect
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
import torch
from research.grid4d.codec import KEYS, export_lossless, export_quantized, import_tables, sha, write_json
from . import entropy
from .models import ChannelContext, HistogramModel, context_class, frequencies, TOTAL


def fixture(root):
    grid, records = {}, {}
    rng = np.random.default_rng(0)
    for key in KEYS:
        prefix = key.split('.')[0]
        grid[key] = torch.from_numpy(rng.normal(size=(97, 2)).astype(np.float32))
        grid[f'{prefix}.offsets'] = torch.tensor([0, 17, 97], dtype=torch.int32)
        grid[f'{prefix}.base_resolution'] = torch.tensor([1., 1., 1.])
        grid[f'{prefix}.per_level_scale'] = torch.tensor([2., 2., 2.])
        records[key] = {'shape': [97, 2], 'levels': 2, 'feature_dimension': 2,
            'offsets': [0, 17, 97], 'table_rows_per_level': [17, 80], 'scalar_count': 194,
            'bytes': 776, 'allocation_resolutions': [[3]*3, [5]*3], 'cuda_lookup_resolutions': [[3]*3, [5]*3],
            'base_resolution': [1.]*3, 'per_level_scale': [2.]*3}
    checkpoint = root/'source.pth'
    torch.save((grid, {}), checkpoint)
    runtime = root/'runtime.json'
    write_json(runtime, {'checkpoint_sha256': sha(checkpoint), 'grid_args': {}, 'network_args': {}, 'trainable_parameters': records})
    export_lossless(checkpoint, runtime, root/'float')
    export_quantized(root/'float', root/'quant', 8, 'level')
    return root/'quant'


class EntropyTests(unittest.TestCase):
    def test_finite_cdf_empty_constant_and_extremes(self):
        for counts in (np.zeros(256), np.ones(256), np.r_[1e9, np.zeros(255)]):
            f = frequencies(counts)
            cdf = np.r_[0, np.cumsum(f, dtype=np.uint64)]
            self.assertEqual(int(cdf[-1]), TOTAL)
            self.assertTrue(np.all(np.diff(cdf) >= 1))
            self.assertAlmostEqual(float((f.astype(np.float64)/TOTAL).sum()), 1.)
            self.assertTrue(np.array_equal(f, frequencies(counts)))
        model = HistogramModel(np.stack([frequencies(np.zeros(256))]*2))
        x = np.column_stack((np.arange(256, dtype=np.uint8), np.arange(255, -1, -1, dtype=np.uint8)))
        self.assertTrue(np.array_equal(x, entropy.decode_symbols(entropy.encode_symbols(x, model), len(x), model)))

    def test_decoder_available_causal_context_independent_reference(self):
        first = np.arange(256, dtype=np.uint8)
        expected = np.array([int(value)//16 for value in first], dtype=np.uint8)
        np.testing.assert_array_equal(context_class(first), expected)
        self.assertEqual(list(inspect.signature(context_class).parameters), ['first'])
        x = np.column_stack((first, first))
        model = ChannelContext.fit(x)
        plan = model.plan_second(first)
        for distribution, indices in plan:
            self.assertTrue(all(int(first[i])//16 == distribution-1 for i in indices))
            self.assertTrue(np.all(np.diff(indices) > 0))
        seen = np.concatenate([idx for _, idx in plan])
        np.testing.assert_array_equal(np.sort(seen), np.arange(256))
        changed_future = x.copy(); changed_future[:, 1] ^= 255
        # Changing any q1 cannot affect extraction of contexts or scheduling.
        np.testing.assert_array_equal(context_class(changed_future[:, 0]), expected)
        modified_first = first.copy(); modified_first[0] = 255
        self.assertEqual(int(context_class(modified_first)[0]), 15)
        self.assertTrue(np.array_equal(x, entropy.decode_symbols(entropy.encode_symbols(x, model), len(x), model)))
        empirical, _ = entropy._entropy_cost(x, model)
        # Independent reference: H(q0)=8, H(q1|floor(q0/16))=4.
        self.assertAlmostEqual(empirical, 256*(8+4))
        iid = HistogramModel.fit(x)
        self.assertAlmostEqual(entropy._entropy_cost(x, iid)[0], 256*(8+8))

    def test_constant_and_empty_contexts(self):
        for x in (np.zeros((17, 2), dtype=np.uint8), np.full((17, 2), 255, dtype=np.uint8),
                  np.array([[0, 255], [16, 0], [255, 128]], dtype=np.uint8)):
            for cls in (HistogramModel, ChannelContext):
                model = cls.fit(x)
                np.testing.assert_array_equal(x, entropy.decode_symbols(entropy.encode_symbols(x, model), len(x), model))
                for row in model.freq:
                    self.assertEqual(int(row.sum()), TOTAL)
                    self.assertTrue(np.all(row > 0))

    def test_invalid_schedules_and_iid_context_fairness(self):
        x = np.array([[0, 0], [16, 255], [255, 16]], dtype=np.uint8)
        iid, contextual = HistogramModel.fit(x), ChannelContext.fit(x)
        np.testing.assert_array_equal(iid.freq[0], contextual.freq[0])
        class BadPlan(HistogramModel):
            def plan_second(self, first):
                return [(1, np.array([0, 0, 2]))]
        invalid = BadPlan(iid.freq)
        with self.assertRaises(ValueError):
            entropy.encode_symbols(x, invalid)
        class MissingPlan(HistogramModel):
            def plan_second(self, first):
                return [(1, np.array([0, 1]))]
        with self.assertRaises(ValueError):
            entropy.encode_symbols(x, MissingPlan(iid.freq))

    def test_real_file_restart_no_source_and_overhead(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/'source-data'
            source.mkdir()
            quantized = fixture(source)
            original, _, _ = import_tables(quantized)
            records = {}
            for model in ('fixed8', 'iid', 'channel_context'):
                first = root/f'{model}.bin'
                record = entropy.encode(quantized, first, model)
                second = root/f'{model}-repeat.bin'
                entropy.encode(quantized, second, model)
                self.assertEqual(first.read_bytes(), second.read_bytes())
                self.assertEqual(first.stat().st_size, record['total_compressed_bytes'])
                self.assertEqual(record['coded_payload_bytes']+record['model_overhead_bytes']+record['metadata_framing_bytes'], first.stat().st_size)
                records[model] = record
            # Remove every synthetic source file before any isolated decoder runs.
            self.assertTrue(source.resolve().is_relative_to(root.resolve()))
            shutil.rmtree(source)
            for model, record in records.items():
                first = root/f'{model}.bin'
                # An isolated child process has access only to stream + public code.
                isolated = root/f'{model}-isolated'
                isolated.mkdir()
                shutil.copy2(first, isolated/'only-input.bin')
                code = ('import sys; from pathlib import Path; '
                    'from research.experiment_bench.entropy import decode; '
                    'base=Path(sys.argv[1]); '
                    'original_read=Path.read_bytes; '
                    'Path.read_bytes=lambda p: original_read(p) if p.resolve()==(base/"only-input.bin").resolve() else (_ for _ in ()).throw(RuntimeError("unexpected input read")); '
                    'decode(base/"only-input.bin",base/"restored")')
                subprocess.run([sys.executable, '-c', code, str(isolated)], check=True, env=os.environ.copy())
                restored, _, _ = import_tables(isolated/'restored')
                self.assertTrue(all(torch.equal(original[k], restored[k]) for k in KEYS))
                self.assertAlmostEqual(record['compression_ratio_float32'], 776*4/first.stat().st_size)
                self.assertAlmostEqual(record['bits_per_symbol'], first.stat().st_size*8/776)

    def test_corruption_truncation_version_and_sizes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            quantized = fixture(root)
            stream = root/'valid.bin'
            entropy.encode(quantized, stream, 'channel_context')
            valid = stream.read_bytes()
            bad_values = [valid[:-1], valid[:12], valid+b'X']
            damaged = bytearray(valid); damaged[-40] ^= 1; bad_values.append(bytes(damaged))
            wrong_version = bytearray(valid); struct.pack_into('<H', wrong_version, 8, 999); bad_values.append(bytes(wrong_version))
            # Recomputed outer checksum must not conceal invalid component counts.
            header, models, payload = entropy.parse(stream)
            header['components'][KEYS[0]]['symbols'] += 2
            h = json.dumps(header, separators=(',', ':'), sort_keys=True).encode()
            body = entropy.PREFIX.pack(entropy.MAGIC, entropy.VERSION, len(h), len(models), len(payload))+h+models+payload
            bad_values.append(body+hashlib.sha256(body).digest())
            # A valid outer digest must not conceal an invalid finite CDF/model.
            header, models, payload = entropy.parse(stream)
            damaged_models = bytearray(models)
            struct.pack_into('<I', damaged_models, 0, 0)
            h = json.dumps(header, separators=(',', ':'), sort_keys=True).encode()
            body = entropy.PREFIX.pack(entropy.MAGIC, entropy.VERSION, len(h), len(models), len(payload))+h+damaged_models+payload
            bad_values.append(body+hashlib.sha256(body).digest())
            for i, bad in enumerate(bad_values):
                path = root/f'bad-{i}.bin'; path.write_bytes(bad)
                with self.assertRaises((ValueError, KeyError)):
                    entropy.decode(path, root/f'bad-output-{i}')


if __name__ == '__main__':
    unittest.main()
