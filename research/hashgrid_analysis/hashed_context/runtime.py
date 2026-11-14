"""Small portable resource/JSON helpers for this diagnostic only."""
import ctypes
import json
import os
from pathlib import Path

def peak_rss_mib():
    if os.name == 'nt':
        class Counters(ctypes.Structure):
            _fields_ = [('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)] + [
                (n,ctypes.c_size_t) for n in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
                'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        c = Counters();c.cb=ctypes.sizeof(c)
        kernel=ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype=ctypes.c_void_p
        api=ctypes.windll.psapi.GetProcessMemoryInfo
        api.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
        if not api(kernel.GetCurrentProcess(),ctypes.byref(c),c.cb):
            raise OSError('Cannot measure peak working set')
        return c.PeakWorkingSetSize/(1<<20)
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024

def write_json(path,value):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')

def save_npz(path,arrays):
    import numpy as np
    with Path(path).open('xb') as f:
        np.savez_compressed(f,**arrays)
