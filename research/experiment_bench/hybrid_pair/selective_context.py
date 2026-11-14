"""Optional target-free group skipping; checked against canonical bitstreams.

Not used to produce the primary dataset. Preserve x-fast update order and
all per-point float32 operations; omit whole slots unused by Mean8 routing.
"""
import time
import numpy as np
from . import model,frame
from research.hashgrid_analysis.hashed_context import core

def reconstruct(g,coarse,mask,edges):
 started=time.perf_counter();geometry=frame.legacy._contexts(g,coarse,'Geometry4')['geometry'];gt=time.perf_counter()-started
 b=model.bits(mask);needed=((geometry==2)&bool(b[0] or b[2]))|((geometry==3)&bool(b[1] or b[3]))
 k=np.zeros((len(geometry),2),np.uint8);k[geometry<2]=geometry[geometry<2,None]
 timing={'geometry_seconds':gt,'selected_slots':int(needed.sum()),'looked_up_points':0,'lookup_seconds':0.}
 if not needed.any():timing['wall_seconds']=time.perf_counter()-started;return geometry,k,timing
 c,f=g['coarse'],g['fine'];r=np.asarray(f['lookup_resolution'],np.int64);scale=np.asarray(f['scale'],np.float32);er=np.floor(scale).astype(np.int64)+1
 table=core.dequantize_symbols(coarse,c['quantization']);n=f['rows'];count=np.zeros(n,np.int64);ordinal=np.full(n,np.iinfo(np.int64).max,np.int64);canonical=np.zeros((n,2),np.float32);sums=np.zeros((n,2),np.float64)
 total=int(np.prod(r))
 for start in range(0,total,65536):
  linear=np.arange(start,min(start+65536,total),dtype=np.int64);v=core.vertices_from_ordinals(linear,r);slot=core.slot_indices(v,r,n)
  keep=(v<er).all(1)&needed[slot]
  if not keep.any():continue
  v,linear,slot=v[keep],linear[keep],slot[keep];count+=np.bincount(slot,minlength=n)
  u=np.divide(v.astype(np.float32),scale,dtype=np.float32);t=time.perf_counter();feat=core.lookup_cpu(u,table,c['scale'],c['lookup_resolution']);timing['lookup_seconds']+=time.perf_counter()-t;timing['looked_up_points']+=len(v)
  np.minimum.at(ordinal,slot,linear);first=ordinal[slot]==linear;canonical[slot[first]]=feat[first];delta=feat.astype(np.float64)-canonical[slot].astype(np.float64)
  for ch in range(2):np.add.at(sums[:,ch],slot,delta[:,ch])
 assert np.all(count[needed]>0)
 mean=np.zeros((n,2),np.float64);mean[needed]=canonical[needed].astype(np.float64)+sums[needed]/count[needed,None]
 edge_index=0
 for ch in range(2):
  if model.active(mask)[ch]:
   use=((geometry==2)&bool(b[2*ch]))|((geometry==3)&bool(b[2*ch+1]));k[use,ch]=2+np.searchsorted(edges[edge_index],mean[use,ch],side='right');edge_index+=1
 timing['wall_seconds']=time.perf_counter()-started
 return geometry,k,timing
