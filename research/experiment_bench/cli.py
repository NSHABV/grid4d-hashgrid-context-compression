"""One experiment CLI, reusing Phase2 export/quantization/render/evaluation."""
import argparse
import datetime
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from research.grid4d.codec import (KEYS, _read_array, export_lossless, export_quantized,
                                  import_tables, load_checkpoint, sha, substitute, write_json)
from research.grid4d.study import prepare_model, csv_save
from . import entropy
from .models import MODELS

ROOT = Path(__file__).resolve().parents[2]
REVISION = '3ab7b74482910d22fba7d51ac60c8cae1fe24bf1'


def source_identity(repo):
    critical = ('train.py','render.py','metrics.py','arguments/__init__.py',
        'arguments/dnerf/bouncingballs.py','scene/network.py','scene/deform_model.py',
        'hashencoder/hashgrid.py','hashencoder/src/hashencoder.cu','gaussian_renderer/__init__.py')
    hashes = {}
    with tarfile.open(ROOT/'research/audit/grid4d-upstream.tar') as archive:
        for name in critical:
            actual = (repo/name).read_bytes().replace(b'\r\n',b'\n')
            expected = archive.extractfile(name).read().replace(b'\r\n',b'\n')
            if actual != expected:
                raise ValueError(f'Upstream algorithm changed: {name}')
            hashes[name] = hashlib.sha256(actual).hexdigest()
    return hashes


def resolve(path):
    p = Path(path)
    return p.resolve() if p.is_absolute() else (ROOT / p).resolve()


def execute(command, log, cwd=ROOT, env=None):
    started = time.perf_counter()
    with log.open('w') as file:
        subprocess.run(command, cwd=cwd, env=env, stdout=file, stderr=subprocess.STDOUT, check=True)
    return time.perf_counter()-started


def render_evaluate(model, config, checkpoint, logs, record):
    repo, dataset = resolve(config['repo']), resolve(config['dataset'])
    iteration = int(config['iteration'])
    environment = dict(os.environ, GRID4D_BENCH_REPO=str(repo), GRID4D_BENCH_SOURCE=str(checkpoint))
    timing = {}
    timing['render_seconds'] = execute([sys.executable, str(ROOT/'research/grid4d/inference_check.py'),
        str(record), '--conf', 'arguments/dnerf/bouncingballs.py', '-m', str(model), '-s', str(dataset),
        '--iteration', str(iteration), '--skip_train'], logs/'render.log', cwd=repo, env=environment)
    timing['evaluation_seconds'] = execute([sys.executable, 'metrics.py', '-m', str(model)], logs/'metrics.log', cwd=repo)
    metrics = json.loads((model/'results.json').read_text())[f'ours_{iteration}']
    per_view = json.loads((model/'per_view.json').read_text())[f'ours_{iteration}']
    if set(metrics) != {'PSNR', 'SSIM', 'LPIPS', 'MS-SSIM'} or not all(map(math.isfinite, metrics.values())):
        raise ValueError('Metrics missing/nonfinite (upstream suppresses exceptions)')
    if not all(len(v) == 20 and all(map(math.isfinite, v.values())) for v in per_view.values()):
        raise ValueError('Per-view metric count/values mismatch')
    test = model / f'test/ours_{iteration}'
    cpu_psnr = []
    png_hashes = []
    for category in ('renders', 'gt', 'depth'):
        files = sorted((test/category).glob('*.png'))
        if len(files) != 20:
            raise ValueError('Expected 20 test frames')
        for path in files:
            image = np.asarray(Image.open(path))
            if image.shape[:2] != (800, 800) and image.shape[:2] != (400, 400):
                raise ValueError('Unexpected frame dimensions')
            if image.std() == 0:
                raise ValueError('Degenerate image')
            if category == 'renders':
                png_hashes.append(sha(path))
                gt = np.asarray(Image.open(test/'gt'/path.name))
                mse = np.square(image[:, :, :3].astype(np.float64)/255 - gt[:, :, :3].astype(np.float64)/255).mean()
                psnr = -10*math.log10(mse)
                if abs(psnr-per_view['PSNR'][path.name]) > 1e-4:
                    raise ValueError('Independent CPU PSNR mismatch')
                cpu_psnr.append(psnr)
    return metrics, timing, {'cpu_mean_psnr': float(np.mean(cpu_psnr)), 'png_hashes': png_hashes,
                           'frames': 20, 'rgb_depth_finite': True}


