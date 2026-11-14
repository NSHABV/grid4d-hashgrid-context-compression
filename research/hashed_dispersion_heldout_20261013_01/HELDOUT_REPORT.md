> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Held-out исследование dispersion-контекстов HashGrid: этапы 2–3

Начало run: 13 октября 2026 года; завершение отчёта: 14 октября 2026 года. Checkpoint `bouncingballs-reference-50000`; xyz L4→L5 и L5→L6, уровни zero-based. Существующие table-wise uint8 targets. CPU Python 3.12.14 / NumPy 1.26.4. Все результаты относятся к одной сцене и одному checkpoint.

**Итог: NO-GO для перехода H1 к отдельной реализации bitstream.** Измерены held-out CE и реальные размеры сериализованных вероятностных моделей. Экономия payload и net — исключительно **PREDICTED**. Actual entropy stream отсутствует; quantization, Grid4D training и neural probability models не выполнялись.

## 1. Неизменность входов и предварительная фиксация

Проверены SHA256 и PASS-статусы предшествующей диагностики: **3131 защищённых файлов**. Источник: предыдущий диагностический отчёт (внешний артефакт; см. каталог исключённых ссылок). Исследовательский протокол: RESEARCH_DIRECTION_DECISION.md (внешний артефакт; см. каталог исключённых ссылок).

Parent использует готовые `contexts.npz` и `fine_symbols.npy`; geometry/coarse features повторно вычисляются только в отдельном decoder replay, что необходимо для независимого восстановления class IDs. Targets одинаковы для всех arms; каждый fine slot и оба его канала принадлежат одному split.

Frozen protocol SHA256: `5c762ab79cac429098a151adf7040318712ae46ec2c9fa926b6695b82189bce5`. Фиксация моделей: `3e866289fa4452e8a87d1e88628c145b859b1fe334a78a128c1eff0cf869ed7a`. PREREGISTERED_PROTOCOL.json (внешний артефакт; см. каталог исключённых ссылок) создан до fitting/test; MODEL_FREEZE.json (внешний артефакт; см. каталог исключённых ссылок) — до test. Test вычислен один раз после exact class replay.

## 2. Заранее определённые модели, splits и оценка

PCG64 permutation по fine slots, seeds 0/1/2: train **335545**, validation **83886**, test **104857** slots на seed. Train — остаток после floor(20% test), floor(16% validation). Splits и hashes сохранены отдельно. Seeds — повторные разбиения одной таблицы, не независимые сцены или training runs.

| Модель | Максимум C на канал | Правило |
|---|---:|---|
| IID | 1 | Один histogram на канал |
| Geometry4 | 4 | G0 nominal-empty; G1 nominal-positive/point-empty; G2 singleton; G3 colliding |
| Canonical8 | 10 | 8 quantile bins canonical feature + отдельные G0/G1 |
| Mean8 | 10 | 8 quantile bins mean + G0/G1 |
| Mean4 | 6 | 4 quantile bins mean + G0/G1 |
| Mean4×Std2 | 10 | 4 bins mean × 2 bins Std + G0/G1 |

Edges fit только по train G2+G3 отдельно для каждого канала: `np.quantile(method="linear")`, float64. Повторяющиеся thresholds сохраняются; `searchsorted(side="right")`: значения на threshold принадлежат правому интервалу. Mean4 и Mean4×Std2 используют одинаковые mean edges. Std разделён одним общим median threshold по train G2+G3 на канал, без настройки по mean-bin. Никакие thresholds, число классов или smoothing не менялись после test.

Train histograms преобразованы существующей `models.frequencies`: Laplace α=1, минимальная integer mass 1, stable largest remainder, сумма 65536. Пустой train class получает uniform masses 256. Все C distributions передаются, включая пустые; omission по train-empty не применяется. CE = среднее `−log2(mass/65536)`, без аналитической подмены finite PMF. CDF строго возрастает; cumulative endpoint=65536.

