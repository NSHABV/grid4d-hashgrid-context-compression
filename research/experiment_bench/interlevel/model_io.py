"""Exact mass transport; entropy engine remains experiment_bench.entropy."""
import struct
import numpy as np
from research.experiment_bench.models import validate_frequencies,frequencies

STORAGES={'dense_u32':1,'packed_u16':2,'sparse_default_u16':3}
PREFIX=struct.Struct('<4sBBBBH')

def serialize(masses,storage,unreachable=None):
    f=np.asarray(masses);validate_frequencies(f.reshape(-1,256))
    if f.ndim!=3 or f.shape[0]!=2 or f.shape[2]!=256 or f.shape[1] not in (1,2,9):raise ValueError('Invalid model shape')
    C=f.shape[1];data=bytearray(PREFIX.pack(b'HGPM',1,STORAGES[storage],2,C,256))
    if storage=='dense_u32':data.extend(f.astype('<u4').tobytes())
    elif storage=='packed_u16':
        if f.max()>65535:raise ValueError('u16 overflow')
        data.extend(f.astype('<u2').tobytes())
    else:
        unreachable=np.zeros((2,C),bool) if unreachable is None else np.asarray(unreachable,bool)
        if unreachable.shape!=(2,C):raise ValueError('Invalid omission map')
        for ch in range(2):
            for cls in range(C):
                row=f[ch,cls]
                if unreachable[ch,cls]:
                    if not np.all(row==256):raise ValueError('Omitted model must reconstruct uniform masses')
                    data.append(1);continue
                data.append(0);values,counts=np.unique(row,return_counts=True);default=int(values[np.argmax(counts)])
                exceptions=np.flatnonzero(row!=default)
                data.extend(struct.pack('<HH',default,len(exceptions)))
                for symbol in exceptions:data.extend(struct.pack('<BH',int(symbol),int(row[symbol])))
    return bytes(data)

def deserialize(data,storage,C):
    if len(data)<PREFIX.size:raise ValueError('Truncated model header')
    if PREFIX.unpack_from(data)!=(b'HGPM',1,STORAGES[storage],2,C,256):raise ValueError('Invalid model specification')
    if C not in (1,2,9):raise ValueError('Unsupported class count')
    omitted=np.zeros((2,C),bool);offset=PREFIX.size
    if storage in ('dense_u32','packed_u16'):
        dtype='<u4' if storage=='dense_u32' else '<u2';expected=2*C*256*np.dtype(dtype).itemsize
        if len(data)-offset!=expected:raise ValueError('Model length mismatch')
        f=np.frombuffer(data,dtype=dtype,offset=offset).reshape(2,C,256).astype(np.uint32);offset=len(data)
    else:
        f=np.empty((2,C,256),np.uint32)
        for ch in range(2):
            for cls in range(C):
                if offset>=len(data):raise ValueError('Missing sparse row')
                tag=data[offset];offset+=1
                if tag==1:f[ch,cls]=256;omitted[ch,cls]=True;continue
                if tag!=0 or offset+4>len(data):raise ValueError('Invalid sparse row')
                default,n=struct.unpack_from('<HH',data,offset);offset+=4
                if not default or n>256 or offset+3*n>len(data):raise ValueError('Invalid sparse exceptions')
                f[ch,cls]=default;previous=-1
                for _ in range(n):
                    symbol,mass=struct.unpack_from('<BH',data,offset);offset+=3
                    if symbol<=previous or not mass or mass==default:raise ValueError('Noncanonical sparse exception')
                    previous=symbol;f[ch,cls,symbol]=mass
    if offset!=len(data):raise ValueError('Extra model bytes')
    validate_frequencies(f.reshape(-1,256))
    cdf=np.cumsum(f,dtype=np.uint64,axis=2)
    if not np.all(cdf[:,:,-1]==65536):raise ValueError('CDF overflow')
    return f,omitted

def fit(fine,class_ids,C):
    return np.stack([np.stack([frequencies(np.bincount(fine[class_ids[:,ch]==cls,ch],minlength=256)) for cls in range(C)]) for ch in range(2)])
