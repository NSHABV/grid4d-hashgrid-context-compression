"""Fresh-process coarse-only replay of every frozen held-out class specification.

This module never reads parent contexts or fine targets.  The Python audit hook
is an instrumentation guard for this decoder, not an OS security sandbox.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import numpy as np


def class_sha(array):
    """Versioned digest over dtype, shape and C-order bytes (not NPY framing)."""
    array = np.ascontiguousarray(array)
    h = hashlib.sha256()
    h.update(array.dtype.str.encode('ascii'))
    h.update(str(array.shape).encode('ascii'))
    h.update(array.tobytes())
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--specs', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--chunk', type=int, default=4096)
    parser.add_argument('--probe-forbidden', nargs='*')
    args = parser.parse_args()
    bundle = Path(args.bundle).resolve()
    specs_path = Path(args.specs).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[3]
    allowed = {bundle / 'decoder_metadata.json', bundle / 'coarse_symbols.npy', specs_path}
    reads, blocked, public = [], [], []
    sys.dont_write_bytecode = True

    def audit(event, values):
        if event != 'open' or not isinstance(values[0], (str, bytes)):
            return
        path = Path(os.fsdecode(values[0])).resolve()
        mode, flags = values[1], values[2]
        is_read = ((mode is None and not (flags & os.O_WRONLY)) or
                   (isinstance(mode, str) and ('r' in mode or '+' in mode)))
        if not is_read:
            if not path.is_relative_to(output):
                raise PermissionError('Decoder write outside fresh output: ' + str(path))
            return
        if path in allowed:
            reads.append(str(path))
            return
        if (path.suffix in ('.py', '.pyc', '.pyd', '.so') and
                any(path.is_relative_to(p) for p in
                    (root / 'research', Path(sys.prefix), Path(sys.base_prefix)))):
            public.append(str(path))
            return
        blocked.append(str(path))
        raise PermissionError('Forbidden decoder data read: ' + str(path))

    sys.addaudithook(audit)

    def write_json(name, value):
        with (output / name).open('x', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write('\n')

    if args.probe_forbidden is not None:
        for name in args.probe_forbidden:
            try:
                Path(name).read_bytes()
            except PermissionError:
                continue
            raise AssertionError('Forbidden data probe unexpectedly succeeded: ' + name)
        assert len(blocked) == len(args.probe_forbidden)
        write_json('read-audit.json', {
            'status': 'PASS', 'mode': 'negative-read-probes', 'pid': os.getpid(),
            'blocked_reads': blocked, 'probe_count': len(args.probe_forbidden),
            'allowed_data_reads': sorted(set(reads)),
        })
        return

    from research.hashgrid_analysis.hashed_context.core import (
        load_bundle, compute_context, arrays_sha, ARITHMETIC)
    from research.hashgrid_analysis.hashed_context.runtime import peak_rss_mib
    from .core import classify

    started, cpu_started = time.perf_counter(), time.process_time()
    specifications = json.loads(specs_path.read_text(encoding='utf-8'))
    if not isinstance(specifications, list) or not specifications:
        raise ValueError('Expected a nonempty list of frozen context specifications')
    for entry in specifications:
        if (set(entry) != {'id', 'spec'} or
                set(entry['spec']) != {'name', 'C', 'edges'} or
                set(entry['spec']['edges']) != {'primary', 'std'}):
            raise ValueError('Decoder input must contain class rules and thresholds only')
    ids = [entry['id'] for entry in specifications]
    if len(set(ids)) != len(ids) or any(not isinstance(k, str) or not k for k in ids):
        raise ValueError('Specifications require unique, nonempty ids')
    metadata, coarse = load_bundle(bundle)
    contexts = compute_context(metadata, coarse, chunk=args.chunk)
    classes, signatures = {}, {}
    for entry in specifications:
        value = classify(contexts, entry['spec'])
        assert value.dtype == np.uint8 and value.shape == (metadata['fine']['rows'], 2)
        assert np.all(value < entry['spec']['C'])
        classes[entry['id']] = value
        signatures[entry['id']] = class_sha(value)
    context_signature = arrays_sha(contexts)
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **classes)
    payload = buffer.getvalue()
    with (output / 'class_ids.npz').open('xb') as stream:
        stream.write(payload)
    elapsed, cpu_elapsed = time.perf_counter()-started, time.process_time()-cpu_started
    result = {
        'status': 'PASS', 'pid': os.getpid(), 'mode': 'coarse-only-class-replay',
        'context_recomputations': 1, 'chunk': args.chunk,
        'rows': metadata['fine']['rows'], 'channels': 2, 'model_count': len(classes),
        'arithmetic': ARITHMETIC, 'numpy': np.__version__, 'python': sys.version,
        'context_arrays_sha256': context_signature,
        'class_digest_convention': 'sha256(dtype.str + str(shape) + C-order bytes)',
        'class_ids_sha256': signatures,
        'class_npz_sha256': hashlib.sha256(payload).hexdigest(),
        'wall_seconds': elapsed, 'cpu_seconds': cpu_elapsed, 'peak_rss_mib': peak_rss_mib(),
        'allowed_data_reads': sorted(set(reads)), 'blocked_reads': blocked,
        'public_code_reads': sorted(set(public)),
        'checkpoint_read': False, 'fine_targets_read': False, 'parent_contexts_read': False,
        'specifications_contain': 'context rules and transmitted thresholds only; no probabilities or targets',
    }
    assert set(reads) == {str(p) for p in allowed} and not blocked
    write_json('read-audit.json', result)
    print(json.dumps({key: result[key] for key in
                     ('status', 'rows', 'model_count', 'context_recomputations', 'cpu_seconds', 'peak_rss_mib')}))


if __name__ == '__main__':
    main()
