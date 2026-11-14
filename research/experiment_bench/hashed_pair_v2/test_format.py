"""V2 semantic and complete-allocation synthetic tests; no scene targets read."""
from __future__ import annotations
import copy
import hashlib
import unittest
from unittest.mock import patch
import numpy as np

from . import format as fmt
from research.experiment_bench.hashed_pair import test_format as legacy_tests
from research.experiment_bench.hashed_pair import format as legacy
from research.experiment_bench.hashed_interlevel import dry_model


def quantizer(lo=-2., hi=3.):
    return {'row_start': 0, 'row_end': 6098108, 'bits': 8, 'min': lo, 'max': hi,
            'step': (hi-lo)/255, 'rounding': 'nearest-even', 'reconstruction_dtype': 'float32'}


def header(q=None):
    h = legacy_tests.synthetic_header()
    h['version'] = 2
    h['geometry']['coarse']['quantization'] = quantizer() if q is None else q
    return h


class ContainerTests(legacy_tests.ContainerStructureTests):
    """Apply the original structural attacks to V2 rather than alter V1 tests."""
    def setUp(self):
        self.fmt = fmt
        self.header = header()
        self.sections = dict.fromkeys(fmt.NAMES, b'\0'*4)

    def test_bound_precedes_digest_for_actual_v2_prefix(self):
        prefix = fmt.PREFIX.pack(fmt.MAGIC, 2, 2**50, 0, 0, 0, 0)+bytes(32)
        with patch.object(fmt.hashlib, 'sha256', side_effect=AssertionError('digest before bound')):
            with self.assertRaises(ValueError): fmt.unpack(prefix)

    def test_v1_v2_are_explicitly_distinct(self):
        v1 = legacy.pack(legacy_tests.synthetic_header(), self.sections)
        v2 = fmt.pack(self.header, self.sections)
        with self.assertRaises(ValueError): fmt.unpack(v1)
        with self.assertRaises(ValueError): legacy.unpack(v2)

    def test_quantizer_scope_types_and_malformed_metadata(self):
        changes = {'bits': [True, 8., 7, '8'], 'row_start': [False, 1, 0.],
                   'row_end': [6098107, 6098108., None], 'min': [True, '-2', None],
                   'max': [False, None], 'step': [True, None],
                   'rounding': ['floor', None], 'reconstruction_dtype': ['float64', None]}
        for field, values in changes.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    q = quantizer(); q[field] = value
                    with self.assertRaises(ValueError): fmt.validate_quantizer(q)
        for q in (None, [], {}, {**quantizer(), 'scope': 'level'},
                  {k:v for k,v in quantizer().items() if k!='min'}):
            with self.assertRaises(ValueError): fmt.validate_quantizer(q)
        for field in ('min', 'max', 'step'):
            for value in (float('nan'), float('inf'), -float('inf'), 10**1000):
                q = quantizer(); q[field] = value
                with self.assertRaises(ValueError): fmt.validate_quantizer(q)

    def test_quantizer_order_step_and_float32_bounds(self):
        cases = [quantizer(3., -2.), quantizer(1e100, 1e100), quantizer(-1e100, 1e100)]
        for lo, hi in ((0., 1.), (-2., 3.), (7., 7.)):
            q = quantizer(lo, hi); q['step'] = np.nextafter(q['step'], np.inf).item(); cases.append(q)
        for q in cases:
            with self.assertRaises(ValueError): fmt.validate_quantizer(q)

    def test_finite_quantizers_match_existing_dequantizer(self):
        # Alternate ranges, asymmetric ranges, negative and positive constants,
        # subnormal float32 values and both extremes of the finite float32 domain.
        tiny = float(np.nextafter(np.float32(0), np.float32(1)))
        big = float(np.finfo(np.float32).max)
        for lo, hi in ((-2., 3.), (1., 255.), (-11., -2.), (0., tiny), (-big, big),
                       (-4., -4.), (0., 0.), (3.25, 3.25)):
            q = quantizer(lo, hi); fmt.validate_quantizer(q)
            symbols = np.zeros((256, 2), np.uint8) if lo==hi else np.repeat(
                np.arange(256, dtype=np.uint8)[:,None], 2, axis=1)
            actual = fmt.dequantize_symbols(symbols, q)
            expected = np.clip(lo+symbols.astype(np.float64)*q['step'],lo,hi).astype(np.float32)
            np.testing.assert_array_equal(actual, expected)
            self.assertTrue(np.isfinite(actual).all())

    def test_exact_specification_types(self):
        for field, value in (('C', 10.), ('C', '10'), ('name', None)):
            spec = {'name':'Mean8','C':10,'rules':copy.deepcopy(fmt.RULES)};spec[field]=value
            with self.assertRaises(ValueError): fmt.validate_spec(spec, {'primary':np.zeros((2,7))}, 'Mean8')
        bad = header();bad['geometry']['fallback']['features']=[False,False]
        with self.assertRaises(ValueError): fmt.unpack(fmt.pack(bad,self.sections))

    def test_noncanonical_and_duplicate_json_rejected(self):
        original = fmt.pack(self.header,self.sections)
        _, sections = fmt.unpack(original)
        for metadata in (sections['metadata']+b' ', b'{"version":2,"version":2}', b'[]'):
            parts=[metadata]+[sections[k] for k in fmt.NAMES[1:]]
            body=fmt.PREFIX.pack(fmt.MAGIC,2,*map(len,parts))+b''.join(parts)
            with self.assertRaises(ValueError):fmt.unpack(body+hashlib.sha256(body).digest())


class CompleteAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=header()['geometry']
        # Synthetic low-entropy symbols cover both endpoint symbols and all
        # allocated rows, including geometry-empty and colliding hash slots.
        rng=np.random.default_rng(7741)
        cls.q4=rng.integers(0,16,(205379,2),dtype=np.uint8)
        cls.q5=rng.integers(0,16,(524288,2),dtype=np.uint8)
        cls.q4[[0,-1]]=[[0,255],[255,0]];cls.q5[[0,-1]]=[[0,255],[255,0]]
        cls.stream,cls.detail=fmt.encode_pair(cls.meta,cls.q4,cls.q5,'Mean8')

    def test_complete_roundtrip_every_arm_and_repeat(self):
        for name in fmt.ARMS:
            data, detail=fmt.encode_pair(self.meta,self.q4,self.q5,name)
            repeat,_=fmt.encode_pair(self.meta,self.q4,self.q5,name)
            self.assertEqual(data,repeat)
            q4,q5,classes,restored=fmt.decode_bytes(data)
            np.testing.assert_array_equal(q4,self.q4);np.testing.assert_array_equal(q5,self.q5)
            self.assertEqual(classes.shape,(524288,2))
            self.assertEqual(fmt.array_sha(classes),detail['classes_sha256'])
            self.assertTrue(restored['canonical_payload_verified'])
            sizes=fmt.section_sizes(data)
            self.assertEqual(sum(sizes[k] for k in ('coarse_bytes','fine_payload_bytes','model_bytes','metadata_framing_bytes')),len(data))

    def test_constant_table_all_arms_exact(self):
        meta=copy.deepcopy(self.meta);meta['coarse']['quantization']=quantizer(3.25,3.25)
        q4=np.zeros_like(self.q4);q5=np.zeros_like(self.q5)
        for name in fmt.ARMS:
            data,_=fmt.encode_pair(meta,q4,q5,name)
            a,b,_,_=fmt.decode_bytes(data)
            np.testing.assert_array_equal(a,q4);np.testing.assert_array_equal(b,q5)

    def test_constant_nonzero_coarse_or_fine_rejected(self):
        meta=copy.deepcopy(self.meta);meta['coarse']['quantization']=quantizer(0.,0.)
        q4=np.zeros_like(self.q4);q5=np.zeros_like(self.q5)
        for role in ('coarse','fine'):
            a=q4.copy();b=q5.copy();(a if role=='coarse' else b)[-1,-1]=1
            with self.assertRaises(ValueError):fmt.encode_pair(meta,a,b,'IID')

    def test_declaring_nonzero_symbols_constant_is_rejected_on_decode(self):
        h,s=fmt.unpack(self.stream);h['geometry']['coarse']['quantization']=quantizer(0.,0.)
        with self.assertRaisesRegex(ValueError,'Constant'):
            fmt.decode_bytes(fmt.pack(h,s))

    def test_context_does_not_receive_fine_symbols(self):
        expected=fmt._contexts(self.meta,self.q4,'Mean8')
        with patch.object(fmt,'_contexts',wraps=fmt._contexts) as call:
            changed=np.bitwise_xor(self.q5,np.uint8(255))
            _,detail=fmt.encode_pair(self.meta,self.q4,changed,'Mean8')
            self.assertEqual(call.call_count,1)
            self.assertIs(call.call_args.args[1],self.q4)
            self.assertEqual(len(call.call_args.args),3)
        self.assertEqual(detail['classes_sha256'],self.detail['classes_sha256'])
        self.assertEqual(len(expected['slot_index']),524288)
        np.testing.assert_array_equal(expected['slot_index'],np.arange(524288))

    def test_payload_semantic_corruption_rejected_with_repaired_outer_sha(self):
        header0,sections0=fmt.unpack(self.stream)
        for role in ('coarse_payload','fine_payload'):
            payload=sections0[role];flipped=bytearray(payload);flipped[len(flipped)//2]^=128
            for bad in (b'',payload+b'\0',payload[:-4],payload+bytes(4),bytes(flipped)):
                sections=dict(sections0);sections[role]=bad
                with self.subTest(role=role,length=len(bad)):
                    with self.assertRaises(ValueError):fmt.decode_bytes(fmt.pack(header0,sections))
        for key in ('q4','q5','classes','coarse_masses','fine_masses'):
            h=copy.deepcopy(header0);h['integrity'][key]='0'*64
            with self.assertRaises(ValueError):fmt.decode_bytes(fmt.pack(h,sections0))

    def test_model_corruption_and_thresholds_rejected(self):
        h,s=fmt.unpack(self.stream)
        for role in ('coarse_model','fine_model'):
            for bad in (b'',s[role][:-1],s[role]+b'\0'):
                changed=dict(s);changed[role]=bad
                with self.assertRaises(ValueError):fmt.decode_bytes(fmt.pack(h,changed))
        masses,edges,spec,meta=dry_model.deserialize(s['fine_model'])
        spec['C']=10.0
        changed=dict(s);changed['fine_model']=dry_model.serialize(masses,edges,spec,meta,h['model']['storage'])
        with self.assertRaises(ValueError):fmt.decode_bytes(fmt.pack(h,changed))

    def test_input_dtype_and_coverage_validation(self):
        for a,b in ((self.q4[:-1],self.q5),(self.q4,self.q5[:-1]),
                    (self.q4.astype(np.uint16),self.q5),(self.q4,self.q5[:,0])):
            with self.assertRaises(ValueError):fmt.encode_pair(self.meta,a,b,'IID')


if __name__=='__main__':unittest.main()
