> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Фаза 2: экспорт, статистика и scalar quantization HashGrid Grid4D

Дата: 2026-10-09. **PASS**: lossless round trip, GPU forward/render parity и все шесть quantization variants проверены.

## A–B. Модули и тесты

`research/grid4d/codec.py`: отдельный versioned raw interchange, CPU decoder, uniform min/max quantization, empirical entropy.
`study.py`: статистика, гистограммы, 6 вариантов и копии inference bundles. `test_codec.py`: автоматические unit tests.
`test_forward.py`: подстановка lossless tensors в настоящую GPU модель и torch.equal outputs на 257 coordinates, включая OOB.
`inference_check.py`: wrapper upstream render.py; strict states, неизменность buffers/MLP, finite деформации/RGB/depth каждого view.
`report.py`: проверка всех artifacts, float32 render hashes и PNG parity 20 views, метрик и сохранности исходных artifacts.

5 unit tests PASS (каждый проверяет несколько bit depths/arrays). GPU test PASS. Original/restored forward и 20 float32 RGB frames bitwise equal.
Все 8 запусков (original, restored, 6 quantized) создали по 20 RGB/GT/depth frames 400×400; 4 метрики ×20 views конечны.
Evidence: `phase2/tests.log`, `forward-test.json`, `verification.json`, variant `inference.json`, `model/results.json`, `model/per_view.json`.

## C. Lossless export/import и metadata

Источник: `outputs/grid4d/bouncingballs-audit-200/deform/iteration_200/deform.pth`, SHA256 729f0e8b86a2b867e8e1bdcead85722f7b0b2b96a3b3f58d641e43cc14cf22a9.
Grid4D official commit `3ab7b74482910d22fba7d51ac60c8cae1fe24bf1`; Python 3.10.21, torch 2.7.0+cu128, nvcc 12.8.93, GCC 13.4.0, sm120.
Использовано существующее audit-env, без новых Grid4D dependencies. Upstream, исходные snapshots и datasets не изменялись; training не запускался.
Matplotlib figures построены отдельно в Windows `.tools/phase2-plotting-env`: Python 3.12, NumPy 1.26.4, matplotlib 3.9.4; exact closure `phase2/plotting-requirements.txt`.
Неизменность: проверены 1620 upstream source/resource files, SHA256 обеих исходных model bundles, 193+193 dataset files и обоих generated points3d.ply.

Формат `phase2/lossless/manifest.json` + little-endian raw `.bin`: float32 embeddings, int32 offsets, float32 base_resolution/per_level_scale.
Metadata включают имена, shapes/dtypes, feature dimensions, counts/bytes, L, offsets, table rows, allocation resolutions и actual CUDA lookup resolutions, config и source/runtime hashes.
Metadata сверены с реальными checkpoint buffers; resolutions взяты из ранее проверенного GPU runtime record, а не выведены из shape.
Temporal last level: allocation [32,32,16], CUDA lookup [33,33,16]. Их нельзя подменять друг другом.

Программный интерфейс (из workspace root, в Grid4D environment):

```python
from pathlib import Path
from research.grid4d.codec import export_lossless, import_tables, load_checkpoint, substitute
checkpoint = Path("outputs/grid4d/bouncingballs-audit-200/deform/iteration_200/deform.pth")
export_lossless(checkpoint, "research/audit/hashgrid-runtime.json", Path("research/new-export"))
tables, buffers, metadata = import_tables("research/new-export")
restored_state = substitute(load_checkpoint(checkpoint), tables, buffers)
```

Decoder использует только exported payload и metadata; исходные float32 нужны лишь для сравнения и неизменяемых MLP/Gaussians.
Для настоящей модели: copy_ в `deform.grid4d.get_parameter(key)` под no_grad; сброс `deform.deform.attention_score=None` после подстановки.
Исходные offsets и buffers не меняются. Gaussian PLY, deformation MLP, cfg_args/config, cameras и normalization остаются внешними необходимыми компонентами.

## D. Статистика

