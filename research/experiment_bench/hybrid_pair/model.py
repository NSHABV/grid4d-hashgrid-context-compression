"""H3PM v1 dry transport and target-free routing; no fitting or entropy coding."""
import struct
import numpy as np
HEADER=struct.Struct('<4sBBBBHIII');MAGIC=b'H3PM';STORAGES=('dense_u32','packed_u16','sparse_default_u16');UNUSED=255
def bits(mask):
 if type(mask) is not int or not 0<=mask<16:raise ValueError('Invalid four-bit mask')
 return [(mask>>(3-i))&1 for i in range(4)]
def active(mask):
 b=bits(mask);return [bool(b[0] or b[1]),bool(b[2] or b[3])]
def sources(geometry,mean_classes,mask):
 b=bits(mask);g=np.asarray(geometry)
 if g.ndim!=1 or not np.issubdtype(g.dtype,np.integer) or np.any(g>3) or np.any(g<0):raise ValueError('Invalid geometry')
 out=np.repeat(g[:,None],2,axis=1).astype(np.uint8)
 if any(b):
  k=np.asarray(mean_classes)
  if k.shape!=out.shape or not np.issubdtype(k.dtype,np.integer) or np.any(k<0) or np.any(k>9):raise ValueError('Invalid Mean8 classes')
  for ch in range(2):
   for cat in (2,3):
    if b[2*ch+cat-2]:
     use=g==cat
     if np.any(k[use,ch]<2):raise ValueError('Invalid active class')
     out[use,ch]=k[use,ch]+2
 return out
def validate(pool,mapping,thresholds,mask):
 b=bits(mask);a=active(mask);f=np.asarray(pool);m=np.asarray(mapping);e=np.asarray(thresholds)
 if f.dtype!=np.uint32 or f.ndim!=2 or f.shape[1]!=256 or not 1<=len(f)<=24 or np.any(f<1) or np.any(f.sum(1,dtype=np.uint64)!=65536):raise ValueError('Invalid PMF pool')
 if m.dtype!=np.uint8 or m.shape!=(2,12) or np.any((m!=UNUSED)&(m>=len(f))):raise ValueError('Invalid row references')
 if e.dtype!=np.float64 or e.shape!=(sum(a),7) or not np.isfinite(e).all() or np.any(np.diff(e,axis=1)<0):raise ValueError('Invalid thresholds')
 for ch in range(2):
  for cat in (2,3):
   if b[2*ch+cat-2] and m[ch,cat]!=UNUSED:raise ValueError('Unused geometry PMF retained')
  if not a[ch] and np.any(m[ch,4:]!=UNUSED):raise ValueError('Unused feature PMFs retained')
 seen=[]
 for row in m.flat:
  if row!=UNUSED and int(row) not in seen:seen.append(int(row))
 if seen!=list(range(len(f))):raise ValueError('Noncanonical or unreferenced PMF pool')
 if len({row.tobytes() for row in f})!=len(f):raise ValueError('Duplicate PMF pool rows')
def routed(geometry,mean_classes,mask,pool,mapping,thresholds):
 validate(pool,mapping,thresholds,mask);src=sources(geometry,mean_classes,mask)
 expected=np.zeros((2,12),bool)
 for ch in range(2):expected[ch,np.unique(src[:,ch])]=True
 if not np.array_equal(mapping!=UNUSED,expected):raise ValueError('Mapping coverage differs from decoder routing')
 return mapping[np.arange(2)[None,:],src]
def build(geometry,mean_classes,geo_pmf,mean_pmf,edges,mask):
 if geo_pmf.shape!=(2,4,256) or mean_pmf.shape!=(2,10,256):raise ValueError('Original model shape')
 if not np.array_equal(geo_pmf[:,:2],mean_pmf[:,:2]):raise ValueError('G0/G1 distributions differ')
 src=sources(geometry,mean_classes,mask);mapping=np.full((2,12),UNUSED,np.uint8);pool=[];known={}
 for ch in range(2):
  for key in np.unique(src[:,ch]):
   row=geo_pmf[ch,key] if key<4 else mean_pmf[ch,key-2];raw=row.astype('<u4').tobytes()
   if raw not in known:known[raw]=len(pool);pool.append(row.copy())
   mapping[ch,key]=known[raw]
 f=np.array(pool,dtype=np.uint32);e=np.asarray(edges,np.float64)[active(mask)].copy()
 ids=routed(geometry,mean_classes,mask,f,mapping,e)
 return f,mapping,e,ids