def run(config_path):
    started = time.perf_counter()
    config = json.loads(Path(config_path).read_text())
    required = ('id', 'scene', 'checkpoint', 'runtime_metadata', 'iteration', 'repo', 'dataset', 'quantization', 'compression', 'evaluation', 'output_dir', 'seed')
    if any(k not in config for k in required) or config['scene'] != 'bouncingballs':
        raise ValueError('Incomplete config or unsupported scene')
    if config['seed'] != 0:
        raise ValueError('Pinned upstream safe_state uses seed=0; this bench currently supports that seed only')
    model_name = config['compression']['model']
    if model_name not in ('float32', 'quantized', 'fixed8', *MODELS):
        raise ValueError('Unsupported model')
    bits = int(config['quantization']['bits'])
    if model_name in ('fixed8', *MODELS) and bits != 8:
        raise ValueError('Entropy baseline supports only 8 bits')
    if model_name == 'float32' and bits != 32 or model_name != 'float32' and bits not in (8,12,16):
        raise ValueError('Invalid quantization bit depth')
    if model_name in MODELS and config['compression']['coder'] != 'range':
        raise ValueError('Only range coding is implemented')
    output = resolve(config['output_dir'])
    output.mkdir(parents=True, exist_ok=False)
    logs = output/'logs'
    logs.mkdir()
    write_json(output/'config.json', config)
    checkpoint = resolve(config['checkpoint'])
    source = checkpoint.parents[2]
    source_hash = sha(checkpoint)
    runtime = resolve(config['runtime_metadata'])
    core_sources = source_identity(resolve(config['repo']))
    states = load_checkpoint(checkpoint)
    if config.get('lossless_input'):
        lossless = resolve(config['lossless_input'])
    else:
        lossless = output/'input_float32'
        export_lossless(checkpoint, runtime, lossless)
    original_tables, buffers, manifest = import_tables(lossless)
    if manifest['source_sha256'] != source_hash:
        raise ValueError('Export/checkpoint identity mismatch')
    for key in KEYS:
        if not torch.equal(states[0][key], original_tables[key]):
            raise ValueError('Lossless restore mismatch')
    count = sum(t.numel() for t in original_tables.values())
    timing = {}
    symbols_equal = None
    if model_name == 'float32':
        restored, new_buffers = original_tables, buffers
        total = sum(p.stat().st_size for p in lossless.iterdir() if p.is_file())
        compression = {'model': 'float32', 'symbols': count, 'actual_bitstream_bytes': None,
            'coded_payload_bytes': count*4, 'model_overhead_bytes': 0,
            'metadata_framing_bytes': total-count*4, 'total_compressed_bytes': total,
            'bits_per_symbol': total*8/count, 'compression_ratio_float32': count*4/total,
            'compression_ratio_fixed8_payload': count/total, 'theoretical_empirical_bits': None,
            'theoretical_bits_per_symbol': None, 'encode_seconds': None, 'decode_seconds': None,
            'status': 'lossless raw float32 reference, not entropy coded'}
        decoded = lossless
    else:
        if config.get('quantized_input'):
            quantized = resolve(config['quantized_input'])
        else:
            quantized = output/'input_quantized'
            export_quantized(lossless, quantized, bits, config['quantization']['scope'])
        q_manifest = json.loads((quantized/'manifest.json').read_text())
        if (q_manifest['bits'] != bits or q_manifest['scope'] != config['quantization']['scope'] or
                q_manifest['source_sha256'] != source_hash):
            raise ValueError('Quantized input/config mismatch')
        if model_name == 'quantized':
            decoded = quantized
            restored, new_buffers, _ = import_tables(decoded)
            total = sum(p.stat().st_size for p in quantized.iterdir() if p.is_file())
            payload = sum(m['payload']['bytes'] for m in q_manifest['grids'].values())
            compression = {'model': 'quantized', 'symbols': count, 'actual_bitstream_bytes': None,
                'coded_payload_bytes': payload, 'model_overhead_bytes': 0, 'metadata_framing_bytes': total-payload,
                'total_compressed_bytes': total, 'bits_per_symbol': total*8/count,
                'compression_ratio_float32': count*4/total, 'compression_ratio_fixed8_payload': count/total,
                'theoretical_bits_per_symbol': None, 'theoretical_empirical_bits': None,
                'fixed_ideal_bits': count*bits, 'encode_seconds': None, 'decode_seconds': None,
                'status': 'direct quantization reference; uint16 container for 12/16 bits'}
        else:
            compression = entropy.encode(quantized, output/'bitstream.bin', model_name)
            decoded = output/'decoded'
            # New interpreter; arguments contain no source or quantized input path.
            wall = execute([sys.executable, '-m', 'research.experiment_bench.cli', 'decode',
                str(output/'bitstream.bin'), str(decoded), '--record', str(output/'decode.json')], logs/'decode.log')
            decoder_record = json.loads((output/'decode.json').read_text())
            compression.update(decode_seconds=decoder_record['decode_seconds'])
            timing['decode_process_wall_seconds'] = wall
            decoded_manifest = json.loads((decoded/'manifest.json').read_text())
            for key in KEYS:
                a = _read_array(quantized, q_manifest['grids'][key]['payload'])
                b = _read_array(decoded, decoded_manifest['grids'][key]['payload'])
                if not np.array_equal(a, b):
                    raise ValueError('Entropy symbol round trip mismatch')
            symbols_equal = True
            restored, new_buffers, _ = import_tables(decoded)
            direct, direct_buffers, _ = import_tables(quantized)
            if not all(torch.equal(restored[k], direct[k]) for k in KEYS):
                raise ValueError('Decoded dequantization differs from direct quantization')
        mse_sum = sum(float(np.square(original_tables[k].numpy().astype(np.float64)-restored[k].numpy().astype(np.float64)).sum()) for k in KEYS)
        compression['parameter_mse'] = mse_sum/count
    compression.setdefault('parameter_mse', 0.)
    compression['fixed_ideal_bits'] = count*(32 if model_name == 'float32' else bits)
    compression['fixed_ideal_bytes_without_metadata'] = (compression['fixed_ideal_bits']+7)//8
    compression['hashgrid_only'] = True
    compression['quantization_bits'] = bits
    compression['quantization_scope'] = config['quantization']['scope']
    compression['scene_gaussians_mlp_excluded'] = True
    write_json(output/'compression.json', compression)
    write_json(output/'model_info.json', {'model': model_name, 'histogram_granularity': 'table and channel',
        'context': 'q0 >> 4, 16 classes' if model_name == 'channel_context' else None,
        'q0_order': 'all rows ascending', 'q1_order': 'class ascending, rows ascending within class' if model_name == 'channel_context' else 'all rows ascending',
        'histogram_precision': 16, 'coder_precision': 24, 'smoothing': 'Laplace alpha=1 + minimum mass=1',
        'cdf_in_bitstream': model_name in MODELS, 'future_symbol_access': False})
    model = prepare_model(source, output, substitute(states, restored, new_buffers), config['iteration'])
    verification = {'lossless_export_import': True, 'symbols_exact': symbols_equal,
        'dequantized_tensors_equal_direct_quantization': True, 'decoder_new_process': model_name in ('fixed8', *MODELS),
        'state_shapes_dtypes_offsets_verified': True}
    if config['evaluation'].get('render', True):
        metrics, render_times, render_check = render_evaluate(model, config, checkpoint, logs, output/'inference.json')
        timing.update(render_times)
        verification.update(render_check)
        if config.get('direct_render_reference'):
            reference = resolve(config['direct_render_reference'])
            other = json.loads((reference/'inference.json').read_text())
            current = json.loads((output/'inference.json').read_text())
            if current['frames'] != other['frames']:
                raise ValueError('Float RGB differs from direct quantization/reference')
            expected_png = [sha(p) for p in sorted((reference/f'model/test/ours_{config["iteration"]}/renders').glob('*.png'))]
            if expected_png != render_check['png_hashes']:
                raise ValueError('PNG differs from direct quantization/reference')
            reference_metrics = json.loads((reference/'metrics.json').read_text())['values']
            if metrics != reference_metrics:
                raise ValueError('Metrics differ from direct quantization/reference')
            verification['float_render_png_metrics_equal_reference'] = True
        metrics_record = {'status': 'PASS', 'values': metrics, 'protocol': 'upstream PNG, LPIPS VGG [0,1] normalize=False'}
        shutil.copytree(model/f'test/ours_{config["iteration"]}/renders', output/'renders')
    else:
        metrics_record = {'status': 'NOT RUN', 'reason': 'evaluation.render=false', 'values': None}
        verification['render'] = 'NOT RUN'
    write_json(output/'metrics.json', metrics_record)
    if sha(checkpoint) != source_hash:
        raise ValueError('Source checkpoint changed')
    verification['source_checkpoint_unchanged'] = True
    verification['passed'] = True
    write_json(output/'verification.json', verification)
    timing['total_seconds'] = time.perf_counter()-started
    timing['encode_seconds'] = compression.get('encode_seconds')
    timing['decode_seconds'] = compression.get('decode_seconds')
    write_json(output/'timings.json', timing)
    write_json(output/'manifest.json', {'id': config['id'], 'date': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat(),
        'checkpoint_path': str(checkpoint), 'checkpoint_sha256': source_hash, 'source_revision': REVISION,
        'core_source_sha256': core_sources,
        'iteration': config['iteration'], 'seed': config['seed'], 'format_version': entropy.VERSION,
        'coder_version': entropy.CODER_VERSION, 'torch_version': torch.__version__, 'python_version': sys.version,
        'config_sha256': sha(output/'config.json'), 'bitstream_sha256': sha(output/'bitstream.bin') if (output/'bitstream.bin').exists() else None,
        'diagnostic_float32_model_excluded_from_compression_size': True,
        'renders_path': str(model/f'test/ours_{config["iteration"]}/renders')})
    print(json.dumps({'id': config['id'], 'compression': compression, 'metrics': metrics_record, 'passed': True}, indent=2))


