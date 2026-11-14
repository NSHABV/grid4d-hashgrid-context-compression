import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
from .statistics import entropy_counts,joint_metrics,pearson,histogram,describe,sample_indices,average_ranks
from .mapping import slots,corners,lookup,multiplicity,vertex_sample

class StatisticsTests(unittest.TestCase):
    def test_windows_figure_paths_summary(self):
        from .report import summary_rows
        out=Path('known-summary-fixture')
        existing={out/'memory/data.json',out/'memory/levels.csv',out/'entropy/levels.csv'}
        with patch('research.hashgrid_analysis.report.read',return_value=[{'png':'memory\\by-grid.png'},{'png':'entropy\\xyz-levels.png'}]), patch.object(Path,'exists',lambda p:p in existing):
            checks=[{'status':'PASS','input':'memory/data.json'},{'status':'PASS','input':'entropy/levels.csv'}]
            rows={r['Visualization / Analysis']:r['Status'] for r in summary_rows(out,checks)}
            self.assertEqual(rows['Memory by grid'],'PASS');self.assertEqual(rows['Memory by level'],'PASS')
            self.assertEqual(rows['Entropy by level'],'PASS');self.assertEqual(rows['Raw feature histograms'],'NOT RUN')

    def test_histogram_mean_std_box(self):
        x=np.array([0,0,1,3],dtype=np.float32)
        self.assertEqual(histogram(x,np.array([-.5,.5,1.5,3.5])),[2,1,1])
        s=describe(x);self.assertEqual(s['mean'],1);self.assertAlmostEqual(s['std'],np.sqrt(1.5))
        self.assertEqual(s['zero_fraction'],.5);self.assertEqual(s['unique'],3)
        self.assertEqual(s['top_values'][0],{'value':0.,'count':2})
        self.assertEqual(s['box']['med'],.5)

    def test_entropy_conditional_mutual_information(self):
        self.assertEqual(entropy_counts([1,1,1,1]),2)
        self.assertEqual(entropy_counts([0,9]),0)
        equal=joint_metrics([[2,0],[0,2]])
        self.assertEqual(equal['mutual_information'],1);self.assertEqual(equal['H_target_given_context'],0)
        independent=joint_metrics([[1,1],[1,1]])
        self.assertEqual(independent['mutual_information'],0);self.assertEqual(independent['H_target_given_context'],1)
        with self.assertRaises(ValueError):entropy_counts([float('nan'),1])

    def test_correlations_cumulative_bytes_and_bits(self):
        self.assertAlmostEqual(pearson([1,2,3],[3,2,1]),-1)
        self.assertIsNone(pearson([1,1],[2,3]))
        sizes=np.array([8,16,24]);np.testing.assert_array_equal(np.cumsum(sizes),[8,24,48])
        self.assertEqual(int(sizes.sum()*8),384);self.assertEqual(1048576/2**20,1)

    def test_sampling_determinism_and_no_replacement(self):
        a=sample_indices(1000,100,5);b=sample_indices(1000,100,5)
        np.testing.assert_array_equal(a,b);self.assertEqual(len(np.unique(a)),100)
        self.assertFalse(np.array_equal(a,sample_indices(1000,100,6)))

    def test_spearman_tied_ranks_independent_reference(self):
        x=average_ranks([1,1,2,3]);y=average_ranks([3,2,1,1])
        np.testing.assert_array_equal(x,[1.5,1.5,3,4]);np.testing.assert_array_equal(y,[4,3,1.5,1.5])
        self.assertAlmostEqual(pearson(x,y),-8/9)

class MappingTests(unittest.TestCase):
    def test_dense_slots_independent_reference(self):
        v=np.array([[0,0,0],[2,3,4],[1,1,1]])
        r=np.array([3,4,5])
        expected=np.array([0,2+3*3+4*12,1+3+12])
        np.testing.assert_array_equal(slots(v,r,60),expected)

    def test_hash_and_distinct_vertex_multiplicity(self):
        v=np.array([[0,0,0],[1,2,3],[2,1,0],[1,2,3]])
        expected=np.array([((int(x)^((int(y)*2654435761)&0xffffffff)^((int(z)*805459861)&0xffffffff))&0xffffffff)%7 for x,y,z in v])
        np.testing.assert_array_equal(slots(v,[10,10,10],7),expected)
        unique,d=multiplicity(v,[10,10,10],7)
        self.assertEqual(len(unique),3);self.assertEqual(int(d.sum()),3)
        _,all_collide=multiplicity(np.array([[0,0,0],[1,0,0],[1,0,0]]),[2,2,2],1)
        self.assertEqual(all_collide.tolist(),[2])

    def test_smoothstep_interpolation_constant_and_linear_vertex(self):
        vertices,weights=corners(np.array([[.25,.5,.75]],np.float32),[1,1,1])
        self.assertAlmostEqual(float(weights.sum()),1)
        table=np.full((8,2),3,dtype=np.float32)
        np.testing.assert_allclose(lookup(np.array([[.25,.5,.75]],np.float32),table,[1,1,1],[2,2,2]),3)
        # x-fastest grid table stores vertex x in both channels.
        table=np.column_stack((np.arange(8)%2,np.arange(8)%2)).astype(np.float32)
        out=lookup(np.array([[.25,.5,.75]],np.float32),table,[1,1,1],[2,2,2])
        np.testing.assert_allclose(out,.25**2*(3-2*.25))

    def test_nominal_sampling_and_slice_counts(self):
        v,mode,n=vertex_sample([2,3,4],10,0,24)
        self.assertEqual(n,24);self.assertEqual(len(np.unique(v,axis=0)),24)
        np.testing.assert_array_equal(slots(v,[2,3,4],24),np.arange(24))
        sampled,_,_=vertex_sample([100,100,100],100,0,24)
        self.assertEqual(len(sampled),100)
        np.testing.assert_array_equal(sampled,vertex_sample([100,100,100],100,0,24)[0])

if __name__=='__main__':unittest.main()
