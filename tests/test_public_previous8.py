"""Exercise the unchanged G4DPREV1 codec without private arrays/checkpoints.

Synthetic masses are a test fixture, not a fitted research model. This test
does not measure or claim compression efficiency. No original run is written.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'research/frozen_previous8_actual_20261108_01'
sys.path.insert(0,str(F))
import codec as c

def build_fixture(mode):
    rows=[4097 if 6<=l<=10 else 3 for l in range(16)]
    offsets=np.r_[0,np.cumsum(rows)].tolist()
    rng=np.random.default_rng(8124)
    q=rng.integers(0,256,(offsets[-1],2),dtype=np.uint8)
    quant={'bits':8,'min':-1.,'max':1.,'step':2./255.,'rounding':'nearest-even','reconstruction_dtype':'float32'}
    md={'schema':'grid4d-standard-spatial-v1','codec':'XZ6','layout':'slot-major',
        'arithmetic':c.baselines.ARITHMETIC,
        'source_metadata':{'dtype':'uint8','shape':list(q.shape),'offsets':offsets,
            'level_order':list(range(16)),'tensor':'xyz_encoding.embeddings',
            'quantization_scope':'entire xyz table shared across all levels/channels',
            'quantizer':quant,'symbols_sha256':c.digest(q.tobytes())},
        'canonical_restored_sha256':c.digest(c.canonical_dequantize(q,quant).tobytes())}
    desc=[];parts=[];class_hashes=[]
    for l,n in enumerate(rows):
        a=q[offsets[l]:offsets[l+1]];kind=mode if 6<=l<=10 else 'X';raw=b'';hashes=[]
        if kind=='X':payload=[c.baselines.compress(a.tobytes(),'XZ6')]
        else:
            rc=[1,1] if kind=='I' else [9,9]
            masses=np.full((sum(rc),256),255,dtype=np.uint32)
            for j in range(len(masses)):masses[j,(j*29)%256]=511
            spec={'family':'IID' if kind=='I' else 'PREVIOUS8','level':l,'slots':n,
                  'channels':2,'alphabet':256,'mass_total':65536,'mass_precision':16}
            th={}
            if kind=='P':
                spec.update(block_slots=4096,first_slot='separate IID row fitted on all fit symbols in channel; reset each4096 slots')
                th={'edges':np.array([[0,0,64,128,192,255,255],[1,1,50,100,200,254,255]],np.float64)}
            raw=c.model_side.serialize(masses,th,spec,rc,'packed_u16')
            prepared,_=c.prepare_model(raw,kind,l,n);payload=[]
            for ch in range(2):
                data,ids,_,_=c.encode_channel(a[:,ch],ch,kind,prepared)
                expected=np.full(n,ch if kind=='I' else 9*ch,dtype=np.uint8)
                if kind=='P':
                    # Independent scalar oracle, comparisons rather than searchsorted.
                    for i in range(1,n):
                        if i%4096:expected[i]=9*ch+1+sum(int(a[i-1,ch])>=float(e) for e in th['edges'][ch])
                np.testing.assert_array_equal(ids,expected)
                payload.append(data);hashes.append(c.digest(expected.tobytes()))
        desc.append({'level':l,'codec':kind,'rows':n,'model_bytes':len(raw),
                     'payload_bytes':list(map(len,payload)),'symbols_sha256':c.digest(a.tobytes())})
        parts.extend([raw,*payload]);class_hashes.append(hashes)
    data=c.assemble({'contract':copy.deepcopy(c.CONTRACT),'baseline_metadata':md,'mode':mode,'levels':desc},parts)
    return data,q,class_hashes

class PublicPrevious8(unittest.TestCase):
    def test_fresh_decoder_exact_classes_and_repeat_bytes(self):
        with tempfile.TemporaryDirectory(prefix='grid4d-public-') as temp:
            for mode in ('X','I','P'):
                with self.subTest(mode=mode):
                    data,q,hashes=build_fixture(mode)
                    self.assertEqual(data,build_fixture(mode)[0])
                    p=Path(temp)/(mode+'.bin');p.write_bytes(data);out=Path(temp)/(mode+'_decoded')
                    env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
                    result=subprocess.run([sys.executable,'-B',str(F/'codec.py'),str(p),str(out)],
                                          cwd=ROOT,env=env,capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    np.testing.assert_array_equal(np.load(out/'decoded.npy',allow_pickle=False),q)
                    report=json.loads((out/'DECODE.json').read_text())
                    self.assertEqual([r['context_ids_sha256'] for r in report['levels']],hashes)
                    self.assertEqual(report['status'],'PASS')
                    self.assertTrue(report['data_reads'])
                    self.assertEqual(set(report['data_reads']),{str(p.resolve())})

    def test_damaged_container_rejected(self):
        data,_,_=build_fixture('P')
        damaged=bytearray(data);damaged[len(damaged)//2]^=1
        for bad in (bytes(damaged),data[:-1],data+b'extra'):
            with self.assertRaises(ValueError):c.decode(bad)

if __name__=='__main__':unittest.main()