Validation выбирает описательного победителя из шести фиксированных arms по общей CE. Hyperparameters/refit не используются; все шесть сравнений на test заданы заранее. Paired gain = CE baseline − CE candidate; положительный знак означает лучший candidate. Для обоих каналов сначала усредняются две разности одного slot. Интервалы ±1.96 SE — описательные, conditional-on-fit; они не учитывают пространственную зависимость/coarse sharing и не доказывают generalization.

| Fine level | seed 0 validation winner | seed 1 | seed 2 |
|---|---|---|---|
| L5 (L4→L5) | Mean8 | Mean8 | Mean8 |
| L6 (L5→L6) | Mean4Std2 | Mean4Std2 | Mean4Std2 |

## 3. Test cross-entropy: все заранее заданные arms

Среднее трёх split seeds, bits/symbol; в скобках min…max по seeds. Это среднее результатов повторных holdout, не объединённый независимый test.

| Модель | L5 all | L6 all | L5 G3 | L6 G3 |
|---|---:|---:|---:|---:|
| IID | 1.426675 (1.424231…1.431235) | 1.976134 (1.971861…1.979764) | 2.455960 (2.443878…2.472209) | 2.148152 (2.145097…2.152458) |
| Geometry4 | 1.220547 (1.217738…1.225379) | 1.904874 (1.899850…1.908259) | 2.257348 (2.246828…2.273888) | 2.135199 (2.132447…2.138671) |
| Canonical8 | 1.170992 (1.168430…1.175049) | 1.923798 (1.919257…1.927029) | 2.316170 (2.305266…2.329560) | 2.141573 (2.138599…2.145275) |
| Mean8 | 1.105837 (1.102956…1.110543) | 1.901429 (1.897193…1.904591) | 2.134654 (2.122728…2.149682) | 2.120041 (2.117715…2.123667) |
| Mean4 | 1.155098 (1.152513…1.159892) | 1.908270 (1.904127…1.911583) | 2.216287 (2.204007…2.232922) | 2.124774 (2.122639…2.128383) |
| Mean4×Std2 | 1.155098 (1.152513…1.159892) | 1.891378 (1.887150…1.895152) | 2.216287 (2.204007…2.232922) | 2.116337 (2.114304…2.120363) |

По каналам: среднее CE трёх seeds.

| Fine | Model | all ch0 | all ch1 | G3 ch0 | G3 ch1 |
|---|---|---:|---:|---:|---:|
| L5 (L4→L5) | IID | 1.450231 | 1.403118 | 2.499534 | 2.412387 |
| L5 (L4→L5) | Geometry4 | 1.242087 | 1.199007 | 2.300121 | 2.214576 |
| L5 (L4→L5) | Canonical8 | 1.189490 | 1.152494 | 2.359311 | 2.273028 |
| L5 (L4→L5) | Mean8 | 1.096145 | 1.115530 | 2.117235 | 2.152072 |
| L5 (L4→L5) | Mean4 | 1.177569 | 1.132626 | 2.255503 | 2.177070 |
| L5 (L4→L5) | Mean4×Std2 | 1.177569 | 1.132626 | 2.255503 | 2.177070 |
| L6 (L5→L6) | IID | 1.962025 | 1.990242 | 2.128566 | 2.167738 |
| L6 (L5→L6) | Geometry4 | 1.889405 | 1.920344 | 2.115024 | 2.155374 |
| L6 (L5→L6) | Canonical8 | 1.908419 | 1.939176 | 2.121512 | 2.161635 |
| L6 (L5→L6) | Mean8 | 1.885707 | 1.917151 | 2.098966 | 2.141116 |
| L6 (L5→L6) | Mean4 | 1.891543 | 1.924996 | 2.104165 | 2.145383 |
| L6 (L5→L6) | Mean4×Std2 | 1.876266 | 1.906491 | 2.096945 | 2.135730 |

## 4. Парные сравнения и роль geometry