def aggregate(folder, output):
    rows = []
    for manifest_path in sorted(Path(folder).glob('*/manifest.json')):
        experiment = manifest_path.parent
        if not (experiment/'verification.json').exists():
            continue
        manifest = json.loads(manifest_path.read_text())
        compression = json.loads((experiment/'compression.json').read_text())
        metric = json.loads((experiment/'metrics.json').read_text())
        rows.append({'id': manifest['id'], 'checkpoint_sha256': manifest['checkpoint_sha256'],
            'iteration': manifest['iteration'], **compression, 'metrics_status': metric['status'], **(metric['values'] or {})})
    if not rows:
        raise ValueError('No completed experiments')
    fixed = {(r['checkpoint_sha256'],r.get('quantization_scope','table')):r['total_compressed_bytes']
             for r in rows if r['model']=='fixed8'}
    for row in rows:
        size=fixed.get((row['checkpoint_sha256'],row.get('quantization_scope','table')))
        row['compression_ratio_fixed8_total']=size/row['total_compressed_bytes'] if size else None
    Path(output).mkdir(parents=True, exist_ok=True)
    csv_save(Path(output)/'results.csv', rows)
    write_json(Path(output)/'results.json', rows)
    print(f'Aggregated {len(rows)} experiments')


def main():
    p = argparse.ArgumentParser()
    commands = p.add_subparsers(dest='command', required=True)
    r = commands.add_parser('run'); r.add_argument('config')
    d = commands.add_parser('decode'); d.add_argument('bitstream'); d.add_argument('output'); d.add_argument('--record')
    e = commands.add_parser('encode'); e.add_argument('quantized'); e.add_argument('bitstream'); e.add_argument('--model', choices=['fixed8', *MODELS], required=True)
    a = commands.add_parser('aggregate'); a.add_argument('experiments'); a.add_argument('output')
    args = p.parse_args()
    if args.command == 'run': run(args.config)
    elif args.command == 'decode':
        record = entropy.decode(args.bitstream, args.output)
        if args.record: write_json(args.record, record)
        print(json.dumps(record))
    elif args.command == 'encode': print(json.dumps(entropy.encode(args.quantized, args.bitstream, args.model)))
    else: aggregate(args.experiments, args.output)


if __name__ == '__main__':
    main()
