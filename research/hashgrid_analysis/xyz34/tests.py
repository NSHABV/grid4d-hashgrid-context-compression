import unittest
import numpy as np
from research.grid4d.codec import dequantize,quantize
from research.hashgrid_analysis.mapping import slots
from .decoder import dense_vertices,geometry,cpu_context

def metadata(res=(3,3,3),scale=(2.,2.,2.)):
    return {'fine':{'rows':int(np.prod(res)),'lookup_resolution':list(res),'scale':list(scale)},
        'coarse':{'rows':27,'lookup_resolution':[3,3,3],'scale':[2.,2.,2.]}}

class PairTests(unittest.TestCase):
    def test_x_fastest_inverse_non_cubic(self):
        expected=np.array([[x,y,z] for z in range(2) for y in range(4) for x in range(3)])
        v=dense_vertices(24,[3,4,2]);np.testing.assert_array_equal(v,expected)
        np.testing.assert_array_equal(slots(v,[3,4,2],24),np.arange(24))
        self.assertEqual(len(np.unique(v,axis=0)),24)

    def test_padding_or_hashing_rejected(self):
        for rows in (26,28):
            with self.assertRaises(ValueError):dense_vertices(rows,[3,3,3])

    def test_fractional_boundary_not_clamped(self):
        m=metadata((4,3,5),(2.5,1.5,3.25));v,u,exact,valid=geometry(m)
        self.assertEqual(valid.sum(),3*2*4);self.assertTrue(np.any(u>1))
        np.testing.assert_allclose(u[0],[0,0,0]);np.testing.assert_allclose(exact[-1],[3/2.5,2/1.5,4/3.25])
        np.testing.assert_array_equal(valid,(v[:,0]<=2)&(v[:,1]<=1)&(v[:,2]<=3))

    def test_quantized_coarse_and_smoothstep_analytic(self):
        v=dense_vertices(27,[3,3,3])
        raw=np.column_stack((v[:,0]+2*v[:,1]-3*v[:,2],np.full(27,7))).astype(np.float32)
        q,params=quantize(raw,8);m=metadata();m['coarse']['quantization']=params
        # Known quantized reconstruction; independent double-precision eight-corner reference.
        reconstructed=dequantize(q,params);actual=cpu_context(m,q)
        np.testing.assert_allclose(actual,reconstructed,atol=1e-6)
        m['fine']=metadata((5,5,5),(4.,4.,4.))['fine'];actual=cpu_context(m,q)
        vv,u,_,_=geometry(m);reference=[]
        for point in u.astype(np.float64):
            p=point*2;b=np.floor(p).astype(int);f=p-b;h=f*f*(3-2*f);result=np.zeros(2)
            for dz in (0,1):
                for dy in (0,1):
                    for dx in (0,1):
                        weight=np.prod([h[0] if dx else 1-h[0],h[1] if dy else 1-h[1],h[2] if dz else 1-h[2]])
                        if weight==0:continue
                        x,y,z=b+[dx,dy,dz];result+=weight*reconstructed[x+3*y+9*z]
            reference.append(result)
        np.testing.assert_allclose(actual,reference,atol=2e-6)

    def test_oob_context_zero_and_no_target_input(self):
        m=metadata((4,4,4),(2.5,2.5,2.5));q=np.full((27,2),128,np.uint8)
        m['coarse']['quantization']={'bits':8,'min':-1.,'max':1.,'step':2/255}
        context=cpu_context(m,q);_,_,_,valid=geometry(m)
        np.testing.assert_array_equal(context[~valid],0)
        self.assertTrue(np.all(context[valid]!=0));m['unavailable_fine_weights']=np.full((64,2),np.nan)
        np.testing.assert_array_equal(context,cpu_context(m,q))

    def test_existing_codec_known_symbols(self):
        q,p=quantize(np.array([-1.,0.,1.],np.float32),8)
        np.testing.assert_array_equal(q,[0,128,255]);np.testing.assert_allclose(dequantize(q,p),[-1.,1/255,1.],atol=1e-8)

if __name__=='__main__':unittest.main()
