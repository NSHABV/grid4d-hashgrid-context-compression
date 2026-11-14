"""Self-contained range-coded files. No checkpoint or encoder-side state in decoder."""
import copy
import hashlib
import importlib.metadata
import json
import struct
import time
from pathlib import Path

import constriction
import numpy as np
from research.grid4d.codec import (BUFFERS, KEYS, _read_array, _save_array,
                                  empirical_entropy, validate_grid, write_json)
from .models import MODELS, TOTAL

MAGIC = b'G4DBENCH'
VERSION = 1
PREFIX = struct.Struct('<8sHQQQ')
CODER_VERSION = '0.4.2'


def categorical(model, index):
    return constriction.stream.model.Categorical(model.distribution(index), perfect=False)


def validated_plan(model, first):
    plan = model.plan_second(first)
    seen = np.zeros(first.size, dtype=bool)
    for distribution, indices in plan:
        if (not 1 <= distribution < model.distributions or indices.ndim != 1 or
                not np.issubdtype(indices.dtype, np.integer) or
                (indices.size and (indices.min() < 0 or indices.max() >= first.size)) or
                np.any(np.diff(indices) <= 0) or np.any(seen[indices])):
            raise ValueError('Invalid causal symbol partition/order')
        seen[indices] = True
    if not seen.all():
        raise ValueError('Missing q1 rows in coding schedule')
    return plan


def _entropy_cost(symbols, model):
    total, finite = 0., 0.
    groups = [(0, symbols[:, 0])]
    groups += [(dist, symbols[idx, 1]) for dist, idx in validated_plan(model, symbols[:, 0])]
    for dist, values in groups:
        if not values.size:
            continue
        total += empirical_entropy(values)['theoretical_bits']
        counts = np.bincount(values, minlength=256)
        finite += float(-(counts * np.log2(model.distribution(dist).astype(np.float64))).sum())
    return total, finite


def encode_symbols(symbols, model):
    encoder = constriction.stream.queue.RangeEncoder()
    encoder.encode(symbols[:, 0].astype(np.int32), categorical(model, 0))
    for dist, indices in validated_plan(model, symbols[:, 0]):
        if indices.size:
            encoder.encode(symbols[indices, 1].astype(np.int32), categorical(model, dist))
    return encoder.get_compressed().astype('<u4').tobytes()


def decode_symbols(data, rows, model):
    if len(data) % 4 or not data:
        raise ValueError('Invalid range payload length')
    decoder = constriction.stream.queue.RangeDecoder(np.frombuffer(data, dtype='<u4').copy())
    result = np.empty((rows, 2), dtype=np.uint8)
    # q0 is completely decoded before any conditional q1 request.
    result[:, 0] = decoder.decode(categorical(model, 0), rows).astype(np.uint8)
    for dist, indices in validated_plan(model, result[:, 0]):
        if indices.size:
            result[indices, 1] = decoder.decode(categorical(model, dist), indices.size).astype(np.uint8)
    return result


def _indexed_inputs(classes, masses):
    """Versioned inter-level extension: same engine, fixed channel-major order."""
    from .models import validate_frequencies
    c = np.asarray(classes)
    f = np.asarray(masses)
    if c.ndim != 2 or c.shape[1] != 2 or not np.issubdtype(c.dtype, np.integer):
        raise ValueError('Expected two-channel class array')
    if f.ndim != 3 or f.shape[0] != 2 or f.shape[2] != 256:
        raise ValueError('Expected channel/class/mass array')
    validate_frequencies(f.reshape(-1, 256))
    if c.size == 0 or c.min() < 0 or c.max() >= f.shape[1]:
        raise ValueError('Invalid context class')
    return c, f.astype(np.float32)/TOTAL


def encode_indexed(symbols, classes, masses, chunk_rows=4096):
    """Ascending rows of q0, then q1; never regroup targets by context."""
    c, p = _indexed_inputs(classes, masses)
    if symbols.dtype != np.uint8 or symbols.shape != c.shape or chunk_rows < 1:
        raise ValueError('Invalid symbols/chunk')
    encoder = constriction.stream.queue.RangeEncoder()
    family = constriction.stream.model.Categorical(perfect=False)
    for ch in range(2):
        for a in range(0, len(c), chunk_rows):
            b = min(a+chunk_rows, len(c))
            encoder.encode(symbols[a:b, ch].astype(np.int32), family, p[ch, c[a:b, ch]])
    return encoder.get_compressed().astype('<u4').tobytes()


