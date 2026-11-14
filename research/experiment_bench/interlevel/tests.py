import copy
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
from research.experiment_bench import entropy
from research.experiment_bench.models import HistogramModel,frequencies
from research.hashgrid_analysis.common import ROOT
from .context import context,classes,boundaries
from .model_io import serialize,deserialize,fit,PREFIX
from .format import make,decode_data,unpack,pack,sha,SHARED

def fixture():
    meta={'checkpoint_sha256':'0'*64,
        'coarse':{'level':3,'rows':27,'offset_start':20,'offset_end':47,'lookup_resolution':[3]*3,'scale':[1.9]*3,
            'quantization':{'bits':8,'min':0.,'max':255.,'step':1.,'rounding':'nearest-even','reconstruction_dtype':'float32','row_start':0,'row_end':172}},
        'fine':{'level':4,'rows':125,'offset_start':47,'offset_end':172,'lookup_resolution':[5]*3,'scale':[3.5]*3}}
    rng=np.random.default_rng(17);return meta,rng.integers(0,256,(27,2),dtype=np.uint8),rng.integers(0,256,(125,2),dtype=np.uint8)

class InterlevelTests(unittest.TestCase):
    def test_all_mass_storage_exact_and_u64_cdf(self):
        rng=np.random.default_rng(11);f=np.stack([frequencies(rng.integers(0,1000,256)) for _ in range(18)]).reshape(2,9,256)
        f[0,5]=256;mask=np.zeros((2,9),bool);mask[0,5]=True
        for storage in ('dense_u32','packed_u16','sparse_default_u16'):
            restored,omit=deserialize(serialize(f,storage,mask),storage,9)
            np.testing.assert_array_equal(restored,f)
            self.assertTrue(np.all(np.cumsum(restored,dtype=np.uint64,axis=2)[:,:,-1]==65536))
            self.assertEqual(bool(omit[0,5]),storage=='sparse_default_u16')

    def test_deterministic_default_sparse_and_empty(self):
        f=np.full((2,1,256),256,np.uint32);data=serialize(f,'sparse_default_u16')
        self.assertEqual(data,serialize(f,'sparse_default_u16'))
        self.assertEqual(len(data),PREFIX.size+2*5)
        np.testing.assert_array_equal(deserialize(data,'sparse_default_u16',1)[0],f)

    def test_invalid_model_transport(self):
        f=np.full((2,1,256),256,np.uint32)
        for storage in ('dense_u32','packed_u16','sparse_default_u16'):
            data=serialize(f,storage)
            for bad in (data[:-1],data+b'X',b'BAD!'+data[4:]):
                with self.assertRaises(ValueError):deserialize(bad,storage,1)
        data=bytearray(serialize(f,'packed_u16'));struct.pack_into('<H',data,PREFIX.size,0)
        with self.assertRaises(ValueError):deserialize(bytes(data),'packed_u16',1)
        data=bytearray(serialize(f,'sparse_default_u16'));struct.pack_into('<H',data,PREFIX.size+3,257)
        with self.assertRaises(ValueError):deserialize(bytes(data),'sparse_default_u16',1)
        f[0,0,0]=65536
        with self.assertRaises(ValueError):serialize(f,'packed_u16')

    def test_smoothstep_independent_linear_lattice(self):
        meta,c3,_=fixture();i=np.arange(27,dtype=np.uint8);c3=np.column_stack((i,i))
        out,inside=context(meta,c3)
        for slot in (0,1,5,31,62,93):
            v=np.array([slot%5,(slot//5)%5,slot//25]);p=v/3.5*1.9;b=np.floor(p);d=p-b;s=d*d*(3-2*d)
            expected=(b+s)@np.array([1,3,9])
            self.assertAlmostEqual(float(out[slot,0]),expected,places=4)
        self.assertEqual(int(inside.sum()),4**3);self.assertTrue(np.all(out[~inside]==0))

    def test_ties_OOB_and_no_future_target_input(self):
        meta,c3,q4=fixture();c3[:]=166;values,inside=context(meta,c3);e=np.full((2,7),166.)
        c,valid,_=classes(meta,c3,'spatial8',e)
        self.assertTrue(np.all(c[~valid]==8));self.assertTrue(np.all(c[values[:,0]==166,0]==7))
        again=classes(meta,c3.copy(),'spatial8',e)[0];q4[:]=0
        np.testing.assert_array_equal(c,again)
        self.assertTrue(np.all(np.diff(boundaries(values,inside),axis=1)>=0))

    def test_fixed_symbol_order_and_chunk_independence(self):
        _,_,q=fixture();m=HistogramModel.fit(q);f=m.freq[:,None,:];c=np.zeros(q.shape,np.uint8)
        a=entropy.encode_indexed(q,c,f,7);b=entropy.encode_indexed(q,c,f,31)
        self.assertEqual(a,b);self.assertEqual(a,entropy.encode_symbols(q,m))
        np.testing.assert_array_equal(q,entropy.decode_indexed(a,c,f,19))
        with self.assertRaises(ValueError):entropy.encode_indexed(q,np.full(q.shape,2,np.uint8),f)

    def test_nine_toy_files_exact_shared_and_sizes(self):
        meta,c3,q4=fixture();shared=None
        for model in ('iid','boundary','spatial8'):
            class_ref=None;payload_ref=None
            for storage in ('dense_u32','packed_u16','sparse_default_u16'):
                data,info=make(meta,c3,q4,model,storage);h,s=unpack(data);a,_=decode_data(data)
                np.testing.assert_array_equal(c3,a['coarse']);np.testing.assert_array_equal(q4,a['fine'])
                self.assertEqual(sum(info['sections'].values())+info['prefix_bytes']+info['header_json_bytes']+32,len(data))
                common={k:s[k] for k in SHARED}
                if shared is None:shared=common
                else:self.assertEqual(shared,common)
                if class_ref is None:class_ref=a['classes'];payload_ref=s['l4.payload']
                else:np.testing.assert_array_equal(class_ref,a['classes']);self.assertEqual(payload_ref,s['l4.payload'])
                self.assertEqual(data,make(meta,c3,q4,model,storage)[0])

    def test_corruption_truncation_header(self):
        meta,c3,q4=fixture();data,_=make(meta,c3,q4,'spatial8','sparse_default_u16')
        wrong=bytearray(data);wrong[-40]^=1
        values=[data[:-1],data[:10],data+b'x',bytes(wrong),b'XXXXXXXX'+data[8:]]
        h,s=unpack(data);h['order']='group-by-context';values.append(pack(h,s))
        h,s=unpack(data);h['sections'][0]['bytes']+=1;values.append(pack(h,s))
        for bad in values:
            with self.assertRaises(ValueError):decode_data(bad)

    def test_recomputed_checksum_semantic_validation(self):
        meta,c3,q4=fixture();data,_=make(meta,c3,q4,'spatial8','dense_u32')
        h,s=unpack(data);i=json.loads(s['l4.info']);i['class_sha256']='0'*64;s['l4.info']=json.dumps(i,sort_keys=True,separators=(',',':')).encode()
        with self.assertRaisesRegex(ValueError,'Context classes'):decode_data(pack(h,s))
        h,s=unpack(data);bad=bytearray(s['l4.model']);struct.pack_into('<I',bad,PREFIX.size,0);s['l4.model']=bytes(bad)
        with self.assertRaises(ValueError):decode_data(pack(h,s))
        h,s=unpack(data);g=json.loads(s['geometry']);g['fine']['rows']-=1;s['geometry']=json.dumps(g,sort_keys=True,separators=(',',':')).encode()
        h['sections'][0]['bytes']=len(s['geometry'])
        with self.assertRaises(ValueError):decode_data(pack(h,s))

    def test_omitted_reachable_class_rejected(self):
        meta,c3,q4=fixture();data,_=make(meta,c3,q4,'iid','sparse_default_u16')
        h,s=unpack(data);f=np.full((2,1,256),256,np.uint32);s['l4.model']=serialize(f,'sparse_default_u16',np.ones((2,1),bool))
        i=json.loads(s['l4.info']);i['model_sha256']=sha(f.tobytes());s['l4.info']=json.dumps(i,sort_keys=True,separators=(',',':')).encode()
        h['sections'][5]['bytes']=len(s['l4.model'])
        with self.assertRaisesRegex(ValueError,'Omitted reachable'):decode_data(pack(h,s))

    def test_isolated_child_only_stream_and_forbidden_original(self):
        meta,c3,q4=fixture();data,_=make(meta,c3,q4,'spatial8','packed_u16')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);stream=root/'only.bin';stream.write_bytes(data)
            forbidden=ROOT/'research/interlevel_xyz34_results/pairs.npz'
            code='from research.experiment_bench.interlevel.format import decode; import sys; from pathlib import Path; decode(sys.argv[1],sys.argv[2]);\ntry: Path(sys.argv[3]).read_bytes()\nexcept PermissionError: print("FORBIDDEN ORIGINAL READ BLOCKED")\nelse: raise RuntimeError("audit failed")'
            run=subprocess.run([sys.executable,'-c',code,str(stream),str(root/'decoded'),str(forbidden)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr);self.assertIn('FORBIDDEN ORIGINAL READ BLOCKED',run.stdout)
            np.testing.assert_array_equal(np.load(root/'decoded/coarse.npy'),c3);np.testing.assert_array_equal(np.load(root/'decoded/fine.npy'),q4)

if __name__=='__main__':unittest.main()
