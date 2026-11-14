"""Four bounded standard lossless transports, not a contextual entropy coder.

The isolated diagnostic wrapper stores 16 independently compressed raw uint8
levels and immutable GLOBAL8 metadata.  No existing container is changed.
Entry points for orchestration: run_scene(scene, output), budget(path), decode.
"""
from input_sources import (R, ROOT, SCENES, EXPECTED, np, check, canonical,
                           canonical_dequantize, sha, arrsha, put, read_json,
                           inspect_source, iter_source_levels, source_paths, load_codes)
import ctypes
import hashlib
import json
import lzma
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import time
import zipfile
import zlib

MAGIC = b'G4DBASE1'
VERSION = 1
PREFIX = struct.Struct('<8sHHI')  # magic, version, levels, JSON bytes:16B
DESCRIPTOR = struct.Struct('<QQ32s')  # raw bytes, compressed bytes, codes SHA256:48B
CODECS = ('DEFLATE6', 'XZ6')
LAYOUTS = ('slot-major', 'channel-major')
ARITHMETIC = 'codec.dequantize:f64-affine-clip-cast-f32:v1'
MAX_FILE = 32 * 2**20
MAX_JSON = 65536
MAX_LEVEL_BYTES = 524288 * 2


def peak_rss_bytes():
    if sys.platform == 'win32':
        class Counters(ctypes.Structure):
            _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong),
                        ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        api = ctypes.windll.psapi.GetProcessMemoryInfo
        api.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
        api.restype = ctypes.c_int
        ok = api(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
        check(ok, 'Cannot measure process working set')
        return int(counters.PeakWorkingSetSize)
    import resource
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024))


def runtime():
    return {'python': platform.python_version(), 'numpy': np.__version__,
            'zlib_build': zlib.ZLIB_VERSION, 'zlib_runtime': zlib.ZLIB_RUNTIME_VERSION,
            'lzma': 'Python stdlib lzma; FORMAT_XZ default LZMA2 preset6/checkCRC64',
            'cpu_only': True, 'torch_imported': 'torch' in sys.modules}


def validate_metadata(m):
    check(set(m) == {'schema', 'codec', 'layout', 'arithmetic', 'source_metadata',
                     'canonical_restored_sha256'}, 'Unknown metadata fields')
    check(m['schema'] == 'grid4d-standard-spatial-v1', 'Unknown baseline schema')
    check(m['codec'] in CODECS and m['layout'] in LAYOUTS, 'Unknown codec/layout')
    check(m['arithmetic'] == ARITHMETIC, 'Unknown reconstruction arithmetic')
    s = m['source_metadata']
    check(s['dtype'] == 'uint8' and s['shape'][1] == 2, 'Codes dtype/channels')
    off = s['offsets']
    check(isinstance(off, list) and len(off) == 17 and all(type(v) == int for v in off), 'Offsets type')
    check(off[0] == 0 and 0 < off[-1] <= 6098108 and
          all(0 < b - a <= 524288 for a, b in zip(off, off[1:])), 'Offsets limits')
    check(s['shape'] == [off[-1], 2] and s['level_order'] == list(range(16)), 'Shape/level order')
    check(s['tensor'] == 'xyz_encoding.embeddings' and s['quantizer']['bits'] == 8 and
          s['quantization_scope'] == 'entire xyz table shared across all levels/channels', 'GLOBAL8 specification')
    q = s['quantizer']
    check(set(q) == {'bits', 'min', 'max', 'step', 'rounding', 'reconstruction_dtype'}, 'Quantizer fields')
    check(q['rounding'] == 'nearest-even' and q['reconstruction_dtype'] == 'float32', 'Quantizer convention')
    check(all(type(q[k]) in (int, float) and np.isfinite(q[k]) for k in ('min', 'max', 'step')),
          'Quantizer finite')
    check(q['max'] >= q['min'] and q['step'] == (q['max'] - q['min']) / 255, 'Frozen quantizer step')
    for digest in (s['symbols_sha256'], m['canonical_restored_sha256']):
        check(isinstance(digest, str) and len(digest) == 64 and
              all(c in '0123456789abcdef' for c in digest), 'Invalid content digest')


