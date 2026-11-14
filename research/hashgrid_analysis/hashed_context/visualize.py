"""Descriptive plots of coarse-only collision contexts; no target/model access.

Usage: python -m research.hashgrid_analysis.hashed_context.visualize RUN_DIRECTORY
Writes only a fresh RUN_DIRECTORY/diagnostics directory. All summaries use all
allocated slots; plot samples and the bounded illustrative pair search are
explicitly marked. Input contains no fine symbols.
"""
from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np

QUANTILES = [0, .01, .05, .25, .5, .75, .9, .95, .99, 1]
GEOMETRY = ['G0', 'G1', 'G2', 'G3']
PAIRS = ['L4_to_L5', 'L5_to_L6']
SEED = 20261013


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(4 << 20), b''):
            h.update(data)
    return h.hexdigest()


def peak_rss():
    """Process high-water mark in bytes; not incremental experiment memory."""
    if os.name == 'nt':
        class MemoryCounters(ctypes.Structure):
            _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong),
                        ('PeakWorkingSetSize', ctypes.c_size_t),
                        ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t),
                        ('PeakPagefileUsage', ctypes.c_size_t)]
        counters = MemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        api = ctypes.WinDLL('psapi', use_last_error=True).GetProcessMemoryInfo
        api.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        if api(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return int(counters.PeakWorkingSetSize)
        return None
    try:
        import resource
        import sys
        amount = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(amount if sys.platform == 'darwin' else amount * 1024)
    except ImportError:
        return None


def describe(values):
    x = np.asarray(values, np.float64)
    if not x.size:
        return {'n': 0, 'quantiles': None, 'zero_count': 0, 'nonzero_count': 0}
    if not np.isfinite(x).all():
        raise ValueError('Nonfinite context in diagnostic')
    nonzero = x[x != 0]
    return {'n': int(x.size), 'min': float(x.min()), 'max': float(x.max()),
            'mean': float(x.mean()), 'population_std': float(x.std()),
            'zero_count': int((x == 0).sum()), 'nonzero_count': int(nonzero.size),
            'zero_fraction': float((x == 0).mean()),
            'quantiles': dict(zip(map(str, QUANTILES), map(float, np.quantile(x, QUANTILES)))),
            'positive_quantiles': dict(zip(map(str, QUANTILES), map(float, np.quantile(nonzero, QUANTILES)))) if nonzero.size else None}


def load_pair(folder):
    source = folder / 'contexts.npz'
    with np.load(source, allow_pickle=False) as file:
        data = {key: file[key] for key in ('slot_index', 'nominal_count', 'point_count',
            'geometry', 'canonical_ordinal', 'canonical_vertex', 'canonical_coordinates',
            'canonical_features', 'mean', 'std')}
    n = len(data['slot_index'])
    if not np.array_equal(data['slot_index'], np.arange(n)):
        raise ValueError('Slots are not a complete unique ascending array')
    nominal, point, geo = data['nominal_count'], data['point_count'], data['geometry']
    if np.any(nominal < point) or np.any(point < 0):
        raise ValueError('Invalid correspondence counts')
    expected = np.zeros(n, np.uint8)
    expected[(nominal > 0) & (point == 0)] = 1
    expected[point == 1] = 2
    expected[point > 1] = 3
    if not np.array_equal(geo, expected):
        raise ValueError('Geometry category mismatch')
    for key in ('mean', 'std', 'canonical_features'):
        if data[key].shape != (n, 2) or not np.isfinite(data[key]).all():
            raise ValueError('Invalid two-channel feature shape/value')
    if np.any(data['std'] < 0) or np.any(data['std'][point == 1] != 0):
        raise ValueError('Population std must be nonnegative and singleton std exact zero')
    empty = point == 0
    for key in ('mean', 'std', 'canonical_features'):
        if np.any(data[key][empty] != 0):
            raise ValueError('Empty fallback must be exact zeros')
    meta_file = folder / 'decoder_bundle' / 'decoder_metadata.json'
    meta = json.loads(meta_file.read_text(encoding='utf-8'))
    quant = meta['coarse']['quantization']
    if 'step' in quant:
        step = float(quant['step'])
    else:
        # Existing table-wise uint8 quantizer defines this from its stored endpoints.
        step = (float(quant['max']) - float(quant['min'])) / 255
    if not np.isfinite(step) or step <= 0:
        raise ValueError('Positive quantization step required')
    return data, step, {'contexts_path': str(source.resolve()), 'contexts_sha256': sha(source),
                        'metadata_path': str(meta_file.resolve()), 'metadata_sha256': sha(meta_file)}


def count_hist(values):
    counts = np.bincount(values)
    return [{'multiplicity': i, 'slots': int(count)} for i, count in enumerate(counts)]


def pair_summary(data, step, sources):
    nominal, point, geo = data['nominal_count'], data['point_count'], data['geometry']
    result = {'allocated_slots': int(len(geo)), 'nominal_correspondences': int(nominal.sum()),
        'point_correspondences': int(point.sum()), 'quantization_step': step,
        'geometry_counts': {name: int((geo == i).sum()) for i, name in enumerate(GEOMETRY)},
        'nominal_multiplicity_histogram': count_hist(nominal),
        'point_multiplicity_histogram': count_hist(point), 'sources': sources,
        'channels': {}, 'vector_dispersion': {}}
    strata = {'all_allocated': np.ones(len(geo), bool), 'point_singleton_G2': geo == 2,
              'point_colliding_G3': geo == 3, 'nominal_colliding': nominal > 1,
              'point_empty_G0_G1': point == 0}
    for channel in range(2):
        result['channels'][str(channel)] = {}
        for name, mask in strata.items():
            result['channels'][str(channel)][name] = {'mean': describe(data['mean'][mask, channel]),
                'std': describe(data['std'][mask, channel]),
                'canonical_minus_mean': describe(data['canonical_features'][mask, channel].astype(np.float64) - data['mean'][mask, channel])}
    norm = np.sqrt(np.square(data['std']).sum(axis=1))
    for name, mask in strata.items():
        result['vector_dispersion'][name] = describe(norm[mask])
    colliding = geo == 3
    result['colliding_both_channels_exact_zero_std'] = int((colliding & (data['std'] == 0).all(axis=1)).sum())
    result['colliding_at_least_one_nonzero_std'] = int((colliding & (data['std'] > 0).any(axis=1)).sum())
    result['colliding_sigma_norm_gt_one_quantization_step'] = int((colliding & (norm > step)).sum())
    result['colliding_sigma_norm_gt_quarter_quantization_step'] = int((colliding & (norm > step/4)).sum())
    return result


def illustrative_pairs(data, step, max_examples=3):
    """Bounded deterministic search, not a global optimal nearest-neighbour claim.

    Compare G3 slots from upper vs lower sigma-norm halves. A search query uses
    a fixed Euclidean mean tolerance of step/4, at most 8192 lower-half points
    within the first-channel window, and at most 2048 higher-half queries.
    """
    eligible = np.flatnonzero(data['geometry'] == 3)
    mean, std = data['mean'], data['std']
    sigma = np.sqrt(np.square(std).sum(axis=1))
    positive = eligible[sigma[eligible] > 0]
    method = {'category': 'G3 only', 'mean_l2_tolerance': step/4,
              'maximum_high_dispersion_queries': 2048, 'maximum_low_candidates_per_query': 8192,
              'search_is_bounded_illustrative_not_exhaustive': True,
              'selection_uses_only_coarse_context': True}
    if not len(positive):
        return [], {**method, 'reason': 'All G3 sigma norms are exact zero'}
    median = float(np.median(sigma[eligible]))
    low = eligible[sigma[eligible] <= median]
    high = positive[sigma[positive] > median]
    if not len(low) or not len(high):
        return [], {**method, 'reason': 'No distinct low/high dispersion groups'}
    low = low[np.lexsort((low, mean[low, 0]))]
    order = high[np.lexsort((high, -sigma[high]))][:2048]
    sorted_mu0 = mean[low, 0]
    tolerance = step/4
    choices = []
    for high_slot in order:
        lo = int(np.searchsorted(sorted_mu0, mean[high_slot, 0] - tolerance, side='left'))
        hi = int(np.searchsorted(sorted_mu0, mean[high_slot, 0] + tolerance, side='right'))
        if lo == hi:
            continue
        if hi-lo > 8192:
            positions = np.linspace(lo, hi-1, 8192, dtype=np.int64)
            candidates = low[positions]
        else:
            candidates = low[lo:hi]
        distance = np.sqrt(np.square(mean[candidates] - mean[high_slot]).sum(axis=1))
        valid = distance <= tolerance
        candidates, distance = candidates[valid], distance[valid]
        if not len(candidates):
            continue
        # Largest sigma contrast, then smallest distance, then slot index.
        rank = np.lexsort((candidates, distance, sigma[candidates]))
        j = int(rank[0]); low_slot = int(candidates[j])
        contrast = float(sigma[high_slot] - sigma[low_slot])
        if contrast <= step/4:
            continue
        choices.append((contrast, float(distance[j]), low_slot, int(high_slot)))
    choices.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))
    examples, used = [], set()
    for difference, distance, a, b in choices:
        if a in used or b in used:
            continue
        used.update((a, b))
        item = {'example_index': len(examples), 'mean_l2_distance': distance,
                'mean_tolerance': tolerance, 'sigma_norm_difference': difference,
                'sigma_difference_in_quantization_steps': difference/step, 'low_slot': a, 'high_slot': b}
        for role, slot in (('low', a), ('high', b)):
            item[f'{role}_nominal_count'] = int(data['nominal_count'][slot])
            item[f'{role}_point_count'] = int(data['point_count'][slot])
            item[f'{role}_canonical_ordinal'] = int(data['canonical_ordinal'][slot])
            item[f'{role}_canonical_vertex'] = data['canonical_vertex'][slot].tolist()
            item[f'{role}_mean'] = mean[slot].tolist()
            item[f'{role}_std'] = std[slot].tolist()
            item[f'{role}_sigma_norm'] = float(sigma[slot])
        examples.append(item)
        if len(examples) == max_examples:
            break
    return examples, {**method, 'low_group_slots': len(low), 'high_group_slots': len(high),
                      'queries_evaluated': len(order), 'qualifying_query_pairs': len(choices),
                      'examples_returned': len(examples),
                      'interpretation': 'Different dispersion at similar means is descriptive, not an entropy or predictiveness result'}


