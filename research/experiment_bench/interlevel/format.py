"""G4DBENCH v2: standalone dense XYZ L3/L4 subset, existing range engine."""
import hashlib
import importlib.metadata
import json
import struct
import time
from pathlib import Path
import numpy as np
from research.experiment_bench import entropy
from research.experiment_bench.models import HistogramModel
from research.hashgrid_analysis.common import write
from .context import context,boundaries,classes,ARITHMETIC
from .model_io import STORAGES,serialize,deserialize,fit

MODELS={'iid':1,'boundary':2,'spatial8':9}
META_NAMES=('geometry','quantization','l3.info','l3.model','l4.info','l4.model','thresholds')
PAYLOAD_NAMES=('l3.payload','l4.payload')
NAMES=META_NAMES+PAYLOAD_NAMES
SHARED=('geometry','quantization','l3.info','l3.model','l3.payload')
RUNTIME_CODER_VERSION=importlib.metadata.version('constriction')  # Read public package metadata before the decoder data-read audit.

def sha(data):return hashlib.sha256(data).hexdigest()
def json_bytes(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
def check_runtime():
    if RUNTIME_CODER_VERSION!=entropy.CODER_VERSION:raise ValueError('Pinned constriction0.4.2 required')
    if np.__version__!='1.21.6':raise ValueError('Canonical context pins NumPy1.21.6; another platform/version needs separate parity validation')

def shared_sections(meta,coarse,timing=None):
    geometry={'coarse':{k:meta['coarse'][k] for k in ('level','rows','offset_start','offset_end','lookup_resolution','scale')},
        'fine':{k:meta['fine'][k] for k in ('level','rows','offset_start','offset_end','lookup_resolution','scale')},
        'indexing':'dense-x-fastest-unpadded','interpolation':'smoothstep','coordinate_rule':'float32(v)/float32(fine_scale), OOB zero, no clamp',
        'source_checkpoint_sha256':meta['checkpoint_sha256']}
    quant=dict(meta['coarse']['quantization']);quant['scope']='table';quant['shared_by_levels']=[3,4]
    t=time.perf_counter();m=HistogramModel.fit(coarse)
    if timing is not None:timing['l3_fit_seconds']=time.perf_counter()-t
    t=time.perf_counter();model_data=m.to_bytes()
    if timing is not None:timing['l3_model_serialize_seconds']=time.perf_counter()-t
    t=time.perf_counter();payload=entropy.encode_symbols(coarse,m)
    if timing is not None:timing['entropy_encode_l3_seconds']=time.perf_counter()-t
    return {'geometry':json_bytes(geometry),'quantization':json_bytes(quant),'l3.info':json_bytes({'shape':list(coarse.shape),'symbols_sha256':sha(coarse.tobytes()),'model':'iid','storage':'dense_u32','model_sha256':sha(m.freq.tobytes())}),
        'l3.model':model_data,'l3.payload':payload}

def make(meta,coarse,fine,model,storage,shared=None):
    check_runtime();started=time.perf_counter();timing={}
    shared=shared_sections(meta,coarse,timing) if shared is None else shared
    t=time.perf_counter();edges=None
    if model=='spatial8':x,inside=context(meta,coarse);edges=boundaries(x,inside)
    c,inside,_=classes(meta,coarse,model,edges)
    timing['context_build_seconds']=time.perf_counter()-t
    C=MODELS[model];t=time.perf_counter();f=fit(fine,c,C);timing['fit_seconds']=time.perf_counter()-t
    unreachable=np.stack([np.bincount(c[:,ch],minlength=C)==0 for ch in range(2)])
    t=time.perf_counter();model_data=serialize(f,storage,unreachable)
    timing['model_serialize_seconds']=time.perf_counter()-t
    restored,omitted=deserialize(model_data,storage,C);np.testing.assert_array_equal(restored,f)
    t=time.perf_counter();payload=entropy.encode_indexed(fine,c,f);timing['entropy_encode_l4_seconds']=time.perf_counter()-t
    sections=dict(shared);sections.update({'l4.info':json_bytes({'shape':list(fine.shape),'symbols_sha256':sha(fine.tobytes()),'class_sha256':sha(c.tobytes()),'model_sha256':sha(f.tobytes())}),
        'l4.model':model_data,'thresholds':b'' if edges is None else edges.astype('<f8').tobytes(),'l4.payload':payload})
    header={'format_version':2,'kind':'dense-xyz-L3-L4','coder_version':entropy.CODER_VERSION,'histogram_precision':16,'coder_precision':24,'categorical_perfect':False,
        'model':model,'storage':storage,'arithmetic':ARITHMETIC,'order':'channel-major-row-ascending-v1','sections':[{'name':name,'bytes':len(sections[name])} for name in NAMES]}
    body=pack(header,sections);timing['encode_total_seconds']=time.perf_counter()-started
    p=f[np.arange(2)[None,:],c,fine].astype(np.float64)/65536
    return body,{'timing':timing,'sections':{k:len(v) for k,v in sections.items()},'header_json_bytes':len(json_bytes(header)),
        'prefix_bytes':entropy.PREFIX.size,'integrity_bytes':32,'classes_sha256':sha(c.tobytes()),'class_counts':[np.bincount(c[:,ch],minlength=C).tolist() for ch in range(2)],
        'omitted_unreachable_rows':np.argwhere(omitted).tolist(),'finite_l4_cross_entropy_bits':float(-np.log2(p).sum()),'encoder_masses_sha256':sha(f.tobytes())}

def pack(header,sections):
    h=json_bytes(header);models=b''.join(sections[name] for name in META_NAMES);payload=b''.join(sections[name] for name in PAYLOAD_NAMES)
    body=entropy.PREFIX.pack(entropy.MAGIC,2,len(h),len(models),len(payload))+h+models+payload
    return body+hashlib.sha256(body).digest()

def unpack(data):
    if len(data)<entropy.PREFIX.size+32:raise ValueError('Truncated stream')
    magic,version,h,m,p=entropy.PREFIX.unpack_from(data)
    if magic!=entropy.MAGIC or version!=2 or h>10000 or m>100000 or p>4000000:raise ValueError('Invalid header/version/length')
    if len(data)!=entropy.PREFIX.size+h+m+p+32:raise ValueError('Truncation or extra bytes')
    if hashlib.sha256(data[:-32]).digest()!=data[-32:]:raise ValueError('Integrity mismatch')
    header=json.loads(data[entropy.PREFIX.size:entropy.PREFIX.size+h]);spec={k:header[k] for k in ('format_version','kind','coder_version','histogram_precision','coder_precision','categorical_perfect','arithmetic','order')}
    expected={'format_version':2,'kind':'dense-xyz-L3-L4','coder_version':entropy.CODER_VERSION,'histogram_precision':16,'coder_precision':24,'categorical_perfect':False,'arithmetic':ARITHMETIC,'order':'channel-major-row-ascending-v1'}
    if spec!=expected or header['model'] not in MODELS or header['storage'] not in STORAGES:raise ValueError('Unsupported spec')
    entries=header['sections']
    if len(entries)!=len(NAMES) or [x['name'] for x in entries]!=list(NAMES) or any(type(x['bytes'])!=int or x['bytes']<0 for x in entries):raise ValueError('Invalid directory')
    if sum(x['bytes'] for x in entries[:len(META_NAMES)])!=m or sum(x['bytes'] for x in entries[len(META_NAMES):])!=p:raise ValueError('Section totals mismatch')
    offset=entropy.PREFIX.size+h;sections={}
    for entry in entries:sections[entry['name']]=data[offset:offset+entry['bytes']];offset+=entry['bytes']
    return header,sections

def decode_data(data):
    check_runtime();started=time.perf_counter();header,s=unpack(data);timing={}
    g=json.loads(s['geometry']);q=json.loads(s['quantization']);i3=json.loads(s['l3.info']);i4=json.loads(s['l4.info'])
    if (g['indexing']!='dense-x-fastest-unpadded' or g['interpolation']!='smoothstep' or g['coordinate_rule']!='float32(v)/float32(fine_scale), OOB zero, no clamp'
        or g['coarse']['level']!=3 or g['fine']['level']!=4 or q['bits']!=8 or q['scope']!='table' or q['shared_by_levels']!=[3,4] or q['rounding']!='nearest-even' or q['reconstruction_dtype']!='float32'):raise ValueError('Invalid geometry/quantization')
    for name,info in [('coarse',i3),('fine',i4)]:
        level=g[name];r=level['lookup_resolution'];n=level['rows'];scale=np.asarray(level['scale'],np.float32)
        if (len(r)!=3 or any(type(x)!=int or x<2 for x in r) or np.prod(r)!=n or not 1<=n<=250000 or info['shape']!=[n,2]
            or level['offset_end']-level['offset_start']!=n or scale.shape!=(3,) or not np.isfinite(scale).all() or np.any(scale<=0) or (np.ceil(scale).astype(int)+1).tolist()!=r):raise ValueError('Invalid dense shape/scale')
    meta={'coarse':dict(g['coarse'],quantization=q),'fine':g['fine']}
    if i3['model']!='iid' or i3['storage']!='dense_u32':raise ValueError('Shared L3 codec mismatch')
    if g['coarse']['offset_end']!=g['fine']['offset_start']:raise ValueError('Nonadjacent levels')
    t=time.perf_counter();m3=HistogramModel.from_bytes(s['l3.model']);coarse=entropy.decode_symbols(s['l3.payload'],g['coarse']['rows'],m3)
    timing['entropy_decode_l3_seconds']=time.perf_counter()-t
    if sha(coarse.tobytes())!=i3['symbols_sha256'] or sha(m3.freq.tobytes())!=i3['model_sha256']:raise ValueError('L3 symbol/model integrity')
    from research.grid4d.codec import dequantize
    dequantize(coarse,q)  # Quantization metadata must be valid even for IID/Boundary.
    model=header['model'];C=MODELS[model]
    expected=112 if model=='spatial8' else 0
    if len(s['thresholds'])!=expected:raise ValueError('Threshold size mismatch')
    edges=np.frombuffer(s['thresholds'],dtype='<f8').reshape(2,7).copy() if expected else None
    t=time.perf_counter();f,omitted=deserialize(s['l4.model'],header['storage'],C);timing['model_deserialize_seconds']=time.perf_counter()-t
    if sha(f.tobytes())!=i4['model_sha256']:raise ValueError('Model integrity')
    t=time.perf_counter();c,inside,x=classes(meta,coarse,model,edges);timing['context_restore_seconds']=time.perf_counter()-t
    if sha(c.tobytes())!=i4['class_sha256']:raise ValueError('Context classes integrity')
    for ch,cls in np.argwhere(omitted):
        if np.any(c[:,ch]==cls):raise ValueError('Omitted reachable class')
    t=time.perf_counter();fine=entropy.decode_indexed(s['l4.payload'],c,f);timing['entropy_decode_l4_seconds']=time.perf_counter()-t
    if sha(fine.tobytes())!=i4['symbols_sha256']:raise ValueError('L4 symbol integrity')
    timing['decode_total_seconds']=time.perf_counter()-started
    return {'coarse':coarse,'fine':fine,'classes':c,'inside':inside,'masses3':m3.freq,'masses4':f,'edges':edges,'context':x},timing

def decode(path,output,audited=True):
    path=Path(path).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    if audited:
        from .audit import install
        reads,blocked=install([path],output)
    else:reads=[];blocked=[]
    arrays,timing=decode_data(path.read_bytes())
    for name in ('coarse','fine','classes','inside','masses3','masses4'):np.save(output/(name+'.npy'),arrays[name],allow_pickle=False)
    if arrays['edges'] is not None:np.save(output/'edges.npy',arrays['edges'],allow_pickle=False)
    report={'status':'PASS','timing':timing,'allowed_data_reads':sorted(set(reads)),'blocked_reads':blocked,'pid':__import__('os').getpid(),
        'coarse_shape':list(arrays['coarse'].shape),'fine_shape':list(arrays['fine'].shape),'classes_sha256':sha(arrays['classes'].tobytes()),
        'standalone':True,'model_masses_sha256':sha(arrays['masses4'].tobytes())}
    write(output/'decoder.json',report);return report
