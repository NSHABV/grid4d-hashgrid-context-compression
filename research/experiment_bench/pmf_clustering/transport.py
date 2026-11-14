"""Canonical H4PM v1 model transport shared by C0, C1 and C2.

Context IDs are local Mean8 IDs 0..9 within each of two channels. Mapping
entries are *physical pool* IDs, not context IDs. Empty source classes map to
255. Exact row sharing in C1/C2 is a storage operation, not statistical fitting.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct
import numpy as np

MAGIC = b'H4PM'
VERSION = 1
HEADER = struct.Struct('<4sBBBBHIII')
MODES = ('C0', 'C1', 'C2')
STORAGES = ('dense_u32', 'packed_u16', 'sparse_default_u16')
CHANNELS = 2
CLASSES = 10
ALPHABET = 256
TOTAL = 65536
UNUSED = 255
THRESHOLD_BYTES = 112
MAPPING_BYTES = 20
MAX_ROWS = CHANNELS * CLASSES
MAX_BYTES = HEADER.size + MAX_ROWS * ALPHABET * 4 + THRESHOLD_BYTES + MAPPING_BYTES


@dataclass(frozen=True)
class Model:
    pool: np.ndarray
    mapping: np.ndarray
    thresholds: np.ndarray
    mode: str


def validate(model: Model) -> None:
    if not isinstance(model, Model) or type(model.mode) is not str or model.mode not in MODES:
        raise ValueError('Expected H4 Model with mode C0/C1/C2')
    f, m, e = model.pool, model.mapping, model.thresholds
    if (not isinstance(f, np.ndarray) or f.dtype != np.dtype('uint32')
            or f.ndim != 2 or f.shape[1] != ALPHABET or len(f) > MAX_ROWS
            or np.any(f < 1) or np.any(f.sum(axis=1, dtype=np.uint64) != TOTAL)):
        raise ValueError('Positive uint32 PMFs [R,256], R<=20, sum65536 required')
    if (not isinstance(m, np.ndarray) or m.dtype != np.dtype('uint8')
            or m.shape != (CHANNELS, CLASSES)
            or np.any((m != UNUSED) & (m >= len(f)))):
        raise ValueError('Invalid context-to-pool mapping')
    if (not isinstance(e, np.ndarray) or e.dtype != np.dtype('float64')
            or e.shape != (CHANNELS, 7) or not np.isfinite(e).all()
            or np.any(np.diff(e, axis=1) < 0)):
        raise ValueError('Finite sorted original Mean8 thresholds [2,7] required')
    refs = [int(v) for v in m.flat if v != UNUSED]
    if list(dict.fromkeys(refs)) != list(range(len(f))):
        raise ValueError('Unreferenced or noncanonical pool row order')
    if model.mode == 'C0':
        if len(refs) != len(f):
            raise ValueError('C0 needs one independent physical row per active class')
    elif len({row.tobytes() for row in f}) != len(f):
        raise ValueError('C1/C2 require exact physical sharing of identical rows')


def _mass_bytes(pool: np.ndarray, storage: str) -> bytes:
    if storage == 'dense_u32':
        return pool.astype('<u4').tobytes()
    if storage == 'packed_u16':
        # Positivity of all256 entries plus total65536 implies max mass65281.
        return pool.astype('<u2').tobytes()
    result = bytearray()
    for row in pool:
        values, counts = np.unique(row, return_counts=True)
        default = int(values[np.argmax(counts)])  # Smallest mass on a tie.
        exceptions = np.flatnonzero(row != default)
        result.extend(struct.pack('<HH', default, len(exceptions)))
        for symbol in exceptions:
            result.extend(struct.pack('<BH', int(symbol), int(row[symbol])))
    return bytes(result)


def serialize(model: Model, storage: str) -> bytes:
    validate(model)
    if type(storage) is not str or storage not in STORAGES:
        raise ValueError('Unknown probability mass storage')
    masses = _mass_bytes(model.pool, storage)
    header = HEADER.pack(MAGIC, VERSION, STORAGES.index(storage) + 1,
                         MODES.index(model.mode), CHANNELS, len(model.pool),
                         len(masses), THRESHOLD_BYTES, MAPPING_BYTES)
    return header + masses + model.thresholds.astype('<f8').tobytes() + model.mapping.tobytes()


def deserialize(data: bytes) -> tuple[Model, str]:
    if not isinstance(data, (bytes, bytearray)) or not HEADER.size <= len(data) <= MAX_BYTES:
        raise ValueError('Invalid H4PM byte buffer/size')
    magic, version, storage_id, mode_id, channels, rows, nm, ne, nr = HEADER.unpack_from(data)
    if (magic != MAGIC or version != VERSION or storage_id not in (1, 2, 3)
            or mode_id not in (0, 1, 2) or channels != CHANNELS or rows > MAX_ROWS
            or nm > MAX_ROWS * ALPHABET * 4 or ne != THRESHOLD_BYTES or nr != MAPPING_BYTES
            or len(data) != HEADER.size + nm + ne + nr):
        raise ValueError('Invalid H4PM header or section lengths')
    raw = data[HEADER.size:HEADER.size + nm]
    if storage_id in (1, 2):
        width = 4 if storage_id == 1 else 2
        if nm != rows * ALPHABET * width:
            raise ValueError('Dense/packed PMF length mismatch')
        pool = np.frombuffer(raw, dtype='<u4' if storage_id == 1 else '<u2').astype(np.uint32).reshape(rows, ALPHABET)
    else:
        pool = np.empty((rows, ALPHABET), np.uint32)
        pos = 0
        for row in pool:
            if pos + 4 > len(raw):
                raise ValueError('Truncated sparse PMF header')
            default, count = struct.unpack_from('<HH', raw, pos)
            pos += 4
            if default == 0 or count > 255 or pos + 3 * count > len(raw):
                raise ValueError('Invalid sparse default or exception count')
            row.fill(default)
            previous = -1
            for _ in range(count):
                symbol, mass = struct.unpack_from('<BH', raw, pos)
                pos += 3
                if symbol <= previous or mass == 0 or mass == default:
                    raise ValueError('Noncanonical sparse exception')
                row[symbol] = mass
                previous = symbol
        if pos != len(raw):
            raise ValueError('Trailing PMF bytes')
    pos = HEADER.size + nm
    thresholds = np.frombuffer(data[pos:pos + ne], dtype='<f8').copy().reshape(CHANNELS, 7)
    mapping = np.frombuffer(data[pos + ne:], dtype=np.uint8).copy().reshape(CHANNELS, CLASSES)
    model = Model(pool, mapping, thresholds, MODES[mode_id])
    validate(model)
    storage = STORAGES[storage_id - 1]
    # Also rejects a non-modal default, a non-minimal default tie, alternate
    # sparse encodings and noncanonical mapping/pool order.
    if serialize(model, storage) != data:
        raise ValueError('Noncanonical H4PM representation')
    return model, storage


def choose(model: Model) -> tuple[bytes, dict[str, int]]:
    """Physically serialize the entire model in every supported transport."""
    candidates = {storage: serialize(model, storage) for storage in STORAGES}
    storage = min(STORAGES, key=lambda key: len(candidates[key]))
    return candidates[storage], {key: len(value) for key, value in candidates.items()}


def sizes(data: bytes) -> dict:
    model, storage = deserialize(data)
    mass_bytes = HEADER.unpack_from(data)[6]
    return {'model_bytes': len(data), 'pmf_bytes': mass_bytes,
            'mapping_bytes': MAPPING_BYTES, 'threshold_bytes': THRESHOLD_BYTES,
            'header_bytes': HEADER.size, 'mode_identifier_bytes': 1,
            'storage_identifier_bytes': 1, 'pool_rows': len(model.pool),
            'mode': model.mode, 'storage': storage}


def route(classes: np.ndarray, model: Model) -> np.ndarray:
    """Map coarse-derived *local* context IDs to physical pool IDs, no targets."""
    validate(model)
    c = np.asarray(classes)
    if c.dtype != np.dtype('uint8') or c.ndim != 2 or c.shape[1] != CHANNELS or np.any(c >= CLASSES):
        raise ValueError('Expected local Mean8 uint8 classes [N,2], values0..9')
    used = np.zeros((CHANNELS, CLASSES), bool)
    for channel in range(CHANNELS):
        used[channel, np.unique(c[:, channel])] = True
    if not np.array_equal(used, model.mapping != UNUSED):
        raise ValueError('Missing/unused mapping: context support differs')
    return model.mapping[np.arange(CHANNELS)[None, :], c]
