> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

> При разработке и оформлении исследования использовались ИИ-агенты; [область помощи и ответственность автора](../../docs/AI_ASSISTANCE.md). Этот исторический интерфейс может требовать внешних артефактов; проверенный публичный запуск описан в корневом README.

# Grid4D HashGrid visual analysis

Read-only scientific module using the current trained baseline. No new codec,
training, pruning, or upstream changes. Data are taken from the Phase2 interchange,
experiment manifests, real bitstreams and saved PNGs. Large histograms/statistics
are full-array; scatter/inter-level pairs and large collision lattices are sampled
with recorded deterministic settings. Two GPU-checked inter-level correspondences
are exploratory vertex-domain diagnostics; they do not define a finished table code.

From `<PROJECT_ROOT>`, using the existing plotting environment:

```powershell
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --output research/analysis_results_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --section histograms --output research/histograms_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --section entropy --quantization level-8 --output research/entropy_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --section channels --output research/channels_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --section interlevel --grids xyz --levels 5 6 7 --output research/interlevel_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --section collisions --collision-budget 100000 --output research/collisions_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --section rate-distortion --output research/rate_distortion_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --section rendering --output research/rendering_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --section dashboard --output research/analysis_results
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli test
```

The main `run` command orchestrates existing WSL compute and Windows matplotlib.
It requires WSL Ubuntu GPU access, the existing pinned audit-env, and the separate
Windows plotting env already used by the bench. No new dependency is installed.
Runtime/study/repo/checkpoint/results paths can be overridden. Quantization filters:
all or table/level-8/12/16; `--seed`, `--sampling-budget`, `--collision-budget`,
`--enumeration-limit`, `--grids`, `--levels` select the recorded scope.

Split workflow (the same compute/plot functions):

```powershell
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli prepare --output research/analysis_results_new
wsl -d Ubuntu -- bash research/run_hashgrid_analysis_compute.sh <PROJECT_ROOT>/research/analysis_results_new/config.json
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli finish --config research/analysis_results_new/config.json
```

Repeat a full run from its saved config into a new output, then:

```powershell
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.compare research/analysis_results research/analysis_results_repeat
```

Numeric-data SHA, figure artist values and PNG/SVG bytes are compared. Reproduction
is NOT RUN until a real repeated run passes. A single-section run reports partial
overall readiness honestly; its requested figures/tests can still be PASS.
Each figure has PNG, SVG, `.plot.json` (actual artist values/settings/source SHA).
Large error arrays are saved as NPZ; image values are reconstructible from referenced
original PNGs. Source CSV/JSON, figure-index, validation/test/reproduction logs,
static dashboard, research notes and report are saved in the new directory.

Extensibility: existing new experiment manifests with the same checkpoint are
included automatically. Compatible new bitstream models are read through the
bench parser; actual per-grid gain is built for every available model vs IID.
`plots.gain_heatmap` accepts records by grid/level, a numeric field, title/source,
and an explicit actual/diagnostic interpretation. Do not invent per-level actual
bits: a table-wide range stream has no measured independent level sections.
Different schedules/formats require explicit parser/specification support first.

See `SPATIAL_CORRESPONDENCE.md` for collision-domain definitions, coordinate mapping,
representative/aggregation alternatives, decoder metadata costs and causal limits.
