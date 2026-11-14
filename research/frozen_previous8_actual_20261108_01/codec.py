"""Isolated spatial measurement container; existing constriction core, exact CDFs."""
import sys,json,hashlib,struct,time,os
from pathlib import Path
R=Path(__file__).resolve().parent;ROOT=R.parents[1]
H=ROOT/'research/context_compression_headroom_20261107_01'
sys.path[:0]=[str(ROOT/'.tools/hashed-pair-deps'),str(H),str(ROOT)]
import numpy as np,constriction
import model_side,baselines
from input_sources import canonical,canonical_dequantize,check
MAGIC=b'G4DPREV1';PREFIX=struct.Struct('<8sI')
CONTRACT={'version':1,'coder':'constriction-0.4.2-range','categorical_perfect':True,'CDF':'uint16-mass cumulative *256 at precision24','stream_order':'channel0 then channel1, each ascending slots','streams_per_range_level':2,'block_slots':4096,'context_reset':'start PMF every4096; no entropy-stream reset','thresholds':'searchsorted right; duplicates retained','envelope_order':'container channel-major overrides legacy descriptive code_order only','mode_levels':list(range(6,11))}
def digest(b):return hashlib.sha256(b).hexdigest()
def prepare_model(raw,mode,level,n):
    t=time.perf_counter();m,th,sp,rc,storage=model_side.deserialize(raw)
    check(mode in ('I','P'),'Range mode')
    family='IID' if mode=='I' else 'PREVIOUS8'
    check(sp['family']==family and sp['level']==level and sp['slots']==n and sp['channels']==2,'Model routing')
    check(sp['alphabet']==256 and sp['mass_total']==65536 and sp['mass_precision']==16,'Mass contract')
    check(rc==([1,1] if mode=='I' else [9,9]),'Class mapping')
    if mode=='I':check(th=={} and 'threshold_rule' not in sp,'IID extra threshold fields');edges=None
    else:
        check(set(th)=={'edges'},'Threshold keys');edges=np.asarray(th['edges'])
        check(edges.shape==(2,7) and np.isfinite(edges).all() and (np.diff(edges,axis=1)>=0).all() and (edges>=0).all() and (edges<=255).all(),'Threshold bounds/order')
        check(sp['block_slots']==4096 and sp['first_slot']=='separate IID row fitted on all fit symbols in channel; reset each4096 slots','Reset contract')
    models=[constriction.stream.model.Categorical(row.astype(np.float64)/65536,perfect=True) for row in m]
    lut=np.zeros((2,256),np.uint8)
    if mode=='P':
        for ch in range(2):lut[ch]=1+np.searchsorted(edges[ch],np.arange(256),side='right')+9*ch
    else:lut[1].fill(1)
    return (m,rc,models,lut),time.perf_counter()-t
def encode_channel(q,ch,mode,prepared):
    m,rc,models,lut=prepared;e=constriction.stream.queue.RangeEncoder();ids=np.empty(len(q),np.uint8)
    startrow=0 if ch==0 else rc[0];prev=0;t=time.perf_counter()
    for i,v in enumerate(q):
        idx=startrow if mode=='I' or i%4096==0 else int(lut[ch,prev]);ids[i]=idx
        e.encode(int(v),models[idx]);prev=int(v)
    pure=time.perf_counter()-t;t=time.perf_counter();data=e.get_compressed().astype('<u4').tobytes();termination=time.perf_counter()-t
    return data,ids,pure,termination
def decode_channel(data,n,ch,mode,prepared):
    check(bool(data) and len(data)%4==0,'Range payload alignment')
    _,rc,models,lut=prepared;d=constriction.stream.queue.RangeDecoder(np.frombuffer(data,dtype='<u4').copy())
    q=np.empty(n,np.uint8);ids=np.empty(n,np.uint8);startrow=0 if ch==0 else rc[0];prev=0;t=time.perf_counter()
    for i in range(n):
        idx=startrow if mode=='I' or i%4096==0 else int(lut[ch,prev]);ids[i]=idx
        v=int(d.decode(models[idx]));check(0<=v<=255,'Decoded domain');q[i]=v;prev=v
    return q,ids,time.perf_counter()-t
def assemble(metadata,parts):
    h=canonical(metadata);body=PREFIX.pack(MAGIC,len(h))+h+b''.join(parts)
    return body+hashlib.sha256(body).digest()