def compress(raw, codec):
    if codec == 'DEFLATE6':
        c = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=-15)
        return c.compress(raw) + c.flush()
    check(codec == 'XZ6', 'Unknown compressor')
    return lzma.compress(raw, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=6)


def decompress(payload, codec, expected):
    check(0 < expected <= MAX_LEVEL_BYTES, 'Uncompressed section limit')
    if codec == 'DEFLATE6':
        c = zlib.decompressobj(wbits=-15)
        raw = c.decompress(payload, expected + 1)
        check(c.eof and not c.unused_data and not c.unconsumed_tail, 'Malformed/trailing DEFLATE stream')
    else:
        check(codec == 'XZ6', 'Unknown decompressor')
        c = lzma.LZMADecompressor(format=lzma.FORMAT_XZ, memlimit=128 * 2**20)
        raw = c.decompress(payload, max_length=expected + 1)
        check(c.eof and not c.unused_data, 'Malformed/trailing XZ stream')
    check(len(raw) == expected, 'Decompressed byte count mismatch')
    return raw


def assemble(metadata, descriptors, payloads):
    validate_metadata(metadata)
    blob = canonical(metadata)
    check(len(blob) <= MAX_JSON and len(descriptors) == len(payloads) == 16, 'Container dimensions')
    body = PREFIX.pack(MAGIC, VERSION, 16, len(blob)) + blob
    body += b''.join(DESCRIPTOR.pack(*d) for d in descriptors)
    body += b''.join(payloads)
    check(len(body) + 32 <= MAX_FILE, 'Container byte limit')
    return body + hashlib.sha256(body).digest()


def encode_arrays(levels, source_metadata, restored_sha256, codec, layout):
    """Bounded construction; independent standard compressors only."""
    check(codec in CODECS and layout in LAYOUTS, 'Registered variant only')
    t = time.perf_counter()
    metadata = {'schema': 'grid4d-standard-spatial-v1', 'codec': codec, 'layout': layout,
                'arithmetic': ARITHMETIC, 'source_metadata': source_metadata,
                'canonical_restored_sha256': restored_sha256}
    validate_metadata(metadata)
    payloads, descriptors = [], []
    compression_seconds = hashing_seconds = 0.0
    qhash = hashlib.sha256()
    r_hash = hashlib.sha256()
    indices = []
    for i, q in levels:
        indices.append(i)
        lo, hi = source_metadata['offsets'][i:i + 2]
        check(q.dtype == np.uint8 and q.shape == (hi - lo, 2), 'Source level shape/dtype')
        h0 = time.perf_counter()
        original = q.tobytes(order='C')
        digest = hashlib.sha256(original).digest()
        qhash.update(original)
        r_hash.update(canonical_dequantize(q, source_metadata['quantizer']).tobytes())
        hashing_seconds += time.perf_counter() - h0
        raw = original if layout == 'slot-major' else q.T.tobytes(order='C')
        c0 = time.perf_counter()
        payload = compress(raw, codec)
        compression_seconds += time.perf_counter() - c0
        descriptors.append((len(raw), len(payload), digest))
        payloads.append(payload)
    check(indices == list(range(16)), 'Exact ordered level coverage')
    check(qhash.hexdigest() == source_metadata['symbols_sha256'], 'Unchanged symbols')
    check(r_hash.hexdigest() == restored_sha256, 'Canonical reconstruction parity')
    data = assemble(metadata, descriptors, payloads)
    return data, {'encode_wall_seconds': time.perf_counter() - t,
                  'compression_seconds': compression_seconds,
                  'identity_and_reconstruction_seconds': hashing_seconds,
                  'peak_RSS_bytes': peak_rss_bytes()}


