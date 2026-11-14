"""Deterministic greedy clustering using full physical model serialization.

Statistical clusters refer to global source IDs10*channel+local Mean8 class.
Only active feature bins2..9 in the same channel can merge. G0/G1 remain fixed.
Physical exact sharing is independent of those statistical partitions and is
enabled from the start for C1/C2, including bit-identical cross-channel rows.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
from research.experiment_bench.models import frequencies
from . import transport

MAX_COUNT_SUM = (1 << 53) - 256


def validate_counts(counts: np.ndarray) -> np.ndarray:
    n = np.asarray(counts)
    if (n.shape != (2, 10, 256) or not np.issubdtype(n.dtype, np.integer)
            or np.any(n < 0)):
        raise ValueError('Raw nonnegative integer counts [2,10,256] required')
    # Python integers avoid overflow before the uint64 conversion and ensure
    # all pooled counts plus Laplace pseudocounts fit the float64 integer range.
    if sum(int(value) for value in n.flat) > MAX_COUNT_SUM:
        raise ValueError('Histogram total exceeds exact-float64 count bound')
    return n.astype(np.uint64, copy=True)


def histogram(symbols: np.ndarray, classes: np.ndarray) -> np.ndarray:
    q, c = np.asarray(symbols), np.asarray(classes)
    if (q.dtype != np.dtype('uint8') or q.ndim != 2 or q.shape[1] != 2
            or c.dtype != np.dtype('uint8') or c.shape != q.shape or np.any(c >= 10)):
        raise ValueError('Expected uint8 symbols and local context IDs [N,2]')
    counts = np.empty((2, 10, 256), np.uint64)
    for channel in range(2):
        indices = 256 * c[:, channel].astype(np.int64) + q[:, channel]
        counts[channel] = np.bincount(indices, minlength=2560).reshape(10, 256)
    return validate_counts(counts)


def objective(counts: np.ndarray, model: transport.Model, metadata_bytes: int = 0) -> dict:
    """Exact serialized side costs plus float64 ideal payload bytes.

metadata_bytes is the exact outer metadata/framing constant, already measured
by the container serializer. The invariant coarse prerequisite is not part of
this objective and can be added separately for a standalone pair forecast.
"""
    n = validate_counts(counts)
    if type(metadata_bytes) is not int or not 0 <= metadata_bytes <= (1 << 53):
        raise ValueError('Nonnegative measured metadata byte count required')
    transport.validate(model)
    active = n.sum(axis=2, dtype=np.uint64) > 0
    if not np.array_equal(active, model.mapping != transport.UNUSED):
        raise ValueError('Histogram support and transmitted mapping differ')
    data, candidates = transport.choose(model)
    per_class_bits = []
    for channel, context in np.argwhere(active):
        masses = model.pool[model.mapping[channel, context]].astype(np.float64)
        symbol_costs = n[channel, context].astype(np.float64) * (16.0 - np.log2(masses))
        per_class_bits.append(float(np.sum(symbol_costs, dtype=np.float64)))
    bits = math.fsum(per_class_bits)
    payload_bytes = bits / 8.0
    return {**transport.sizes(data), 'ideal_payload_bits': bits,
            'ideal_payload_bytes': payload_bytes, 'outer_metadata_bytes': metadata_bytes,
            'J_bytes': math.fsum((payload_bytes, len(data), metadata_bytes)),
            'transport_candidates': candidates}


@dataclass(frozen=True)
class _Cluster:
    members: tuple[int, ...]
    pmf: np.ndarray


@dataclass(frozen=True)
class Result:
    model: transport.Model
    initial: dict
    final: dict
    history: list[dict]
    candidates_evaluated: int


def _materialize(clusters: list[_Cluster], thresholds: np.ndarray, mode: str) -> transport.Model:
    by_class = {source: cluster.pmf for cluster in clusters for source in cluster.members}
    mapping = np.full((2, 10), transport.UNUSED, np.uint8)
    pool, seen = [], {}
    for source in sorted(by_class):
        row = by_class[source]
        key = source if mode == 'C0' else row.astype('<u4').tobytes()
        if key not in seen:
            seen[key] = len(pool)
            pool.append(row.copy())
        mapping.flat[source] = seen[key]
    result = transport.Model(np.asarray(pool, np.uint32).reshape(-1, 256), mapping,
                             np.asarray(thresholds).copy(), mode)
    transport.validate(result)
    return result


def _eligible(left: _Cluster, right: _Cluster) -> bool:
    sources = left.members + right.members
    return len({source // 10 for source in sources}) == 1 and all(source % 10 >= 2 for source in sources)


def optimize(counts: np.ndarray, original: np.ndarray, thresholds: np.ndarray,
             mode: str, metadata_bytes: int = 0) -> Result:
    """Exhaustively evaluate every admissible pair at every greedy step.

Unmerged PMFs are copied from original, never silently refitted. A merged PMF
uses frequencies(sum of RAW member histograms), so smoothing is applied once.
Exact float64 J ties use lexicographic original member tuples. Only strict
J decrease is accepted. Mode/storage IDs, mapping, thresholds and all model
framing are included in every physically serialized candidate evaluation.
"""
    n = validate_counts(counts)
    f = np.asarray(original)
    if (type(mode) is not str or mode not in transport.MODES
            or f.dtype != np.dtype('uint32') or f.shape != (2, 10, 256)
            or np.any(f < 1) or np.any(f.sum(axis=2, dtype=np.uint64) != 65536)):
        raise ValueError('Original positive uint32 PMFs [2,10,256] required')
    active = np.flatnonzero(n.sum(axis=2, dtype=np.uint64).reshape(-1))
    clusters = [_Cluster((int(source),), f.reshape(20, 256)[source].copy()) for source in active]
    current = _materialize(clusters, thresholds, mode)
    cost = objective(n, current, metadata_bytes)
    initial = dict(cost)
    history, evaluations = [], 0
    if mode == 'C2':
        while True:
            best = None
            for left_index, left in enumerate(clusters):
                for right_index in range(left_index + 1, len(clusters)):
                    right = clusters[right_index]
                    if not _eligible(left, right):
                        continue
                    members = tuple(sorted(left.members + right.members))
                    pooled_counts = n.reshape(20, 256)[list(members)].sum(axis=0, dtype=np.uint64)
                    merged = _Cluster(members, frequencies(pooled_counts))
                    proposal = sorted([cluster for index, cluster in enumerate(clusters)
                                       if index not in (left_index, right_index)] + [merged],
                                      key=lambda cluster: cluster.members)
                    model = _materialize(proposal, thresholds, mode)
                    trial = objective(n, model, metadata_bytes)
                    evaluations += 1
                    rank = (trial['J_bytes'], left.members, right.members)
                    if best is None or rank < best[0]:
                        best = (rank, proposal, model, trial, left.members, right.members)
            if best is None or not best[3]['J_bytes'] < cost['J_bytes']:
                break
            _, clusters, current, trial, left_members, right_members = best
            history.append({'left': list(left_members), 'right': list(right_members),
                            'J_before': cost['J_bytes'], 'J_after': trial['J_bytes'],
                            'ideal_delta_bytes': trial['ideal_payload_bytes'] - cost['ideal_payload_bytes'],
                            'side_delta_bytes': trial['model_bytes'] - cost['model_bytes'],
                            'storage_before': cost['storage'], 'storage_after': trial['storage']})
            cost = trial
    return Result(current, initial, cost, history, evaluations)