| Fine | Candidate / baseline | ΔCE all | ΔCE G3 | G3 min…max seed/channel |
|---|---|---:|---:|---:|
| L5 (L4→L5) | Canonical8 / Geometry4 | +0.049555 | -0.058821 | -0.063090…-0.055596 |
| L5 (L4→L5) | Mean8 / Canonical8 | +0.065155 | +0.181516 | 0.120184…0.244078 |
| L5 (L4→L5) | Mean8 / Geometry4 | +0.114710 | +0.122695 | 0.058567…0.184030 |
| L5 (L4→L5) | Mean4×Std2 / Geometry4 | +0.065449 | +0.041062 | 0.034111…0.045869 |
| L5 (L4→L5) | Mean4×Std2 / Canonical8 | +0.015894 | +0.099883 | 0.094381…0.107776 |
| L5 (L4→L5) | Mean4×Std2 / Mean8 | -0.049260 | -0.081633 | -0.140340…-0.024397 |
| L5 (L4→L5) | Mean4×Std2 / Mean4 | +0.000000 | +0.000000 | 0.000000…0.000000 |
| L6 (L5→L6) | Canonical8 / Geometry4 | -0.018923 | -0.006374 | -0.006709…-0.006027 |
| L6 (L5→L6) | Mean8 / Canonical8 | +0.022369 | +0.021532 | 0.019766…0.022862 |
| L6 (L5→L6) | Mean8 / Geometry4 | +0.003445 | +0.015158 | 0.013590…0.016153 |
| L6 (L5→L6) | Mean4×Std2 / Geometry4 | +0.013496 | +0.018862 | 0.016899…0.020786 |
| L6 (L5→L6) | Mean4×Std2 / Canonical8 | +0.032419 | +0.025236 | 0.023527…0.026814 |
| L6 (L5→L6) | Mean4×Std2 / Mean8 | +0.010051 | +0.003704 | 0.000754…0.005853 |
| L6 (L5→L6) | Mean4×Std2 / Mean4 | +0.016891 | +0.008437 | 0.006254…0.010246 |

Парные gains и conditional интервалы (внешний артефакт; см. каталог исключённых ссылок)

Интервалы нарисованы отдельно для каждого seed. Они не служат новым post-hoc критерием GO. Не следует интерпретировать перекрытие/неперекрытие этих интервалов как независимые сравнения сцен.

Mean4×Std2 против Mean8, раздельно по G0/G1/G2/G3; знак и величина не смешиваются с долями strata.

| Fine | Stratum | test slots min…max | Mean8 CE | Mean4×Std2 CE | ΔCE |
|---|---|---:|---:|---:|---:|
| L5 (L4→L5) | G0 | 36656…36854 | 0.008759 | 0.008759 | +0.000000 |
| L5 (L4→L5) | G1 | 1370…1451 | 0.083677 | 0.083677 | +0.000000 |
| L5 (L4→L5) | G2 | 39631…40102 | 1.461749 | 1.536385 | -0.074636 |
| L5 (L4→L5) | G3 | 26594…27002 | 2.134654 | 2.216287 | -0.081633 |
| L6 (L5→L6) | G0 | 5545…5612 | 0.026093 | 0.026093 | +0.000000 |
| L6 (L5→L6) | G1 | 605…643 | 0.182235 | 0.182235 | +0.000000 |
| L6 (L5→L6) | G2 | 18049…18384 | 1.568602 | 1.527093 | +0.041510 |
| L6 (L5→L6) | G3 | 80287…80553 | 2.120041 | 2.116337 | +0.003704 |

## 5. Multiplicity внутри G3: описательный анализ

Группы K=2, K=3, K≥4 определены заранее, минимально 100 test slots. Новые классы по этим группам не fit. Это exploratory описание regime, не отдельное подтверждение H2 и не настройка победителя.

| Fine | K | test slots min…max | ΔCE vs Mean8 | ΔCE vs Mean4 | ch0/ch1 ΔCE vs Mean8 |
|---|---|---:|---:|---:|---|
| L5 (L4→L5) | G3_K2 | 19420…19682 | -0.082437 | +0.000000 | -0.137911 / -0.026963 |
| L5 (L4→L5) | G3_K3 | 5790…5872 | -0.078663 | +0.000000 | -0.135821 / -0.021505 |
| L5 (L4→L5) | G3_K4plus | 1384…1454 | -0.082742 | +0.000000 | -0.153113 / -0.012370 |
| L6 (L5→L6) | G3_K2 | 27393…27595 | -0.003617 | +0.002866 | -0.003615 / -0.003619 |
| L6 (L5→L6) | G3_K3 | 26457…26687 | -0.000509 | +0.004717 | -0.001927 / +0.000910 |
| L6 (L5→L6) | G3_K4plus | 26402…26437 | +0.015557 | +0.017969 | +0.011850 / +0.019264 |

