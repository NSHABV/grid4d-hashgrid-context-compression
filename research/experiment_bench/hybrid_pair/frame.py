"""Frozen outer framing specification used for exact dry side-byte accounting."""
import copy,hashlib,struct
from research.experiment_bench.hashed_pair_v3 import format as legacy
from research.experiment_bench.hashed_interlevel import dry_model
from . import model
MAGIC=b'G4DHYBRD';VERSION=1;PREFIX=struct.Struct('<8sH5Q');NAMES=legacy.NAMES;BOUNDS=legacy.BOUNDS
ROUTING='G2c0-G3c0-G2c1-G3c1-v1'
def header(g,coarse,fine,ids,pool,coarse_masses,coarse_storage):
 legacy.validate_geometry(g)
 return {'version':1,'kind':legacy.pair_kind(g),'engine':copy.deepcopy(legacy.ENGINE),'arithmetic':legacy.ARITHMETIC,'numpy':'1.26.4','order':legacy.ORDER,'geometry':copy.deepcopy(g),
 'model':{'name':'Hybrid','coarse_storage':coarse_storage,'routing':ROUTING},
 'integrity':{'coarse_symbols':legacy.array_sha(coarse),'fine_symbols':legacy.array_sha(fine),'classes':legacy.array_sha(ids),'coarse_masses':legacy.array_sha(coarse_masses),'fine_masses':legacy.array_sha(pool)}}
def dry_sizes(h,coarse_model,coarse_payload,fine_model):
 s=model.sizes(fine_model);metadata=dry_model._json_bytes(h);coarse=len(coarse_model)+len(coarse_payload)
 return {**s,'coarse_bytes':coarse,'central_metadata_bytes':len(metadata),'prefix_bytes':PREFIX.size,'integrity_bytes':32,
 'all_side_bytes_excluding_coarse':len(metadata)+len(fine_model)+PREFIX.size+32,
 'metadata_bytes_excluding_pmf':len(metadata)+len(fine_model)-s['pmf_bytes']+PREFIX.size+32}