def parse(data):
    check(PREFIX.size + 16 * DESCRIPTOR.size + 32 < len(data) <= MAX_FILE, 'Container size')
    check(hashlib.sha256(data[:-32]).digest() == data[-32:], 'Container SHA256 mismatch')
    magic, version, count, mlen = PREFIX.unpack_from(data)
    check(magic == MAGIC and version == VERSION and count == 16 and 0 < mlen <= MAX_JSON,
          'Container prefix')
    start = PREFIX.size
    raw = data[start:start + mlen]
    try:
        m = json.loads(raw)
    except (ValueError, UnicodeError) as e:
        raise ValueError('Metadata JSON') from e
    check(canonical(m) == raw, 'Noncanonical metadata JSON')
    validate_metadata(m)
    start += mlen
    check(start + 16 * DESCRIPTOR.size <= len(data) - 32, 'Truncated descriptors')
    descriptors = [DESCRIPTOR.unpack_from(data, start + i * DESCRIPTOR.size) for i in range(16)]
    start += 16 * DESCRIPTOR.size
    rows = []
    for i, (nb, cb, digest) in enumerate(descriptors):
        lo, hi = m['source_metadata']['offsets'][i:i + 2]
        check(nb == (hi - lo) * 2 and 0 < cb <= 2 * MAX_LEVEL_BYTES, 'Section byte bounds')
        check(start + cb <= len(data) - 32, 'Truncated section payload')
        rows.append({'level': i, 'offset_start': lo, 'offset_end': hi, 'rows': hi - lo,
                     'raw_bytes': nb, 'compressed_payload_bytes': cb,
                     'descriptor_bytes': DESCRIPTOR.size, 'section_bytes': cb + DESCRIPTOR.size,
                     'symbols_sha256': digest.hex(), 'payload_offset': start})
        start += cb
    check(start == len(data) - 32, 'Unaccounted/trailing container bytes')
    return m, rows


def decode_data(data, codes_output=None):
    t = time.perf_counter()
    m, rows = parse(data)
    qhash, r_hash = hashlib.sha256(), hashlib.sha256()
    output = None
    if codes_output is not None:
        check(not Path(codes_output).exists(), 'Refusing to overwrite decoded codes')
        output = np.lib.format.open_memmap(codes_output, mode='w+', dtype=np.uint8,
                                          shape=tuple(m['source_metadata']['shape']))
    level_hashes = []
    for row in rows:
        start, nb, cb = row['payload_offset'], row['raw_bytes'], row['compressed_payload_bytes']
        raw = decompress(data[start:start + cb], m['codec'], nb)
        q = np.frombuffer(raw, dtype=np.uint8)
        q = q.reshape(row['rows'], 2) if m['layout'] == 'slot-major' else q.reshape(2, row['rows']).T.copy()
        original = q.tobytes(order='C')
        digest = hashlib.sha256(original).hexdigest()
        check(digest == row['symbols_sha256'], 'Level code SHA256 mismatch')
        qhash.update(original)
        restored = canonical_dequantize(q, m['source_metadata']['quantizer'])
        r_hash.update(restored.tobytes())
        level_hashes.append({'level': row['level'], 'symbols_sha256': digest,
                             'canonical_restored_sha256': arrsha(restored)})
        if output is not None:
            output[row['offset_start']:row['offset_end']] = q
    if output is not None:
        output.flush()
        del output
    check(qhash.hexdigest() == m['source_metadata']['symbols_sha256'], 'Full codes SHA256 mismatch')
    check(r_hash.hexdigest() == m['canonical_restored_sha256'], 'Canonical dequantization SHA256 mismatch')
    return {'status': 'PASS', 'symbols_sha256': qhash.hexdigest(),
            'canonical_restored_sha256': r_hash.hexdigest(), 'all_allocated_slots': True,
            'levels': level_hashes, 'metadata': m, 'internal_decode_seconds': time.perf_counter() - t,
            'peak_RSS_bytes': peak_rss_bytes()}


def decode(path, output=None):
    check(Path(path).stat().st_size <= MAX_FILE, 'Container byte limit')
    return decode_data(Path(path).read_bytes(), None if output is None else Path(output) / 'symbols.npy')