Полные CE и paired tables включают каждый seed, канал, stratum и subgroup: test-scores.csv (внешний артефакт; см. каталог исключённых ссылок); paired-differences.csv (внешний артефакт; см. каталог исключённых ссылок).

## 6. Effective capacity и degenerate thresholds

| Fine | Model | C max | train occupied ch0 min…max | ch1 min…max |
|---|---|---:|---|---|
| L5 (L4→L5) | IID | 1 | 1…1 | 1…1 |
| L5 (L4→L5) | Geometry4 | 4 | 4…4 | 4…4 |
| L5 (L4→L5) | Canonical8 | 10 | 9…9 | 9…9 |
| L5 (L4→L5) | Mean8 | 10 | 10…10 | 9…9 |
| L5 (L4→L5) | Mean4 | 6 | 6…6 | 6…6 |
| L5 (L4→L5) | Mean4×Std2 | 10 | 6…6 | 6…6 |
| L6 (L5→L6) | IID | 1 | 1…1 | 1…1 |
| L6 (L5→L6) | Geometry4 | 4 | 4…4 | 4…4 |
| L6 (L5→L6) | Canonical8 | 10 | 10…10 | 10…10 |
| L6 (L5→L6) | Mean8 | 10 | 10…10 | 10…10 |
| L6 (L5→L6) | Mean4 | 6 | 6…6 | 6…6 |
| L6 (L5→L6) | Mean4×Std2 | 10 | 10…10 | 10…10 |

Std thresholds (ch0/ch1), seeds 0/1/2:

- L5 (L4→L5): 0 / 0; 0 / 0; 0 / 0.

**L5 (L4→L5): вырождение Std-bin подтверждено.** Median=0 и все Std≥0; `searchsorted(right)` относит и нулевые, и положительные Std в bin1. Поэтому Mean4×Std2 совпадает с Mean4 по test losses побитно во всех seeds; четыре active classes на канал недостижимы. Здесь Std не проверяется содержательно в качестве разделяющего признака. Это отрицательный результат данного заранее фиксированного binning, не доказательство отсутствия информации в Std. Перенастройка zero-edge после test не проводилась; она потребовала бы отдельного нового протокола.

- L6 (L5→L6): 0.011262924950170412 / 0.010772043971637798; 0.011238881487850251 / 0.010762272802262354; 0.011271454969304573 / 0.010778608033433557.

Максимальная и эффективная capacity (внешний артефакт; см. каталог исключённых ссылок)

## 7. Измеренная стоимость модели и PREDICTED net

Новый versioned dry serializer поддерживает C=1/4/6/10. Хранит exact integer masses и float64 thresholds, model specification, обязательную geometry/quantizer/runtime metadata и собственный header. Проверены dense_u32, packed_u16 и sparse_default_u16. Для sparse modal default выбирается детерминированно, исключения хранят symbol u8 / mass u16. CDF восстанавливается из masses, повторно не оплачивается.

Для каждой модели независимо выбирается самый короткий measured dry envelope; равенство размеров разрешается фиксированным порядком storage. Coarse payload — общий prerequisite и сокращается в разности; это не новый pair/full-grid file. Metadata включает консервативные provenance поля; все одинаковые поля учитываются симметрично. Переданные train-fit models не refit на полной таблице.

