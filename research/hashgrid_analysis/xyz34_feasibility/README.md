> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

> При разработке и оформлении исследования использовались ИИ-агенты; [область помощи и ответственность автора](../../../docs/AI_ASSISTANCE.md). Этот исторический интерфейс может требовать внешних артефактов; проверенный публичный запуск описан в корневом README.

# CPU feasibility study for decoder-available xyz L3 -> L4

Uses immutable `research/interlevel_xyz34_results`, the existing table-wise8 symbols,
and the existing `experiment_bench.models.frequencies` finite-mass estimator.
No GPU, raw floating-point embeddings, new entropy coder or neural model is used.

From `<PROJECT_ROOT>`, with the existing Windows plotting environment:

```powershell
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.xyz34_feasibility.run --output research/interlevel_xyz34_feasibility_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.xyz34_feasibility.finish --output research/interlevel_xyz34_feasibility_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.xyz34_feasibility.compare research/interlevel_xyz34_feasibility research/interlevel_xyz34_feasibility_new
.tools/phase2-plotting-env/Scripts/python.exe -m unittest research.hashgrid_analysis.xyz34_feasibility.tests -v
```

Output directories must be new for `run`. `finish` can regenerate plots from the
saved numeric results. A full repeated run into a different directory is required
before reproduction receives PASS. Defaults: seeds0/1/2, random/block8/block16
splits, train/validation/test64/16/20, 1000 conditional-on-fit spatial bootstrap
draws, Laplace alpha1 and deterministic finite masses sum65536.

All bins use training-only in-bounds context values. Model selection uses validation
projected cost under each explicitly named storage scenario. Final test is never
used for selecting K, edges or smoothing. Empty tied-quantile classes are retained
and charged in dense formats. Targets and models are separated by channel.

Every fitted count/mass/edge and per-test-row cost is in `fitted_histograms.npz`;
`splits.npz` stores row IDs. `results.json`, per-split results, class occupancy and
overhead CSVs contain exact numeric results. PNG/SVG/settings have source/checkpoint
SHA. The report explains bootstrap limits, empirical MI, projected cost, model
selection and the three proposed storage scenarios.

Primary dense uint32 is the existing bench model-section width. Packed uint16 and
sparse-default uint16 are diagnostic lossless-storage estimates, not implemented
transport formats. Derived CDF memory is not charged again as file bytes. Every
actual_bitstream_bytes field is null. Entire-scene rate is not inferred from this
single pair. Production coding, other levels and other contexts are separate tasks.