Population std (ddof=0), exact np.unique float32, нулевая доля включает ±0; histograms 80 bins. Статистика объединяет оба channels.
JSON содержит counts/edges; CSV все уровни. PNG: `phase2/plots/tables.png` (bin probabilities, common x range) и четыре `*-levels.png` (per-level counts, individual x ranges); y scale logarithmic.

| Grid | N | min | max | mean | std | unique | zero fraction |
|---|---:|---:|---:|---:|---:|---:|---:|
| xyz_encoding.embeddings | 12196216 | -1.246158 | 1.123889 | -0.003587354 | 0.05507131 | 11503673 | 0 |
| xyt_encoding.embeddings | 322426 | -0.4905356 | 0.4515899 | -0.006047358 | 0.06807313 | 321734 | 0 |
| yzt_encoding.embeddings | 322426 | -0.501526 | 0.4773272 | -0.009719398 | 0.07028506 | 321729 | 0 |
| xzt_encoding.embeddings | 322426 | -0.6083447 | 0.537317 | -0.006454976 | 0.0716024 | 321767 | 0 |

G_xyz содержит большую часть scalar parameters; spatial/temporal marginal ranges и variances приведены отдельно. Сходство гистограмм не доказывает межуровневую/межсеточную зависимость.

| Grid | Level | N | min | max | mean | std | unique | zero fraction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| xyz | 0 | 8192 | -0.746634 | 0.638026 | 0.0217025 | 0.11233 | 8191 | 0 |
| xyz | 1 | 24334 | -0.555438 | 0.898493 | 0.00274206 | 0.105441 | 24329 | 0 |
| xyz | 2 | 59582 | -0.957992 | 0.722465 | 0.00391148 | 0.111846 | 59560 | 0 |
| xyz | 3 | 159014 | -0.895825 | 0.769433 | -0.0204492 | 0.0921489 | 158791 | 0 |
| xyz | 4 | 410758 | -1.24616 | 0.607792 | 0.012807 | 0.0829249 | 409349 | 0 |
| xyz | 5 | 1048576 | -0.797395 | 1.12389 | 0.0022676 | 0.0704085 | 1036746 | 0 |
| xyz | 6 | 1048576 | -0.73804 | 1.02949 | -0.0164463 | 0.0874328 | 1042519 | 0 |
| xyz | 7 | 1048576 | -1.06643 | 0.779466 | -0.0136473 | 0.0711218 | 1042417 | 0 |
| xyz | 8 | 1048576 | -0.68937 | 0.520046 | -5.1764e-05 | 0.0537855 | 1042004 | 0 |
| xyz | 9 | 1048576 | -0.652517 | 0.438593 | -0.0107323 | 0.0441124 | 1041099 | 0 |
| xyz | 10 | 1048576 | -0.347528 | 0.373873 | -0.00224809 | 0.035799 | 1041638 | 0 |
| xyz | 11 | 1048576 | -0.350813 | 0.378489 | 0.000264757 | 0.0371726 | 1041650 | 0 |
| xyz | 12 | 1048576 | -0.364552 | 0.364231 | -0.00586069 | 0.0344898 | 1041328 | 0 |
| xyz | 13 | 1048576 | -0.274015 | 0.29288 | 0.00516163 | 0.0329968 | 1041214 | 0 |
| xyz | 14 | 1048576 | -0.335876 | 0.345485 | -0.000887556 | 0.0329451 | 1041462 | 0 |
| xyz | 15 | 1048576 | -0.289552 | 0.328055 | -0.00191652 | 0.0327187 | 1041413 | 0 |
| xyt | 0 | 1024 | -0.238656 | 0.202155 | -0.0236103 | 0.0844975 | 1024 | 0 |
| xyt | 1 | 1458 | -0.131092 | 0.264932 | 0.0674724 | 0.0590694 | 1458 | 0 |
| xyt | 2 | 1458 | -0.261296 | 0.268869 | -0.00554106 | 0.100919 | 1458 | 0 |
| xyt | 3 | 1800 | -0.226194 | 0.249495 | -0.0130608 | 0.0736482 | 1800 | 0 |
| xyt | 4 | 1800 | -0.382226 | 0.045918 | -0.0779612 | 0.0590935 | 1800 | 0 |
| xyt | 5 | 2178 | -0.279288 | 0.296364 | 0.0047641 | 0.0978066 | 2178 | 0 |
| xyt | 6 | 2420 | -0.271235 | 0.28823 | 0.0138285 | 0.0779487 | 2420 | 0 |
| xyt | 7 | 2420 | -0.330228 | 0.45159 | -0.00347876 | 0.0928544 | 2420 | 0 |
| xyt | 8 | 2880 | -0.190617 | 0.314266 | 0.0716746 | 0.0562713 | 2879 | 0 |
| xyt | 9 | 2880 | -0.31352 | 0.240132 | -0.0629917 | 0.0612218 | 2880 | 0 |
| xyt | 10 | 3718 | -0.254444 | 0.268616 | 0.000188533 | 0.0862248 | 3718 | 0 |
| xyt | 11 | 4312 | -0.441285 | 0.449423 | -0.0200643 | 0.0715811 | 4312 | 0 |
| xyt | 12 | 4312 | -0.217422 | 0.310147 | 0.0397932 | 0.0510463 | 4312 | 0 |
| xyt | 13 | 4950 | -0.309695 | 0.248479 | -0.0496782 | 0.0546762 | 4950 | 0 |
| xyt | 14 | 4950 | -0.312783 | 0.358476 | -0.0102298 | 0.0825558 | 4950 | 0 |
| xyt | 15 | 6144 | -0.490536 | 0.278243 | -0.0438942 | 0.0580569 | 6143 | 0 |
| xyt | 16 | 6936 | -0.44784 | 0.328039 | 0.0179816 | 0.0684366 | 6934 | 0 |
| xyt | 17 | 7776 | -0.251839 | 0.370018 | 0.00771071 | 0.0702605 | 7776 | 0 |
| xyt | 18 | 7776 | -0.331073 | 0.272924 | -0.00259018 | 0.0849337 | 7776 | 0 |
| xyt | 19 | 9386 | -0.288747 | 0.350606 | -0.0180849 | 0.0625054 | 9386 | 0 |
| xyt | 20 | 10400 | -0.248189 | 0.415145 | -0.00263994 | 0.0694336 | 10400 | 0 |
| xyt | 21 | 11466 | -0.356838 | 0.338536 | -0.0429058 | 0.0574666 | 11465 | 0 |
| xyt | 22 | 13552 | -0.405925 | 0.371803 | -0.000778066 | 0.0676006 | 13551 | 0 |
| xyt | 23 | 14812 | -0.330006 | 0.292155 | -0.00348503 | 0.0665129 | 14812 | 0 |
| xyt | 24 | 16128 | -0.327987 | 0.392127 | 0.0272378 | 0.0640705 | 16126 | 0 |
| xyt | 25 | 17500 | -0.264215 | 0.421202 | 0.0137302 | 0.0627572 | 17498 | 0 |
| xyt | 26 | 20280 | -0.389157 | 0.327535 | -0.00820531 | 0.0760229 | 20279 | 0 |
| xyt | 27 | 21870 | -0.34538 | 0.376503 | -0.0167437 | 0.062798 | 21864 | 0 |
| xyt | 28 | 23520 | -0.347683 | 0.326018 | 0.0125677 | 0.0651398 | 23518 | 0 |
| xyt | 29 | 28800 | -0.383575 | 0.324805 | 0.00579214 | 0.0561995 | 28795 | 0 |
| xyt | 30 | 30752 | -0.404623 | 0.308136 | -0.035448 | 0.0537744 | 30743 | 0 |
| xyt | 31 | 32768 | -0.401574 | 0.381703 | -0.0111261 | 0.0503171 | 32753 | 0 |
| yzt | 0 | 1024 | -0.270352 | 0.411387 | 0.00774538 | 0.119541 | 1024 | 0 |
| yzt | 1 | 1458 | -0.239438 | 0.390001 | 9.09874e-05 | 0.0910815 | 1458 | 0 |
| yzt | 2 | 1458 | -0.30346 | 0.257729 | -0.00294803 | 0.0983462 | 1458 | 0 |
| yzt | 3 | 1800 | -0.297222 | 0.299379 | 0.0228987 | 0.0857092 | 1800 | 0 |
| yzt | 4 | 1800 | -0.287365 | 0.436916 | -0.00344649 | 0.102704 | 1800 | 0 |
| yzt | 5 | 2178 | -0.303276 | 0.381219 | -0.0438671 | 0.0852047 | 2178 | 0 |
| yzt | 6 | 2420 | -0.322388 | 0.277897 | 0.0381366 | 0.0730912 | 2420 | 0 |
| yzt | 7 | 2420 | -0.304108 | 0.309567 | -0.000233652 | 0.0990806 | 2420 | 0 |
| yzt | 8 | 2880 | -0.294127 | 0.313849 | -0.0117208 | 0.0930036 | 2880 | 0 |
| yzt | 9 | 2880 | -0.452129 | 0.220264 | -0.0592577 | 0.0741036 | 2880 | 0 |
| yzt | 10 | 3718 | -0.364229 | 0.206837 | -0.0499407 | 0.061949 | 3718 | 0 |
| yzt | 11 | 4312 | -0.336467 | 0.275602 | -0.0380679 | 0.0606741 | 4312 | 0 |
| yzt | 12 | 4312 | -0.223252 | 0.187703 | -0.04957 | 0.05808 | 4312 | 0 |
| yzt | 13 | 4950 | -0.303767 | 0.398175 | -0.0338312 | 0.0695032 | 4950 | 0 |
| yzt | 14 | 4950 | -0.501526 | 0.316965 | -0.0469365 | 0.0806778 | 4950 | 0 |
| yzt | 15 | 6144 | -0.377424 | 0.250876 | -0.0451391 | 0.0554009 | 6143 | 0 |
| yzt | 16 | 6936 | -0.410029 | 0.378832 | -0.0145456 | 0.0696835 | 6936 | 0 |
| yzt | 17 | 7776 | -0.494432 | 0.247346 | -0.00101689 | 0.0800519 | 7776 | 0 |
| yzt | 18 | 7776 | -0.234034 | 0.276197 | 0.0532731 | 0.0613274 | 7776 | 0 |
| yzt | 19 | 9386 | -0.268981 | 0.355833 | 0.0183417 | 0.0696187 | 9386 | 0 |
| yzt | 20 | 10400 | -0.297394 | 0.33574 | -0.00764106 | 0.0644889 | 10400 | 0 |
| yzt | 21 | 11466 | -0.312051 | 0.477327 | 0.0363972 | 0.0664636 | 11465 | 0 |
| yzt | 22 | 13552 | -0.376862 | 0.394869 | -0.0357051 | 0.060574 | 13551 | 0 |
| yzt | 23 | 14812 | -0.290647 | 0.350129 | 0.000277373 | 0.0730185 | 14811 | 0 |
| yzt | 24 | 16128 | -0.384208 | 0.339074 | -0.00464427 | 0.0709857 | 16127 | 0 |
| yzt | 25 | 17500 | -0.444135 | 0.312358 | 0.0161248 | 0.0606713 | 17500 | 0 |
| yzt | 26 | 20280 | -0.360889 | 0.415986 | -0.0273064 | 0.0638498 | 20278 | 0 |
| yzt | 27 | 21870 | -0.42274 | 0.300502 | -0.0339817 | 0.0587431 | 21864 | 0 |
| yzt | 28 | 23520 | -0.373993 | 0.338862 | -0.0315921 | 0.0640036 | 23518 | 0 |
| yzt | 29 | 28800 | -0.36798 | 0.366365 | 0.019662 | 0.0582616 | 28797 | 0 |
| yzt | 30 | 30752 | -0.413945 | 0.316243 | -0.0266743 | 0.0578064 | 30748 | 0 |
| yzt | 31 | 32768 | -0.349465 | 0.449098 | 0.000836508 | 0.0604458 | 32758 | 0 |
| xzt | 0 | 1024 | -0.240811 | 0.274282 | 0.0061215 | 0.115777 | 1024 | 0 |
| xzt | 1 | 1458 | -0.411789 | 0.240443 | 0.0047393 | 0.0892916 | 1458 | 0 |
| xzt | 2 | 1458 | -0.490248 | 0.143999 | -0.0838448 | 0.06912 | 1458 | 0 |
| xzt | 3 | 1800 | -0.284545 | 0.17842 | -0.0716337 | 0.0604925 | 1800 | 0 |
| xzt | 4 | 1800 | -0.272296 | 0.34543 | -0.0509787 | 0.074964 | 1800 | 0 |
| xzt | 5 | 2178 | -0.304618 | 0.346378 | -0.0174998 | 0.0857344 | 2178 | 0 |
| xzt | 6 | 2420 | -0.269342 | 0.219537 | -0.0504667 | 0.0586689 | 2420 | 0 |
| xzt | 7 | 2420 | -0.510383 | 0.342561 | -0.00762134 | 0.102792 | 2420 | 0 |
| xzt | 8 | 2880 | -0.256841 | 0.462428 | 0.00819736 | 0.0945881 | 2880 | 0 |
| xzt | 9 | 2880 | -0.427841 | 0.311406 | -0.0598701 | 0.0742624 | 2880 | 0 |
| xzt | 10 | 3718 | -0.41087 | 0.533257 | 0.0133359 | 0.0778778 | 3718 | 0 |
| xzt | 11 | 4312 | -0.327037 | 0.537317 | -0.000657918 | 0.0673138 | 4312 | 0 |
| xzt | 12 | 4312 | -0.334506 | 0.253433 | -0.0467154 | 0.0570112 | 4312 | 0 |
| xzt | 13 | 4950 | -0.232611 | 0.318296 | 0.00896732 | 0.0732586 | 4950 | 0 |
| xzt | 14 | 4950 | -0.356981 | 0.273199 | 0.00324577 | 0.0778786 | 4950 | 0 |
| xzt | 15 | 6144 | -0.584132 | 0.272123 | 0.00127126 | 0.0734096 | 6144 | 0 |
| xzt | 16 | 6936 | -0.44693 | 0.326495 | 0.0208358 | 0.0660931 | 6936 | 0 |
| xzt | 17 | 7776 | -0.292823 | 0.294538 | -0.0210959 | 0.0624259 | 7776 | 0 |
| xzt | 18 | 7776 | -0.608345 | 0.350216 | -0.0342264 | 0.0709443 | 7776 | 0 |
| xzt | 19 | 9386 | -0.264489 | 0.479968 | 0.00945992 | 0.077364 | 9386 | 0 |
| xzt | 20 | 10400 | -0.269723 | 0.342626 | -0.0315586 | 0.0532816 | 10399 | 0 |
| xzt | 21 | 11466 | -0.392786 | 0.335474 | -0.0252687 | 0.0655295 | 11465 | 0 |
| xzt | 22 | 13552 | -0.545015 | 0.407004 | 0.0123862 | 0.0656908 | 13550 | 0 |
| xzt | 23 | 14812 | -0.423548 | 0.322727 | -0.0107 | 0.0687048 | 14810 | 0 |
| xzt | 24 | 16128 | -0.365127 | 0.332799 | -0.0469237 | 0.058935 | 16125 | 0 |
| xzt | 25 | 17500 | -0.504212 | 0.469741 | -0.0105836 | 0.0784196 | 17498 | 0 |
| xzt | 26 | 20280 | -0.395077 | 0.422115 | -0.000961758 | 0.0689659 | 20276 | 0 |
| xzt | 27 | 21870 | -0.455122 | 0.471314 | 0.0208449 | 0.0695672 | 21865 | 0 |
| xzt | 28 | 23520 | -0.417443 | 0.524484 | -0.0126643 | 0.0826798 | 23518 | 0 |
| xzt | 29 | 28800 | -0.309478 | 0.392714 | 0.00721225 | 0.0604507 | 28799 | 0 |
| xzt | 30 | 30752 | -0.480086 | 0.516612 | 0.0087761 | 0.0693294 | 30746 | 0 |
| xzt | 31 | 32768 | -0.439579 | 0.31948 | -0.00629298 | 0.0527544 | 32756 | 0 |

