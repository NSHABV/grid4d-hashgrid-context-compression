"""Causal context interfaces. No probability fitting or entropy decoding."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import numpy as np

BLOCK = 4096


def edges_array(edges, shape):
    e = np.asarray(edges, dtype=np.float64)
    if e.shape != shape or not np.isfinite(e).all() or np.any(np.diff(e, axis=-1) < 0):
        raise ValueError('Invalid transmitted edges')
    return e


def channel_classes(decoded_channel0, edges):
    q0 = np.asarray(decoded_channel0)
    if q0.dtype != np.uint8 or q0.ndim != 1:
        raise ValueError('Only decoded channel0 uint8 is accepted')
    e = edges_array(edges, (7,))
    ids = np.zeros((len(q0), 2), np.uint8)
    ids[:, 1] = 1 + np.searchsorted(e, q0, side='right')
    return ids


class PreviousPrefix:
    """Only two most recently revealed symbols are retained; no future input API."""
    def __init__(self, edges, block=BLOCK):
        self.edges = edges_array(edges, (2, 7))
        if block <= 0: raise ValueError('Invalid block')
        self.block = block; self.position = 0; self.previous = None
        self.awaiting_reveal = False

    def predict(self):
        if self.awaiting_reveal: raise ValueError('Current symbols must be revealed before next prediction')
        self.awaiting_reveal = True
        if self.position % self.block == 0:
            return np.array([0, 9], np.uint8)
        return np.array([1 + np.searchsorted(self.edges[0], self.previous[0], side='right'),
                         10 + np.searchsorted(self.edges[1], self.previous[1], side='right')], np.uint8)

    def reveal(self, decoded_current):
        if not self.awaiting_reveal: raise ValueError('Must predict before seeing current targets')
        x = np.asarray(decoded_current)
        if x.dtype != np.uint8 or x.shape != (2,): raise ValueError('Reveal exactly one decoded pair')
        self.previous = x.copy(); self.position += 1; self.awaiting_reveal = False


def previous_vectorized(q, edges, block=BLOCK):
    """Encoder calculation; independent replay uses the prefix state machine."""
    if q.dtype != np.uint8 or q.ndim != 2 or q.shape[1] != 2: raise ValueError('Bad q')
    e = edges_array(edges, (2, 7)); ids = np.empty(q.shape, np.uint8)
    ids[0] = (0, 9)
    for ch in range(2):
        ids[1:, ch] = ch * 9 + 1 + np.searchsorted(e[ch], q[:-1, ch], side='right')
    ids[::block] = (0, 9)
    return ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('channel', 'previous'))
    parser.add_argument('--edges', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--q0')
    parser.add_argument('--slots', type=int)
    parser.add_argument('--audit', required=True)
    args = parser.parse_args()
    allowed = {str(Path(args.edges).resolve())}
    if args.q0: allowed.add(str(Path(args.q0).resolve()))
    reads = []
    def audit(event, values):
        if event != 'open' or isinstance(values[0], int): return
        filename, mode, flags = values
        writing = (isinstance(mode, str) and any(x in mode for x in 'wax+')) or (flags & (os.O_WRONLY|os.O_RDWR))
        if writing: return
        path = str(Path(filename).resolve())
        if path not in allowed:
            raise PermissionError('Replay read outside explicit inputs: '+path)
        reads.append(path)
    sys.addaudithook(audit)
    edges = np.load(args.edges, allow_pickle=False)
    if args.mode == 'channel':
        # This child receives only q0 and transmitted thresholds, never q1.
        q0 = np.load(args.q0, allow_pickle=False)
        ids = channel_classes(q0, edges)
        with Path(args.output).open('xb') as f: np.save(f, ids, allow_pickle=False)
    else:
        # One prediction is output before the corresponding pair is revealed.
        # Binary protocol: child emits2class bytes; parent sends2decoded bytes.
        if not args.slots or args.slots < 1: raise ValueError('Missing slots')
        if edges.ndim == 2: edges = edges[None, ...]
        if edges.ndim != 3 or edges.shape[1:] != (2,7): raise ValueError('Invalid batched edges')
        states = [PreviousPrefix(e) for e in edges]
        ids = np.empty((args.slots, len(states), 2), np.uint8)
        source, sink = sys.stdin.buffer, sys.stdout.buffer
        for i in range(args.slots):
            for j, state in enumerate(states): ids[i,j] = state.predict()
            sink.write(ids[i].tobytes()); sink.flush()
            pair = source.read(2)
            if len(pair) != 2: raise ValueError('Premature reveal EOF')
            revealed = np.frombuffer(pair, dtype=np.uint8)
            for state in states: state.reveal(revealed)
        if source.read(1): raise ValueError('Unexpected reveals')
        with Path(args.output).open('xb') as f: np.save(f, ids, allow_pickle=False)
    with Path(args.audit).open('x', encoding='utf-8') as f:
        json.dump({'status':'PASS','read_files':sorted(set(reads)), 'mode':args.mode,
                   'future_targets_file_access':False, 'checkpoint_access':False,
                   'prefix_protocol':'Predict all seed classes before parent reveals this slot; block resets4096',
                   'scope':'Trusted Python public replay; explicit file allowlist; not OS sandbox'},f,indent=2)


def _read_exact(stream, count):
    chunks=[]; size=0
    while size < count:
        block=stream.read(count-size)
        if not block: raise RuntimeError('Replay child exited before prediction')
        chunks.append(block); size += len(block)
    return b''.join(chunks)


def prefix_process(q, edges, output, *, max_slots=None):
    """External validator owns q; independent child receives each target after predicting."""
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    edgefile=output/'transmitted_edges.npy'
    with edgefile.open('xb') as f: np.save(f,edges,allow_pickle=False)
    n=len(q) if max_slots is None else min(len(q),max_slots)
    count=edges.shape[0] if edges.ndim==3 else 1
    command=[sys.executable,'-B',str(Path(__file__).resolve()),'previous','--edges',str(edgefile),
             '--slots',str(n),'--output',str(output/'classes.npy'),'--audit',str(output/'ACCESS.json')]
    started=time.perf_counter()
    with (output/'stderr.log').open('xb') as errors:
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors)
        predicted=np.empty((n,count,2),np.uint8)
        try:
            for slot in range(n):
                predicted[slot]=np.frombuffer(_read_exact(process.stdout,2*count),dtype=np.uint8).reshape(count,2)
                process.stdin.write(q[slot].tobytes()); process.stdin.flush()
            process.stdin.close()
            if process.stdout.read(1): raise RuntimeError('Unexpected replay output')
            code=process.wait(timeout=30)
            if code: raise RuntimeError('Replay child failed; original stderr saved')
        except BaseException:
            process.kill(); process.wait(); raise
    actual=np.load(output/'classes.npy',allow_pickle=False)
    if not np.array_equal(actual,predicted): raise RuntimeError('Written/streamed classes mismatch')
    record={'status':'PASS','slots':n,'seeds':count,'seconds':time.perf_counter()-started,
            'classes_sha256':hashlib.sha256(actual.tobytes()).hexdigest(),
            'command':command,'read_policy':'edges-only file access; each current pair revealed only after all predictions'}
    with (output/'RESULT.json').open('x',encoding='utf-8') as f: json.dump(record,f,indent=2)
    return actual,record


def replay_level(q, level_directory):
    """Exactly compare three seed CHANNEL8/PREVIOUS8 class arrays in fresh processes."""
    base=Path(level_directory); replay=base/'context_replay'; replay.mkdir(exist_ok=False)
    q0file=replay/'decoded_channel0.npy'
    with q0file.open('xb') as f: np.save(f,q[:,0],allow_pickle=False)
    records=[]
    for seed in (0,1,2):
        model=base/f'seed{seed}'/'CHANNEL8'; output=replay/f'channel_seed{seed}.npy'
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'channel','--q0',str(q0file),
                 '--edges',str(model/'thresholds.npy'),'--output',str(output),
                 '--audit',str(replay/f'channel_seed{seed}_ACCESS.json')]
        started=time.perf_counter()
        with (replay/f'channel_seed{seed}.stderr.log').open('xb') as err:
            subprocess.run(command,check=True,stdout=subprocess.DEVNULL,stderr=err)
        actual=np.load(output,allow_pickle=False)
        expected=np.load(model/'classes.npy',mmap_mode='r',allow_pickle=False)
        if not np.array_equal(actual,expected): raise RuntimeError('CHANNEL8 decoder class mismatch')
        records.append({'family':'CHANNEL8','seed':seed,'status':'EXACT','seconds':time.perf_counter()-started,
                        'classes_sha256':hashlib.sha256(actual.tobytes()).hexdigest(),'command':command})
    edges=np.stack([np.load(base/f'seed{s}'/'PREVIOUS8/thresholds.npy',allow_pickle=False) for s in (0,1,2)])
    actual,record=prefix_process(q,edges,replay/'previous_all_seeds')
    for seed in (0,1,2):
        expected=np.load(base/f'seed{seed}'/'PREVIOUS8/classes.npy',mmap_mode='r',allow_pickle=False)
        if not np.array_equal(actual[:,seed,:],expected): raise RuntimeError('PREVIOUS8 decoder class mismatch')
    records.append({'family':'PREVIOUS8','status':'EXACT','seeds':[0,1,2],**record})
    result={'status':'PASS','allocated_slots':len(q),'records':records,'no_context_bitstream_claim':True}
    with (replay/'COMPLETE.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    return result


if __name__ == '__main__':
    main()
