> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Experimental API and format v1

The implementation codes HashGrid embeddings only. Gaussian PLY and deformation
MLP remain external scene components. Decoder `decode(bitstream, fresh_output)`
receives no checkpoint, raw symbol path, fitted Python object, or RNG state.

## Commands

From workspace root, in the pinned Grid4D environment:

```bash
python -m research.experiment_bench.cli run research/experiment_bench/configs/reference-iid.json
python -m research.experiment_bench.cli decode experiments/reference-iid/bitstream.bin experiments/restarted-decode
python -m research.experiment_bench.cli aggregate experiments research/experiment_bench/aggregate
python -m research.experiment_bench.check_all
```

Windows entry point: `wsl -d Ubuntu -- bash research/run_bench.sh cli run <config>`.
JSON config is the dependency-free equivalent of the requested YAML interface.
All output directories must be new. Source and dataset files are never overwritten.
The current protocol pins seed=0, matching upstream `safe_state`; other seeds are
rejected rather than silently recorded without affecting execution.

## Interfaces

1. **Order:** `HistogramModel.plan_second(decoded_first)` returns ordered pairs
   `(distribution_id, row_indices)`. q0 is always coded first in ascending row order;
   each q1 row must appear exactly once. Existing context model uses classes 0..15,
   stable row order inside each class. IID uses one q1 block. This v1 schedule exposes
   all decoded q0 and immutable public metadata, never undecoded q1. Models that
   require a different causal traversal need a new versioned schedule, with tests.
2. **Decoder context:** `context_class(first)` accepts only uint8 q0. The caller
   supplies q0 recovered from the range decoder, not encoder data. Current mapping
   is `q0 >> 4`. `self.metadata` contains the public grid offsets/resolutions; no new
   level/cross-grid/temporal/collision models have been implemented.
3. **Probability:** `distribution(id)` returns the deterministic float32 vector
   from transmitted uint32 masses; sum=65536, every mass>=1. `categorical` pins
   `perfect=False`; constriction constructs an invertible 24-bit fixed-point model.
4. **Model parameters:** `fit(symbols, metadata)` runs at encoder only; fitted
   histograms are charged to the file. `to_bytes()` / `from_bytes(data, metadata)`
   exchange all necessary finite masses. Empty classes become uniform distributions.
5. **Entropy engine:** `encode_symbols` / `decode_symbols` contain only range-coder
   operations and scheduling. They do not access Grid4D. `encode` / `decode` provide
   framing, integrity checks, metadata transport and fresh-process restoration.
6. **Rate accounting:** `entropy.encode` records measured file length, coded payload,
   model bytes, metadata/framing bytes, N, file and payload bits/symbol, ratios,
   empirical H*N and finite-mass cross entropy. Diagnostic restored `.pth` files,
   PLY, PNG and logs are excluded from coded HashGrid size.

For another static q0-based context: subclass `HistogramModel`, override
`distributions` and `plan_second` (and any required serialization), register the
class in `MODELS`, and select its name in a JSON config. Add independent context and
partition tests. The range engine, quantization, renderer and metric integration
remain reusable. ChannelContext is the working extensibility example; no extra toy
model is necessary. Do not silently change semantics under an existing model name.

## Binary specification

Little-endian prefix `<8sHQQQ>`:

- magic `G4DBENCH`, uint16 format version=1;
- uint64 JSON byte length, model-section length, coded-payload length.

Then UTF-8 compact JSON, raw model bytes, raw coded payload, SHA256 of every preceding
byte (32-byte trailer). Extra bytes, truncation, unsupported version, invalid
lengths, checksum or symbol hashes cause failure. There is no implicit side file.

JSON includes model/coder IDs, pinned constriction version 0.4.2, histogram and coder
precision, quantization manifest, per-grid section lengths and decoded symbol hashes.
Every buffer and quantization min/max/step is embedded via lossless decimal values
and dtype metadata. Buffer binary reconstruction is checked against original hashes.
Grid section order is public: xyz, xyt, yzt, xzt. Each range-coded section contains
little-endian uint32 coder words. `fixed8` stores uint8 rows/channels interleaved and
has no probability-model bytes. IID transmits 2x256 uint32 masses per grid;
channel_context transmits 17x256 per grid (q0 and 16 conditional q1 histograms).

Laplace alpha=1, followed by deterministic largest-remainder mass allocation with
minimum 1 and total 2^16. CDF prefix sums are strictly increasing. Input probabilities
are exactly representable binary fractions; constriction internally converts them
to its 24-bit model. Encoder/decoder use the same pinned implementation/settings.
Reported finite-mass cross entropy is distinct from empirical entropy and actual
file length; actual size additionally includes framing and range finalization.

## Interpretation

Compare IID and context on identical quantized values and per-table/channel
granularity. Context may lose after model overhead; preserve that result. Marginal
histograms do not establish dependencies. No main NIR method is implemented here.
Float32 reference is the real Phase2 lossless serialized directory; 12-bit direct
quantization uses a uint16 container and reports ideal 12-bit size separately.

## Dense XYZ inter-level subset extension (version 2)

The L3->L4 actual coding study is implemented under `experiment_bench/interlevel`.
It reuses the same range engine and finite-mass estimator. `encode_indexed` and
`decode_indexed` add a fixed channel-major, row-ascending schedule with decoder-known
per-symbol class IDs; targets are never regrouped by class. Existing v1 semantics
and files remain unchanged. The v2 pair envelope uses the same prefix/digest framing
but carries only the dense XYZ L3/L4 subset, with identical shared L3 across variants.
For commands, supported CPU arithmetic, serialization formats and exact accounting
see [interlevel/README.md](interlevel/README.md). The new pair decoder requires no
previous decoder bundle or checkpoint. It does not reconstruct a whole Grid4D scene.
