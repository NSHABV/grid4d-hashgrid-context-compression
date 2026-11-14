"""Standalone H3 fixed-PMF hybrid entropy container; no fitting APIs."""
import hashlib,time
import numpy as np
from . import model,frame,context
from research.experiment_bench.hashed_pair import engine
from research.experiment_bench.hashed_interlevel import dry_model as dm
legacy=frame.legacy
def masses_for_engine(pool):return np.stack([pool,pool])
def validate_header(h):
 if not isinstance(h,dict) or set(h)!={'version','kind','engine','arithmetic','numpy','order','geometry','model','integrity'}:raise ValueError('Header fields')
 if type(h['version']) is not int or h['version']!=1 or h['arithmetic']!=legacy.ARITHMETIC or h['numpy']!='1.26.4' or h['order']!=legacy.ORDER or dm._json_bytes(h['engine'])!=dm._json_bytes(legacy.ENGINE):raise ValueError('Unsupported contract')
 legacy.validate_geometry(h['geometry'])
 if h['kind']!=legacy.pair_kind(h['geometry']):raise ValueError('Wrong level pair')
 m=h['model']
 if not isinstance(m,dict) or set(m)!={'name','coarse_storage','routing'} or m['name']!='Hybrid' or m['coarse_storage'] not in dm.STORAGES or m['routing']!=frame.ROUTING:raise ValueError('Routing contract')
 integ=h['integrity']
 if not isinstance(integ,dict) or set(integ)!={'coarse_symbols','fine_symbols','classes','coarse_masses','fine_masses'} or not all(legacy._digest(v) for v in integ.values()):raise ValueError('Integrity fields')
def pack(h,sections):
 if set(sections)!=set(frame.NAMES):raise ValueError('Sections')
 parts=[dm._json_bytes(h)]+[bytes(sections[k]) for k in frame.NAMES[1:]]
 body=frame.PREFIX.pack(frame.MAGIC,1,*(len(p) for p in parts))+b''.join(parts)
 return body+hashlib.sha256(body).digest()
def unpack(data):
 if not isinstance(data,(bytes,bytearray)) or len(data)<frame.PREFIX.size+32:raise ValueError('Truncated container')
 magic,version,*lengths=frame.PREFIX.unpack_from(data)
 if magic!=frame.MAGIC or version!=1 or any(n>b for n,b in zip(lengths,frame.BOUNDS)) or frame.PREFIX.size+sum(lengths)+32!=len(data):raise ValueError('Invalid magic/version/lengths')
 if hashlib.sha256(data[:-32]).digest()!=data[-32:]:raise ValueError('Container checksum')
 sections={};pos=frame.PREFIX.size
 for name,n in zip(frame.NAMES,lengths):sections[name]=bytes(data[pos:pos+n]);pos+=n
 h=dm._json_load(sections['metadata'])
 try:validate_header(h)
 except (KeyError,TypeError,OverflowError,IndexError) as exc:raise ValueError('Malformed metadata') from exc
 for name in ('coarse_payload','fine_payload'):
  if not sections[name] or len(sections[name])%4:raise ValueError('Invalid payload length')
 model.deserialize(sections['fine_model'])
 return h,sections
def sizes(data):
 h,s=unpack(data);v=frame.dry_sizes(h,s['coarse_model'],s['coarse_payload'],s['fine_model'])
 v.update(total_bytes=len(data),fine_payload_bytes=len(s['fine_payload']))
 if v['total_bytes']!=v['coarse_bytes']+v['fine_payload_bytes']+v['pmf_bytes']+v['metadata_bytes_excluding_pmf']:raise AssertionError('Size accounting')
 return v