## E–G. Квантование, энтропия и rendering

Uniform scalar min/max affine, round-to-nearest-even, arithmetic float64, decoded float32; диапазон 0..2^b-1. Scope table: одна пара min/max на grid; scope level: на каждый level.
Constant arrays: zero symbols, step=0, exact constant reconstruction. Empty/nonfinite/wrong dtype rejected. Extreme float32 и subnormal arrays tested.
Quantization params (bits/min/max/step/row interval/rounding) сохранены в manifest; decoder не читает original embeddings.

Размер ниже — реально сериализованные embeddings/symbols + 12 buffers + JSON manifest, без Gaussians/MLP и без diagnostic inference copies.
12-bit symbols сохранены в uint16, поэтому фактический payload совпадает по контейнерному размеру с 16-bit. Packed 12-bit stream не реализован.
MSE вычислен float64, взвешен по всем 13163494 scalar values. Все quality metrics mean на тех же 20 камерах и PNG upstream protocol.

| Вариант | Реальный размер, bytes | H, bits/symbol | MSE параметров | PSNR dB | SSIM | LPIPS |
|---|---:|---:|---:|---:|---:|---:|
| original | 52680472 | — | 0 | 16.12583160 | 0.87903941 | 0.16759041 |
| table-16 | 26354833 | 11.957208 | 1.0312021e-10 | 16.12583351 | 0.87903959 | 0.16759130 |
| table-12 | 26354831 | 8.092683 | 2.4517535e-08 | 16.12583160 | 0.87903816 | 0.16759059 |
| table-8 | 13191322 | 4.389216 | 6.1678425e-06 | 16.12648392 | 0.87906283 | 0.16758530 |
| level-16 | 26387257 | 12.654356 | 2.7912745e-11 | 16.12583351 | 0.87903941 | 0.16758987 |
| level-12 | 26387281 | 8.937159 | 7.8537803e-09 | 16.12583351 | 0.87903816 | 0.16760316 |
| level-8 | 13223549 | 5.301964 | 1.9055985e-06 | 16.12607574 | 0.87904185 | 0.16760325 |