| Fine | Model | Best storage (seeds) | Probability bytes min…max | Threshold bytes | Spec bytes | Metadata bytes | Header bytes | Total bytes min…max |
|---|---|---|---:|---:|---:|---:|---:|---:|
| L5 (L4→L5) | IID | sparse_default_u16 | 524…542 | 34 | 200 | 1890 | 26 | 2674…2692 |
| L5 (L4→L5) | Geometry4 | sparse_default_u16 | 2678…2735 | 34 | 206 | 1890 | 26 | 4834…4891 |
| L5 (L4→L5) | Canonical8 | sparse_default_u16 | 5891…6023 | 146 | 208 | 1890 | 26 | 8161…8293 |
| L5 (L4→L5) | Mean8 | sparse_default_u16 | 6464…6494 | 146 | 203 | 1890 | 26 | 8729…8759 |
| L5 (L4→L5) | Mean4 | sparse_default_u16 | 3381…3474 | 82 | 202 | 1890 | 26 | 5581…5674 |
| L5 (L4→L5) | Mean4×Std2 | sparse_default_u16 | 3413…3506 | 98 | 207 | 1890 | 26 | 5634…5727 |
| L6 (L5→L6) | IID | sparse_default_u16 | 506…512 | 34 | 200 | 1907 | 26 | 2673…2679 |
| L6 (L5→L6) | Geometry4 | sparse_default_u16 | 1541…2009 | 34 | 206 | 1907 | 26 | 3714…4182 |
| L6 (L5→L6) | Canonical8 | sparse_default_u16 | 6077…6563 | 146 | 208 | 1907 | 26 | 8364…8850 |
| L6 (L5→L6) | Mean8 | sparse_default_u16 | 5972…6416 | 146 | 203 | 1907 | 26 | 8254…8698 |
| L6 (L5→L6) | Mean4 | sparse_default_u16 | 1995…2430 | 82 | 202 | 1907 | 26 | 4212…4647 |
| L6 (L5→L6) | Mean4×Std2 | sparse_default_u16 | 4385…4892 | 98 | 207 | 1907 | 26 | 6623…7130 |

Все 108 dry roundtrips и варианты хранения: model-sizes.csv (внешний артефакт; см. каталог исключённых ссылок). Файлы `.model` содержат только probability model и metadata, без закодированных target symbols.

`N_full = 524288 slots × 2 channels = 1048576 symbols`. `gross = N_full × (CE_baseline − CE_candidate) / 8`; `net = gross − (side_candidate − side_baseline)`. Все следующие числа **PREDICTED**; test→full-level перенос и конечный coder overhead не измерены. Условие запаса: gross > Δside + max(4096 B, 0.2·Δside), отдельно для каждого pair/seed/comparator.

| Fine | Mean4×Std2 vs | ΔCE test mean | gross B mean | Δside B mean | net B mean | net B min…max | Margin PASS seeds |
|---|---|---:|---:|---:|---:|---:|---:|
| L5 (L4→L5) | Geometry4 | +0.065449 | +8578.6 | +810.0 | +7768.6 | 7755.2…7783.4 | 3/3 |
| L5 (L4→L5) | Canonical8 | +0.015894 | +2083.3 | -2554.0 | +4637.3 | 4513.6…4795.1 | 3/3 |
| L5 (L4→L5) | Mean8 | -0.049260 | -6456.6 | -3075.0 | -3381.6 | -3512.6…-3259.0 | 0/3 |
| L5 (L4→L5) | Mean4 | +0.000000 | +0.0 | +53.0 | -53.0 | -53.0…-53.0 | 0/3 |
| L6 (L5→L6) | Geometry4 | +0.013496 | +1768.9 | +2953.0 | -1184.1 | -1284.1…-1023.7 | 0/3 |
| L6 (L5→L6) | Canonical8 | +0.032419 | +4249.3 | -1708.0 | +5957.3 | 5841.1…6081.3 | 3/3 |
| L6 (L5→L6) | Mean8 | +0.010051 | +1317.4 | -1585.0 | +2902.4 | 2793.2…2966.6 | 0/3 |
| L6 (L5→L6) | Mean4 | +0.016891 | +2214.0 | +2457.0 | -243.0 | -323.4…-185.8 | 0/3 |

PREDICTED net (внешний артефакт; см. каталог исключённых ссылок)

Все paired forecasts: predicted-net.csv (внешний артефакт; см. каталог исключённых ссылок). Real entropy file size = null; положительная CE разность сама по себе не является экономией файла.

## 8. Decoder reproducibility и проверки