def encode(g,coarse,fine,gf,mf,edges,mask,coarse_model,coarse_payload,coarse_storage):
 engine.check_runtime();started=time.perf_counter();cpu=time.process_time();legacy.validate_geometry(g)
 for q,role in ((coarse,'coarse'),(fine,'fine')):
  if q.dtype!=np.uint8 or q.shape!=(g[role]['rows'],2):raise ValueError('Complete frozen uint8 symbols required')
  legacy._constant_symbols(q,g['coarse']['quantization'])
 geometry,k,timing=context.reconstruct(g,coarse,mask,np.asarray(edges,np.float64)[model.active(mask)])
 t=time.perf_counter();pool,mapping,e,ids=model.build(geometry,k,gf,mf,edges,mask);wire,choices=model.choose(pool,mapping,e,mask)
 fcoarse,_=legacy._load_model(coarse_model,'IID',coarse_storage)
 h=frame.header(g,coarse,fine,ids,pool,fcoarse,coarse_storage);timing['model_and_routing_seconds']=time.perf_counter()-t
 t=time.perf_counter();payload=engine.encode_indexed(fine,ids,masses_for_engine(pool));timing['fine_entropy_seconds']=time.perf_counter()-t
 sections={'metadata':b'','coarse_model':coarse_model,'fine_model':wire,'coarse_payload':coarse_payload,'fine_payload':payload}
 data=pack(h,sections);timing.update(encode_wall_seconds=time.perf_counter()-started,encode_cpu_seconds=time.process_time()-cpu,coarse_entropy_encode_seconds=0.,coarse_payload_reused=True)
 return data,ids,{'sizes':sizes(data),'timing':timing,'mask':format(mask,'04b'),'transport_candidates':choices}
def decode(data,strict=True):
 engine.check_runtime();started=time.perf_counter();cpu=time.process_time();h,s=unpack(data);g=h['geometry'];integrity=h['integrity'];timing={}
 t=time.perf_counter();fc,_=legacy._load_model(s['coarse_model'],'IID',h['model']['coarse_storage']);pool,mapping,edges,mask,storage=model.deserialize(s['fine_model']);fp=masses_for_engine(pool)
 if legacy.array_sha(fc)!=integrity['coarse_masses'] or legacy.array_sha(pool)!=integrity['fine_masses']:raise ValueError('Mass integrity mismatch')
 timing['model_restore_seconds']=time.perf_counter()-t
 t=time.perf_counter();coarse_ids=np.zeros((g['coarse']['rows'],2),np.uint8);coarse=legacy._decode_payload(s['coarse_payload'],coarse_ids,fc);timing['coarse_entropy_seconds']=time.perf_counter()-t
 if legacy.array_sha(coarse)!=integrity['coarse_symbols']:raise ValueError('Coarse symbols mismatch')
 legacy._constant_symbols(coarse,g['coarse']['quantization'])
 geometry,k,ct=context.reconstruct(g,coarse,mask,edges);timing.update(ct)
 t=time.perf_counter();ids=model.routed(geometry,k,mask,pool,mapping,edges);timing['routing_seconds']=time.perf_counter()-t
 if legacy.array_sha(ids)!=integrity['classes']:raise ValueError('Reconstructed routing mismatch')
 t=time.perf_counter();fine=legacy._decode_payload(s['fine_payload'],ids,fp);timing['fine_entropy_seconds']=time.perf_counter()-t
 if legacy.array_sha(fine)!=integrity['fine_symbols']:raise ValueError('Fine symbols mismatch')
 legacy._constant_symbols(fine,g['coarse']['quantization']);t=time.perf_counter()
 if strict and (engine.encode_indexed(coarse,coarse_ids,fc)!=s['coarse_payload'] or engine.encode_indexed(fine,ids,fp)!=s['fine_payload']):raise ValueError('Noncanonical payload or trailing words')
 timing.update(strict_verification_seconds=time.perf_counter()-t,decode_wall_seconds=time.perf_counter()-started,decode_cpu_seconds=time.process_time()-cpu)
 return coarse,fine,ids,{'status':'PASS','mask':format(mask,'04b'),'strict':strict,'sizes':sizes(data),'timing':timing}
