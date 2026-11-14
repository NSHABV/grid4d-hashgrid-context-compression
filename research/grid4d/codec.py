"""Versioned raw tensor interchange and scalar quantization (no entropy coder)."""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

KEYS = tuple(f'{g}_encoding.embeddings' for g in ('xyz', 'xyt', 'yzt', 'xzt'))
BUFFERS = ('offsets', 'base_resolution', 'per_level_scale')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def load_checkpoint(path):
    states = torch.load(path, map_location='cpu', weights_only=True)
    if not isinstance(states, tuple) or len(states) != 2:
        raise ValueError('Expected (grid state_dict, network state_dict)')
    for key in KEYS:
        t = states[0][key]
        if t.dtype != torch.float32 or t.ndim != 2 or not torch.isfinite(t).all():
            raise ValueError(f'Invalid embeddings: {key}')
    return states


def validate_grid(meta):
    shape, offsets = meta['shape'], meta['offsets']
    if (len(shape) != 2 or shape[1] != meta['feature_dimension'] or
            len(offsets) != meta['levels'] + 1 or offsets[0] != 0 or
            offsets[-1] != shape[0] or any(b <= a for a, b in zip(offsets, offsets[1:])) or
            np.diff(offsets).tolist() != meta['table_rows_per_level'] or
            np.prod(shape) != meta['scalar_count'] or meta['bytes'] != meta['scalar_count'] * 4):
        raise ValueError('Invalid level structure')
    for field in ('allocation_resolutions', 'cuda_lookup_resolutions'):
        if len(meta[field]) != meta['levels'] or any(len(r) != 3 or min(r) < 1 for r in meta[field]):
            raise ValueError('Invalid resolution metadata')


def _save_array(folder, name, array):
    path = folder / name
    array.tofile(path)
    return {'file': name, 'dtype': array.dtype.str, 'shape': list(array.shape),
            'bytes': path.stat().st_size, 'sha256': sha(path)}


def _read_array(folder, record):
    # File names cannot escape the interchange directory.
    name = record['file']
    if Path(name).name != name or '/' in name or '\\' in name:
        raise ValueError('Unsafe payload path')
    path = folder / name
    dtype = np.dtype(record['dtype'])
    expected = int(np.prod(record['shape'])) * dtype.itemsize
    if path.stat().st_size != expected or expected != record['bytes'] or sha(path) != record['sha256']:
        raise ValueError('Payload length/hash mismatch')
    return np.fromfile(path, dtype=dtype).reshape(record['shape'])