def budget(path):
    data = Path(path).read_bytes()
    m, rows = parse(data)
    payload = sum(x['compressed_payload_bytes'] for x in rows)
    desc = 16 * DESCRIPTOR.size
    meta = len(canonical(m))
    common = PREFIX.size + meta + 32
    check(len(data) == Path(path).stat().st_size == payload + desc + common, 'Exact physical accounting')
    return {'codec': m['codec'], 'layout': m['layout'], 'actual_filesystem_bytes': len(data),
            'compressed_payload_bytes': payload, 'level_descriptor_bytes': desc,
            'metadata_bytes': meta, 'prefix_bytes': PREFIX.size, 'digest_bytes': 32,
            'common_metadata_framing_bytes': common, 'section_bytes': payload + desc,
            'sha256': hashlib.sha256(data).hexdigest(), 'levels': rows,
            'measurement': 'ACTUAL', 'format': 'grid4d-standard-spatial-v1'}


def historical_budget(scene):
    p = source_paths(scene)['archive']
    check(sha(p) == EXPECTED[scene]['archive_sha256'], 'Frozen historical archive hash')
    rows = []
    raw = p.read_bytes()
    with zipfile.ZipFile(p) as z:
        infos = z.infolist()
        for i in range(16):
            e = z.getinfo(f'level_{i:02d}.npy')
            fields = struct.unpack_from('<4s5H3I2H', raw, e.header_offset)
            check(fields[0] == b'PK\x03\x04', 'ZIP local header')
            local = 30 + fields[-2] + fields[-1]
            central = 46 + len(e.filename.encode()) + len(e.extra) + len(e.comment)
            rows.append({'level': i, 'compressed_payload_bytes': e.compress_size,
                         'descriptor_bytes': local + central,
                         'section_bytes': e.compress_size + local + central,
                         'NPY_uncompressed_bytes': e.file_size,
                         'local_header_bytes': local, 'central_header_bytes': central})
        metadata = z.getinfo('metadata.npy')
        payload = sum(e.compress_size for e in infos)
    total = p.stat().st_size
    sections = sum(r['section_bytes'] for r in rows)
    return {'codec': 'DEFLATE6', 'layout': 'slot-major', 'variant': 'HISTORICAL_NPZ_DEFLATE6',
            'actual_filesystem_bytes': total, 'section_bytes': sections,
            'compressed_payload_bytes': sum(r['compressed_payload_bytes'] for r in rows),
            'level_descriptor_bytes': sum(r['descriptor_bytes'] for r in rows),
            'common_metadata_framing_bytes': total - sections,
            'metadata_member_bytes': metadata.compress_size, 'zip_framing_bytes': total - payload,
            'sha256': EXPECTED[scene]['archive_sha256'], 'levels': rows,
            'format': 'historical_numpy_NPZ', 'measurement': 'ACTUAL_EXISTING_FILE'}