| Вариант | Payload bytes | JSON+buffers bytes | Fixed codes bits | Fixed codes+metadata bytes | H*N bits | H*N/8+metadata bytes | Fixed reduction vs f32 | Entropy reduction vs f32 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| table-16 | 26326988 | 27845 | 210615904 | 26354833 | 157398630.372 | 19702673.796 | 50.000% | 62.634% |
| table-12 | 26326988 | 27843 | 157961928 | 19773084 | 106527978.398 | 13343840.300 | 62.500% | 74.710% |
| table-8 | 13163494 | 27828 | 105307952 | 13191322 | 57777411.982 | 7250004.498 | 75.000% | 86.284% |
| level-16 | 26326988 | 60269 | 210615904 | 26387257 | 166575543.767 | 20882211.971 | 50.000% | 60.455% |
| level-12 | 26326988 | 60293 | 157961928 | 19805534 | 117644235.891 | 14765822.486 | 62.500% | 72.071% |
| level-8 | 13163494 | 60055 | 105307952 | 13223549 | 69792377.542 | 8784102.193 | 75.000% | 83.431% |

Fixed и entropy reductions в последней паре columns относятся к scalar payload без metadata; с metadata размеры указаны отдельно.
H=-sum p log2 p. Для scope table итог — сумма N_g H_g; для scope level — сумма N_gl H_gl. Это marginal IID plug-in entropy, не contextual entropy.
`phase2/entropy.csv/json`: H, unique symbols, theoretical bits и fixed bits для каждой таблицы и каждого уровня всех шести variants.
**H*N — теоретическая оценка. Ни probability-count header, ни coder termination/framing, ни actual encoded bitstream не реализованы.** JSON и buffers учтены; незаданный entropy model/coder overhead не выдумывался.
Saved reconstructed `model/deform/...pth` — диагностическая float32 копия для upstream inference, не compressed payload и не участвует в size columns.

