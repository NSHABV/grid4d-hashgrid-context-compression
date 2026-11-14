"""Canonical Mean8 classes. Production contract is unchanged from Grid4D V3."""
from __future__ import annotations

import numpy as np
from research.experiment_bench.hashed_pair_v3 import format as legacy
from research.experiment_bench.hashed_interlevel import dry_model as dm
from research.hashgrid_analysis.hashed_context import core

PRODUCTION = 'grid4d-v3'
SYNTHETIC = 'synthetic-test-v1'


def validate(g: dict, profile: str) -> None:
    """Do not weaken the old validator to accommodate synthetic smoke tests."""
    try:
        _validate(g, profile)
    except (KeyError, TypeError, OverflowError, IndexError) as exc:
        raise ValueError('Malformed geometry') from exc


def _validate(g, profile):
    if profile == PRODUCTION:
        legacy.validate_geometry(g)
        return
    if profile != SYNTHETIC:
        raise ValueError('Unknown geometry profile')
    keys = {'version', 'grid', 'arithmetic', 'geometry_convention', 'fallback', 'hash',
            'interpolation', 'coarse', 'fine', 'source_checkpoint_sha256', 'source_symbols_sha256'}
    if (not isinstance(g, dict) or set(g) != keys or type(g['version']) is not int
            or g['version'] != 1 or g['grid'] != 'xyz' or g['arithmetic'] != core.ARITHMETIC
            or g['geometry_convention'] != legacy.CONVENTION
            or dm._json_bytes(g['fallback']) != dm._json_bytes(legacy.FALLBACK)
            or dm._json_bytes(g['hash']) != dm._json_bytes(legacy.HASH)
            or g['interpolation'] != 'smoothstep-corners0to7'
            or not all(legacy._digest(g[k]) for k in ('source_checkpoint_sha256', 'source_symbols_sha256'))):
        raise ValueError('Invalid synthetic geometry contract')
    for role in ('coarse', 'fine'):
        level = g[role]
        keys = set(legacy.GEOMETRY_KEYS) | ({'quantization'} if role == 'coarse' else set())
        if not isinstance(level, dict) or set(level) != keys:
            raise ValueError('Invalid level fields')
        if (any(type(level[k]) is not int for k in ('level', 'rows', 'offset_start', 'offset_end'))
                or not 0 <= level['level'] <= 15 or not 1 <= level['rows'] <= 4096
                or not 0 <= level['offset_start'] < level['offset_end'] <= 8192
                or level['offset_end'] - level['offset_start'] != level['rows']):
            raise ValueError('Synthetic level exceeds bounded fixture limits')
        r, s = level['lookup_resolution'], level['scale']
        if (not isinstance(r, list) or len(r) != 3
                or any(type(x) is not int or not 2 <= x <= 32 for x in r)
                or not isinstance(s, list) or len(s) != 3
                or any(type(x) not in (int, float) for x in s)
                or not np.isfinite(s).all() or np.any(np.asarray(s) <= 0)
                or np.any(np.asarray(s) > 31)
                or not np.array_equal(np.asarray(s, np.float32).astype(np.float64), s)
                or not np.array_equal(np.ceil(np.asarray(s, np.float32)).astype(np.int64) + 1, r)):
            raise ValueError('Invalid exact-float32 scales/resolutions')
    if (g['fine']['level'] != g['coarse']['level'] + 1
            or g['fine']['offset_start'] != g['coarse']['offset_end']):
        raise ValueError('Nonconsecutive synthetic levels/offsets')
    legacy.validate_quantizer(g['coarse']['quantization'])


def validate_thresholds(thresholds):
    e = np.asarray(thresholds)
    if (e.dtype != np.float64 or e.shape != (2, 7) or not np.isfinite(e).all()
            or np.any(np.diff(e, axis=1) < 0)):
        raise ValueError('Expected finite sorted float64[2,7] frozen Mean8 thresholds')
    return e


def contexts(g, coarse, thresholds, profile=PRODUCTION):
    """Only decoded coarse and metadata; never receives targets or PMF counts."""
    validate(g, profile)
    e = validate_thresholds(thresholds)
    if not isinstance(coarse, np.ndarray) or coarse.dtype != np.uint8 or coarse.shape != (g['coarse']['rows'], 2):
        raise ValueError('Invalid coarse uint8 symbols')
    legacy._constant_symbols(coarse, g['coarse']['quantization'])
    ctx = core.compute_context(g, coarse)
    if not np.isfinite(ctx['mean']).all():
        raise ValueError('Nonfinite context')
    result = np.empty((g['fine']['rows'], 2), np.uint8)
    for ch in range(2):
        result[:, ch] = 2 + np.searchsorted(e[ch], ctx['mean'][:, ch], side='right')
    empty = ctx['geometry'] < 2
    result[empty] = ctx['geometry'][empty, None]
    return result
