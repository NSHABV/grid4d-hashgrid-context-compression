> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

> При разработке и оформлении исследования использовались ИИ-агенты; [область помощи и ответственность автора](../../../docs/AI_ASSISTANCE.md). Этот исторический интерфейс может требовать внешних артефактов; проверенный публичный запуск описан в корневом README.

# Standalone XYZ L3/L4 experiment (G4DBENCH version 2)

This is an extension under the existing experiment bench, not another entropy engine.
`entropy.encode_indexed/decode_indexed` reuse constriction0.4.2 RangeEncoder/Decoder,
16-bit masses and Categorical(perfect=False). L3 uses the existing HistogramModel and
encode_symbols/decode_symbols unchanged. Original G4DBENCH version1 files and APIs stay
supported by their original decoder. This subset version2 uses the interlevel CLI.

CPU runtime: existing WSL audit-env (Python3.10.21, NumPy1.21.6, constriction0.4.2).
The wrapper disables CUDA. Windows matplotlib environment only creates figures/report.
No extra dependencies, training, checkpoint edits or requantization.

From <PROJECT_ROOT>, use a NEW output path:

```powershell
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh gate --output research/interlevel_xyz34_bitstream_new
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh run --output research/interlevel_xyz34_bitstream_new
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh compare --output research/interlevel_xyz34_bitstream_new
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh compare --output research/interlevel_xyz34_bitstream_new --against research/interlevel_xyz34_bitstream
.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.interlevel.cli finish --output research/interlevel_xyz34_bitstream_new
```

Individual commands (fresh target files/directories):

```powershell
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh encode research/my-spatial8.bin --model spatial8 --storage sparse_default_u16
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh decode research/my-spatial8.bin research/my-spatial8-decoded
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh validate --output research/interlevel_xyz34_bitstream
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh benchmark --output research/interlevel_xyz34_bitstream --repeats 3
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh tests
```

Validate reuses the saved input symbols in the parent verification process; its fresh
decoder child gets only the stream path and empty output directory. Re-validation uses
a fresh directory instead of replacing the previous decoded artifacts. The parent
checks array_equal for both levels/channels, all class IDs and serialized masses.
`compare` without --against evaluates predictions vs actual files and corruption tests.
With --against it checks the SHA256/bytes of all nine streams from a separate run.

## Context

Coordinates v/fine_scale; preserve every dense x-fastest row, no clamp. OOB has zero
coarse context and its own class. Decode L3, float64 affine dequantization -> float32;
separate float32 ufuncs for positions/smoothstep/weights; corners0..7 accumulation.
Quantile edges: linear interpolation on all in-bounds canonical CPU context, float64
serialized thresholds, searchsorted(side=right), repeated edges retained. This is the
same bin construction rule as feasibility, but now scene-specific fitting and a pinned
CPU arithmetic replace the earlier saved GPU context. CPU/GPU classes are NOT interchangeable.
Supported runtime is pinned; cross-platform decoder portability is NOT VERIFIED.

## Framing and costs

Reuse prefix <8sHQQQ>, magic G4DBENCH, version2, compact JSON directory, metadata/model
blob, coded payload blob, SHA256 trailer. Sections in order: geometry, quantization,
l3.info, l3.model, l4.info, l4.model, thresholds, l3.payload, l4.payload.
L3 symbols/model, public geometry/quantizer and L3 info are identical across all nine
files. ALL outer prefix/directory/trailer bytes are conservatively assigned to L4.
Incremental L4 = filesystem total minus the exact identical shared sections.

Model transport HGPM version1 <4sBBBBH>: storage ID, channels, context count, alphabet.
Dense: little-endian u32 masses; packed: u16 masses. Sparse row: tag0, default u16,
exception count u16, ascending (symbol u8,mass u16). Default = most frequent mass, ties
choose smallest. Tag1 omits a uniform table only for a class proven unreachable from
all decoder-known geometry/L3/edges; decoder independently verifies no row reaches it.
Reachable classes may never be omitted just because their training count was zero.
CDF accumulated in uint64; derived from exact transmitted masses, not stored twice.
All masses>=1 and sum65536. Coder additionally creates its pinned 24-bit distribution.

SHA256 provides integrity checks, not cryptographic authenticity. Trust research-sized
streams and public implementation. This file restores ONLY quantized L3/L4, not the
other HashGrid levels, Gaussian/MLP, cameras or a renderable whole scene.
