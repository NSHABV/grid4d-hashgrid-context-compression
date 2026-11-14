"""Fresh decoder: one geometry JSON is the only allowed data input."""
import argparse,json,os,sys,time
from pathlib import Path
import numpy as np
from .geometry import compute_geometry
from research.hashgrid_analysis.hashed_context.runtime import write_json,save_npz,peak_rss_mib

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--spec',required=True);ap.add_argument('--output',required=True)
    ap.add_argument('--chunk',type=int,default=4096);ap.add_argument('--probe',nargs='*');a=ap.parse_args()
    spec=Path(a.spec).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    reads=[];blocked=[];code=[];root=Path(__file__).resolve().parents[3];sys.dont_write_bytecode=True
    def audit(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes)):return
        p=Path(os.fsdecode(args[0])).resolve();mode,flags=args[1],args[2]
        reading=(mode is None and not flags&os.O_WRONLY) or (isinstance(mode,str) and ('r' in mode or '+' in mode))
        if not reading:
            if not p.is_relative_to(out):raise PermissionError('Output only')
            return
        if p==spec:reads.append(str(p));return
        if p.suffix in ('.py','.pyc','.pyd','.so') and any(p.is_relative_to(d) for d in (root/'research',Path(sys.prefix),Path(sys.base_prefix))):
            code.append(str(p));return
        blocked.append(str(p));raise PermissionError('Forbidden data: '+str(p))
    sys.addaudithook(audit)
    if a.probe is not None:
        for p in a.probe:
            try:Path(p).read_bytes()
            except PermissionError:continue
            raise AssertionError('Forbidden read succeeded')
        assert len(blocked)==len(a.probe)
        write_json(out/'read-audit.json',{'status':'PASS','blocked_reads':blocked,'probe_count':len(blocked)});return
    t=time.perf_counter();cpu=time.process_time();metadata=json.loads(spec.read_text(encoding='utf-8'))
    assert set(metadata)=={'version','fine','hash','geometry_convention'}
    data=compute_geometry(metadata,chunk=a.chunk);save_npz(out/'geometry_classes.npz',data)
    assert reads==[str(spec)] and not blocked
    write_json(out/'read-audit.json',{'status':'PASS','pid':os.getpid(),'data_reads':reads,'blocked_reads':blocked,
        'public_code_reads':code,'coarse_values_read':False,'fine_targets_read':False,'checkpoint_read':False,
        'wall_seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-cpu,'peak_rss_mib':peak_rss_mib(),
        'chunk':a.chunk,'scope':'Python open audit, not OS sandbox'})
if __name__=='__main__':main()
