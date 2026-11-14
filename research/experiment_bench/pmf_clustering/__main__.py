"""H4 CLI. Scene processing occurs only when optimize/encode is explicitly run."""
import argparse
import hashlib
import json
from pathlib import Path


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as file:
        json.dump(value, file, indent=2, allow_nan=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('optimize')
    p.add_argument('--bundle', required=True)
    p.add_argument('--mode', choices=('C0', 'C1', 'C2'), required=True)
    p.add_argument('--output', required=True, help='New plan directory')
    p = sub.add_parser('inspect')
    p.add_argument('--model', required=True)
    p.add_argument('--counts', help='NPZ with raw counts[2,10,256]')
    p.add_argument('--metadata-bytes', type=int, help='Measured outer bytes; default from bound optimization.json')
    p = sub.add_parser('encode')
    p.add_argument('--bundle', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--output', required=True, help='New standalone .bin')
    p = sub.add_parser('decode')
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True, help='New decoded directory')
    p = sub.add_parser('test')
    p.add_argument('--output', required=True, help='New technical validation directory')
    args = parser.parse_args()
    if args.command == 'decode':
        from .replay import run
        run(args.input, args.output)
        return
    if args.command == 'test':
        from .verification import run
        run(args.output)
        return
    import numpy as np
    from . import transport, optimizer, codec, bundle
    if args.command == 'inspect':
        raw = Path(args.model).read_bytes()
        model, _ = transport.deserialize(raw)
        best, choices = transport.choose(model)
        result = {'supplied_transport': transport.sizes(raw),
                  'minimum_transport': transport.sizes(best), 'transport_candidates': choices}
        if args.counts:
            with np.load(args.counts, allow_pickle=False) as z:
                counts = z['counts']
            meta = args.metadata_bytes
            if meta is None:
                plan = json.loads((Path(args.model).parent / 'optimization.json').read_text())
                if (plan['model_sha256'] != hashlib.sha256(raw).hexdigest()
                        or plan['input_fingerprints']['arrays']['counts'] != codec.legacy.array_sha(counts)):
                    raise ValueError('Model/counts do not match the metadata plan')
                meta = plan['final']['outer_metadata_bytes']
            result['objective'] = optimizer.objective(counts, model, meta)
        print(json.dumps(result, indent=2))
        return
    output = Path(args.output)
    if output.exists():
        raise FileExistsError('Choose a new output path; completed files are immutable')
    a = bundle.load(args.bundle)
    if args.command == 'optimize':
        result = optimizer.optimize(a['counts'], a['original'], a['thresholds'], args.mode, a['metadata_bytes'])
        wire, _ = transport.choose(result.model)
        output.mkdir(parents=True, exist_ok=False)
        with (output / 'model.h4pm').open('xb') as file:
            file.write(wire)
        with (output / 'histograms.npz').open('xb') as file:
            np.savez_compressed(file, counts=a['counts'])
        coarse_size = len(a['coarse_model']) + len(a['coarse_payload'])
        write_json(output / 'optimization.json', {'mode': args.mode, 'initial': result.initial, 'final': result.final,
            'history': result.history, 'candidates_evaluated': result.candidates_evaluated,
            'model_sha256': hashlib.sha256(wire).hexdigest(), 'input_fingerprints': bundle.fingerprints(a),
            'sealed_input': a['sealed_input'], 'coarse_bytes': coarse_size,
            'predicted_pair_bytes': result.final['J_bytes'] + coarse_size})
        print(json.dumps(result.final, indent=2))
        return
    raw = Path(args.model).read_bytes()
    model, _ = transport.deserialize(raw)
    plan = json.loads((Path(args.model).parent / 'optimization.json').read_text())
    if (plan['model_sha256'] != hashlib.sha256(raw).hexdigest()
            or plan['input_fingerprints'] != bundle.fingerprints(a) or plan['sealed_input'] != a['sealed_input']
            or plan['mode'] != model.mode):
        raise ValueError('Optimization plan belongs to different model/frozen inputs')
    check = optimizer.objective(a['counts'], model, a['metadata_bytes'])
    if check != plan['final']:
        raise ValueError('Recorded model objective does not reproduce')
    data, detail = codec.encode(a['geometry'], a['coarse'], a['fine'], a['classes'], model,
                               a['coarse_model'], a['coarse_payload'], a['coarse_storage'],
                               original_masses=a['original'], original_thresholds=a['thresholds'], profile=a['profile'])
    with output.open('xb') as file:
        file.write(data)
    print(json.dumps({'sha256': hashlib.sha256(data).hexdigest(), **detail}, indent=2))


if __name__ == '__main__':
    main()
