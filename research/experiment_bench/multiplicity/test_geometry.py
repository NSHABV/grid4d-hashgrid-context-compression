import unittest,itertools
import numpy as np
from .geometry import slots,compute_geometry,count6_classes,geometry4_classes,HASH,CONVENTION
from research.experiment_bench.hashed_interlevel.core import fit_masses,losses

def scalar_slot(v,r,rows):
    index=0;stride=1
    for d in range(3):
        if stride>rows:break
        index=(index+int(v[d])*stride)%(2**32);stride=(stride*int(r[d]))%(2**32)
    if stride>rows:index=int(v[0]) ^ ((int(v[1])*2654435761)%(2**32)) ^ ((int(v[2])*805459861)%(2**32))
    return index%rows

class Tests(unittest.TestCase):
    def test_six_classes(self):
        n=np.array([0,2,2,3,4,5,9]);p=np.array([0,0,1,2,3,4,8])
        expected=np.array([0,1,2,3,4,5,5]);c=count6_classes(n,p)
        np.testing.assert_array_equal(c[:,0],expected);np.testing.assert_array_equal(c[:,1],expected)
        np.testing.assert_array_equal(geometry4_classes(n,p)[:,0],np.minimum(expected,3))
    def test_bad_counts(self):
        for n,p in [([0],[1]),([1],[-1]),([1.],[1.])]:
            with self.assertRaises(ValueError):count6_classes(n,p)
    def test_scalar_hash_and_wrap(self):
        v=np.array([[0,0,0],[1,2,3],[2**32-1,2**31,2**30],[99999,456,123]])
        for r,rows in [([3,4,5],60),([3,4,5],7),([65536,65536,65536],65536)]:
            np.testing.assert_array_equal(slots(v,r,rows),[scalar_slot(x,r,rows) for x in v])
    def test_small_colliding_geometry_and_boundaries(self):
        for scales,rows in [([2.4,3.2,1.1],7),([2.,2.,2.],40),([1.2,1.2,1.2],29)]:
            r=(np.ceil(np.array(scales,np.float32)).astype(int)+1).tolist()
            spec={'version':1,'hash':HASH,'geometry_convention':CONVENTION,'fine':{'scale':scales,'lookup_resolution':r,'rows':rows,'offset_start':11,'offset_end':11+rows}}
            n=np.zeros(rows,np.int64);p=n.copy()
            for v in itertools.product(*(range(k) for k in r)):
                h=scalar_slot(v,r,rows);n[h]+=1
                if all(v[d]<=np.floor(np.float32(scales[d])) for d in range(3)):p[h]+=1
            for chunk in (1,7,65536):
                got=compute_geometry(spec,chunk)
                np.testing.assert_array_equal(got['nominal_count'],n);np.testing.assert_array_equal(got['point_count'],p)
                np.testing.assert_array_equal(got['slot_index'],np.arange(rows))
    def test_train_only(self):
        n=np.ones(20,dtype=int);p=n.copy();c=count6_classes(n,p);q=np.arange(40,dtype=np.uint8).reshape(20,2);train=np.arange(10)
        cnt,m=fit_masses(q,c,train,6);q2=q.copy();q2[10:]=255
        cnt2,m2=fit_masses(q2,c,train,6);np.testing.assert_array_equal(m,m2);np.testing.assert_array_equal(cnt,cnt2)
        self.assertTrue(np.all(m>0));np.testing.assert_array_equal(m.sum(axis=2),np.full((2,6),65536))
        self.assertTrue(np.all(m[:,0]==256));self.assertTrue(np.isfinite(losses(q,c,m,np.arange(20))).all())
if __name__=='__main__':unittest.main()