Два новых decoder process, по одному на пару, читают только coarse symbols, decoder metadata и переданные thresholds/specs. Каждый один раз воспроизводит geometry/coarse contexts в закреплённой CPU arithmetic, затем все 18 class arrays (6 arms × 3 seeds), по 524288 slots × 2 channels. **Все 36 arrays совпали побитно**. Fine targets, parent contexts.npz, полный xyz bin, checkpoint и probability masses decoder для классов не читает.

Нормальные read audits имеют пустой список blocked reads; отдельные negative probes блокируют четыре запрещённых пути на пару. Audit hook контролирует этот Python decoder, не является OS sandbox. Code/stdlib imports разрешены. GPU не использовался; приблизительный CPU/GPU feature parity прошлого этапа не подменяет текущую exact class equality.

| Проверка | Статус |
|---|---|
| Synthetic class/fit/serializer tests: 42 | PASS |
| Predecessor manifests, hashes, PASS records | PASS |
| Slots split disjoint/complete; channels kept together | PASS |
| Train-only edges/counts, unchanged targets, model freeze before test | PASS |
| Exact fresh decoder classes, all slots × both channels × all arms/seeds | PASS |
| Four forbidden-read probes per pair | PASS |
| Positive masses/sum65536; dry threshold+mass+metadata roundtrip | PASS |

replay-validation.json (внешний артефакт; см. каталог исключённых ссылок); input-validation.json (внешний артефакт; см. каталог исключённых ссылок); splits.json (внешний артефакт; см. каталог исключённых ссылок). Итоговая проверка сохранности артефактов и критический review записываются отдельно после этого отчёта.

## 9. Вычислительная стоимость

Предварительная оценка: 180 s CPU и 512 MiB; без N×C×256 tensor.

Fit/validation/dry serializations: 8.612 s wall, 6.766 s CPU, peak total process RSS 110.61 MiB. Test/paired/forecasts: 2.973 s wall, 2.859 s CPU, peak RSS 60.61 MiB.

| Decoder pair | wall s | CPU s | peak RSS MiB |
|---|---:|---:|---:|
| L5 (L4→L5) | 1.708 | 1.703 | 121.55 |
| L6 (L5→L6) | 3.412 | 3.391 | 127.67 |

Этапы выполнялись последовательно. RSS — total process, не сумма одновременно живущих копий. Startup, разработка/обсуждение и визуальный review не входят в вычислительные интервалы fit/test.

## 10. Ответы на исследовательские вопросы и GO / NO-GO

1. **Canonical8 против Geometry4:** L5 (L4→L5) +0.049555 bits/symbol; L6 (L5→L6) -0.018923 bits/symbol. Знак оценивается на одинаковых test slots.
2. **Mean8 против Canonical8:** L5 (L4→L5) +0.065155 bits/symbol; L6 (L5→L6) +0.022369 bits/symbol. Это проверка среднего относительно representative, отдельно от Std.
3. **Mean4×Std2 против Mean8 при C≤10:** L5 (L4→L5) -0.049260 bits/symbol; L6 (L5→L6) +0.010051 bits/symbol. Равенство max C не гарантирует равенства effective capacity.
4. **Дополнительная польза Std внутри G3:** против Mean8 L5 (L4→L5) -0.081633 bits/symbol; L6 (L5→L6) +0.003704 bits/symbol; против Mean4 L5 (L4→L5) +0.000000 bits/symbol; L6 (L5→L6) +0.008437 bits/symbol. Вырождение binning и эти разности ограничивают вывод H1.
5. **L5 против L6:** collision regimes, coarse tables и effective Std classes различаются. Различие уровней измерено, причинный эффект только числа коллизий не выделен.
6. **Устойчивость seeds/channels:** строгие положительные gain checks не пройдены в 18 из 84 проверок. Полная детализация есть в paired CSV; нулевой gain не считается положительным.
7. **Оплата модели:** safety margin не пройден в 9 из 18 основных pair/seed/comparator checks. Оценка оплачивает самый короткий measured transport каждого baseline и candidate.
8. **Переход к bitstream: NO-GO.** Решение относится к этой H1 и заданным шести arms; actual entropy coding автоматически не запускается.
9. **Не подтверждено:** actual file reduction, full-grid/scene gain, generalization на другие checkpoints/scenes/quantizers, spatially independent prediction, переносимость exact classes на произвольный CPU/GPU runtime, самостоятельная научная новизна Mean+Std. Prior art заново не исследовался.
10. **Граница отрицательного вывода:** этот fixed Mean4×Std2 protocol не даёт достаточного основания для следующего compressor stage. Он не доказывает отсутствия всех dispersion-based зависимостей. Если продолжать отдельной задачей, протокол уже предлагает H2: integer Count6 = G0/G1/K1/K2/K3/K≥4 против Geometry4 на тех же frozen targets, с новым preregistration, train-only PMF и оплатой metadata. Текущие K-subgroups — только описание; Count6 не fit, не оценивался и не объявлен полезным.

