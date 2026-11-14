"""One tiny geometry fixture, public CLI paths and preserved H3 regression."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch
import numpy as np
from research.experiment_bench.models import frequencies
from research.experiment_bench.hybrid_pair import codec as h3
from . import codec, geometry, transport, optimizer, bundle

ROOT = Path(__file__).resolve().parents[3]
H3 = ROOT / 'research/hybrid_context_selection_20261027_01'
ARTIFACT_DIR = None  # Set by verification.run, never writes into an old run.


def fixture():
    rng = np.random.default_rng(9414)
    qmeta = {'row_start': 0, 'row_end': 6098108, 'bits': 8, 'min': -1., 'max': 1.,
             'step': 2. / 255., 'rounding': 'nearest-even', 'reconstruction_dtype': 'float32'}
    g = {'version': 1, 'grid': 'xyz', 'arithmetic': codec.legacy.ARITHMETIC,
         'geometry_convention': codec.legacy.CONVENTION, 'fallback': copy.deepcopy(codec.legacy.FALLBACK),
         'hash': copy.deepcopy(codec.legacy.HASH), 'interpolation': 'smoothstep-corners0to7',
         'source_checkpoint_sha256': '0' * 64, 'source_symbols_sha256': '0' * 64,
         'coarse': {'level': 0, 'rows': 11, 'offset_start': 0, 'offset_end': 11,
                    'lookup_resolution': [3] * 3, 'scale': [float(np.float32(1.4))] * 3, 'quantization': qmeta},
         'fine': {'level': 1, 'rows': 61, 'offset_start': 11, 'offset_end': 72,
                  'lookup_resolution': [4] * 3, 'scale': [float(np.float32(2.7))] * 3}}
    coarse = rng.integers(0, 256, (11, 2), dtype=np.uint8)
    fine = rng.integers(0, 8, (61, 2), dtype=np.uint8)
    fine[-1, 1] = 255
    edges = np.tile(np.linspace(-.6, .6, 7), (2, 1)).astype(np.float64)
    classes = geometry.contexts(g, coarse, edges, geometry.SYNTHETIC)
    counts = optimizer.histogram(fine, classes)
    original = np.stack([frequencies(row) for row in counts.reshape(20, 256)]).reshape(2, 10, 256)
    # Known bit-identical source fallback rows. They deliberately need not equal
    # a refit of each channel's separate histogram; C0/C1 must retain originals.
    for cls in (0, 1):
        original[:, cls] = frequencies(counts[:, cls].sum(0))
    fc = np.stack([frequencies(np.bincount(coarse[:, ch], minlength=256)) for ch in range(2)])[:, None, :]
    spec = {'name': 'IID', 'C': 1, 'edges': {'primary': [[], []], 'std': [[], []]}}
    cm, storage, _ = codec.legacy._model_bytes(fc, spec, 'auto')
    cp = codec.engine.encode_indexed(coarse, np.zeros_like(coarse), fc)
    return dict(geometry=g, profile=geometry.SYNTHETIC, coarse=coarse, fine=fine,
                classes=classes, counts=counts, original=original, thresholds=edges,
                coarse_model=cm, coarse_payload=cp, coarse_storage=storage,
                metadata_bytes=codec.outer_side_bytes(g, geometry.SYNTHETIC, storage),
                sealed_input={'fixture': 'tiny-61-slots-v1'})


def encode_fixture(a, model):
    return codec.encode(a['geometry'], a['coarse'], a['fine'], a['classes'], model,
                        a['coarse_model'], a['coarse_payload'], a['coarse_storage'],
                        original_masses=a['original'], original_thresholds=a['thresholds'], profile=a['profile'])


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        codec.engine.check_runtime()
        cls.a = fixture()
        cls.plans = {mode: optimizer.optimize(cls.a['counts'], cls.a['original'], cls.a['thresholds'], mode, cls.a['metadata_bytes']) for mode in transport.MODES}
        cls.streams = {mode: encode_fixture(cls.a, plan.model)[0] for mode, plan in cls.plans.items()}

    def test_exact_all_modes_and_c1_payload_identity(self):
        a = self.a
        for mode, data in self.streams.items():
            c, f, ctx, ids, info = codec.decode(data, strict=True)
            for x, y in ((c, a['coarse']), (f, a['fine']), (ctx, a['classes']), (ids, transport.route(ctx, self.plans[mode].model))):
                np.testing.assert_array_equal(x, y)
            self.assertEqual(data, encode_fixture(a, self.plans[mode].model)[0])
            s = info['sizes']
            self.assertEqual(s['outer_metadata_bytes'], a['metadata_bytes'])
            self.assertEqual(s['model_bytes'], self.plans[mode].final['model_bytes'])
            self.assertEqual(s['total_bytes'], s['fine_payload_bytes'] + s['model_bytes'] + a['metadata_bytes'] + len(a['coarse_model']) + len(a['coarse_payload']))
        self.assertEqual(codec.unpack(self.streams['C0'])[1]['fine_payload'], codec.unpack(self.streams['C1'])[1]['fine_payload'])
        self.assertTrue(np.any(transport.route(a['classes'], self.plans['C1'].model) != a['classes']))

    def test_fresh_bin_only_decoder_each_mode(self):
        if ARTIFACT_DIR is None:
            self.fail('Use CLI test --output NEW_DIR to retain independent decode evidence')
        for mode, data in self.streams.items():
            path = ARTIFACT_DIR / (mode + '.bin')
            with path.open('xb') as file:
                file.write(data)
            out = ARTIFACT_DIR / (mode + '_decoded')
            command = [sys.executable, '-B', '-m', 'research.experiment_bench.pmf_clustering',
                       'decode', '--input', str(path), '--output', str(out)]
            p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            with (ARTIFACT_DIR / (mode + '_decoder.log')).open('x', encoding='utf-8') as file:
                file.write(p.stdout + p.stderr)
            self.assertEqual(p.returncode, 0, p.stderr)
            audit = json.loads((out / 'audit.json').read_text())
            self.assertTrue(audit['only_bin_data_read'])
            self.assertFalse(audit['optimizer_imported'])
            self.assertEqual(audit['forbidden_actual_reads'], [])
            self.assertEqual(len(audit['forbidden_probes_denied']), 5)
            for key, expected in (('coarse', self.a['coarse']), ('fine', self.a['fine']),
                                  ('contexts', self.a['classes']), ('clusters', transport.route(self.a['classes'], self.plans[mode].model))):
                np.testing.assert_array_equal(np.load(out / (key + '.npy'), allow_pickle=False), expected)

    def test_encoder_invariants_no_hidden_refit_or_threshold_change(self):
        a = self.a
        for mode in transport.MODES:
            plan = self.plans[mode]
            original = a['original'].copy()
            cls = 0 if mode == 'C2' else int(np.flatnonzero(plan.model.mapping[0] != 255)[-1])
            original[0, cls, 0] += 1
            donor = int(np.argmax(original[0, cls]))
            original[0, cls, donor] -= 1
            self.assertNotEqual(donor, 0)
            with self.assertRaises(ValueError):
                codec.validate_original(plan.model, original, a['thresholds'])
            altered = a['thresholds'].copy()
            altered[:, 0] -= .01
            with self.assertRaises(ValueError):
                codec.validate_original(plan.model, a['original'], altered)
        wrong = dict(a)
        wrong['classes'] = a['classes'].copy()
        wrong['classes'][0, 0] = (int(wrong['classes'][0, 0]) + 1) % 10
        with self.assertRaises(ValueError):
            encode_fixture(wrong, self.plans['C1'].model)
        wrong = dict(a)
        wrong['coarse_payload'] += b'\0' * 4
        with self.assertRaises(ValueError):
            encode_fixture(wrong, self.plans['C1'].model)

    def test_corruption_rechecked_outer_hash_and_strict_payloads(self):
        data = self.streams['C2']
        h, s = codec.unpack(data)
        changed = bytearray(data)
        changed[-1] ^= 1
        bads = [bytes(changed), data[:-1], data + b'junk']
        for key in ('coarse_payload', 'fine_payload'):
            for raw in (s[key] + b'\0' * 4, s[key][:-4], bytes([s[key][0] ^ 128]) + s[key][1:]):
                altered = dict(s)
                altered[key] = raw
                bads.append(codec.pack(h, altered))
        for key in codec.DIGEST_KEYS:
            altered = copy.deepcopy(h)
            altered['integrity'][key] = 'f' * 64
            bads.append(codec.pack(altered, s))
        for key, value in (('version', 2), ('version', True), ('numpy', '2.0'), ('geometry_profile', 'unknown')):
            altered = copy.deepcopy(h)
            altered[key] = value
            bads.append(codec.pack(altered, s))
        for index, value in ((4, 2), (5, 9), (6, 9), (7, 3), (len(s['fine_model']) - 20, 254)):
            raw = bytearray(s['fine_model'])
            raw[index] = value
            altered = dict(s)
            altered['fine_model'] = raw
            bads.append(codec.pack(h, altered))
        for index, bad in enumerate(bads):
            with self.subTest(index=index), self.assertRaises(ValueError):
                codec.decode(bad, strict=True)
        # A valid canonical model with missing fallback, and updated model
        # digests, still fails decoder source-class support, not just SHA.
        n = self.a['counts'].copy()
        n[:, 0] = 0
        partial = optimizer.optimize(n, self.a['original'], self.a['thresholds'], 'C1').model
        altered = dict(s)
        altered['fine_model'] = transport.choose(partial)[0]
        hh = copy.deepcopy(h)
        hh['integrity']['fine_masses'] = codec.legacy.array_sha(partial.pool)
        hh['integrity']['mapping'] = codec.legacy.array_sha(partial.mapping)
        with self.assertRaisesRegex(ValueError, 'mapping'):
            codec.decode(codec.pack(hh, altered))

    def test_geometry_profiles_and_original_h3_regression(self):
        with self.assertRaises(ValueError):
            geometry.validate(self.a['geometry'], geometry.PRODUCTION)
        for case, mask in (('bouncingballs_L6', '0100'), ('hellwarrior_L6', '1100')):
            path = H3 / case / 'actual' / (mask + '.bin')
            c, f, ids, info = h3.decode(path.read_bytes(), strict=True)
            for key, array in (('coarse', c), ('fine', f), ('routes', ids)):
                expected = np.load(path.parent / (mask + '_decoded') / (key + '.npy'), allow_pickle=False)
                np.testing.assert_array_equal(array, expected)
            self.assertEqual(info['status'], 'PASS')
        for case in ('bouncingballs_L5', 'hellwarrior_L6'):
            g = json.loads((H3 / case / 'decoder_bundle/geometry.json').read_text())
            geometry.validate(g, geometry.PRODUCTION)
            self.assertGreater(codec.outer_side_bytes(g, geometry.PRODUCTION, 'sparse_default_u16'), 0)

    def test_adapter_seal_metadata_only_and_hash_rejection(self):
        case = H3 / 'bouncingballs_L6'
        evidence = bundle.verify_seal(case)  # File hashes only; no H4 scene optimize/encode.
        self.assertEqual(set(evidence['files']), set(bundle.FILES))
        with patch.object(bundle, 'sha_file', return_value='0' * 64), self.assertRaises(ValueError):
            bundle.verify_seal(case)

    def test_cli_roundtrip_and_plan_binding_without_scene_processing(self):
        from . import __main__ as cli
        target = ARTIFACT_DIR / 'mock_cli'
        a = self.a
        with patch.object(bundle, 'load', return_value=a):
            with patch.object(sys, 'argv', ['h4', 'optimize', '--bundle', 'mock', '--mode', 'C2', '--output', str(target)]), contextlib.redirect_stdout(io.StringIO()):
                cli.main()
                with self.assertRaises(FileExistsError):
                    cli.main()
            capture = io.StringIO()
            with patch.object(sys, 'argv', ['h4', 'inspect', '--model', str(target / 'model.h4pm'), '--counts', str(target / 'histograms.npz')]), contextlib.redirect_stdout(capture):
                cli.main()
            inspected = json.loads(capture.getvalue())
            plan = json.loads((target / 'optimization.json').read_text())
            self.assertEqual(plan['final'], inspected['objective'])
            command = ['h4', 'encode', '--bundle', 'mock', '--model', str(target / 'model.h4pm'), '--output', str(target / 'pair.bin')]
            with patch.object(sys, 'argv', command), contextlib.redirect_stdout(io.StringIO()):
                cli.main()
            c, f, _, _, _ = codec.decode((target / 'pair.bin').read_bytes())
            np.testing.assert_array_equal(c, a['coarse'])
            np.testing.assert_array_equal(f, a['fine'])
        wrong = dict(a)
        wrong['fine'] = a['fine'].copy()
        wrong['fine'][0, 0] ^= 1
        wrong['counts'] = optimizer.histogram(wrong['fine'], wrong['classes'])
        command[-1] = str(target / 'must_not_exist.bin')
        with patch.object(bundle, 'load', return_value=wrong), patch.object(sys, 'argv', command), self.assertRaises(ValueError):
            cli.main()
        self.assertFalse((target / 'must_not_exist.bin').exists())
