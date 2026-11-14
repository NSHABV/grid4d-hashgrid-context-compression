"""Fresh-process decoding: the only experiment data input is one .bin."""
import argparse, json, os, sys, time
from pathlib import Path
import numpy as np
# Load only public software/version metadata before the data-read guard.
from research.experiment_bench.hashed_pair import engine
from research.hashgrid_analysis.hashed_context.runtime import write_json, peak_rss_mib

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    p.add_argument('--probe-forbidden',nargs='*')
    p.add_argument('--probe-write-forbidden',nargs='*');a=p.parse_args()
    source=Path(a.input).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[3];reads=[];blocked=[];blocked_writes=[];public=[];sys.dont_write_bytecode=True
    def audit(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes)):return
        path=Path(os.fsdecode(args[0])).resolve();mode,flags=args[1:3]
        reading=(mode is None and not flags&os.O_WRONLY) or (isinstance(mode,str) and ('r' in mode or '+' in mode))
        writing=bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)) or (
            isinstance(mode,str) and any(mark in mode for mark in ('w','a','x','+')))
        if writing and not path.is_relative_to(out):
            blocked_writes.append(str(path));raise PermissionError('Write outside decoder output: '+str(path))
        if not reading:return
        if path==source:reads.append(str(path));return
        if path.suffix in ('.py','.pyc','.pyd','.so','.dll') and any(path.is_relative_to(d) for d in
                (root/'research',root/'.tools/hashed-pair-deps',Path(sys.prefix),Path(sys.base_prefix))):
            public.append(str(path));return
        blocked.append(str(path));raise PermissionError('Forbidden decoder data read: '+str(path))
    sys.addaudithook(audit)
    if a.probe_forbidden is not None or a.probe_write_forbidden is not None:
        for path in a.probe_forbidden or []:
            try:Path(path).read_bytes()
            except PermissionError:continue
            raise AssertionError('Forbidden file readable: '+path)
        for path in a.probe_write_forbidden or []:
            try:
                with Path(path).open('r+b'):pass
            except PermissionError:pass
            else:raise AssertionError('Forbidden read/write file open allowed: '+path)
            try:
                descriptor=os.open(path,os.O_RDWR)
            except PermissionError:pass
            else:
                os.close(descriptor);raise AssertionError('Forbidden O_RDWR file open allowed: '+path)
        assert len(blocked)==len(a.probe_forbidden or [])
        assert len(blocked_writes)==2*len(a.probe_write_forbidden or [])
        write_json(out/'read-audit.json',{'status':'PASS','negative_probes':len(blocked),
            'negative_write_probes':len(blocked_writes),'blocked_reads':blocked,'blocked_writes':blocked_writes,
            'scope':'Python open audit; not an OS security sandbox'})
        return
    from .format import decode_bytes, MAX_CONTAINER_BYTES
    start=time.perf_counter();cpu=time.process_time()
    with source.open('rb') as handle:data=handle.read(MAX_CONTAINER_BYTES+1)
    if len(data)>MAX_CONTAINER_BYTES:raise ValueError('Container file exceeds bounded V3 maximum')
    coarse_symbols,fine_symbols,classes,detail=decode_bytes(data)
    for name,array in [('coarse_symbols',coarse_symbols),('fine_symbols',fine_symbols),('classes',classes)]:
        with (out/(name+'.npy')).open('xb') as f:np.save(f,array,allow_pickle=False)
    assert set(reads)=={str(source)} and not blocked and not blocked_writes
    detail.update(pid=os.getpid(),allowed_data_reads=sorted(set(reads)),blocked_reads=blocked,blocked_writes=blocked_writes,
        public_code_reads=sorted(set(public)),checkpoint_read=False,targets_read=False,parent_contexts_read=False,
        scope='Python open audit; not an OS security sandbox',peak_rss_mib=peak_rss_mib(),
        body_with_io_seconds=time.perf_counter()-start,cpu_with_io_seconds=time.process_time()-cpu,
        python=sys.version,numpy=np.__version__)
    write_json(out/'read-audit.json',detail)
    print(json.dumps({'status':'PASS','model':detail['model'],'peak_rss_mib':detail['peak_rss_mib']}))

if __name__=='__main__':main()
