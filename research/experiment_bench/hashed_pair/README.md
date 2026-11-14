> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

> При разработке и оформлении исследования использовались ИИ-агенты; [область помощи и ответственность автора](../../../docs/AI_ASSISTANCE.md). Этот исторический интерфейс может требовать внешних артефактов; проверенный публичный запуск описан в корневом README.

# Hashed xyz L4/L5 standalone container

Implementation date: 2026-10-15. This module implements experiment B only, with the frozen `bouncingballs-reference-50000` table-wise uint8 symbols. The earlier dense `interlevel/` V2 format and its results are unchanged. Supported arms are IID, Geometry4, Canonical8 and Mean8. No Count6 stream is produced after experiment A's NO-GO.

The format is deliberately bounded to the verified runtime geometry: dense L4 has 205379 rows, offsets [125561,330940), resolution 59³ and actual scale 57.3502311706543; hashed L5 has 524288 rows, offsets [330940,855228), resolution 81³ and actual scale 79.63493347167969. Both have two channels. The original full-table quantizer is preserved exactly: min −5.548852920532227, max 2.9999356269836426, step 0.03352466097065047, nearest-even, float32 reconstruction. Encoding neither changes nor recomputes symbols.

## Public API

```python
from research.experiment_bench.hashed_pair.format import (
    encode_pair, decode_bytes, unpack, pack, section_sizes)

data, encoder_detail = encode_pair(metadata, q4, q5, 'Mean8', storage='auto')
q4_restored, q5_restored, classes, decoder_detail = decode_bytes(data)
header, sections = unpack(data)
assert pack(header, sections) == data
sizes = section_sizes(data)
```

`metadata` is the existing diagnostic decoder metadata object. q4/q5 must be complete uint8 arrays with shapes [205379,2]/[524288,2]. Explicit transports are `dense_u32`, `packed_u16`, and `sparse_default_u16`; `auto` selects the shortest fully serialized transport, with fixed storage-order ties. Every encode serializes and roundtrips all three options. The coarse IID transport is selected independently once per encode, identically across arms. All histogram fits use all scene symbols, Laplace smoothing and the existing deterministic positive-16-bit mass normalization. This is **actual scene-specific coding**, not held-out generalization.

`unpack` validates framing, canonical JSON, geometry/model declarations and payload alignment. `pack` deliberately permits semantically invalid test headers, while regenerating section lengths and the outer checksum; this permits meaningful rechecksummed corruption tests. `decode_bytes` validates model transport, hashes, context semantics, exact decoded-symbol hashes and canonical range payloads. Its optional `verify_canonical=False` is for explicit diagnostics only; the public independent decoder uses the default `True`.

## Binary format

Magic `G4DHPAIR`, version 1. Prefix is little-endian `struct '<8sH5Q'`, 50 bytes. It records the five section lengths in this fixed order:

1. `metadata`: canonical UTF-8 JSON (`sort_keys=True`, compact separators, no NaN, no duplicate keys).
2. `coarse_model`: HDPM V1 model envelope for IID q4.
3. `fine_model`: HDPM V1 model envelope for the chosen q5 arm.
4. `coarse_payload`: range-coded q4, little-endian uint32 words.
5. `fine_payload`: range-coded q5, little-endian uint32 words.

A 32-byte SHA256 digest of prefix plus all sections closes the file. Exact length is required; trailing bytes are rejected. The maximum section sizes are respectively 64000, 1048576, 1048576, 4194304 and 4194304 bytes. Unknown versions, fields, arms and geometries are rejected.

The metadata keys are `version`, `kind`, `engine`, `arithmetic`, `numpy`, `order`, `geometry`, `model`, and `integrity`. Geometry includes coarse/fine levels, rows, offsets, actual scales and resolutions, quantizer, uint32 hash specification, point-domain convention and fallback. Provenance SHA256 values identify the frozen checkpoint and full xyz export; no paths to source data are needed. Integrity values are SHA256 of raw C-order q4, q5, uint8 class IDs, and uint32 coarse/fine mass arrays. The little-endian Windows execution environment is the tested environment.

Model envelopes use the preserved `hashed_interlevel/dry_model.py` serializer: positive masses with shape [2,C,256], sum 65536 for every row; sparse modal default plus sorted exceptions, packed u16, or dense u32. C=1 for IID, C=4 for Geometry4, C=10 for Canonical8/Mean8. Every distribution is transmitted, including uniform unreachable rows. CDF is derived from masses and is not stored separately. Float64 primary thresholds are stored once as a binary [2,7] array for feature arms. The JSON specification contains name/C/rules but no duplicate threshold values. Per-model metadata is `{}` because geometry and quantizer are centralized.

## Decoder contract

