"""CPU statistics, interchange round trip, and six scalar-quantization variants."""
import argparse
import csv
import json
import shutil
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

from .codec import (KEYS, _read_array, empirical_entropy, export_lossless,
                    export_quantized, import_tables, load_checkpoint, sha,
                    substitute, write_json)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'outputs/grid4d/bouncingballs-audit-200'
OUT = ROOT / 'research/phase2'


def csv_save(path, records):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in records for k in r)))
        writer.writeheader()
        writer.writerows(records)


def statistics(x):
    y = x.astype(np.float64)
    counts, edges = np.histogram(y, bins=80)
    return {'min': float(y.min()), 'max': float(y.max()), 'mean': float(y.mean()),
            'std': float(y.std()), 'parameters': x.size, 'unique_values': np.unique(x).size,
            'zero_fraction': float(np.mean(x == 0)),
            'histogram_counts': counts.tolist(), 'histogram_edges': edges.tolist()}


def histogram_plot(records, path, title):
    width, panel_h = 1100, 205
    image = Image.new('RGB', (width, 45 + panel_h * len(records)), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((20, 12), title, fill='black')
    for i, (label, s) in enumerate(records):
        top = 50 + panel_h * i
        draw.text((20, top), f'{label} | N={s["parameters"]} | mean={s["mean"]:.5g} std={s["std"]:.5g}', fill='black')
        counts = np.asarray(s['histogram_counts'], dtype=float)
        heights = np.log10(counts + 1)
        maximum = max(1, heights.max())
        for j, h in enumerate(heights):
            left = 50 + j * 12
            draw.rectangle((left, top + 150 - int(110 * h / maximum), left + 10, top + 150), fill=(35, 110, 170))
        draw.text((50, top + 157), f'min={s["min"]:.6g}', fill='black')
        draw.text((830, top + 157), f'max={s["max"]:.6g}', fill='black')
        draw.text((50, top + 177), 'Vertical: log10(count+1). Horizontal: scalar feature value. Each panel has its own range.', fill='black')
    image.save(path)


def prepare_model(source, folder, states, iteration=200):
    target = folder / 'model'
    (target / f'deform/iteration_{iteration}').mkdir(parents=True)
    (target / f'point_cloud/iteration_{iteration}').mkdir(parents=True)
    shutil.copy2(source / 'cfg_args', target / 'cfg_args')
    shutil.copy2(source / f'point_cloud/iteration_{iteration}/point_cloud.ply', target / f'point_cloud/iteration_{iteration}/point_cloud.ply')
    torch.save(states, target / f'deform/iteration_{iteration}/deform.pth')
    return target


def run(source, runtime, out, iteration=200):
    started = time.perf_counter()
    out.mkdir(parents=True, exist_ok=False)
    checkpoint = source / f'deform/iteration_{iteration}/deform.pth'
    states = load_checkpoint(checkpoint)
    source_hash = sha(checkpoint)
    metadata = export_lossless(checkpoint, runtime, out / 'lossless')
    tables, buffers, _ = import_tables(out / 'lossless')
    for key in KEYS:
        assert torch.equal(states[0][key], tables[key]), key
    for key, value in buffers.items():
        assert torch.equal(states[0][key], value), key
    (out / 'plots').mkdir()
    stats_records, grid_stats = [], []
    for key in KEYS:
        x = tables[key].numpy()
        whole = statistics(x)
        grid_stats.append((key, whole))
        level_stats = []
        meta = metadata['grids'][key]
        for level, (a, b) in enumerate(zip(meta['offsets'], meta['offsets'][1:])):
            s = statistics(x[a:b])
            stats_records.append({'grid': key, 'level': level, 'row_start': a, 'row_end': b, **s})
            level_stats.append((f'{key} level {level}', s))
        histogram_plot(level_stats, out / f'plots/{key.split(".")[0]}-levels.png', f'HashGrid per-level histograms ({iteration}-iteration checkpoint)')
    histogram_plot(grid_stats, out / 'plots/tables.png', 'Spatial and spatiotemporal tables; histogram similarity is not evidence of dependence')
    write_json(out / 'statistics.json', {'tables': dict(grid_stats), 'levels': stats_records})
    csv_save(out / 'statistics.csv', [{k: v for k, v in s.items() if not k.startswith('histogram_')} for s in stats_records])
    n = sum(t.numel() for t in tables.values())
    raw_bytes = n * 4
    def storage(folder):
        meta_bytes = (folder / 'manifest.json').stat().st_size
        buffer_bytes = sum(p.stat().st_size for p in folder.glob('*') if p.name.endswith(('.offsets.bin', '.base_resolution.bin', '.per_level_scale.bin')))
        payload_bytes = sum(m['payload']['bytes'] for m in json.loads((folder / 'manifest.json').read_text())['grids'].values())
        return {'serialized_bytes': meta_bytes + buffer_bytes + payload_bytes,
                'metadata_json_bytes': meta_bytes, 'buffer_bytes': buffer_bytes, 'payload_bytes': payload_bytes}
    results = [{'variant': 'original', 'mse': 0., 'scalar_count': n, 'raw_float32_bytes': raw_bytes,
                **storage(out / 'lossless'), 'fixed_code_bits': n * 32,
                'fixed_with_metadata_bytes': storage(out / 'lossless')['serialized_bytes'],
                'empirical_bits_per_symbol': None, 'theoretical_entropy_bits': None}]
    prepare_model(source, out / 'original', states, iteration)
    prepare_model(source, out / 'restored', substitute(states, tables, buffers), iteration)
    entropy_rows = []
    for scope in ('table', 'level'):
        for bits in (16, 12, 8):
            name = f'{scope}-{bits}'
            folder = out / name
            manifest = export_quantized(out / 'lossless', folder, bits, scope)
            decoded, decoded_buffers, _ = import_tables(folder)
            error_sum, entropy_sum = 0., 0.
            for key in KEYS:
                x, y = tables[key].numpy(), decoded[key].numpy()
                error_sum += np.square(x.astype(np.float64) - y.astype(np.float64)).sum()
                meta = manifest['grids'][key]
                codes = _read_array(folder, meta['payload'])
                e = empirical_entropy(codes)
                entropy_rows.append({'variant': name, 'grid': key, 'level': 'all', **e,
                                     'fixed_bits': codes.size * bits,
                                     'fixed_reduction_vs_float32': 1 - bits / 32,
                                     'entropy_reduction_vs_float32': 1 - e['bits_per_symbol'] / 32})
                level_sum = 0.
                for level, (a, b) in enumerate(zip(meta['offsets'], meta['offsets'][1:])):
                    e_level = empirical_entropy(codes[a:b])
                    level_sum += e_level['theoretical_bits']
                    entropy_rows.append({'variant': name, 'grid': key, 'level': level, **e_level,
                                         'fixed_bits': codes[a:b].size * bits,
                                         'fixed_reduction_vs_float32': 1 - bits / 32,
                                         'entropy_reduction_vs_float32': 1 - e_level['bits_per_symbol'] / 32})
                entropy_sum += e['theoretical_bits'] if scope == 'table' else level_sum
            sizes = storage(folder)
            overhead = sizes['metadata_json_bytes'] + sizes['buffer_bytes']
            results.append({'variant': name, 'bits': bits, 'scope': scope, 'mse': float(error_sum / n),
                            'scalar_count': n, 'raw_float32_bytes': raw_bytes, **sizes,
                            'fixed_code_bits': n * bits, 'fixed_with_metadata_bytes': (n * bits + 7) // 8 + overhead,
                            'theoretical_entropy_bits': entropy_sum, 'empirical_bits_per_symbol': entropy_sum / n,
                            'theoretical_with_metadata_bytes': entropy_sum / 8 + overhead,
                            'fixed_reduction_vs_float32': 1 - bits / 32,
                            'entropy_reduction_vs_float32': 1 - entropy_sum / (n * 32)})
            prepare_model(source, folder, substitute(states, decoded, decoded_buffers), iteration)
            print(name, 'MSE', error_sum / n, 'H', entropy_sum / n, flush=True)
    write_json(out / 'entropy.json', entropy_rows)
    csv_save(out / 'entropy.csv', entropy_rows)
    write_json(out / 'summary.json', {'source_checkpoint_sha256': source_hash,
               'lossless_torch_equal': True, 'source_unchanged': sha(checkpoint) == source_hash,
               'variants': results, 'cpu_study_seconds': time.perf_counter() - started,
               'note': 'No packed bitstream. 12-bit symbols occupy uint16 containers. Entropy excludes a probability-model header and coder/framing overhead.'})
    print('Lossless round trip PASS; CPU study complete', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=SOURCE)
    p.add_argument('--runtime', type=Path, default=ROOT / 'research/audit/hashgrid-runtime.json')
    p.add_argument('--out', type=Path, default=OUT)
    p.add_argument('--iteration', type=int, default=200)
    args = p.parse_args()
    run(args.source, args.runtime, args.out, args.iteration)
