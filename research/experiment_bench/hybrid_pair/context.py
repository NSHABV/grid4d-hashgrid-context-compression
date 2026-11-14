"""Canonical CPU context interface with explicit geometry/lookup timing."""
import time
import numpy as np
from research.experiment_bench.hashed_pair_v3 import format as legacy
from research.hashgrid_analysis.hashed_context import core
from .model import active
def reconstruct(g,coarse,mask,thresholds):
 t=time.perf_counter();geometry=legacy._contexts(g,coarse,'Geometry4')['geometry'];times={'geometry_seconds':time.perf_counter()-t,'mean_context_seconds':0.,'lookup_seconds':0.,'mean_skipped':not any(active(mask))}
 classes=np.zeros((len(geometry),2),np.uint8)
 if not any(active(mask)):return geometry,classes,times
 original=core.lookup_cpu;lookup_time=0.
 def timed(*a,**k):
  nonlocal lookup_time
  t0=time.perf_counter();out=original(*a,**k);lookup_time+=time.perf_counter()-t0;return out
 t=time.perf_counter();core.lookup_cpu=timed
 try:contexts=core.compute_context(g,coarse)
 finally:core.lookup_cpu=original
 if not np.array_equal(geometry,contexts['geometry']):raise AssertionError('Geometry mismatch')
 pos=0
 for ch,isactive in enumerate(active(mask)):
  if isactive:
   classes[:,ch]=2+np.searchsorted(thresholds[pos],contexts['mean'][:,ch],side='right');pos+=1
   classes[geometry<2,ch]=geometry[geometry<2]
 times.update(mean_context_seconds=time.perf_counter()-t,lookup_seconds=lookup_time)
 return geometry,classes,times
