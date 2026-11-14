"""Fresh-process decoder with one bin input and audited public dependencies."""
import argparse
import json
import os
import sys
from pathlib import Path
import numpy as np
from . import codec

ROOT = Path(__file__).resolve().parents[3]


def run(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source.stat().st_size > codec.MAX_BYTES:
        raise ValueError('Container exceeds bound')
    output.mkdir(parents=True, exist_ok=False)
    reads, denied = set(), []
    # Permit actual public source/runtime files, not arbitrary .py files in
    # completed experiments or a target file renamed with a source suffix.
    public = {p.resolve() for d in (ROOT / 'research/experiment_bench', ROOT / 'research/hashgrid_analysis',
                                   ROOT / 'research/grid4d') for p in d.glob('*.py')}
    for package in ('pmf_clustering', 'hashed_pair', 'hashed_pair_v3', 'hashed_interlevel'):
        public.update(p.resolve() for p in (ROOT / 'research/experiment_bench' / package).glob('*.py'))
    public.update(p.resolve() for p in (ROOT / 'research/hashgrid_analysis/hashed_context').glob('*.py'))
    runtime_roots = (ROOT / '.tools', Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve())

    def guard(event, args):
        if event != 'open':
            return
        raw, mode, flags = args[:3]
        if isinstance(raw, int):
            raise PermissionError('Unexpected explicit descriptor open')
        if not isinstance(raw, (str, bytes)):
            raise PermissionError('Unexpected data open type')
        path = Path(os.fsdecode(raw)).resolve()
        writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        reading = not flags & os.O_WRONLY or bool(flags & os.O_RDWR)
        if writing and not path.is_relative_to(output):
            raise PermissionError('Decoder write outside output directory')
        if not reading:
            return
        if path == source:
            reads.add(str(path))
            return
        is_runtime = path.suffix in ('.py', '.pyc', '.dll', '.pyd', '.so') and any(path.is_relative_to(r) for r in runtime_roots)
        if path in public or is_runtime:
            return
        denied.append(str(path))
        raise PermissionError('Forbidden external decoder data read')

    def no_fit(*args, **kwargs):
        raise AssertionError('Fitting is forbidden in standalone decoder')

    # These functions are imported by old public modules but must never run.
    codec.legacy.fit_spec = codec.legacy.fit_masses = no_fit
    from research.experiment_bench import models
    models.frequencies = no_fit
    sys.addaudithook(guard)
    coarse, fine, classes, ids, detail = codec.decode(source.read_bytes(), strict=True)
    if reads != {str(source)} or denied:
        raise AssertionError('Unexpected actual decoder data dependency')
    for name, value in (('coarse', coarse), ('fine', fine), ('contexts', classes), ('clusters', ids)):
        with (output / (name + '.npy')).open('xb') as file:
            np.save(file, value, allow_pickle=False)
    probes = []
    for name in ('checkpoint.pth', 'histograms.npz', 'fine_symbols.npy', 'contexts.npz', 'mapping.npy'):
        try:
            (source.parent / name).open('rb')
        except PermissionError:
            probes.append(name)
        else:
            raise AssertionError('Forbidden probe was allowed')
    result = {'status': 'PASS', 'only_bin_data_read': True, 'data_reads': sorted(reads),
              'forbidden_actual_reads': [], 'forbidden_probes_denied': probes,
              'optimizer_imported': 'research.experiment_bench.pmf_clustering.optimizer' in sys.modules,
              'detail': detail}
    if result['optimizer_imported']:
        raise AssertionError('Decoder imported optimizer')
    with (output / 'audit.json').open('x', encoding='utf-8') as file:
        json.dump(result, file, indent=2)
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.input, args.output)


if __name__ == '__main__':
    main()
