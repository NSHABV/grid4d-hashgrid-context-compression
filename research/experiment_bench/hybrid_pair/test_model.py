import unittest,struct
import numpy as np
from . import model
class DryTests(unittest.TestCase):
 def setUp(self):
  self.g=np.array([0,1,2,3]*8,np.uint8);self.k=np.zeros((32,2),np.uint8)
  for i,g in enumerate(self.g):self.k[i]=g if g<2 else [2+i%8,2+(i+1)%8]
  self.gf=np.full((2,4,256),256,np.uint32);self.mf=np.full((2,10,256),256,np.uint32)
  for c in range(2):
   for j in range(2,4):self.gf[c,j,0]+=10*c+j;self.gf[c,j,1]-=10*c+j
   for j in range(2,10):self.mf[c,j,0]+=20+10*c+j;self.mf[c,j,1]-=20+10*c+j
  self.edges=np.array([np.arange(7),np.arange(7)+.2],np.float64)
 def test_scalar_all_masks_all_transports(self):
  q=np.arange(64,dtype=np.uint8).reshape(32,2)
  for mask in range(16):
   f,m,e,ids=model.build(self.g,self.k,self.gf,self.mf,self.edges,mask)
   for i,g in enumerate(self.g):
    for c in range(2):
     use=g>=2 and format(mask,'04b')[2*c+int(g)-2]=='1'
     row=self.mf[c,self.k[i,c]] if use else self.gf[c,g]
     np.testing.assert_array_equal(f[ids[i,c]],row)
   for s in model.STORAGES:
    wire=model.serialize(f,m,e,mask,s);ff,mm,ee,bb,ss=model.deserialize(wire)
    np.testing.assert_array_equal(ff,f);np.testing.assert_array_equal(mm,m);np.testing.assert_array_equal(ee,e);self.assertEqual(bb,mask);self.assertEqual(ss,s)
    costs=model.sizes(wire);self.assertEqual(costs['pmf_bytes']+costs['threshold_bytes']+costs['mapping_bytes']+costs['mask_bytes']+costs['mode_identifier_bytes']+costs['other_model_header_bytes'],len(wire))
 def test_decoder_route_no_targets_and_exact_sharing(self):
  f,m,e,ids=model.build(self.g,self.k,self.gf,self.mf,self.edges,5)
  self.assertEqual(model.bits(5),[0,1,0,1]);self.assertEqual(m[0,0],m[1,0]);self.assertEqual(m[0,1],m[1,1])
  np.testing.assert_array_equal(model.routed(self.g,self.k,5,f,m,e),ids)
  self.assertTrue(np.all(m[:,3]==255));self.assertLess(len(f),int((m!=255).sum()))
 def test_no_threshold_geometry_only(self):
  f,m,e,ids=model.build(self.g,None,self.gf,self.mf,self.edges,0)
  self.assertEqual(e.shape,(0,7));self.assertTrue(np.all(m[:,4:]==255))
 def test_malformed_and_noncanonical(self):
  f,m,e,ids=model.build(self.g,self.k,self.gf,self.mf,self.edges,5);wire=model.serialize(f,m,e,5,'sparse_default_u16')
  cases=[wire[:i] for i in (0,4,model.HEADER.size,len(wire)-1)]+[wire+b'\x00']
  for pos,val in ((0,0),(4,9),(5,0),(6,16),(7,3),(8,255),(10,255)):
   z=bytearray(wire);z[pos]=val;cases.append(bytes(z))
  z=bytearray(wire);z[-24]=254;cases.append(bytes(z))
  for case in cases:
   with self.assertRaises(ValueError):model.deserialize(case)
  bad=m.copy();bad[:,3]=0
  with self.assertRaises(ValueError):model.validate(f,bad,e,5)
  wrong=f.copy();wrong[0,0]=0
  with self.assertRaises(ValueError):model.validate(wrong,m,e,5)
if __name__=='__main__':unittest.main(verbosity=2)
