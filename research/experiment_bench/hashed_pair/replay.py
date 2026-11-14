"""Fresh-process decoding: the only experiment data input is one .bin."""
import argparse, json, os, sys, time
from pathlib import Path
import numpy as np
# Load only public software/version metadata before the data-read guard.
from . import engine
from research.hashgrid_analysis.hashed_context.runtime import write_json, peak_rss_mib

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    p.add_argument('--probe-forbidden',nargs='*');a=p.parse_args()
    source=Path(a.input).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[3];reads=[];blocked=[];public=[];sys.dont_write_bytecode=True
    def audit(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes)):return
        path=Path(os.fsdecode(args[0])).resolve();mode,flags=args[1:3]
        reading=(mode is None and not flags&os.O_WRONLY) or (isinstance(mode,str) and ('r' in mode or '+' in mode))
        if not reading:
            if not path.is_relative_to(out):raise PermissionError('Write outside decoder output: '+str(path))
            return
        if path==source:reads.append(str(path));return
        if path.suffix in ('.py','.pyc','.pyd','.so','.dll') and any(path.is_relative_to(d) for d in
                (root/'research',root/'.tools/hashed-pair-deps',Path(sys.prefix),Path(sys.base_prefix))):
            public.append(str(path));return
        blocked.append(str(path));raise PermissionError('Forbidden decoder data read: '+str(path))
    sys.addaudithook(audit)
    if a.probe_forbidden is not None:
        for path in a.probe_forbidden:
            try:Path(path).read_bytes()
            except PermissionError:continue
            raise AssertionError('Forbidden file readable: '+path)
        assert len(blocked)==len(a.probe_forbidden)
        write_json(out/'read-audit.json',{'status':'PASS','negative_probes':len(blocked),'blocked_reads':blocked})
        return
    from .format import decode_bytes
    start=time.perf_counter();cpu=time.process_time()
    q4,q5,classes,detail=decode_bytes(source.read_bytes())
    for name,array in [('q4',q4),('q5',q5),('classes',classes)]:
        with (out/(name+'.npy')).open('xb') as f:np.save(f,array,allow_pickle=False)
    assert set(reads)=={str(source)} and not blocked
    detail.update(pid=os.getpid(),allowed_data_reads=sorted(set(reads)),blocked_reads=blocked,
        public_code_reads=sorted(set(public)),checkpoint_read=False,targets_read=False,parent_contexts_read=False,
        scope='Python open audit; not an OS security sandbox',peak_rss_mib=peak_rss_mib(),
        body_with_io_seconds=time.perf_counter()-start,cpu_with_io_seconds=time.process_time()-cpu,
        python=sys.version,numpy=np.__version__)
    write_json(out/'read-audit.json',detail)
    print(json.dumps({'status':'PASS','model':detail['model'],'peak_rss_mib':detail['peak_rss_mib']}))

if __name__=='__main__':main()
