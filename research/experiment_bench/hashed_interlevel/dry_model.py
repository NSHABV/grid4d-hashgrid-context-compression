"""Versioned, bounded model-only transport for held-out experiments.

This is a dry serializer, not an entropy stream. It imports no entropy engine,
does not encode targets and does not change the earlier dense L3->L4 format.
Every channel/class distribution is transmitted, including uniform empty rows.
CDFs are derived using uint64 accumulation; all 256 masses are positive and
their sum is 65536, following experiment_bench.models.frequencies.
"""
from __future__ import annotations

import json
import struct
from typing import Any

import numpy as np


MAGIC = b"HDPM"
VERSION = 1
STORAGES = {"dense_u32": 1, "packed_u16": 2, "sparse_default_u16": 3}
CLASS_COUNTS = (1, 4, 6, 10)
# Magic, version, storage, channels, classes, alphabet, four section lengths.
HEADER = struct.Struct("<4sBBBBHIIII")
SECTION_KEYS = (
    "probability_masses", "context_thresholds", "model_specification",
    "mandatory_metadata",
)
MAX_SECTION_BYTES = 1 << 20
MAX_THRESHOLD_ARRAYS = 64
MAX_THRESHOLD_ELEMENTS = 65536
MAX_THRESHOLD_NDIM = 8
MAX_NAME_BYTES = 255


def _validate_masses(masses: np.ndarray) -> np.ndarray:
    f = np.asarray(masses)
    if (f.dtype != np.dtype("uint32") or f.ndim != 3 or f.shape[0] != 2
            or f.shape[1] not in CLASS_COUNTS or f.shape[2] != 256):
        raise ValueError("Expected uint32 masses with shape [2,C,256], C=1/4/6/10")
    if np.any(f < 1) or np.any(f.sum(axis=2, dtype=np.uint64) != 65536):
        raise ValueError("Each finite CDF needs positive masses summing to 65536")
    return f


def _json_bytes(value: dict[str, Any]) -> bytes:
    if not isinstance(value, dict):
        raise ValueError("Specification and metadata must be JSON objects")

    def check(x: Any) -> None:
        if isinstance(x, dict):
            if any(not isinstance(k, str) for k in x):
                raise ValueError("JSON keys must be strings")
            for v in x.values():
                check(v)
        elif isinstance(x, list):
            for v in x:
                check(v)
        elif type(x) not in (str, int, float, bool, type(None)):
            raise ValueError("Only ordinary JSON values are supported")

    try:
        check(value)
        data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, UnicodeError, OverflowError, RecursionError) as exc:
        raise ValueError("Invalid JSON object") from exc
    if len(data) > MAX_SECTION_BYTES:
        raise ValueError("JSON section exceeds bound")
    return data


