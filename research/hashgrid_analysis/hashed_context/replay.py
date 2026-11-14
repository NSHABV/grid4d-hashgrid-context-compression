"""Fresh CPU decoder replay; strict data-read allowlist, no checkpoint/targets."""
import argparse
import importlib
import json
import os
from pathlib import Path
import sys
import time
import zipfile
import numpy as np

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--bundle',required=True);p.add_argument('--output',required=True)
    p.add_argument('--chunk',type=int,default=4096)
    p.add_argument('--probe-forbidden',nargs='*')
    args=p.parse_args()
    bundle=Path(args.bundle).resolve();out=Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[3]
    allowed={bundle/'decoder_metadata.json',bundle/'coarse_symbols.npy'}
    reads=[];blocked=[];public=[]
    def hook(event,values):
        if event!='open' or not isinstance(values[0],(str,bytes)):
            return
        path=Path(os.fsdecode(values[0])).resolve();mode=values[1];flags=values[2]
        is_read=(mode is None and not(flags&os.O_WRONLY)) or (isinstance(mode,str) and ('r' in mode or '+' in mode))
        if not is_read:
            if not path.is_relative_to(out):
                raise PermissionError('Decoder write outside fresh output: '+str(path))
            return
        if path in allowed:
            reads.append(str(path));return
        if (path.suffix in ('.py','.pyc','.pyd','.so') and
            any(path.is_relative_to(d) for d in (root/'research',Path(sys.prefix),Path(sys.base_prefix)))):
            public.append(str(path));return
        blocked.append(str(path));raise PermissionError('Forbidden decoder data read: '+str(path))
    sys.addaudithook(hook)
    if args.probe_forbidden is not None:
        for name in args.probe_forbidden:
            try:
                Path(name).read_bytes()
            except PermissionError:
                pass
            else:
                raise AssertionError('Forbidden probe unexpectedly succeeded')
        (out/'read-audit.json').write_text(json.dumps({'status':'PASS','mode':'negative-read-probes',
            'blocked_reads':blocked,'probe_count':len(args.probe_forbidden)},indent=2)+'\n',encoding='utf-8')
        return
    from .core import load_bundle,compute_context,arrays_sha
    from .runtime import peak_rss_mib,save_npz,write_json
    started=time.perf_counter();cpu=time.process_time()
    meta,q=load_bundle(bundle)
    arrays=compute_context(meta,q,chunk=args.chunk)
    signature=arrays_sha(arrays)
    elapsed=time.perf_counter()-started;cpu_elapsed=time.process_time()-cpu
    save_npz(out/'contexts.npz',arrays)
    result={'status':'PASS','pid':os.getpid(),'chunk':args.chunk,'arrays_sha256':signature,
        'wall_seconds':elapsed,'cpu_seconds':cpu_elapsed,'peak_rss_mib':peak_rss_mib(),
        'allowed_data_reads':sorted(set(reads)),'blocked_reads':blocked,
        'public_code_reads':sorted(set(public)), 'checkpoint_read':False,'fine_targets_read':False,
        'python':sys.version,'numpy':np.__version__,'rows':len(arrays['slot_index'])}
    assert set(result['allowed_data_reads'])=={str(x) for x in allowed} and not blocked
    assert result['peak_rss_mib']<1024
    write_json(out/'read-audit.json',result)
    print(json.dumps({k:result[k] for k in ('status','chunk','rows','arrays_sha256','cpu_seconds','peak_rss_mib')}))

if __name__=='__main__':
    main()