Одинаковые cameras, resolution=2 (400x400), black background, iteration=200, skip_train, Gaussian PLY и MLP. LPIPS net=vgg, upstream [0,1] normalize=False; протокол не менялся.
Все metrics delta к original в `summary-evaluated.json`; per-view в каждом `model/per_view.json`. MS-SSIM также сохранён.
Пример GT/original/table8/level8: `phase2/preview.png`. Lossless restored картинки и float RGB hashes совпали с original; original PNG также совпали с Phase1 audit.

## H. Ограничения

Только checkpoint после 200 iterations, warm_up=10, без densification, downsampled resolution. Качественно обученный snapshot не доступен в текущих artifacts и не обучался на этой фазе.
Результаты подтверждают работоспособность инструментов, finite inference и локальную чувствительность smoke weights; они не являются полноценным rate-distortion исследованием.
Энтропия зависит от histogram symbol counts и выбранного min/max; её нельзя считать достижимым размером без передачи/моделирования распределения.
Snapshot inference-only, без optimizer/RNG. Quantized bundles не предназначены для продолжения обучения.

## I. Следующий этап — только рекомендации

Сначала получить один converged reference checkpoint той же сцены с неизменённым objective и зафиксировать 20-view baseline, затем повторить этот scalar study.
До inter-level coding определить порядок symbols (grid, level, row, channel), доступность decoder-side context и causal schedule, сохранять exact buffers/resolutions и правила addressing.
Нужно измерять conditional likelihood на отделённых данных и сравнивать с текущей marginal entropy, учитывать стоимость model/metadata и проверять decoder round trip.
Текущий export интерфейс даёт tables/level slices и stable metadata; сходство marginal histograms не обосновывает context модель.
Фаза 3 не запускалась. NVCC/CNC/neural models, temporal/collision/cross-grid context, bitstream encoder/decoder и CUDA changes не реализованы.

