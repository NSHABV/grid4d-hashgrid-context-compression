import unittest
import numpy as np
from .core import split_rows,fit_edges,classify,fit_histogram,costs,overhead,block_ids,bootstrap_plan,gain_interval
from research.hashgrid_analysis.statistics import joint_metrics
from research.experiment_bench.models import frequencies

class FeasibilityTests(unittest.TestCase):
    def test_lossless_candidate_mass_representations(self):
        counts=np.zeros(256,np.int64);counts[166]=100000000
        masses=frequencies(counts)
        self.assertLessEqual(int(masses.max()),65535)
        np.testing.assert_array_equal(masses,masses.astype('<u2').astype(np.uint32))
        values,n=np.unique(masses,return_counts=True);default=values[np.argmax(n)];idx=np.flatnonzero(masses!=default)
        rebuilt=np.full(256,default,np.uint32);rebuilt[idx]=masses[idx]
        np.testing.assert_array_equal(rebuilt,masses)

    def test_known_entropy_and_conditional(self):
        self.assertEqual(joint_metrics([[1,0],[0,1]])['mutual_information'],1)
        self.assertEqual(joint_metrics([[1,1],[1,1]])['mutual_information'],0)
        q=np.array([0,1],np.uint8);c=np.zeros(2,np.int64)
        np.testing.assert_array_equal(costs(q,c,np.arange(2),np.full((1,256),1/256)),[8,8])
        np.testing.assert_allclose(costs(q,c,np.arange(2),np.column_stack(([.5],[.5],np.zeros((1,254))))),[1,1])

    def test_train_only_edges_and_ties(self):
        x=np.array([-2.,-1.,0.,1.,2.,999.]);inside=np.ones(6,bool);train=np.arange(5)
        for method in ('uniform','quantile'):
            a=fit_edges(x,inside,train,4,method);x[-1]=-999.
            np.testing.assert_array_equal(a,fit_edges(x,inside,train,4,method))
            self.assertEqual(len(a),3)
        edges=fit_edges(np.ones(6),inside,train,4,'quantile')
        c,n=classify(np.ones(6),inside,'Spatial-4',4,edges)
        np.testing.assert_array_equal(c,3);self.assertEqual(n,5)

    def test_outside_class_and_threshold_rule(self):
        x=np.array([-2.,0.,2.,99.]);inside=np.array([1,1,1,0],bool)
        c,n=classify(x,inside,'Spatial-4',4,np.array([-1.,0.,1.]))
        np.testing.assert_array_equal(c,[0,2,3,4]);self.assertEqual(n,5)
        np.testing.assert_array_equal(classify(x,inside,'Boundary')[0],[0,0,0,1])

    def test_smoothing_empty_and_no_zero_probabilities(self):
        q=np.array([5,5,6],np.uint8);c=np.array([0,0,1]);train=np.array([0,1])
        counts,m,a,p,*_=fit_histogram(q,c,train,3)
        np.testing.assert_array_equal(counts.sum(axis=1),[2,0,0]);np.testing.assert_array_equal(p[1],1/256)
        self.assertTrue(np.all(p>0));self.assertTrue(np.all(m.sum(axis=1)==65536))
        np.testing.assert_allclose(a[0,5],3/258)
        self.assertTrue(np.isfinite(costs(q,c,np.arange(3),p)).all())

    def test_splits_disjoint_and_blocks_never_cross(self):
        v=np.array([[x,y,z] for z in range(12) for y in range(12) for x in range(12)])
        for kind in ('random','block-2','block-3'):
            parts,g=split_rows(v,5,kind);repeat,_=split_rows(v,5,kind)
            np.testing.assert_array_equal(np.sort(np.concatenate(list(parts.values()))),np.arange(len(v)))
            for key in parts:np.testing.assert_array_equal(parts[key],repeat[key])
            if kind!='random':
                sets=[set(g[a]) for a in parts.values()]
                self.assertFalse(sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])

    def test_model_overhead_bytes_bits_and_no_double_CDF(self):
        masses=np.full((5,256),256,np.uint32);h=overhead(masses,np.array([-1.,0.,1.]),'Spatial-4',4,'uniform')
        c=h['components'];self.assertEqual(c['conditional_mass_bytes'],5*256*4)
        self.assertEqual(c['boundary_bytes'],24);self.assertEqual(c['CDF_additional_file_bytes'],0)
        self.assertEqual(h['dense_u32'],5*256*4+24+c['metadata_bytes'])
        self.assertEqual(h['packed_u16'],5*256*2+24+c['metadata_bytes'])
        self.assertEqual(h['sparse_default_u16'],5*4+24+c['metadata_bytes'])
        self.assertEqual((100*.08/8)-(.5),.5)

    def test_cluster_bootstrap_deterministic_constant(self):
        v=np.array([[i%10,(i//10)%10,i//100] for i in range(1000)])
        a=bootstrap_plan(v,np.arange(1000),4,100,2);b=bootstrap_plan(v,np.arange(1000),4,100,2)
        np.testing.assert_array_equal(a[1],b[1]);np.testing.assert_allclose(gain_interval(np.full(1000,.25),a),[.25,.25])

if __name__=='__main__':unittest.main()