def export_lossless(checkpoint, runtime_path, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    grid, _ = load_checkpoint(checkpoint)
    runtime = json.loads(Path(runtime_path).read_text())
    if runtime['checkpoint_sha256'] != sha(checkpoint):
        raise ValueError('Runtime metadata belongs to another checkpoint')
    manifest = {'version': 1, 'kind': 'lossless-float32', 'source_sha256': sha(checkpoint),
                'runtime_sha256': sha(runtime_path), 'grid_args': runtime['grid_args'],
                'network_args': runtime['network_args'], 'grids': {}}
    for key in KEYS:
        meta = copy.deepcopy(runtime['trainable_parameters'][key])
        validate_grid(meta)
        if meta['shape'] != list(grid[key].shape):
            raise ValueError('Checkpoint shape mismatch')
        prefix = key.split('.')[0]
        meta['buffers'] = {}
        for buf in BUFFERS:
            tensor = grid[f'{prefix}.{buf}']
            field = {'offsets': 'offsets', 'base_resolution': 'base_resolution',
                     'per_level_scale': 'per_level_scale'}[buf]
            if tensor.tolist() != meta[field]:
                raise ValueError('Checkpoint buffer/runtime mismatch')
            array = tensor.numpy().astype('<i4' if buf == 'offsets' else '<f4')
            meta['buffers'][buf] = _save_array(folder, f'{prefix}.{buf}.bin', array)
        meta['payload'] = _save_array(folder, f'{prefix}.f32.bin', grid[key].numpy().astype('<f4'))
        manifest['grids'][key] = meta
    write_json(folder / 'manifest.json', manifest)
    return manifest


def quantize(values, bits):
    """Min/max affine quantization; float64 arithmetic, round-to-nearest-even."""
    if bits not in (8, 12, 16):
        raise ValueError('Supported bits: 8, 12, 16')
    x = np.asarray(values)
    if x.size == 0 or x.dtype != np.float32 or not np.isfinite(x).all():
        raise ValueError('Expected nonempty finite float32 array')
    lo, hi = float(x.min()), float(x.max())
    maximum = (1 << bits) - 1
    step = (hi - lo) / maximum
    dtype = np.uint8 if bits == 8 else np.uint16
    if hi == lo:
        codes = np.zeros(x.shape, dtype=dtype)
    else:
        codes = np.clip(np.rint((x.astype(np.float64) - lo) / step), 0, maximum).astype(dtype)
    return codes, {'bits': bits, 'min': lo, 'max': hi, 'step': step,
                   'rounding': 'nearest-even', 'reconstruction_dtype': 'float32'}


def dequantize(codes, params):
    bits = params['bits']
    lo, hi, step = params['min'], params['max'], params['step']
    if (bits not in (8, 12, 16) or not np.isfinite([lo, hi, step]).all() or hi < lo or
            step != (hi - lo) / ((1 << bits) - 1) or
            not np.issubdtype(codes.dtype, np.integer) or codes.size == 0 or
            codes.min() < 0 or codes.max() > (1 << bits) - 1):
        raise ValueError('Invalid quantization data')
    if step == 0 and np.any(codes != 0):
        raise ValueError('Constant array must have zero symbols')
    return np.clip(lo + codes.astype(np.float64) * step, lo, hi).astype(np.float32)


def export_quantized(lossless_folder, folder, bits, scope):
    if scope not in ('table', 'level'):
        raise ValueError('scope must be table or level')
    original, _, manifest = import_tables(lossless_folder)
    result = copy.deepcopy(manifest)
    result.update(kind='uniform-quantized', bits=bits, scope=scope)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    for key, meta in result['grids'].items():
        x = original[key].numpy()
        slices = [(0, x.shape[0])] if scope == 'table' else list(zip(meta['offsets'], meta['offsets'][1:]))
        codes = np.empty(x.shape, dtype=np.uint8 if bits == 8 else '<u2')
        meta['quantization'] = []
        for start, end in slices:
            codes[start:end], params = quantize(x[start:end], bits)
            meta['quantization'].append({'row_start': start, 'row_end': end, **params})
        prefix = key.split('.')[0]
        meta['payload'] = _save_array(folder, f'{prefix}.u{8 if bits == 8 else 16}.bin', codes)
        for buf, record in meta['buffers'].items():
            array = _read_array(Path(lossless_folder), record)
            meta['buffers'][buf] = _save_array(folder, record['file'], array)
    write_json(folder / 'manifest.json', result)
    return result


def import_tables(folder):
    """Standalone decoder: only payloads and manifest, never source embeddings."""
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest['version'] != 1 or set(manifest['grids']) != set(KEYS):
        raise ValueError('Unsupported format or grid keys')
    tables, buffers = {}, {}
    for key in KEYS:
        meta = manifest['grids'][key]
        validate_grid(meta)
        array = _read_array(folder, meta['payload'])
        if list(array.shape) != meta['shape']:
            raise ValueError('Payload shape mismatch')
        if manifest['kind'] == 'lossless-float32':
            if array.dtype != np.dtype('<f4'):
                raise ValueError('Lossless payload must be float32')
            restored = array
        elif manifest['kind'] == 'uniform-quantized':
            expected_slices = ([(0, meta['shape'][0])] if manifest['scope'] == 'table'
                               else list(zip(meta['offsets'], meta['offsets'][1:])))
            actual_slices = [(p['row_start'], p['row_end']) for p in meta['quantization']]
            if expected_slices != actual_slices:
                raise ValueError('Invalid quantization partition')
            restored = np.empty(meta['shape'], dtype=np.float32)
            for params in meta['quantization']:
                if params['bits'] != manifest['bits']:
                    raise ValueError('Bit depth mismatch')
                a, b = params['row_start'], params['row_end']
                restored[a:b] = dequantize(array[a:b], params)
        else:
            raise ValueError('Unsupported format kind')
        if not np.isfinite(restored).all():
            raise ValueError('Nonfinite reconstruction')
        tables[key] = torch.from_numpy(restored.copy())
        prefix = key.split('.')[0]
        for buf in BUFFERS:
            value = _read_array(folder, meta['buffers'][buf])
            if value.tolist() != meta[buf]:
                raise ValueError('Buffer mismatch')
            buffers[f'{prefix}.{buf}'] = torch.from_numpy(value.copy())
    return tables, buffers, manifest


def empirical_entropy(symbols):
    x = np.asarray(symbols)
    if x.size == 0:
        raise ValueError('Empty symbols')
    _, counts = np.unique(x, return_counts=True)
    p = counts.astype(np.float64) / x.size
    h = float(-(p * np.log2(p)).sum())
    return {'symbols': x.size, 'unique_symbols': counts.size, 'bits_per_symbol': h,
            'theoretical_bits': h * x.size}


def substitute(states, tables, buffers):
    grid, network = states
    if set(tables) != set(KEYS):
        raise ValueError('Exactly four grids required')
    new_grid = dict(grid)
    for key, tensor in {**tables, **buffers}.items():
        if key not in grid or tensor.shape != grid[key].shape or tensor.dtype != grid[key].dtype:
            raise ValueError(f'State mismatch: {key}')
        if key not in KEYS and not torch.equal(tensor, grid[key]):
            raise ValueError('Buffers must remain unchanged')
        new_grid[key] = tensor.clone()
    return new_grid, network
