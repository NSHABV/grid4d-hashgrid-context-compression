> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

> При разработке и оформлении исследования использовались ИИ-агенты; [область помощи и ответственность автора](../../../docs/AI_ASSISTANCE.md). Этот исторический интерфейс может требовать внешних артефактов; проверенный публичный запуск описан в корневом README.

# Decoder-available hashed-context diagnostic

This module implements only stages 0–1. It does not fit a probability model,
quantize parameters, encode a stream, modify Grid4D, or train a network.

`core.compute_context(meta, coarse_symbols, chunk)` returns one row for each
allocated fine slot. Canonical lookup uses separate float32 operations and actual
CUDA geometry. Mean/population Std are float64 anchored moments updated by
`np.add.at` in ascending x-fast vertex order. Geometry-empty and boundary-only
sets use explicit zero features and invalid representative sentinels.

The existing `research/grid4d/codec.py::dequantize` function body is loaded verbatim
with AST, avoiding that module's unrelated torch/checkpoint loader in a lightweight
CPU decoder. Its SHA and a source snapshot must be preserved with each run.

Use an existing plotting Python with NumPy, e.g.
`<PROJECT_ROOT>\.tools\phase2-plotting-env\Scripts\python.exe`.
Set `PYTHONDONTWRITEBYTECODE=1`. Create a **new empty** output directory first.
Never reuse a completed result directory.

From the workspace root, with the selected Python executable:

```text
-m research.hashgrid_analysis.hashed_context.diagnostic prepare --output <fresh-run>
-m research.hashgrid_analysis.hashed_context.diagnostic pilot --output <fresh-run>
-m research.hashgrid_analysis.hashed_context.diagnostic compute --output <fresh-run>
-m research.hashgrid_analysis.hashed_context.visualize <fresh-run>
-m research.hashgrid_analysis.hashed_context.verify_real_examples --run <fresh-run>
-m research.hashgrid_analysis.hashed_context.report <fresh-run>
```

Stop if the pilot is NO-GO. Compute performs two independent replay processes per
pair (chunks4096/65536), checks every array bitwise, and runs negative read probes.
Fine symbols are saved in a separate parent-produced file only after replay.
Replay consumes only `coarse_symbols.npy` and `decoder_metadata.json`; imports and
public source files are dependencies. Its read hook is an audit of this decoder,
not an OS security sandbox. The normal replay log must contain zero blocked reads;
negative probes deliberately demonstrate four forbidden reads being blocked.

Optional GPU parity uses `run_gpu_parity.sh` in WSL and already-built CUDA modules.
No new compilation is necessary. Run it for both pair bundles into fresh GPU
subdirectories before final reporting. `cross_cpu_parity.py` compares sampled CPU
lookup outputs across Windows/WSL; it does not certify full aggregation portability.

NPZ stores canonical features/coordinates as float32, mean/Std as float64, ordinal
and counts as int64, vertex as int32, category as uint8, validity as bool. CSV uses
Python round-trip float representations. The slot ID is local to the fine level;
`global_embedding_row=offset_start+slot_index` is also stored. Geometry categories
are G0 nominal-empty, G1 nominal-positive/point-empty, G2 point-singleton and G3
point-multi. E-empty never implies rendering-unused or permission to prune.

Strictly positive Std can include tiny interpolation-rounding variation. Exact
zero, quantiles and comparisons with the existing quantization step are descriptive
diagnostics. Neither these statistics nor scatter plots establish compression gain.