## J. Воспроизведение

Из PowerShell в workspace:

```powershell
wsl -d Ubuntu -- bash research/run_phase2.sh tests
wsl -d Ubuntu -- bash research/run_phase2.sh study
wsl -d Ubuntu -- bash research/run_phase2.sh forward
wsl -d Ubuntu -- bash research/run_phase2.sh render
wsl -d Ubuntu -- bash research/run_phase2.sh metrics
wsl -d Ubuntu -- bash research/run_phase2.sh verify
```

Запуски с сохранением logs и wall times: `powershell -NoProfile -ExecutionPolicy Bypass -File research/run_phase2_checks.ps1` после study. Bypass относится только к процессу, системная ExecutionPolicy не меняется.
Для matplotlib графиков отдельно: создать `.tools/phase2-plotting-env` через Windows Python `-m venv`, установить `-r research/phase2/plotting-requirements.txt`, выполнить `.tools/phase2-plotting-env/Scripts/python.exe research/plot_phase2.py`.
`study` требует отсутствующую output directory и не перезаписывает существующие данные. Для нового study: `python -m research.grid4d.study --out research/phase2-new` после source env_common; runtime stages здесь привязаны к phase2, выбрать соответствующие paths для нового output.
`tests/forward/render/metrics/verify` повторяемы поверх research outputs; оригинальные artifacts не затрагиваются.
CPU study elapsed: 47.49s. Runtime logs: `phase2/render.log`, `metrics.log`; wall time стадий `phase2/stage-times.json`.
Max GPU memory специально не профилировалась; Phase1 resource baseline остаётся в AUDIT_PHASE1.md.
Сбой Windows sandbox setup refresh потребовал разрешённого запуска команд вне sandbox. Windows ExecutionPolicy блокировала .ps1: использован process-only Bypass; stderr warnings записаны без прерывания, проверяется native exit code.
Новый cwd для GPU forward вызвал обычную JIT сборку encoder в root/tmp_build (102s стадия forward); CUDA source/flags не менялись. Rendering использует уже собранный upstream cache.
В штатном bundled Python отсутствовал matplotlib, поэтому вспомогательный plotting env отделён от Grid4D. Исследовательский runtime остаётся locked Phase1.
Итог определяется verification, а не одним exit code upstream metrics.py, который скрывает исключения.