def decode_indexed(data, classes, masses, chunk_rows=4096):
    c, p = _indexed_inputs(classes, masses)
    if not data or len(data) % 4 or chunk_rows < 1:
        raise ValueError('Invalid range payload/chunk')
    decoder = constriction.stream.queue.RangeDecoder(np.frombuffer(data, dtype='<u4').copy())
    family = constriction.stream.model.Categorical(perfect=False)
    result = np.empty(c.shape, dtype=np.uint8)
    for ch in range(2):
        for a in range(0, len(c), chunk_rows):
            b = min(a+chunk_rows, len(c))
            result[a:b, ch] = decoder.decode(family, p[ch, c[a:b, ch]]).astype(np.uint8)
    return result


def encode(folder, path, model_name):
    start = time.perf_counter()
    if model_name not in ('fixed8', *MODELS):
        raise ValueError('Unknown probability model')
    if importlib.metadata.version('constriction') != CODER_VERSION:
        raise ValueError('Pinned coder version required')
    folder, path = Path(folder), Path(path)
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest['kind'] != 'uniform-quantized' or manifest['bits'] != 8:
        raise ValueError('Only Phase2 8-bit quantized inputs are supported')
    header = {'format_version': VERSION, 'model': model_name,
              'coder': 'fixed8' if model_name == 'fixed8' else 'constriction-range',
              'coder_version': CODER_VERSION, 'histogram_precision': 16, 'coder_precision': 24,
              'categorical_perfect': False, 'quantization_manifest': manifest, 'components': {}}
    models, payloads, n, theoretical, finite_bits = [], [], 0, 0., 0.
    for key in KEYS:
        meta = manifest['grids'][key]
        validate_grid(meta)
        symbols = _read_array(folder, meta['payload'])
        if symbols.dtype != np.uint8 or symbols.shape[1] != 2:
            raise ValueError('Expected uint8 [rows,2]')
        for buf in BUFFERS:
            _read_array(folder, meta['buffers'][buf])  # integrity before packaging metadata
        if model_name == 'fixed8':
            model_data, payload = b'', symbols.tobytes()
            h = empirical_entropy(symbols)['theoretical_bits']
            f = symbols.size * 8
        else:
            model = MODELS[model_name].fit(symbols, meta)
            model_data = model.to_bytes()
            payload = encode_symbols(symbols, model)
            h, f = _entropy_cost(symbols, model)
        header['components'][key] = {'model_bytes': len(model_data), 'coded_bytes': len(payload),
                                    'symbols': symbols.size, 'symbols_sha256': hashlib.sha256(symbols.tobytes()).hexdigest(),
                                    'empirical_bits': h, 'finite_histogram_cross_entropy_bits': f}
        models.append(model_data)
        payloads.append(payload)
        n += symbols.size
        theoretical += h
        finite_bits += f
    meta_bytes = json.dumps(header, separators=(',', ':'), sort_keys=True, allow_nan=False).encode('utf8')
    model_bytes, coded = b''.join(models), b''.join(payloads)
    body = PREFIX.pack(MAGIC, VERSION, len(meta_bytes), len(model_bytes), len(coded)) + meta_bytes + model_bytes + coded
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(body)
        stream.write(hashlib.sha256(body).digest())
    total = path.stat().st_size
    return {'model': model_name, 'symbols': n, 'actual_bitstream_bytes': total,
            'coded_payload_bytes': len(coded), 'model_overhead_bytes': len(model_bytes),
            'metadata_framing_bytes': len(meta_bytes) + PREFIX.size + 32,
            'total_compressed_bytes': total, 'bits_per_symbol': total * 8 / n,
            'payload_bits_per_symbol': len(coded) * 8 / n,
            'compression_ratio_float32': n * 4 / total, 'compression_ratio_fixed8_payload': n / total,
            'theoretical_empirical_bits': theoretical, 'theoretical_bits_per_symbol': theoretical / n,
            'finite_histogram_cross_entropy_bits': finite_bits,
            'actual_minus_empirical_payload_bits': len(coded) * 8 - theoretical,
            'actual_minus_empirical_total_bits': total * 8 - theoretical,
            'encode_seconds': time.perf_counter()-start,
            'note': 'Finite cross entropy uses serialized 16-bit masses; Categorical additionally constructs its deterministic 24-bit model. File size is the measured rate.'}