def _json_load(data: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("Invalid JSON section") from exc
    if _json_bytes(value) != data:
        raise ValueError("Noncanonical JSON section")
    return value


def _threshold_bytes(thresholds: dict[str, np.ndarray]) -> bytes:
    if not isinstance(thresholds, dict) or len(thresholds) > MAX_THRESHOLD_ARRAYS:
        raise ValueError("Invalid threshold dictionary")
    if any(not isinstance(k, str) or not k for k in thresholds):
        raise ValueError("Threshold names must be nonempty strings")
    data = bytearray(struct.pack("<H", len(thresholds)))
    total_elements = 0
    for name in sorted(thresholds):
        try:
            key = name.encode("utf-8")
        except UnicodeError as exc:
            raise ValueError("Invalid threshold name") from exc
        arr = np.asarray(thresholds[name])
        if (len(key) > MAX_NAME_BYTES or arr.dtype != np.dtype("float64")
                or arr.ndim > MAX_THRESHOLD_NDIM or not np.isfinite(arr).all()
                or any(dim > MAX_THRESHOLD_ELEMENTS for dim in arr.shape)):
            raise ValueError("Invalid finite float64 threshold array")
        total_elements += arr.size
        if total_elements > MAX_THRESHOLD_ELEMENTS:
            raise ValueError("Too many threshold elements")
        data.extend(struct.pack("<H", len(key)))
        data.extend(key)
        data.extend(struct.pack("<B", arr.ndim))
        data.extend(struct.pack("<" + "I" * arr.ndim, *arr.shape))
        data.extend(arr.astype("<f8", copy=False).tobytes(order="C"))
    if len(data) > MAX_SECTION_BYTES:
        raise ValueError("Threshold section exceeds bound")
    return bytes(data)


def _threshold_load(data: bytes) -> dict[str, np.ndarray]:
    offset = 0

    def take(size: int) -> bytes:
        nonlocal offset
        if size < 0 or offset + size > len(data):
            raise ValueError("Truncated threshold section")
        result = data[offset:offset + size]
        offset += size
        return result

    count, = struct.unpack("<H", take(2))
    if count > MAX_THRESHOLD_ARRAYS:
        raise ValueError("Too many threshold arrays")
    output = {}
    previous = None
    total_elements = 0
    for _ in range(count):
        name_size, = struct.unpack("<H", take(2))
        if not 0 < name_size <= MAX_NAME_BYTES:
            raise ValueError("Invalid threshold name size")
        try:
            name = take(name_size).decode("utf-8")
        except UnicodeError as exc:
            raise ValueError("Invalid threshold name") from exc
        if previous is not None and name <= previous:
            raise ValueError("Threshold names must be unique and sorted")
        previous = name
        ndim, = struct.unpack("<B", take(1))
        if ndim > MAX_THRESHOLD_NDIM:
            raise ValueError("Threshold dimension exceeds bound")
        shape = struct.unpack("<" + "I" * ndim, take(4 * ndim))
        size = 1
        for dim in shape:
            if dim > MAX_THRESHOLD_ELEMENTS:
                raise ValueError("Threshold shape exceeds bound")
            size *= dim
        total_elements += size
        if total_elements > MAX_THRESHOLD_ELEMENTS:
            raise ValueError("Threshold count exceeds bound")
        arr = np.frombuffer(take(8 * size), dtype="<f8").reshape(shape).copy()
        if not np.isfinite(arr).all():
            raise ValueError("Nonfinite threshold")
        output[name] = arr
    if offset != len(data):
        raise ValueError("Trailing threshold bytes")
    return output


def _default(row: np.ndarray) -> int:
    values, counts = np.unique(row, return_counts=True)
    # np.unique sorts: smallest mass wins any mode tie.
    return int(values[np.argmax(counts)])


def _mass_bytes(f: np.ndarray, storage: str) -> bytes:
    if storage == "dense_u32":
        return f.astype("<u4").tobytes()
    if storage == "packed_u16":
        return f.astype("<u2").tobytes()
    data = bytearray()
    for row in f.reshape(-1, 256):
        default = _default(row)
        exceptions = np.flatnonzero(row != default)
        data.extend(struct.pack("<HH", default, len(exceptions)))
        for symbol in exceptions:
            data.extend(struct.pack("<BH", int(symbol), int(row[symbol])))
    return bytes(data)


def _mass_load(data: bytes, storage: str, classes: int) -> np.ndarray:
    if storage in ("dense_u32", "packed_u16"):
        dtype = "<u4" if storage == "dense_u32" else "<u2"
        expected = 2 * classes * 256 * np.dtype(dtype).itemsize
        if len(data) != expected:
            raise ValueError("Mass section length mismatch")
        return np.frombuffer(data, dtype=dtype).reshape(2, classes, 256).astype(np.uint32)
    f = np.empty((2, classes, 256), dtype=np.uint32)
    offset = 0
    for row in f.reshape(-1, 256):
        if offset + 4 > len(data):
            raise ValueError("Missing sparse row")
        default, count = struct.unpack_from("<HH", data, offset)
        offset += 4
        # A canonical modal default occurs at least once, hence <=255 exceptions.
        if not default or count > 255 or offset + 3 * count > len(data):
            raise ValueError("Invalid sparse row")
        row.fill(default)
        previous = -1
        for _ in range(count):
            symbol, mass = struct.unpack_from("<BH", data, offset)
            offset += 3
            if symbol <= previous or not mass or mass == default:
                raise ValueError("Invalid or unsorted sparse exception")
            previous = symbol
            row[symbol] = mass
        if _default(row) != default:
            raise ValueError("Noncanonical sparse default")
    if offset != len(data):
        raise ValueError("Trailing mass bytes")
    return f


def serialize(masses: np.ndarray, thresholds: dict[str, np.ndarray],
              specification: dict[str, Any], metadata: dict[str, Any],
              storage: str) -> bytes:
    """Return deterministic model-only bytes; never reads or codes targets."""
    f = _validate_masses(masses)
    if storage not in STORAGES:
        raise ValueError("Unsupported mass storage")
    parts = (_mass_bytes(f, storage), _threshold_bytes(thresholds),
             _json_bytes(specification), _json_bytes(metadata))
    header = HEADER.pack(MAGIC, VERSION, STORAGES[storage], 2, f.shape[1], 256,
                         *(len(part) for part in parts))
    return header + b"".join(parts)


def _parts(data: bytes) -> tuple[list[bytes], str, int]:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise ValueError("Model must be bytes-like")
    if len(data) < HEADER.size:
        raise ValueError("Truncated model header")
    magic, version, sid, channels, classes, alphabet, *lengths = HEADER.unpack_from(data)
    if (magic != MAGIC or version != VERSION or sid not in STORAGES.values()
            or channels != 2 or classes not in CLASS_COUNTS or alphabet != 256):
        raise ValueError("Unsupported model header")
    if any(length > MAX_SECTION_BYTES for length in lengths):
        raise ValueError("Section length exceeds bound")
    if HEADER.size + sum(lengths) != len(data):
        raise ValueError("Truncated or trailing model bytes")
    parts = []
    offset = HEADER.size
    for length in lengths:
        parts.append(bytes(data[offset:offset + length]))
        offset += length
    storage = next(key for key, value in STORAGES.items() if value == sid)
    return parts, storage, classes


def deserialize(data: bytes) -> tuple[np.ndarray, dict[str, np.ndarray], dict, dict]:
    """Restore every mass and float64 edge exactly; reject malformed framing."""
    parts, storage, classes = _parts(data)
    f = _validate_masses(_mass_load(parts[0], storage, classes))
    return f, _threshold_load(parts[1]), _json_load(parts[2]), _json_load(parts[3])


def section_sizes(data: bytes) -> dict[str, int]:
    """Measured dry section bytes, including the fixed 26-byte header."""
    parts, _, _ = _parts(data)
    deserialize(data)  # Only valid models receive accounting.
    sizes = {name: len(part) for name, part in zip(SECTION_KEYS, parts)}
    sizes.update(header=HEADER.size, total=len(data))
    return sizes