The decoder reads only its `.bin` as experiment data. It restores q4 first, verifies its digest, reconstructs q5 classes from q4 and transmitted metadata, then decodes all q5 symbols. No checkpoint, original xyz export, q4/q5 target file, context cache or parent probability arrays are inputs. All allocated fine slots occur exactly once: channel 0 by ascending slot, then channel 1 by ascending slot. Collision multiplicity never duplicates target symbols.

Official Grid4D indexing uses uint32 dense stride arithmetic until overflow/cap rules select the XOR hash with primes [1,2654435761,805459861], then modulo allocated rows. Nominal vertices satisfy `0 <= v < R`; eligible point correspondences additionally satisfy `v <= floor(actual_scale)`. Coordinates are float32(v)/float32(scale), without clamp. G0/G1 remain separate; E-empty does not mean unused during rendering.

Canonical representative, interpolation and mean reuse the previously verified `hashed_context.core.compute_context`. The arithmetic identifier is `cpu-f32-separate-ufunc-corner0to7-anchor-f64-addat-xfast-popstd-v1`: existing float64 affine dequantization → float32, separate float32 smoothstep/interpolation operations, corners 0…7, x-fast ordered float64 anchored accumulation. Mean8/Canonical8 use transmitted float64 linear quantiles over all G2/G3 coarse contexts, per channel, with searchsorted(right). Quantiles do not use fine symbols. IID bypasses context geometry; Geometry4 performs integer geometry enumeration without feature interpolation. Tests compare their class IDs with the saved canonical context data.

The range engine is unchanged: constriction 0.4.2, RangeEncoder/RangeDecoder, Categorical(perfect=False), finite16 masses and the library's deterministic24 probability representation. `engine.py` AST-extracts the public `_indexed_inputs`, `encode_indexed`, and `decode_indexed` function definitions from `research/experiment_bench/entropy.py`, verbatim. This avoids that module's unrelated torch/checkpoint imports. At implementation, its source SHA256 is `e100e40462e88d66222d09ae8fed0acd6c5d5fa18ee3c780ff40af54b7f563c5`; each encoder detail records the actual source SHA. Dequantization similarly reuses the existing codec function via the established context module.

The decoder re-encodes the restored symbols with the transmitted models to require byte-identical payloads. This rejects unused range words even when someone recomputes the outer SHA. This validation cost is timed separately as `canonical_validation_seconds` and included in total strict decode time.

## Runtime and commands

Verified runtime: Windows x86-64, Python 3.12.14, NumPy 1.26.4, constriction 0.4.2. `check_runtime` rejects other NumPy/constriction versions. Other CPU/GPU environments are not claimed class-equivalent. The canonical path is CPU; no GPU speedup or VRAM measurement is claimed. NumPy 1.26.4 is already installed in `.tools/phase2-plotting-env`; constriction is isolated under `.tools/hashed-pair-deps`.

```powershell
# Installation if the isolated dependency is absent; run from <PROJECT_ROOT>.
$py='<PROJECT_ROOT>\.tools\phase2-plotting-env\Scripts\python.exe'
& $py -m pip install --no-deps --target .tools/hashed-pair-deps constriction==0.4.2

# Decode an existing stream into a new output directory.
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='<PROJECT_ROOT>\.tools\hashed-pair-deps'
& $py -m research.experiment_bench.hashed_pair.replay `
  --input '<ABSOLUTE_STREAM_PATH>' --output '<NEW_OUTPUT_DIRECTORY>'
```

The old bench package prepends a Linux-only vendor path; new `engine.py` restores the isolated Windows vendor priority without modifying that preserved package. The replay preloads public engine/package-version metadata before installing the data-read audit. After the guard, only the input `.bin` and public code/runtime binaries may be read. The Python audit records accesses and blocks forbidden paths; it is an instrumentation guard, not an OS sandbox.

## Measurement definitions

`sizes` partitions `total_bytes` exactly into `coarse_bytes`, `fine_payload_bytes`, `model_bytes`, and `metadata_framing_bytes`. Coarse bytes include the shared coarse model envelope and coarse payload. Model bytes in this partition are the raw fine probability-mass section; fine threshold/specification/model headers, central metadata, prefix and SHA trailer belong to metadata/framing. Additional component fields disclose `fine_model_bytes`, `threshold_bytes`, `coarse_model_bytes`, `central_metadata_bytes` and the other headers. Actual report totals must also equal filesystem size; the in-memory API alone does not constitute that measurement.

Encode timings include context construction/edges, fitting, all candidate model roundtrips, both entropy payloads and framing. Decode timings include model restoration, coarse entropy decode, context reconstruction, fine decode and strict canonical-payload validation. Process imports and disk I/O are outside these function timers; the orchestration records cold subprocess wall time and body-with-I/O separately. Startup overhead must not be described as pure import time when computed as an outer-minus-body residual.

No probability network, new quantization, Grid4D training, temporal levels or levels L7–L15 are implemented here. New results require a fresh unique result directory; old reports and data remain immutable.