def parse(data):
    check(44<=len(data)<=32*2**20,'File bound');check(hashlib.sha256(data[:-32]).digest()==data[-32:],'Integrity')
    magic,size=PREFIX.unpack_from(data);check(magic==MAGIC and 0<size<=65536,'Prefix')
    raw=data[12:12+size];m=json.loads(raw);check(canonical(m)==raw,'Canonical JSON')
    check(set(m)=={'contract','baseline_metadata','mode','levels'},'Metadata fields');check(m['contract']==CONTRACT,'Unknown contract')
    baselines.validate_metadata(m['baseline_metadata']);check(m['baseline_metadata']['codec']=='XZ6' and m['baseline_metadata']['layout']=='slot-major','XZ contract')
    check(m['mode'] in ('X','I','P') and len(m['levels'])==16,'Mode/levels');pos=12+size;parts=[]
    offsets=m['baseline_metadata']['source_metadata']['offsets']
    for l,d in enumerate(m['levels']):
        check(set(d)=={'level','codec','rows','model_bytes','payload_bytes','symbols_sha256'},'Descriptor keys')
        expected=m['mode'] if l in range(6,11) else 'X'
        check(d['level']==l and d['codec']==expected and d['rows']==offsets[l+1]-offsets[l],'Level routing/count')
        check(type(d['model_bytes']) is int and 0<=d['model_bytes']<=65536,'Model bounds')
        lengths=d['payload_bytes'];check(isinstance(lengths,list) and len(lengths)==(1 if expected=='X' else 2),'Stream count')
        check(all(type(v)is int and 0<v<=2**21 for v in lengths),'Payload bounds')
        check((d['model_bytes']==0)==(expected=='X'),'Missing/unexpected model')
        check(isinstance(d['symbols_sha256'],str) and len(d['symbols_sha256'])==64,'Symbol digest')
        end=pos+d['model_bytes']+sum(lengths);check(end<=len(data)-32,'Truncation')
        model=data[pos:pos+d['model_bytes']];pos+=d['model_bytes'];payload=[]
        for length in lengths:payload.append(data[pos:pos+length]);pos+=length
        parts.append((model,payload))
    check(pos==len(data)-32,'Extra data')
    return m,parts,12+size+32
def decode(data):
    t=time.perf_counter();m,parts,framing=parse(data);parse_seconds=time.perf_counter()-t
    sm=m['baseline_metadata']['source_metadata'];output=np.empty(sm['shape'],np.uint8);records=[]
    qhash=hashlib.sha256();deqhash=hashlib.sha256()
    for l,(model,payloads) in enumerate(parts):
        d=m['levels'][l];mode=d['codec'];n=d['rows'];lo,hi=sm['offsets'][l:l+2];q=output[lo:hi];modeltime=0;pure=0;strict=0;hashes=[]
        if mode=='X':
            t=time.perf_counter();q[:]=np.frombuffer(baselines.decompress(payloads[0],'XZ6',n*2),np.uint8).reshape(n,2);pure=time.perf_counter()-t
        else:
            prepared,modeltime=prepare_model(model,mode,l,n)
            for ch,payload in enumerate(payloads):
                v,ids,dt=decode_channel(payload,n,ch,mode,prepared);q[:,ch]=v;pure+=dt;hashes.append(digest(ids.tobytes()))
                t=time.perf_counter();again,_,_,_=encode_channel(v,ch,mode,prepared);check(again==payload,'Noncanonical/truncated/extra range payload');strict+=time.perf_counter()-t
        t=time.perf_counter();check(digest(q.tobytes())==d['symbols_sha256'],'Exact level hash');qhash.update(q.tobytes());deqhash.update(canonical_dequantize(q,sm['quantizer']).tobytes());strict+=time.perf_counter()-t
        records.append({'level':l,'model_prepare_seconds':modeltime,'pure_decode_seconds':pure,'strict_integrity_reencode_seconds':strict,'context_ids_sha256':hashes})
    check(qhash.hexdigest()==sm['symbols_sha256'],'Full symbols');check(deqhash.hexdigest()==m['baseline_metadata']['canonical_restored_sha256'],'Canonical dequantization')
    return output,{'status':'PASS','levels':records,'parse_seconds':parse_seconds,'symbols_sha256':qhash.hexdigest(),'canonical_dequantization_sha256':deqhash.hexdigest(),'peak_RSS':baselines.peak_rss_bytes(),'mode':m['mode'],'framing_bytes':framing}
def main():
    path=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve();check(not output.exists(),'Output exists');output.mkdir()
    accesses=[]
    # Public modules are loaded above. During decode only the provided archive may be read.
    def audit(event,args):
        if event=='open':
            p,mode,flags=args
            if isinstance(p,(str,bytes)):
                writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and bool(flags & (os.O_WRONLY|os.O_RDWR)))
                if not writing:
                    resolved=Path(p).resolve();check(resolved==path,'Forbidden decoder file read: '+str(resolved));accesses.append(str(resolved))
    sys.addaudithook(audit)
    t=time.perf_counter();data=path.read_bytes();io=time.perf_counter()-t
    q,result=decode(data);t=time.perf_counter()
    with (output/'decoded.npy').open('xb') as f:np.save(f,q,allow_pickle=False)
    result.update(file_read_seconds=io,file_write_seconds=time.perf_counter()-t,data_reads=accesses)
    with (output/'DECODE.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print('DECODE PASS',result['mode'])
if __name__=='__main__':main()
