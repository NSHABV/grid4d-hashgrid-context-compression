import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]

def install(allowed,output):
    allowed={Path(p).resolve() for p in allowed};output=Path(output).resolve();reads=[];blocked=[]
    def hook(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes)):return
        path=Path(os.fsdecode(args[0])).resolve();mode=args[1];flags=args[2]
        if path.is_relative_to(output) and (isinstance(mode,str) and mode.startswith(('w','x')) or flags&(os.O_CREAT|os.O_TRUNC)):return
        is_read=mode is None and not (flags&os.O_WRONLY) or isinstance(mode,str) and ('r' in mode or '+' in mode)
        if not is_read:return
        if path in allowed:reads.append(str(path));return
        # Public interpreter/package files are dependencies, not scene side information.
        if path.is_relative_to(Path(sys.prefix)/'lib') or path.is_relative_to(ROOT/'.tools/bench-python'):return
        if path.suffix in ('.py','.pyc','.so','.pyd') and path.is_relative_to(ROOT/'research'):return
        blocked.append(str(path));raise PermissionError('Forbidden decoder data read: '+str(path))
    sys.addaudithook(hook)
    return reads,blocked