def decoder_cli(path, out, historical=False):
    """Independent fresh process: only one supplied archive is data-readable."""
    path, out = Path(path).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    reads, blocked = [], []
    public_roots = (ROOT / 'research', Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve())
    def audit(event, args):
        if event != 'open' or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        p = Path(os.fsdecode(args[0])).resolve()
        mode, flags = args[1], args[2]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR))
        if writing:
            check(p.is_relative_to(out), 'Independent decoder write denied')
        elif p == path:
            reads.append(str(p))
        elif p.suffix in ('.py', '.pyc', '.pyd', '.dll') and any(p.is_relative_to(r) for r in public_roots):
            pass
        else:
            raise PermissionError('Independent baseline decoder data read denied: ' + str(p))
    sys.addaudithook(audit)
    # Probe access controls without reading the prohibited files.
    for probe in (source_paths('bouncingballs')['symbols'], source_paths('hellwarrior')['metadata'],
                  ROOT / 'outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth'):
        try:
            with probe.open('rb') as f:
                f.read(1)
        except PermissionError:
            blocked.append(str(probe))
        else:
            raise RuntimeError('Forbidden decoder probe was readable')
    if historical:
        t = time.perf_counter()
        with np.load(path, allow_pickle=False) as z:
            m = json.loads(z['metadata'].tobytes())
            check(set(z.files) == {'metadata'} | {f'level_{i:02d}' for i in range(16)}, 'Historical members')
            qhash, r_hash = hashlib.sha256(), hashlib.sha256()
            output = np.lib.format.open_memmap(out / 'symbols.npy', mode='w+', dtype=np.uint8, shape=tuple(m['shape']))
            for i, (lo, hi) in enumerate(zip(m['offsets'], m['offsets'][1:])):
                q = z[f'level_{i:02d}']
                check(q.dtype == np.uint8 and q.shape == (hi - lo, 2), 'Historical array')
                output[lo:hi] = q
                qhash.update(q.tobytes())
                r_hash.update(canonical_dequantize(q, m['quantizer']).tobytes())
            output.flush()
            del output
        check(qhash.hexdigest() == m['symbols_sha256'], 'Historical codes SHA')
        result = {'status': 'PASS', 'symbols_sha256': qhash.hexdigest(),
                  'canonical_restored_sha256': r_hash.hexdigest(), 'all_allocated_slots': True,
                  'internal_decode_seconds': time.perf_counter() - t, 'peak_RSS_bytes': peak_rss_bytes()}
    else:
        result = decode(path, out)
    result.update(only_archive_data_reads=sorted(set(reads)), denied_probes=blocked,
                  read_audit_scope='Python audit hook, not OS sandbox', runtime=runtime())
    put(out / 'VALIDATION.json', result)
    print(json.dumps({'status': result['status'], 'codes': result['symbols_sha256']}), flush=True)


def corruption_fixtures(source_metadata):
    """Small fixtures exercise wrapper rejection without touching real inputs."""
    import copy
    m = copy.deepcopy(source_metadata)
    arrays = [(i, ((np.arange(20, dtype=np.uint16) + i) % 256).astype(np.uint8).reshape(10, 2)) for i in range(16)]
    m['offsets'] = list(range(0, 161, 10))
    m['shape'] = [160, 2]
    q = np.concatenate([x for _, x in arrays])
    m['symbols_sha256'] = arrsha(q)
    rh = arrsha(canonical_dequantize(q, m['quantizer']))
    cases = []
    for codec in CODECS:
        for layout in LAYOUTS:
            data, _ = encode_arrays(arrays, m, rh, codec, layout)
            check(data == encode_arrays(arrays, m, rh, codec, layout)[0], 'Fixture byte reproducibility')
            result = decode_data(data)
            check(result['symbols_sha256'] == arrsha(q), 'Fixture exact layout reconstruction')
            candidates = [('truncated', data[:-1]), ('appended', data + b'x')]
            damaged = bytearray(data)
            damaged[-40] ^= 1
            candidates.append(('integrity', bytes(damaged)))
            def resign(body):
                return bytes(body) + hashlib.sha256(body).digest()
            body = bytearray(data[:-32])
            body[0] ^= 1
            candidates.append(('unknown_magic_valid_digest', resign(body)))
            body = bytearray(data[:-32])
            mlen = PREFIX.unpack_from(body)[3]
            struct.pack_into('<Q', body, PREFIX.size + mlen, MAX_LEVEL_BYTES + 1)
            candidates.append(('raw_length_valid_digest', resign(body)))
            body = bytearray(data[:-32])
            first_payload = PREFIX.size + mlen + 16 * DESCRIPTOR.size
            body[first_payload] ^= 255
            candidates.append(('malformed_payload_valid_digest', resign(body)))
            for name, bad in candidates:
                try:
                    decode_data(bad)
                except (ValueError, zlib.error, lzma.LZMAError):
                    cases.append({'codec': codec, 'layout': layout, 'case': name, 'rejected': True})
                else:
                    raise RuntimeError('Malformed baseline accepted: ' + name)
    return {'status': 'PASS', 'roundtrip_variants': 4, 'byte_identical_fixture_rebuilds': 4,
            'rejected': len(cases), 'cases': cases}


