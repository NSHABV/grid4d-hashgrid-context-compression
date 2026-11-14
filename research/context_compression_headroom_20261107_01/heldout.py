"""Frozen block held-out diagnostic; all lengths are estimates, no entropy stream."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import time
import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
import numpy as np
from research.experiment_bench.models import frequencies, validate_frequencies
from research.experiment_bench.hashed_interlevel.core import fit_spec as old_fit_spec, classify as old_classify
import model_side
from context_replay import channel_classes, previous_vectorized

BLOCK = 4096
SEEDS = (0, 1, 2)
ROWS = {'IID': (1, 1), 'CHANNEL8': (1, 8), 'PREVIOUS8': (9, 9), 'Geometry4': (4, 4), 'MEAN8': (10, 10)}


def peak_rss_mib():
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb',wintypes.DWORD),('faults',wintypes.DWORD)] + [(name,ctypes.c_size_t) for name in
                ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
                 'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        api=ctypes.WinDLL('psapi'); kernel=ctypes.WinDLL('kernel32')
        kernel.GetCurrentProcess.restype=wintypes.HANDLE
        api.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        api.GetProcessMemoryInfo.restype=wintypes.BOOL
        counters=Counters(); counters.cb=ctypes.sizeof(counters)
        if not api.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
            raise OSError('GetProcessMemoryInfo failed')
        return counters.PeakWorkingSetSize/2**20
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024


def sha_array(x):
    return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def put(p, x):
    with Path(p).open('x', encoding='utf-8') as f:
        json.dump(x, f, ensure_ascii=False, indent=2, allow_nan=False)


def save(p, x):
    with Path(p).open('xb') as f:
        np.save(f, x, allow_pickle=False)


def npz(p, **arrays):
    with Path(p).open('xb') as f:
        np.savez(f, **arrays)


def split_blocks(n, seed):
    if n < 3 * BLOCK: raise ValueError('Not enough blocks for fixed held-out protocol')
    count = (n + BLOCK - 1) // BLOCK
    order = np.random.Generator(np.random.PCG64(seed)).permutation(count)
    nc, nv = int(np.floor(.20 * count)), int(np.floor(.16 * count))
    assignment = np.zeros(count, np.uint8)
    assignment[order[:nc]] = 2
    assignment[order[nc:nc+nv]] = 1
    slot_assignment = assignment[np.arange(n) // BLOCK]
    rows = {name: np.flatnonzero(slot_assignment == code) for name, code in (('fit', 0), ('validation', 1), ('check', 2))}
    if any(len(ids) == 0 for ids in rows.values()): raise ValueError('Empty split')
    return assignment, rows


def families(level, contexts):
    result = ['IID']
    if 6 <= level <= 10: result.extend(('CHANNEL8', 'PREVIOUS8'))
    if contexts is not None:
        if level not in (7, 8): raise ValueError('Mean8 restricted to L7/L8')
        result.extend(('Geometry4', 'MEAN8'))
    return result


def fit_edges(q, fit, family, contexts):
    if family in ('IID', 'Geometry4'): return np.empty((0,), np.float64)
    if family == 'CHANNEL8':
        return np.quantile(q[fit, 0].astype(np.float64), np.arange(1, 8) / 8, method='linear')
    if family == 'PREVIOUS8':
        eligible = fit[fit % BLOCK != 0]
        if not len(eligible): raise ValueError('No nonstart fit positions')
        return np.stack([np.quantile(q[eligible-1, ch].astype(np.float64), np.arange(1, 8) / 8,
                                     method='linear') for ch in range(2)])
    if family == 'MEAN8':
        old = old_fit_spec(contexts, fit, 'Mean8')
        return np.asarray(old['edges']['primary'], np.float64)
    raise ValueError(family)


def mean8_spec(edges):
    return {'name': 'Mean8', 'C': 10, 'edges': {'primary': edges.tolist(), 'std': [[], []]}}


def classes(q, family, edges, contexts):
    n = len(q)
    if family == 'IID': return np.tile(np.array([0, 1], np.uint8), (n, 1))
    if family == 'CHANNEL8': return channel_classes(q[:, 0], edges)
    if family == 'PREVIOUS8': return previous_vectorized(q, edges, BLOCK)
    if family == 'Geometry4':
        g = np.asarray(contexts['geometry'], np.uint8)
        if g.shape != (n,) or np.any(g > 3): raise ValueError('Invalid geometry')
        return np.column_stack((g, g + 4))
    if family == 'MEAN8':
        ids = old_classify(contexts, mean8_spec(edges))
        ids[:, 1] += 10
        return ids
    raise ValueError(family)


def assigned_counts(q, ids, fit, family):
    counts = np.zeros((sum(ROWS[family]), 256), np.int64)
    offset = 0
    for ch, count in enumerate(ROWS[family]):
        counts[offset:offset+count] = np.bincount(
            (ids[fit, ch].astype(np.int64)-offset) * 256 + q[fit, ch],
            minlength=count*256).reshape(count, 256)
        offset += count
    return counts


def fit_masses(q, ids, fit, family):
    counts = assigned_counts(q, ids, fit, family)
    # Separate start rows use all-fit IID priors. Those are fitting observations,
    # not an assertion that symbols are encoded twice. Assigned counts are saved.
    if family == 'PREVIOUS8':
        counts[0] = np.bincount(q[fit, 0], minlength=256)
        counts[9] = np.bincount(q[fit, 1], minlength=256)
    f = np.stack([frequencies(row) for row in counts])
    validate_frequencies(f)
    return counts, f


def model_spec(family, level, n):
    spec = {'family': family, 'version': 1, 'level': int(level), 'slots': int(n), 'channels': 2,
            'alphabet': 256, 'mass_total': 65536, 'mass_precision': 16,
            'threshold_rule': 'fit-only linear quantiles; duplicates retained; searchsorted right',
            'code_order': 'all channel0 then all channel1; slots ascending',
            'row_order': 'channel-major contiguous IDs; explicit mapping transmitted',
            'representation': 'unchanged frozen GLOBAL8 uint8; shared quantizer in full-grid metadata'}
    if family == 'IID': spec['context'] = 'one separately fitted marginal per channel'
    if family == 'CHANNEL8': spec['context'] = 'ch0 IID; ch1 uses bin8(decoded ch0 of same slot); one7edge array'
    if family == 'PREVIOUS8':
        spec.update(block_slots=BLOCK, context='bin8 previous decoded slot same channel within block',
                    code_order='ascending4096-slot blocks; slots ascending; channel0 then channel1 per slot',
                    first_slot='separate IID row fitted on all fit symbols in channel; reset each4096 slots')
    if family in ('MEAN8', 'Geometry4'):
        spec.update(coarse_level=int(level-1), geometry='G0 nominal empty; G1 eligible empty; G2 singleton; G3 collision',
                    geometry_metadata='official Grid4D geometry/hash/offsets/scales carried by shared full-grid mode metadata')
    if family == 'MEAN8':
        spec.update(context='exact mean of eligible correspondences from decoded GLOBAL8 coarse level; G0/G1 separate',
                    arithmetic='cpu-f32-separate-ufunc-corner0to7-anchor-f64-addat-xfast-popstd-v1')
    return spec


def _save_model(directory, scene, level, seed, q, fit, family, contexts, phase):
    directory.mkdir(parents=True, exist_ok=False)
    t = time.perf_counter(); edges = fit_edges(q, fit, family, contexts); threshold_time = time.perf_counter()-t
    t = time.perf_counter(); ids = classes(q, family, edges, contexts); context_time = time.perf_counter()-t
    t = time.perf_counter(); counts, masses = fit_masses(q, ids, fit, family); fitting_time = time.perf_counter()-t
    specification = model_spec(family, level, len(q))
    t = time.perf_counter()
    data, sizes = model_side.choose(masses, {'edges': edges}, specification, list(ROWS[family]))
    serialization_time = time.perf_counter()-t
    with (directory/'model.hcdm').open('xb') as f: f.write(data)
    save(directory/'classes.npy', ids); save(directory/'thresholds.npy', edges)
    npz(directory/'pmf.npz', counts=counts, assigned_counts=assigned_counts(q, ids, fit, family), masses=masses)
    selected = model_side.sizes(data)
    summary = {'scene': scene, 'level': level, 'seed': seed, 'family': family, 'phase': phase,
               'q_sha256': sha_array(q), 'class_ids_sha256': sha_array(ids),
               'thresholds_sha256': sha_array(edges), 'masses_sha256': sha_array(masses),
               'fit_slots': len(fit), 'side': selected,
               'effective_classes': [len(np.unique(ids[:, ch])) for ch in range(2)],
               'fit_effective_classes': [len(np.unique(ids[fit, ch])) for ch in range(2)],
               'physical_model_file_sha256': hashlib.sha256(data).hexdigest(),
               'all_transport_sizes': sizes,
               'timings': {'threshold_fitting_seconds': threshold_time, 'context_classification_seconds': context_time,
                           'histogram_fitting_seconds': fitting_time, 'serialization_seconds': serialization_time}}
    put(directory/'MODEL.json', summary)
    if family == 'MEAN8': put(directory/'MEAN8_SPEC.json', mean8_spec(edges))
    return {'classes': ids, 'masses': masses, 'summary': summary}


def _load_model(directory, q):
    summary = read(directory/'MODEL.json')
    ids = np.load(directory/'classes.npy', mmap_mode='r', allow_pickle=False)
    data = (directory/'model.hcdm').read_bytes()
    masses, thresholds, specification, row_counts, _ = model_side.deserialize(data)
    if sha_array(q) != summary['q_sha256'] or sha_array(ids) != summary['class_ids_sha256']:
        raise ValueError('Frozen q/classes changed')
    if hashlib.sha256(data).hexdigest() != summary['physical_model_file_sha256']:
        raise ValueError('Frozen model changed')
    if sha_array(masses) != summary['masses_sha256'] or sha_array(thresholds['edges']) != summary['thresholds_sha256']:
        raise ValueError('Frozen PMF/threshold changed')
    return {'classes': ids, 'masses': masses, 'summary': summary}


def _losses(q, model, ids):
    cls = model['classes'][ids]
    return -np.log2(model['masses'][cls, q[ids]].astype(np.float64)/65536.)


def evaluate(scene, level, seed, split, q, selected, models, contexts, *, shuffled=False):
    losses = {name: _losses(q, model, selected) for name, model in models.items()}
    groups = {'all': np.ones(len(selected), bool)}
    if contexts is not None:
        groups.update({f'G{g}': np.asarray(contexts['geometry'])[selected] == g for g in range(4)})
    rows = []
    for family, model in models.items():
        for group, mask in groups.items():
            for ch, cols in (('0', [0]), ('1', [1]), ('total', [0, 1])):
                value = losses[family][mask][:, cols]
                bits = float(value.sum(dtype=np.float64)); n = value.size
                iid = losses['IID'][mask][:, cols]
                geom = losses['Geometry4'][mask][:, cols] if 'Geometry4' in losses else None
                row = {'scene': scene, 'level': level, 'seed': seed, 'split': split,
                       'family': family, 'group': group, 'channel': ch, 'slots': int(mask.sum()),
                       'symbols': n, 'bits': bits, 'CE_bits_per_symbol': bits/n if n else None,
                       'ideal_payload_B': bits/8, 'gain_bits_vs_IID': float(iid.sum(dtype=np.float64)-bits),
                       'gain_CE_vs_IID': float((iid-value).mean()) if n else None,
                       'gain_bits_vs_Geometry4': float(geom.sum(dtype=np.float64)-bits) if geom is not None else None,
                       'gain_CE_vs_Geometry4': float((geom-value).mean()) if geom is not None and n else None,
                       'side_information_bytes': model['summary']['side']['side_information_bytes'],
                       'length_status': 'ESTIMATED_IDEAL_FINITE_PMF_NOT_BITSTREAM', 'shuffled': shuffled}
                if group == 'all' and ch == 'total':
                    row['full_level_ideal_projection_B'] = bits/n * q.size/8
                    row['full_level_paid_projection_B'] = row['full_level_ideal_projection_B'] + row['side_information_bytes']
                else:
                    row['full_level_ideal_projection_B'] = None; row['full_level_paid_projection_B'] = None
                rows.append(row)
    return rows


def shuffled_models(models, selected, family, seed, contexts, evidence=None):
    """Keep PMFs fixed; permute each channel independently within each stratum."""
    result = dict(models); rng = np.random.Generator(np.random.PCG64(10000+seed))
    cls = np.array(models[family]['classes'], copy=True)
    masks = [np.ones(len(selected), bool)] if family != 'MEAN8' else [contexts['geometry'][selected] == g for g in range(4)]
    for ch in range(2):
        for group_index, mask in enumerate(masks):
            ids = selected[mask]
            before = cls[ids, ch].copy() if evidence is not None else None
            cls[ids, ch] = cls[ids[rng.permutation(len(ids))], ch]
            if evidence is not None:
                after = cls[ids, ch]
                width = sum(ROWS[family])
                before_hist = np.bincount(before, minlength=width).astype(np.int64)
                after_hist = np.bincount(after, minlength=width).astype(np.int64)
                if not np.array_equal(before_hist, after_hist):
                    raise RuntimeError('Shuffled context marginal distribution changed')
                evidence.append({'family': family, 'seed': seed, 'channel': ch,
                    'geometry_category': f'G{group_index}' if family == 'MEAN8' else None,
                    'slots': len(ids), 'status': 'EXACT_MARGINALS',
                    'before_histogram': before_hist.tolist(), 'after_histogram': after_hist.tolist(),
                    'before_histogram_sha256': sha_array(before_hist), 'after_histogram_sha256': sha_array(after_hist),
                    'before_assignments_sha256': sha_array(before), 'after_assignments_sha256': sha_array(after),
                    'slot_ids_sha256': sha_array(ids), 'PMFs_refit': False,
                    'diagnostic_not_decoder_available': True})
    result[family] = {**models[family], 'classes': cls}
    return result


def process_level(scene, level, q, mean_contexts, outdir, stage, *, freeze_path=None, selected_family=None):
    """validation fits once; check reuses frozen models; full fits once after check."""
    wall_start=time.perf_counter(); cpu_start=time.process_time()
    if scene not in ('bouncingballs', 'hellwarrior'): raise ValueError('Scene not registered')
    q = np.asarray(q)
    if q.dtype != np.uint8 or q.ndim != 2 or q.shape[1] != 2 or len(q) == 0:
        raise ValueError('Frozen uint8[N,2] required')
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    if stage not in ('validation', 'check', 'full'): raise ValueError(stage)
    target = outdir/(stage.upper()+'_COMPLETE.json')
    if target.exists(): raise FileExistsError('Completed stage must be reused, not repeated')
    candidates = families(level, mean_contexts)
    result = {'scene': scene, 'level': level, 'stage': stage, 'q_sha256': sha_array(q),
              'rows': [], 'model_rows': [], 'timings': [], 'split_records': [], 'shuffled_marginals': []}
    if stage == 'check':
        if freeze_path is None or not Path(freeze_path).is_file(): raise ValueError('Family selection freeze required')
        freeze = read(freeze_path)
        if selected_family != freeze['selected_family']: raise ValueError('Frozen family mismatch')
        result['selection_freeze_sha256'] = hashlib.sha256(Path(freeze_path).read_bytes()).hexdigest()
        if not (outdir/'VALIDATION_COMPLETE.json').is_file(): raise ValueError('Missing validation')
    if stage == 'full' and 6 <= level <= 10 and not (outdir/'CHECK_COMPLETE.json').is_file():
        raise ValueError('Full fitting follows held-out check')
    seeds = SEEDS if stage != 'full' else (-1,)
    for seed in seeds:
        base = outdir/('full_scene' if seed == -1 else f'seed{seed}')
        if stage == 'validation':
            base.mkdir(exist_ok=False)
            assignment, splits = split_blocks(len(q), seed)
            save(base/'block_assignment.npy', assignment)
            split_record = {'seed': seed, 'block_size': BLOCK, 'blocks': len(assignment),
                'block_counts': {k: int((assignment==v).sum()) for k,v in (('fit',0),('validation',1),('check',2))},
                'slot_counts': {k: len(v) for k,v in splits.items()},
                'block_assignment_sha256': sha_array(assignment), 'slot_ids_sha256': {k: sha_array(v) for k,v in splits.items()}}
            put(base/'SPLIT.json', split_record); result['split_records'].append(split_record)
        elif stage == 'check':
            assignment, splits = split_blocks(len(q), seed)
            record = read(base/'SPLIT.json')
            if sha_array(assignment) != record['block_assignment_sha256']: raise ValueError('Split mismatch')
            for k, ids in splits.items():
                if sha_array(ids) != record['slot_ids_sha256'][k]: raise ValueError('Slot split mismatch')
            result['split_records'].append(record)
        else:
            base.mkdir(exist_ok=False); splits = {'fit': np.arange(len(q)), 'full': np.arange(len(q))}
        models = {}
        for family in candidates:
            if stage == 'check': models[family] = _load_model(base/family, q)
            else: models[family] = _save_model(base/family, scene, level, seed, q, splits['fit'], family, mean_contexts, stage)
            summary = models[family]['summary']
            if stage != 'check':
                for storage, costs in summary['all_transport_sizes'].items():
                    result['model_rows'].append({'scene':scene,'level':level,'seed':seed,'family':family,'phase':stage,
                        'selected': storage == summary['side']['storage'], **costs})
                result['timings'].append({'scene':scene,'level':level,'seed':seed,'family':family,**summary['timings']})
        split = {'validation':'validation', 'check':'check', 'full':'full'}[stage]
        t = time.perf_counter()
        result['rows'].extend(evaluate(scene, level, seed, split, q, splits[split], models, mean_contexts))
        result['timings'].append({'scene':scene,'level':level,'seed':seed,'evaluation_seconds':time.perf_counter()-t})
        if stage == 'check' and selected_family in models:
            # Exactly one fixed permutation rule, both held-out splits, no refit.
            for selected_split in ('validation', 'check'):
                t = time.perf_counter()
                marginal_records = []
                permuted = shuffled_models(models, splits[selected_split], selected_family, seed, mean_contexts,
                                            evidence=marginal_records)
                result['shuffled_marginals'].extend({'scene':scene,'level':level,'split':selected_split,**item}
                                                    for item in marginal_records)
                diagnostic = evaluate(scene, level, seed, selected_split, q, splits[selected_split], permuted, mean_contexts, shuffled=True)
                result['rows'].extend(row for row in diagnostic if row['family'] == selected_family)
                result['timings'].append({'scene':scene,'level':level,'seed':seed,'split':selected_split,
                    'shuffled_evaluation_seconds':time.perf_counter()-t})
        del models
    result.update(status='PASS', wall_seconds=time.perf_counter()-wall_start,
                  cpu_seconds=time.process_time()-cpu_start, peak_RSS_MiB=peak_rss_mib(),
                  peak_RSS_scope='OS process lifetime high-water mark; not stage-incremental or aggregate child memory')
    put(target, result)
    return result