def write_json(path, data):
    with path.open('x', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write('\n')


def save_plot(fig, directory, stem, plt):
    for extension in ('png', 'svg'):
        path = directory / (stem + '.' + extension)
        if path.exists():
            raise FileExistsError(path)
        fig.savefig(path, dpi=160, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def make_plots(arrays, summaries, output):
    os.environ['MPLCONFIGDIR'] = str(output / 'matplotlib_config')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for row, name in enumerate(PAIRS):
        stats = summaries[name]
        max_degree = max(len(stats['nominal_multiplicity_histogram']), len(stats['point_multiplicity_histogram']))
        positions = np.arange(max_degree)
        for key, label, shift, color in (('nominal_multiplicity_histogram', 'Nominal', -.2, '#4477aa'),
                                       ('point_multiplicity_histogram', 'Admissible point', .2, '#cc6677')):
            heights = np.zeros(max_degree)
            for item in stats[key]:
                heights[item['multiplicity']] = item['slots']
            ax[row, 0].bar(positions + shift, heights, width=.38, label=label, color=color)
        ax[row, 0].set(xlabel='Correspondences per hash slot', ylabel='Allocated slots',
                       xticks=positions, title=name.replace('_to_', ' → '))
        ax[row, 0].legend()
        heights = [stats['geometry_counts'][key] for key in GEOMETRY]
        bars = ax[row, 1].bar(GEOMETRY, heights, color=['#999999', '#ddcc77', '#88ccee', '#117733'])
        for bar, value in zip(bars, heights):
            ax[row, 1].text(bar.get_x()+bar.get_width()/2, max(value, 0), f'{value:,}', ha='center', va='bottom')
        ax[row, 1].set(ylabel='Allocated slots', title='Point-context categories')
        ax[row, 1].set_ylim(0, max(heights)*1.16)
    fig.suptitle('Exact multiplicity and geometry: every allocated slot counted once')
    save_plot(fig, output, 'multiplicity_geometry', plt)

    fig, ax = plt.subplots(2, 4, figsize=(18, 8), constrained_layout=True)
    for row, name in enumerate(PAIRS):
        data = arrays[name]
        for channel in range(2):
            colliding = data['std'][data['geometry'] == 3, channel]
            singleton = data['std'][data['geometry'] == 2, channel]
            positive = colliding[colliding > 0]
            linear = ax[row, channel*2]
            log = ax[row, channel*2+1]
            linear.hist(colliding, bins=64, color='#117733', alpha=.75,
                label=f'G3: {len(colliding):,} slots')
            linear.axvline(0, color='#4477aa', linewidth=2,
                label=f'G2: {len(singleton):,}; all Std=0')
            linear.set(xlabel='Population Std', ylabel='Slot count', title=f'{name}: channel {channel}')
            linear.legend(fontsize=8)
            if len(positive):
                log.hist(np.log10(positive), bins=64, color='#117733', alpha=.75)
            log.set(xlabel='log10(Std), strictly positive only', ylabel='Slot count',
                title=f'G3 nonzero: {len(positive):,}; zero: {int((colliding == 0).sum()):,}')
    fig.suptitle('Singleton vs colliding dispersion; exact zero distinguished from positive values')
    save_plot(fig, output, 'std_distributions', plt)

    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    sampling = {}
    for row, name in enumerate(PAIRS):
        data = arrays[name]
        indices = np.flatnonzero(data['geometry'] == 3)
        if len(indices) > 80000:
            indices = np.sort(np.random.default_rng(SEED + row).choice(indices, 80000, replace=False))
        sampling[name] = {'G3_slots_plotted': len(indices), 'G3_total': int((data['geometry'] == 3).sum()),
                          'seed': SEED + row, 'budget': 80000, 'uniform_without_replacement': True}
        for channel in range(2):
            axis = axes[row, channel]
            artist = axis.hexbin(data['mean'][indices, channel], data['std'][indices, channel],
                gridsize=60, bins='log', mincnt=1, cmap='viridis')
            fig.colorbar(artist, ax=axis, label='Sampled slot count (log color scale)')
            axis.set(xlabel='Mean decoder-available coarse feature', ylabel='Population Std',
                title=f'{name}: channel {channel}; G3 only')
    fig.suptitle('Coarse mean vs coarse dispersion: descriptive features, no fine targets')
    save_plot(fig, output, 'mean_std_hexbin', plt)
    return sampling


def run(run_directory):
    started = time.perf_counter()
    run_directory = Path(run_directory).resolve()
    output = run_directory / 'diagnostics'
    output.mkdir(exist_ok=False)
    arrays, summaries, examples, source_hashes = {}, {}, [], {}
    for name in PAIRS:
        data, step, sources = load_pair(run_directory / name)
        arrays[name] = data
        source_hashes[name] = sources['contexts_sha256']
        summary = pair_summary(data, step, sources)
        found, search = illustrative_pairs(data, step)
        summary['illustrative_pair_search'] = search
        summaries[name] = summary
        for item in found:
            examples.append({'pair': name, **item})
    plot_sampling = make_plots(arrays, summaries, output)
    write_json(output / 'examples.json', examples)
    flat_examples = []
    for example in examples:
        row = {}
        for key, value in example.items():
            if isinstance(value, list):
                for component, scalar in enumerate(value):
                    row[f'{key}_{component}'] = scalar
            else:
                row[key] = value
        flat_examples.append(row)
    with (output / 'examples.csv').open('x', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(flat_examples[0]) if flat_examples else ['pair', 'reason'])
        writer.writeheader()
        writer.writerows(flat_examples)
    for name in PAIRS:
        if sha(run_directory / name / 'contexts.npz') != source_hashes[name]:
            raise ValueError('Context source changed during diagnostics')
    result = {'scope': 'coarse-only descriptive diagnostic; no fine targets, probabilities, entropy or coding',
        'statistics_population': 'all allocated slots, exact per-stratum summaries',
        'quantile_method': 'NumPy linear empirical quantiles',
        'std_definitions': 'Input population std across admissible point correspondences. Diagnostic describe.population_std summarizes variation across slots and is a different statistic.',
        'zero_test': 'exact == 0, no near-zero threshold substituted',
        'pairs': summaries, 'plot_sampling': plot_sampling,
        'elapsed_seconds': time.perf_counter()-started,
        'process_peak_rss_bytes': peak_rss(), 'peak_rss_is_total_process_not_incremental': True,
        'source_files_unchanged': True, 'numpy_version': np.__version__}
    write_json(output / 'summary.json', result)
    note = '''# Метод диагностических графиков

Все численные summaries рассчитаны по всем выделенным hash slots; G2 означает
ровно одно допустимое point correspondence, G3 — больше одного. Nominal collision
и point collision не тождественны у boundary slots. Empty fallback сохранён в
общей таблице, а отдельно выделенные G3-графики не включают пустые slots.

Population Std поступает из проверяемого canonical CPU context. Статистика
`describe.population_std` в JSON описывает распределение значений по slots и
не является тем же Std внутри отдельного colliding slot. Exact zero отделён
от строго положительных чисел без произвольного near-zero порога.

Multiplicity и одномерные Std histogram используют все соответствующие slots.
Mean/Std hexbin показывает до 80000 равномерно выбранных G3 slots на уровень с
фиксированным seed. Это diagnostic sample; точные summaries не используют
downsampling. Логарифм применяется только к положительным Std или цвету counts.

Примеры похожих средних выбираются только по coarse-only данным. Допуск L2
разности двухкомпонентных mean равен одной четверти существующего quantization
step. Поиск ограничен 2048 query и 8192 candidates/query, поэтому не доказывает
глобально оптимальные nearest neighbours и не исключает другие пары. Три
пары на уровень не повторяют slots. Различие Std должно превосходить step/4.

Эти графики и примеры не оценивают conditional entropy, качество предсказания
fine symbols либо выигрыш полного файла. Такие гипотезы остаются непроверенными.
'''
    with (output / 'METHOD.md').open('x', encoding='utf-8') as file:
        file.write(note)
    artifact_paths = sorted(path for path in output.iterdir() if path.is_file())
    write_json(output / 'artifact_hashes.json', {path.name: sha(path) for path in artifact_paths})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    result = run(args.run_directory)
    print(json.dumps({'status': 'PASS', 'output': str(args.run_directory.resolve() / 'diagnostics'),
                      'elapsed_seconds': result['elapsed_seconds'],
                      'process_peak_rss_bytes': result['process_peak_rss_bytes'],
                      'examples_per_pair': {key: item['illustrative_pair_search'].get('examples_returned', 0)
                         for key, item in result['pairs'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