def run_scene(scene, output, expected_input=None):
    """Call only after root has sealed protocol/input audit; CPU jobs sequential."""
    check((R / 'PREREGISTERED_PROTOCOL.json').exists() and (R / 'INPUT_MANIFEST.json').exists(),
          'Protocol and input manifest must exist before results')
    check(scene in SCENES, 'Registered scene')
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    s = inspect_source(scene)
    if expected_input is not None:
        check(expected_input['metadata'] == s['metadata'], 'Frozen audited metadata changed')
    put(out / 'RUNTIME.json', runtime())
    put(out / 'CORRUPTION_CHECKS.json', corruption_fixtures(s['metadata']))
    rows = []
    frozen = load_codes(scene)
    for codec, layout in [(c, l) for c in CODECS for l in LAYOUTS] + [('HISTORICAL', 'slot-major')]:
        name = 'HISTORICAL_NPZ_DEFLATE6' if codec == 'HISTORICAL' else codec + '_' + layout
        if codec == 'HISTORICAL':
            path = source_paths(scene)['archive']
            b, timing = historical_budget(scene), {'compression_seconds': None, 'encode_wall_seconds': None}
        else:
            path = out / (name + '.bin')
            data, timing = encode_arrays(iter_source_levels(scene), s['metadata'], EXPECTED[scene]['restored_sha256'], codec, layout)
            with path.open('xb') as f:
                f.write(data)
            b = budget(path)
            del data
        dec = out / (name + '_decoded')
        cmd = [sys.executable, '-B', str(Path(__file__).resolve()),
               'decode-historical' if codec == 'HISTORICAL' else 'decode', str(path), str(dec)]
        cold = time.perf_counter()
        with (out / (name + '_decode.log')).open('x', encoding='utf-8') as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
        cold_seconds = time.perf_counter() - cold
        v = read_json(dec / 'VALIDATION.json')
        check(v['status'] == 'PASS' and v['symbols_sha256'] == EXPECTED[scene]['symbols_sha256'] and
              v['canonical_restored_sha256'] == EXPECTED[scene]['restored_sha256'], 'Fresh decoder hash parity')
        q = np.load(dec / 'symbols.npy', mmap_mode='r', allow_pickle=False)
        for lo, hi in zip(s['metadata']['offsets'], s['metadata']['offsets'][1:]):
            check(np.array_equal(q[lo:hi], frozen[lo:hi]), 'Fresh decoder exact equality all codes')
        del q
        row = {**b, **timing, 'scene': scene, 'variant': name, 'path': str(path),
               'fresh_decode_cold_seconds': cold_seconds, 'decode_internal_seconds': v['internal_decode_seconds'],
               'decoder_peak_RSS_bytes': v['peak_RSS_bytes'], 'exact_codes': True,
               'canonical_reconstruction_exact': True, 'decoder_only_archive_reads': v['only_archive_data_reads'],
               'decode_command': cmd}
        put(out / (name + '_BUDGET.json'), row)
        rows.append(row)
    best = min(rows, key=lambda x: (x['actual_filesystem_bytes'], x['variant']))
    result = {'status': 'PASS', 'scene': scene, 'baseline_rows': rows, 'best_variant': best['variant'],
              'best_actual_filesystem_bytes': best['actual_filesystem_bytes'],
              'all_five_baselines_exact': True, 'peak_RSS_bytes': peak_rss_bytes()}
    put(out / 'BASELINES_COMPLETE.json', result)
    return result


if __name__ == '__main__':
    if sys.argv[1] in ('decode', 'decode-historical'):
        decoder_cli(sys.argv[2], sys.argv[3], historical=sys.argv[1] == 'decode-historical')
    elif sys.argv[1] == 'scene':
        result = run_scene(sys.argv[2], sys.argv[3])
        print(json.dumps({'scene': result['scene'], 'status': result['status'],
                          'best_variant': result['best_variant'],
                          'bytes': result['best_actual_filesystem_bytes']}), flush=True)
    else:
        raise ValueError('Expected decode, decode-historical or scene')