def parse(path):
    data = Path(path).read_bytes()
    if len(data) < PREFIX.size + 32:
        raise ValueError('Truncated file')
    magic, version, h_len, m_len, p_len = PREFIX.unpack_from(data)
    if magic != MAGIC or version != VERSION:
        raise ValueError('Unknown format/version')
    if h_len > 4_000_000 or m_len > 4_000_000 or p_len > 400_000_000:
        raise ValueError('Invalid section lengths')
    if len(data) != PREFIX.size + h_len + m_len + p_len + 32:
        raise ValueError('Truncated/extra data or size mismatch')
    if hashlib.sha256(data[:-32]).digest() != data[-32:]:
        raise ValueError('Checksum mismatch')
    header = json.loads(data[PREFIX.size:PREFIX.size+h_len])
    if (header['format_version'] != VERSION or header['coder_version'] != CODER_VERSION or
            header['model'] not in ('fixed8', *MODELS) or
            header['histogram_precision'] != 16 or header['coder_precision'] != 24 or
            header['categorical_perfect'] is not False or
            header['coder'] != ('fixed8' if header['model'] == 'fixed8' else 'constriction-range')):
        raise ValueError('Unsupported coding specification')
    manifest = header['quantization_manifest']
    if (manifest['version'] != 1 or manifest['kind'] != 'uniform-quantized' or manifest['bits'] != 8 or
            manifest['scope'] not in ('table', 'level') or set(manifest['grids']) != set(KEYS) or
            set(header['components']) != set(KEYS)):
        raise ValueError('Invalid quantization specification')
    model_start = PREFIX.size + h_len
    payload_start = model_start + m_len
    model_pos = payload_pos = 0
    for key in KEYS:
        meta, comp = manifest['grids'][key], header['components'][key]
        validate_grid(meta)
        if meta['shape'][1] != 2 or not 0 < meta['shape'][0] <= 100_000_000 or comp['symbols'] != meta['scalar_count']:
            raise ValueError('Invalid symbol count')
        if comp['model_bytes'] < 0 or comp['coded_bytes'] < 0:
            raise ValueError('Negative section length')
        model_pos += comp['model_bytes']
        payload_pos += comp['coded_bytes']
    if model_pos != m_len or payload_pos != p_len:
        raise ValueError('Component lengths do not match sections')
    return header, data[model_start:payload_start], data[payload_start:-32]


def decode(path, output):
    """The two arguments are the only input paths: bitstream and fresh output."""
    started = time.perf_counter()
    header, model_bytes, payloads = parse(path)
    if importlib.metadata.version('constriction') != CODER_VERSION:
        raise ValueError('Pinned coder version required')
    manifest = copy.deepcopy(header['quantization_manifest'])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    model_pos = payload_pos = 0
    for key in KEYS:
        meta, comp = manifest['grids'][key], header['components'][key]
        model_data = model_bytes[model_pos:model_pos+comp['model_bytes']]
        payload = payloads[payload_pos:payload_pos+comp['coded_bytes']]
        model_pos += comp['model_bytes']
        payload_pos += comp['coded_bytes']
        if header['model'] == 'fixed8':
            if model_data or len(payload) != meta['scalar_count']:
                raise ValueError('Fixed8 length mismatch')
            symbols = np.frombuffer(payload, dtype=np.uint8).reshape(meta['shape']).copy()
        else:
            model = MODELS[header['model']].from_bytes(model_data, meta)
            symbols = decode_symbols(payload, meta['shape'][0], model)
        if hashlib.sha256(symbols.tobytes()).hexdigest() != comp['symbols_sha256']:
            raise ValueError('Decoded symbols checksum mismatch')
        prefix = key.split('.')[0]
        meta['payload'] = _save_array(output, f'{prefix}.u8.bin', symbols)
        for buf in BUFFERS:
            values = np.asarray(meta[buf], dtype='<i4' if buf == 'offsets' else '<f4')
            previous = meta['buffers'][buf]
            restored = _save_array(output, f'{prefix}.{buf}.bin', values)
            if restored['sha256'] != previous['sha256'] or restored['shape'] != previous['shape'] or restored['dtype'] != previous['dtype']:
                raise ValueError('Restored buffer checksum/structure mismatch')
            meta['buffers'][buf] = restored
    write_json(output / 'manifest.json', manifest)
    return {'decode_seconds': time.perf_counter()-started, 'symbols_verified': True,
            'input_paths': ['bitstream only'], 'format_version': VERSION, 'model': header['model']}
