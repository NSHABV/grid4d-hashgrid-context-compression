"""Adversarial checks for real G4DHPAIR V3 files; never reads original symbols.

Run with --run RESULT_DIRECTORY --output NEW_CHECK_DIRECTORY.  Input files are
read-only and SHA-checked after the suite.  Mutations are in memory; repaired
outer digests deliberately test semantic validation beyond checksum detection.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct
import time

import numpy as np

from . import format as fmt
from research.experiment_bench.hashed_interlevel import dry_model


def _path_set(value, path, replacement):
    result = copy.deepcopy(value)
    current = result
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = replacement
    return result


def _model(parts, storage, classes):
    prefix = dry_model.HEADER.pack(dry_model.MAGIC, dry_model.VERSION,
                                  dry_model.STORAGES[storage], 2, classes, 256,
                                  *(len(p) for p in parts))
    return prefix + b''.join(parts)


def mutations(data):
    """Yield name, damaged bytes, outer-checksum-repaired flag."""
    header, sections = fmt.unpack(data)
    yield 'file_truncated', data[:-1], False
    yield 'file_trailing_byte', data + b'\x00', False
    for offset, label in ((0, 'magic'), (8, 'version'), (len(data)-1, 'checksum')):
        damaged = bytearray(data); damaged[offset] ^= 1
        yield label + '_bitflip', bytes(damaged), False

    prefix = list(fmt.PREFIX.unpack_from(data))
    prefix[2] = 2**50
    damaged = fmt.PREFIX.pack(*prefix) + data[fmt.PREFIX.size:-32]
    yield 'metadata_declared_length_above_bound', damaged + hashlib.sha256(damaged).digest(), True

    header_cases = [
        ('format_version', ('version',), 99),
        ('wrong_engine', ('engine', 'version'), '0.0.0'),
        ('wrong_numpy_arithmetic', ('numpy',), '1.21.6'),
        ('wrong_symbol_order', ('order',), 'slot-major'),
        ('fine_rows_above_bound', ('geometry', 'fine', 'rows'), 2**50),
        ('fine_float_rows', ('geometry', 'fine', 'rows'), 524288.),
        ('coarse_offset', ('geometry', 'coarse', 'offset_start'), header['geometry']['coarse']['offset_start']+1),
        ('coarse_level', ('geometry', 'coarse', 'level'), 3),
        ('wrong_resolution', ('geometry', 'fine', 'lookup_resolution'), [1, 1, 1]),
        ('wrong_actual_scale', ('geometry', 'fine', 'scale'), [1., 1., 1.]),
        ('wrong_hash_primes', ('geometry', 'hash', 'primes'), [1, 3, 5]),
        ('wrong_hash_uint_width', ('geometry', 'hash', 'mask'), 2**64-1),
        ('wrong_interpolation', ('geometry', 'interpolation'), 'linear'),
        ('wrong_point_domain', ('geometry', 'geometry_convention'), 'clamped-u'),
        ('wrong_empty_fallback', ('geometry', 'fallback', 'features'), [1, 1]),
        ('wrong_quantizer_bits', ('geometry', 'coarse', 'quantization', 'bits'), 7),
        ('wrong_quantizer_step', ('geometry', 'coarse', 'quantization', 'step'), -1.),
        ('inconsistent_quantizer_min', ('geometry', 'coarse', 'quantization', 'min'), -5.5),
        ('wrong_quantizer_rounding', ('geometry', 'coarse', 'quantization', 'rounding'), 'floor'),
        ('model_wrong_class_count', ('model', 'C'), 999),
        ('model_unknown_storage', ('model', 'storage'), 'unknown'),
        ('bad_integrity_hash', ('integrity', 'fine_symbols'), 'not-a-hash'),
        ('wrong_coarse_symbols_hash', ('integrity', 'coarse_symbols'), '0'*64),
        ('wrong_fine_symbols_hash', ('integrity', 'fine_symbols'), '0'*64),
        ('wrong_class_hash', ('integrity', 'classes'), '0'*64),
        ('wrong_mass_hash', ('integrity', 'fine_masses'), '0'*64),
    ]
    for label, path, replacement in header_cases:
        yield label, fmt.pack(_path_set(header, path, replacement), sections), True

    for role in ('coarse_payload', 'fine_payload'):
        payload = sections[role]
        flipped = bytearray(payload); flipped[len(flipped)//2] ^= 128
        cases = [('empty', b''), ('unaligned', payload + b'\x00'),
                 ('truncated_word', payload[:-4]), ('appended_word', payload + bytes(4)),
                 ('bitflip', bytes(flipped))]
        for label, damaged in cases:
            current = dict(sections); current[role] = damaged
            yield role + '_' + label, fmt.pack(header, current), True

    for role in ('coarse_model', 'fine_model'):
        parts, storage, classes = dry_model._parts(sections[role])
        # Low-level mutations bypass the writer's checks to exercise the reader.
        mass = bytearray(parts[0])
        width = 4 if storage == 'dense_u32' else 2
        mass[:width] = bytes(width)
        damaged = list(parts); damaged[0] = bytes(mass)
        current = dict(sections); current[role] = _model(damaged, storage, classes)
        yield role + '_zero_mass', fmt.pack(header, current), True
        mass = bytearray(parts[0])
        old = int.from_bytes(mass[:width], 'little')
        new = old + 1 if old < 65535 else old - 1
        mass[:width] = new.to_bytes(width, 'little')
        damaged = list(parts); damaged[0] = bytes(mass)
        current[role] = _model(damaged, storage, classes)
        yield role + '_wrong_mass_sum', fmt.pack(header, current), True

        spec = dry_model._json_load(parts[2]); spec['rules']['boundary'] = 'searchsorted-left'
        damaged = list(parts); damaged[2] = dry_model._json_bytes(spec)
        current[role] = _model(damaged, storage, classes)
        yield role + '_changed_context_rule', fmt.pack(header, current), True

    if header['model']['name'] in ('Canonical8', 'Mean8'):
        parts, storage, classes = dry_model._parts(sections['fine_model'])
        for label, edges in (
            ('wrong_shape', np.zeros((2, 8), np.float64)),
            ('unsorted', np.array([[1., 0, 0, 0, 0, 0, 0]] * 2)),
        ):
            damaged = list(parts); damaged[1] = dry_model._threshold_bytes({'primary': edges})
            current = dict(sections); current['fine_model'] = _model(damaged, storage, classes)
            yield 'threshold_' + label, fmt.pack(header, current), True
        raw = bytearray(parts[1])
        # H count + H name length + name + B ndim + ndim*I dimensions.
        name_length = struct.unpack_from('<H', raw, 2)[0]
        ndim = raw[4 + name_length]
        first_value = 5 + name_length + 4 * ndim
        raw[first_value:first_value+8] = struct.pack('<d', float('nan'))
        damaged = list(parts); damaged[1] = bytes(raw)
        current = dict(sections); current['fine_model'] = _model(damaged, storage, classes)
        yield 'threshold_nan', fmt.pack(header, current), True


def run(run_dir, output):
    run_dir, output = Path(run_dir).resolve(), Path(output).resolve()
    if not run_dir.is_dir():
        raise ValueError('Input experiment directory does not exist')
    output.mkdir(parents=True, exist_ok=False)
    files = []
    for path in sorted(run_dir.rglob('*.bin')):
        with path.open('rb') as handle:
            if handle.read(10) == fmt.MAGIC + struct.pack('<H', fmt.VERSION):
                files.append(path)
    if not files:
        raise ValueError('No G4DHPAIR V3 streams found')
    source_hashes = {str(p.relative_to(run_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in files}
    started = time.perf_counter()
    result = {'status': 'PASS', 'input_directory': str(run_dir), 'files': [],
              'source_files_read': 'Only completed .bin streams; no checkpoint/targets/contexts',
              'mutations': 'In memory, with recomputed outer SHA for semantic attacks'}
    for path in files:
        data = path.read_bytes()
        original_hash = hashlib.sha256(data).hexdigest()
        coarse_symbols, fine_symbols, classes, detail = fmt.decode_bytes(data)
        del coarse_symbols, fine_symbols, classes
        entry = {'path': str(path.relative_to(run_dir)), 'sha256': original_hash,
                 'valid_original_decode': detail['status'], 'checks': []}
        for name, damaged, repaired in mutations(data):
            began = time.perf_counter()
            check = {'case': name, 'outer_sha_recomputed': repaired,
                     'damaged_sha256': hashlib.sha256(damaged).hexdigest()}
            try:
                fmt.decode_bytes(damaged)
            except ValueError as exc:
                check.update(status='PASS', rejection=str(exc), exception='ValueError')
            except Exception as exc:
                check.update(status='FAIL', rejection=str(exc), exception=type(exc).__name__)
            else:
                check.update(status='FAIL', rejection='Malformed stream was accepted')
            check['seconds'] = time.perf_counter()-began
            if check['status'] != 'PASS': result['status'] = 'FAIL'
            entry['checks'].append(check)
        entry['input_unchanged'] = hashlib.sha256(path.read_bytes()).hexdigest() == original_hash
        if not entry['input_unchanged']: result['status'] = 'FAIL'
        result['files'].append(entry)
        print(json.dumps({'file': entry['path'], 'checks': len(entry['checks']),
                          'failures': sum(c['status'] != 'PASS' for c in entry['checks'])}), flush=True)
    result['elapsed_seconds'] = time.perf_counter()-started
    result['sources_before'] = source_hashes
    result['sources_after'] = {str(p.relative_to(run_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in files}
    result['all_sources_unchanged'] = result['sources_before'] == result['sources_after']
    if not result['all_sources_unchanged']:
        result['status'] = 'FAIL'
    result['checks_total'] = sum(len(f['checks']) for f in result['files'])
    result['failures'] = sum(c['status'] != 'PASS' for f in result['files'] for c in f['checks'])
    with (output / 'corruption-checks.json').open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = run(args.run, args.output)
    print(json.dumps({key: result[key] for key in ('status', 'checks_total', 'failures', 'elapsed_seconds')}))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