def serialize(pool,mapping,thresholds,mask,storage):
 validate(pool,mapping,thresholds,mask)
 if storage not in STORAGES:raise ValueError('Unknown storage')
 if storage=='dense_u32':mass=pool.astype('<u4').tobytes()
 elif storage=='packed_u16':mass=pool.astype('<u2').tobytes()
 else:
  buf=bytearray()
  for row in pool:
   values,counts=np.unique(row,return_counts=True);default=int(values[np.argmax(counts)]);ix=np.flatnonzero(row!=default)
   buf.extend(struct.pack('<HH',default,len(ix)))
   for symbol in ix:buf.extend(struct.pack('<BH',int(symbol),int(row[symbol])))
  mass=bytes(buf)
 edge=thresholds.astype('<f8').tobytes();mapping_bytes=mapping.tobytes()
 return HEADER.pack(MAGIC,1,STORAGES.index(storage)+1,mask,2,len(pool),len(mass),len(edge),len(mapping_bytes))+mass+edge+mapping_bytes
def deserialize(data):
 if not isinstance(data,(bytes,bytearray)) or len(data)<HEADER.size:raise ValueError('Truncated H3PM')
 magic,ver,storage,mask,ch,R,nm,ne,nr=HEADER.unpack_from(data);bits(mask)
 if magic!=MAGIC or ver!=1 or storage not in (1,2,3) or ch!=2 or not 1<=R<=24 or nm>24*1024 or ne!=56*sum(active(mask)) or nr!=24 or len(data)!=HEADER.size+nm+ne+nr:raise ValueError('Invalid H3PM header/lengths')
 offset=HEADER.size;raw=data[offset:offset+nm];offset+=nm
 if storage in (1,2):
  width=4 if storage==1 else 2
  if nm!=R*256*width:raise ValueError('Mass length')
  pool=np.frombuffer(raw,dtype='<u4' if storage==1 else '<u2').astype(np.uint32).reshape(R,256)
 else:
  pool=np.empty((R,256),np.uint32);pos=0
  for row in pool:
   if pos+4>len(raw):raise ValueError('Truncated sparse row')
   default,E=struct.unpack_from('<HH',raw,pos);pos+=4
   if not default or E>255 or pos+3*E>len(raw):raise ValueError('Invalid exceptions')
   row[:]=default;last=-1
   for _ in range(E):
    symbol,mass=struct.unpack_from('<BH',raw,pos);pos+=3
    if symbol<=last or mass==0 or mass==default:raise ValueError('Noncanonical exception')
    row[symbol]=mass;last=symbol
  if pos!=len(raw):raise ValueError('Trailing mass data')
 thresholds=np.frombuffer(data[offset:offset+ne],dtype='<f8').copy().reshape(sum(active(mask)),7);offset+=ne
 mapping=np.frombuffer(data[offset:],np.uint8).copy().reshape(2,12)
 validate(pool,mapping,thresholds,mask);name=STORAGES[storage-1]
 if serialize(pool,mapping,thresholds,mask,name)!=data:raise ValueError('Noncanonical model')
 return pool,mapping,thresholds,mask,name
def sizes(data):
 f,m,e,mask,name=deserialize(data);_,_,_,_,_,_,nm,ne,nr=HEADER.unpack_from(data)
 return {'model_total_bytes':len(data),'pmf_bytes':nm,'threshold_bytes':ne,'mapping_bytes':nr,'mask_bytes':1,'mode_identifier_bytes':1,'other_model_header_bytes':HEADER.size-2,'pool_rows':len(f),'storage':name}
def choose(f,m,e,mask):
 choices={s:serialize(f,m,e,mask,s) for s in STORAGES}
 for data in choices.values():
  ff,mm,ee,bb,_=deserialize(data)
  if not(np.array_equal(ff,f) and np.array_equal(mm,m) and np.array_equal(ee,e) and bb==mask):raise AssertionError('Transport roundtrip')
 storage=min(STORAGES,key=lambda s:len(choices[s]));return choices[storage],{s:len(d) for s,d in choices.items()}