Отдельный результат для Mean8: относительно Geometry4 PREDICTED net составляет L5 **+11150,23 B**, L6 **−4086,41 B**. На L5 среднее полезно при неработающем Std-bin; на L6 снижение CE Mean8 не оплачивает рост модели. Это не разрешение запускать bitstream.

На L6 знак Mean4×Std2 против Mean8 положителен внутри G3 во всех seeds/channels, но по K неоднороден: K=2 и K=3 в среднем проигрывают, K≥4 выигрывает. Относительно Mean4 gain положителен во всех трёх K-группах. Это поддерживает локальную предиктивную пользу данного Std-разбиения L6; независимый причинный эффект dispersion сверх любых более подробных geometry/multiplicity priors не установлен.

Машиночитаемое решение: decision.json (внешний артефакт; см. каталог исключённых ссылок). Критерий GO требует всех correctness PASS, положительных gains на обоих уровнях по каждому seed/channel в all и G3 против Geometry4/Canonical8/Mean8, плюс G3 advantage против Mean4 и safety margin каждого forecast. Никакая удачная subgroup не отменяет провал общего gate.

## 11. Воспроизведение и артефакты

Из <PROJECT_ROOT>, существующее CPU environment. Каждый новый run должен отсутствовать перед prepare. Команды fit/replay/test используют frozen artifacts, test нельзя повторить в том же run.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$py='<PROJECT_ROOT>\.tools\phase2-plotting-env\Scripts\python.exe'
$run='research/hashed_dispersion_heldout_<NEW_UNIQUE_ID>'
& $py -m research.experiment_bench.hashed_interlevel.study prepare --run $run
& $py -m research.experiment_bench.hashed_interlevel.unit_checks --run $run
& $py -m research.experiment_bench.hashed_interlevel.study fit --run $run
& $py -m research.experiment_bench.hashed_interlevel.study replay --run $run
& $py -m research.experiment_bench.hashed_interlevel.study test --run $run
& $py -m research.experiment_bench.hashed_interlevel.report --run $run
& $py -m research.experiment_bench.hashed_interlevel.audit --run $run
& $py -m research.experiment_bench.hashed_interlevel.finalize --run $run
```

Протокол/splits: PREREGISTERED_PROTOCOL.json (внешний артефакт; см. каталог исключённых ссылок), splits.json (внешний артефакт; см. каталог исключённых ссылок). Validation: validation-scores.json (внешний артефакт; см. каталог исключённых ссылок). Test: test-scores.csv (внешний артефакт; см. каталог исключённых ссылок). Paired: paired-differences.csv (внешний артефакт; см. каталог исключённых ссылок). Costs: model-sizes.csv (внешний артефакт; см. каталог исключённых ссылок). Прогнозы: predicted-net.csv (внешний артефакт; см. каталог исключённых ссылок).

В каждой pair directory сохранены splits_seed*.npz, decoder-specs.json, decoder replay class IDs/read-audit, model specs, train counts/masses, exact class arrays и три `.model` transport варианта. Test loss arrays содержат slot_index и loss[N_test,2] каждого arm для повторного анализа уже оценённого test; новые настройки на них запрещены без отдельного exploratory обозначения.

**Остановка после этапов 2–3.** Предыдущие отчёты и данные остаются по прежним путям. Новый run имеет собственные отчёт, данные, графики и проверки; стадии bitstream/training не запускались.
