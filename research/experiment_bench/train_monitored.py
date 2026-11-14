"""Delegate to the Phase1 loss checker and sample total GPU memory separately."""
import json
import runpy
import subprocess
import sys
import threading
import time
from pathlib import Path

root = Path(__file__).resolve().parents[2]
record = Path(sys.argv[1])
stop = threading.Event()
samples = []


def monitor():
    start = time.perf_counter()
    while not stop.is_set():
        try:
            text = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.used,memory.total,temperature.gpu',
                '--format=csv,noheader,nounits'], text=True, timeout=4).strip()
            used, total, temperature = map(float, text.splitlines()[0].split(','))
            samples.append({'elapsed_seconds': time.perf_counter()-start, 'device_used_mib': used,
                            'device_total_mib': total, 'temperature_c': temperature})
        except Exception as error:
            samples.append({'elapsed_seconds': time.perf_counter()-start, 'error': str(error)})
        record.with_name(record.stem + '-gpu.json').write_text(json.dumps(samples))
        stop.wait(5)


record.parent.mkdir(parents=True, exist_ok=True)
thread = threading.Thread(target=monitor, daemon=True)
thread.start()
try:
    runpy.run_path(str(root / 'research/audit_entrypoint.py'), run_name='__main__')
finally:
    stop.set()
    thread.join(timeout=5)
    record.with_name(record.stem + '-gpu.json').write_text(json.dumps(samples, indent=2) + '\n')
