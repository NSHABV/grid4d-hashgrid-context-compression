> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Grid4D experimental bench

Дата: 2026-10-09. Вердикт: **READY FOR RESEARCH**.

## A. Environment and reproducibility

Official upstream: [Grid4D](https://github.com/JiaweiXu8/Grid4D), revision `3ab7b74482910d22fba7d51ac60c8cae1fe24bf1`.
Сохранены Python 3.10.21, PyTorch 2.7.0+cu128, torchvision 0.22.0+cu128, CUDA Toolkit 12.8.93, GCC/G++ 13.4.0; WSL2 Ubuntu, RTX 5060 Laptop 8151 MiB, sm120.
Использован существующий audit-env; baseline conda/pip locks не менялись. `constriction==0.4.2` установлен отдельно в `.tools/bench-python` (413874-byte wheel).
Wheel SHA256 `2f104f35a6156809e9240ab11ee3b321a7b390df54b4dd43942257f3018a6346`; dependency NumPy>=1.16,<3, используется прежняя 1.21.6. License choice MIT; license texts в `experiment_bench/licenses/`.
Sources: [constriction 0.4.2](https://pypi.org/project/constriction/0.4.2/), [API](https://bamler-lab.github.io/constriction/apidoc/python/stream/model.html).
Matplotlib 3.9.4/NumPy 1.26.4 используются только в ранее созданном отдельном Windows plotting env. Новых CUDA kernels, source patches, training objective изменений нет.
Минимальные изменения старого research-кода: Phase2 study/prepare_model и forward test получили iteration/path arguments; inference wrapper получил source/repo environment overrides. Старые defaults и outputs сохранены.

## B. Trained reference checkpoint

Подходящий official pretrained checkpoint не найден в README/project page и [releases](https://github.com/JiaweiXu8/Grid4D/releases); это ограниченный отрицательный результат поиска.
Reference обучен локально с нуля; финальный snapshot выбран по фиксированной iteration=50000, не по best test score.
Checkpoint: `outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth`, SHA256 `3306dabf8057728abfa7cda87d78c723b27a357f968fd7d721ea727ebd043090`.
Gaussian PLY: `point_cloud/iteration_50000/point_cloud.ply`. cfg_args + scene config + cameras также обязательны. Optimizer/RNG не сохраняются upstream; exact resume не заявляется.
Dataset прежний D-NeRF bouncingballs, 150 train/20 test, 800x800, black background. Полный стандартный protocol: 50000 iterations, warm-up3000, densification >500 и <15000 каждые100, threshold0.0002, opacity reset3000.
LR: xyz1.6e-4→1.6e-6, max_steps35000; SH feature0.0025, opacity0.05, scaling0.001, rotation0.001; grid scale50, network scale5, deform LR max_steps45000.
Objective: (1-.2)L1+.2(1-SSIM)+.5 spatial TV+.5 temporal TV; perturb/downsample как в official scene config. Original training densify_and_prune сохранён; отдельный research pruning не реализован.
Runtime отличие: `--load2gpu_on_the_fly` для экономии VRAM; `--resolution 1` явно задаёт исходные 800x800. Warm-up, densification и iterations не уменьшались.
Предварительный smoke3600: 132.42s, all3600 losses finite, save/load/20-view render PASS, torch reserved2.70GiB; это отдельный технический snapshot, не reference.
Full training: 5873.70s (97.90min), loss first=0.50809741, last=0.0011611019, min=0.00086276862; все50000 checks finite.
Peak torch allocated=1.819GiB, reserved=2.748GiB; sampled total device peak=4030.0MiB (includes desktop/other apps, samples5s).
Все стандартные промежуточные snapshots сохранены отдельно, best snapshots также создаёт upstream. Intermediate test PSNR/L1: `training-summary.json`; loss values/timings: `reference-training.json`; TensorBoard events и training log доступны.
Ресурсы до smoke: GPU free6779MiB (nvidia-smi), WSL availableRAM6828MiB из7579, swap2048MiB свободен; disk D free≈125GiB. Нехватки ресурсов/OOM не возникло.

## C. Phase2 repeated results

`reference-study/`: lossless export/import, структуры/buffers, 112-level statistics CSV/JSON, 6 scalar variants и empirical entropy CSV/JSON.
HashGrid ровно4 trainable tables: xyz[6098108,2]L16; xyt/yzt/xzt[161213,2]L32. 13163494 scalars, 52653976 rawfloat32 bytes. Actual offsets/resolutions взяты из checkpoint и GPU runtime metadata.
Allocation vs lookup temporal last resolution [32,32,16] vs [33,33,16] сохранены раздельно. All buffers unchanged; float32 equality и live GPU forward parity проверены.
Quantization прежняя: min/max affine, nearest-even, float64 arithmetic, float32 reconstruction. table и level scopes,8/12/16bits. 12-bit serialized containers uint16; ideal12-bit cost отдельно, packing12 не реализован.

| Variant | Actual serialized bytes | Parameter MSE | PSNR | SSIM | LPIPS | MS-SSIM |
|---|---:|---:|---:|---:|---:|---:|
| float32 | 52680472 | 0 | 42.4922409 | 0.9958137 | 0.0074352 | 0.9973624 |
| table-16 | 26354826 | 1.33321118e-09 | 42.4910278 | 0.9958137 | 0.0074352 | 0.9973624 |
| table-12 | 26354824 | 3.00872811e-07 | 42.4671402 | 0.9958110 | 0.0074399 | 0.9973612 |
| table-8 | 13191313 | 0.000171003541 | 38.7516594 | 0.9944757 | 0.0097342 | 0.9969470 |
| level-16 | 26387139 | 1.25906981e-10 | 42.4922371 | 0.9958140 | 0.0074347 | 0.9973624 |
| level-12 | 26387100 | 2.89267452e-08 | 42.4836578 | 0.9958134 | 0.0074373 | 0.9973625 |
| level-8 | 13223369 | 8.10659038e-06 | 41.0303307 | 0.9954485 | 0.0079172 | 0.9972542 |

Table-level empirical entropy/fixed ideal sizes (without probability header, not real entropy file sizes):

| Variant | Ideal fixed bits | Empirical H bits/symbol | H*N bits | Serialized payload bytes | Metadata+buffers bytes |
|---|---:|---:|---:|---:|---:|
| table-16 | 210615904 | 7.9874608 | 105142891.965 | 26326988 | 27838 |
| table-12 | 157961928 | 4.3096204 | 56729662.880 | 26326988 | 27836 |
| table-8 | 105307952 | 1.6971481 | 22340399.030 | 13163494 | 27819 |
| level-16 | 210615904 | 10.2332149 | 134704862.784 | 26326988 | 60151 |
| level-12 | 157961928 | 6.5713030 | 86501307.190 | 26326988 | 60112 |
| level-8 | 105307952 | 3.0006135 | 39498557.528 | 13163494 | 59875 |

## D. Entropy coding

Настоящий CPU range coder constriction0.4.2; `fixed8` — raw uint8 control с тем же metadata/framing. Self-contained formatv1: little-endian magic/version/section lengths, JSON, transmitted finite histograms, coded uint32 words, trailing SHA256.
Decoder принимает только bitstream path и fresh output; в новом process восстанавливает uint8 symbols, quantization min/max/step, shapes/offsets/resolutions и exact float32 buffers. После этого Phase2 importer деквантует значения.
Original checkpoint и quantized input не доступны isolated decoder tests: synthetic source directory физически удаляется перед restart decoding. Actual experiment decoder CLI также получает только bitstream/output.
Exact symbol equality проверена для всех4 tables всех3 coding models. CRC/hash, version, section length, CDF/symbol failures дают exception/nonzero exit. Диагностические `.pth`, PLY, renders и logs не включены в compressed size.

## E. Probability models

IID: p(q0)p(q1) отдельно для каждой из4 таблиц. Context: p(q0)p(q1|q0>>4),16 classes; та же table/channel granularity и то же table-wise8-bit quantization.
Schedule: decode allq0 rows ascending, затем q1 по class0..15, stable row order. Context extraction принимает только уже decodedq0. Encoder.fit видит всю сцену для двухпроходного histogram fit; все полученные distributions переданы и оплачены.
Laplace alpha1, minimum finite mass1, largest-remainder normalization sum65536. Serialized masses uint32; CDF strict increasing, all256 symbols nonzero. Empty classes uniform. Constriction constructs its own deterministic24-bit model, perfect=False.
IID model cost8192bytes; context69632bytes. Metadata/framing посчитаны по реальным секциям. Quantization parameters, bounds и buffers включены в JSON cost.
Empirical H — plug-in entropy, finite histogram cross entropy — отдельная оценка по переданным masses; реальное coder rounding/finalization учитывается actual bytes. Теоретические числа не называются размером bitstream.

## F. Experimental comparison

| Method | Actual total bytes | Bits/symbol | CR vs raw float32 | CR vs fixed8 total | PSNR | SSIM | LPIPS | Encode s | Decode s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| float32 | 52680472 | 32.0161027 | 0.99950 | 0.25009 | 42.4922409 | 0.9958137 | 0.0074352 | N/A | N/A |
| fixed8 | 13174788 | 8.0068638 | 3.99657 | 1.00000 | 38.7516594 | 0.9944757 | 0.0097342 | 0.47983 | 0.33921 |
| iid | 2815553 | 1.7111281 | 18.70111 | 4.67929 | 38.7516594 | 0.9944757 | 0.0097342 | 0.53244 | 0.57132 |
| channel_context | 2863145 | 1.7400517 | 18.39026 | 4.60151 | 38.7516594 | 0.9944757 | 0.0097342 | 0.57355 | 0.62792 |

Float32 reference actual cost — lossless serialized Phase2 directory (raw payload+buffers+manifest), не entropy stream. CR numerator rawfloat32=52653976bytes; fixed8 total ratio использует полный измеренный файл fixed8 с overhead.

| Model | Payload bytes | Histogram bytes | Metadata/framing bytes | Empirical bits | Finite cross entropy bits | Actual payload bits - empirical | Actual total bits - empirical |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed8 | 13163494 | 0 | 11294 | 22340399.030 | 105307952.000 | 82967552.970 | 83057904.970 |
| iid | 2796008 | 8192 | 11353 | 22307300.482 | 22366110.319 | 60763.518 | 217123.518 |
| channel_context | 2782144 | 69632 | 11369 | 22189680.735 | 22255177.967 | 67471.265 | 715479.265 |

Channel context vs IID: -47592bytes saved (-1.6903%). Это измеренная разница полного файла, включая дополнительные histograms; отрицательное число означает ухудшение.
Все3 coded methods восстанавливают одни и те же quantized symbols и float32 embeddings; float RGB, PNG и все4 mean metrics точно совпадают с direct-table8. Их качество одинаково по построению и фактической проверке.
Encode/decode timers включают fit/serialization/hash/I/O, но исключают Python import/startup; отдельно сохранён decoder process wall time. Скорость не профилировалась повторными microbenchmarks; это один измеренный end-to-end run.
Actual bytes относятся исключительно к HashGrid. MLP, Gaussian PLY и cameras требуются для rendering отдельно; сжатие всей сцены не заявляется.

## G. Automated verification

12 unit tests PASS, failures=0/errors=0. Log: `experiment_bench/logs/tests.log`; подробные статусы `tests.json`.

| Test | Status |
|---|---|
| test_constant_and_extremes (research.grid4d.test_codec.CodecTests) | PASS |
| test_entropy_known (research.grid4d.test_codec.CodecTests) | PASS |
| test_interchange_and_metadata (research.grid4d.test_codec.CodecTests) | PASS |
| test_invalid_quantization (research.grid4d.test_codec.CodecTests) | PASS |
| test_quantization_bounds_and_error (research.grid4d.test_codec.CodecTests) | PASS |
| test_constant_and_empty_contexts (research.experiment_bench.test_entropy.EntropyTests) | PASS |
| test_corruption_truncation_version_and_sizes (research.experiment_bench.test_entropy.EntropyTests) | PASS |
| test_decoder_available_causal_context_independent_reference (research.experiment_bench.test_entropy.EntropyTests) | PASS |
| test_finite_cdf_empty_constant_and_extremes (research.experiment_bench.test_entropy.EntropyTests) | PASS |
| test_invalid_schedules_and_iid_context_fairness (research.experiment_bench.test_entropy.EntropyTests) | PASS |
| test_real_file_restart_no_source_and_overhead (research.experiment_bench.test_entropy.EntropyTests) | PASS |
| test_psnr_independent_known_example (__main__.MetricsTests) | PASS |

Categories A–H: environment/import/data, export/import, quantization, coder/CDF/corruption, causal contexts, GPU forward/render, independent CPU PSNR+SSIM+LPIPS integration, new-process reproducibility — все PASS.
Independent references: context class=int(q0)//16; exact entropy example Hq0=8,Hq1|class=4; known PSNR for constant difference0.5; schedule partition checks ensure each q1 once, ordered, no duplicate/missing rows.
Experiment-level verification paths: `experiments/reference-*/verification.json`, `inference.json`, `model/per_view.json`; decoder reports/logs also сохранены.

## H. Reproducibility

Основная команда запуска одного нового эксперимента:

```powershell
wsl -d Ubuntu -- bash research/run_bench.sh cli run research/experiment_bench/configs/reference-iid.json
wsl -d Ubuntu -- bash research/run_bench.sh tests
```

Config output_dir должен быть новым: для повторного запуска копировать config и выбрать новый output_dir/id; все остальные параметры неизменны. Optional shared lossless/quantized inputs можно убрать — pipeline выполнит extraction/quantization сам.
Из Linux pinned env: `python -m research.experiment_bench.cli run <config.json>`. JSON выбран вместо YAML, без новой зависимости.
Полное обучение с новым model path: команда из `reference-training.json` (default50000, warm-up3000). `run_bench.sh train` защищён guard и не перезаписывает existing reference.
Повтор полного study: `python -m research.grid4d.study --source <model> --runtime <runtime.json> --out <fresh-study> --iteration 50000`.
Проверка GPU lossless restore: `python -m research.grid4d.test_forward --out <study> --checkpoint <pth> --repo <repo> --record <fresh-record.json>`.
Standalone decoder: `python -m research.experiment_bench.cli decode <bitstream.bin> <fresh-directory>`; checkpoint/source paths отсутствуют в CLI.
Aggregation: `python -m research.experiment_bench.cli aggregate experiments research/experiment_bench/aggregate`.
Complete first-run controller `research/run_reference_experiments.sh` требует завершённый standard training и отсутствующие study/experiment dirs. Это последовательность реально выполненных действий; повтор требует новые output paths.
Figures: `.tools/phase2-plotting-env/Scripts/python.exe research/experiment_bench/plot_results.py`; output `experiment_bench/figures/`.

## I. Limitations

Одна synthetic сцена, один seed, один standard training. Bitwise независимых training runs не гарантируется CUDA atomicAdd; save/load/decoded rendering данного snapshot exact.
LPIPS protocol сохранён как Phase2: VGG inputs[0,1],normalize=False. Сравнения с внешними papers/SOTA не заявляются.
Smoke200/3600 не смешиваются с trained50000; aggregate хранит iteration/checkpoint hash, plots выбирают только50000.
Only8-bit entropy streams; 12/16 quantization пока direct serialized references. No CUDA coding. No optimizer/RNG resume. Probability models fitted на кодируемой сцене и оплачены полностью; это технический contextual baseline, не основной метод НИР.
Format checks are integrity validation, not cryptographic authentication. Trusted research-sized data; maximum section lengths ограничены. Version/coder/model semantics pin обязательны.

## J. Extension guide

Рабочие интерфейсы и binary spec: `experiment_bench/API.md`. Subclass/register model in MODELS, define decoder-available context/schedule, probability vectors, fitted-parameter serialization; выбрать model name в config.
Для новых schedules beyond q0-first/q1 partitions нужен versioned schedule и отдельные independent causal tests; текущий baseline честно предоставляет именно q0-derived context + immutable public metadata.
Renderer/training/checkpoint structure не меняются. После добавления модели выполнить test command, standalone restart decode, actual-byte accounting и parity с direct quantization.
Inter-level, temporal, cross-grid, collision-aware и neural models не реализованы.

## K. Readiness verdict

**READY FOR RESEARCH**: standard50000 reference получен, quantization повторён, настоящие IID/context streams восстановлены точно, GPU render/evaluation совпали с direct quantization, actual rates/times измерены и все critical checks PASS.
Фаза реализации основного межуровневого/временного метода не запускалась. Следующий эксперимент должен быть отдельной задачей.
