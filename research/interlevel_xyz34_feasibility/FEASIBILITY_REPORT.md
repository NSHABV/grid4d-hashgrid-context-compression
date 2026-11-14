> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Feasibility: decoder-available G_xyz L3 → L4

**PROMISING**, при компактном хранении вероятностных таблиц. Текущий dense uint32 формат не окупается.

## Краткий результат

Quantile-8 даёт 0.190532 bits/symbol сверх boundary-only на random test (среднее 3 seeds).
На block8 и block16 holdout средний дополнительный выигрыш: 0.184463 и 0.189016 bits/symbol.
Прогноз для всех L4 symbols относительно boundary: payload экономит 9782.8 B; dense-u32 net=-4679.2 B, packed-u16 net=2488.8 B, sparse-default-u16 net=8175.8 B.
**Это оценки, а не измеренные compressed bytes. Ни новый coder, ни production encoder/decoder, ни neural model не реализованы.**

## Данные и гипотезы

Checkpoint SHA256: `3306dabf8057728abfa7cda87d78c723b27a357f968fd7d721ea727ebd043090`. Только bouncingballs / xyz / L3→L4 / table-wise8 /2 channels.
Все 205379 fine rows учтены: 195112 in-bounds и 10267 OOB. Используются исходные pairs и сохранённый decoder-available GPU float32 context; checkpoint/raw L3 embeddings не читаются.
H0: известное coarse feature не даёт практически существенного улучшения предсказания. H1: условная модель уменьшает held-out codelength и потенциально покрывает стоимость модели.
IID оценивается отдельно по каждому feature channel. Boundary использует только геометрически воспроизводимый in_bounds. Spatial добавляет класс того же coarse channel; OOB всегда отдельный класс.

## Протокол

Seeds 0,1,2; slot split 64% training /16% validation /20% final test. Spatial regimes назначают целые кубические блоки ширины 8 и 16 в одну часть; размеры выборок могут отличаться от номинальных процентов.
Uniform-width и quantile bins (4/8/16 внутренних классов) строятся только на training in-bounds features. Равные quantile edges сохраняются; searchsorted(side=right), вне обученного range — крайний класс. Пустые классы не удаляются задним числом.
Сглаживание alpha=1. Используется существующий `experiment_bench.models.frequencies`:256 strictly-positive integer masses, сумма65536. Основные cross-entropies по finite probabilities; аналитический Laplace вариант сохранён отдельно.
Training empirical MI считается отдельно от held-out gain; incremental MI условно по in_bounds не включает выигрыш только от границы.
Для test T стоимость R = −Σ(i∈T) log2 p(q_i|class_i); bits/symbol = R/|T|. Для total суммируются стоимости двух каналов и делятся на 2|T|.
Для каждого заранее заданного storage scenario модель выбирается только по validation прогнозу payload+overhead для L4. Test оценивается после выбора. Все заранее заданные модели также показаны как диагностические сравнения; победитель по final test не выбирался.
95% CI — cluster bootstrap1000 repetitions, с фиксированной fitted model: spatial cluster width8 для random/block8 и width16 для block16. Последний режим имеет12 test blocks; CI не учитывает повторное обучение или вариацию сцен.
Среднее в таблицах: равный вес 3 seeds, а не объединённая эмпирическая выборка. Seeds используют одну сцену и пересекающиеся данные; это не независимые репликации сцены.

## Итоговая таблица: random splits, среднее3 seeds

| Bins / Model | Channel | Held-out bits/symbol | Gain vs IID | Gain vs boundary | Model overhead B (u32) | Estimated net B vs IID |
|---|---|---:|---:|---:|---:|---:|
| none / IID | 0 | 1.494225 | 0.000000 | -0.024743 | 1198.0 | 0.0 |
| none / Boundary | 0 | 1.469482 | 0.024743 | 0.000000 | 2227.0 | -393.8 |
| uniform / Spatial-4 | 0 | 1.447187 | 0.047038 | 0.022295 | 5329.0 | -2923.4 |
| uniform / Spatial-8 | 0 | 1.439516 | 0.054708 | 0.029966 | 9457.0 | -6854.5 |
| uniform / Spatial-16 | 0 | 1.401046 | 0.093179 | 0.068436 | 17715.0 | -14124.9 |
| quantile / Spatial-4 | 0 | 1.381357 | 0.112868 | 0.088125 | 5330.0 | -1234.4 |
| quantile / Spatial-8 | 0 | 1.264374 | 0.229851 | 0.205108 | 9458.0 | -2359.2 |
| quantile / Spatial-16 | 0 | 1.233463 | 0.260761 | 0.236018 | 17716.0 | -9823.6 |
| none / IID | 1 | 1.443421 | 0.000000 | -0.024946 | 1198.0 | 0.0 |
| none / Boundary | 1 | 1.418475 | 0.024946 | 0.000000 | 2227.0 | -388.6 |
| uniform / Spatial-4 | 1 | 1.413030 | 0.030392 | 0.005445 | 5329.0 | -3350.8 |
| uniform / Spatial-8 | 1 | 1.398813 | 0.044609 | 0.019662 | 9457.0 | -7113.8 |
| uniform / Spatial-16 | 1 | 1.349162 | 0.094259 | 0.069313 | 17715.0 | -14097.1 |
| quantile / Spatial-4 | 1 | 1.323892 | 0.119529 | 0.094583 | 5330.0 | -1063.4 |
| quantile / Spatial-8 | 1 | 1.242520 | 0.200902 | 0.175955 | 9458.0 | -3102.4 |
| quantile / Spatial-16 | 1 | 1.199352 | 0.244070 | 0.219123 | 17716.0 | -10252.2 |
| none / IID | total | 1.468823 | 0.000000 | -0.024845 | 2396.0 | 0.0 |
| none / Boundary | total | 1.443978 | 0.024845 | 0.000000 | 4454.0 | -782.4 |
| uniform / Spatial-4 | total | 1.430108 | 0.038715 | 0.013870 | 10658.0 | -6274.2 |
| uniform / Spatial-8 | total | 1.419165 | 0.049658 | 0.024814 | 18914.0 | -13968.3 |
| uniform / Spatial-16 | total | 1.375104 | 0.093719 | 0.068874 | 35430.0 | -28222.0 |
| quantile / Spatial-4 | total | 1.352624 | 0.116199 | 0.091354 | 10660.0 | -2297.8 |
| quantile / Spatial-8 | total | 1.253447 | 0.215376 | 0.190532 | 18916.0 | -5461.6 |
| quantile / Spatial-16 | total | 1.216408 | 0.252415 | 0.227571 | 35432.0 | -20075.8 |

Model overhead — абсолютная стоимость candidate; net вычитает **дополнительную** стоимость относительно baseline, не абсолютную. Total bits/symbol = оба канала /2N. [Полная summary](summary.csv), [все splits/CI/границы](per-split-results.csv).

## Overhead и break-even

Primary dense_u32: C×256×4 B на channel, как существующие `.to_bytes()` probability masses. Нужны ещё(K−1)×8 B bin edges и измеренная длина гипотетического компактного JSON metadata. Bin edges передаются заранее; они не бесплатны.
CDF257×4 B на class производен из масс: учитывается как decoder memory, без двойного начисления в размер файла. Training counts не передаются дополнительно к probability masses.
Packed_u16: C×256×2 B. Все массы≤65281 (sum65536, остальные255 masses≥1), поэтому упаковка вuint16 без потери возможна и проверена на synthetic arrays. Bench stream сейчас хранитuint32; формат потребовал бы отдельной адаптации.
Sparse-default-u16: на class default mass u16 + exception count u16 +3 B на исключение(symbol u8,mass u16). Это размер предварительного представления exact finite masses, а не разработанный bitstream. Model/header/framing новой схемы не проверялись actual coding.
No-overhead — только верхняя граница возможной экономии. Common geometry/quantization metadata, уже известные baseline/decoder, отменяются при сравнении. Неизвестные дополнительные framing/termination bytes будущей схемы не выдаются за ноль фактического файла.
Проекция rate×N использует только 410758 L4 scalar symbols. Прогноз полного размера сцены или сжатия Gaussian/MLP не строится.
Estimated net bytes = gain_bits_per_symbol × N_symbols/8 − (model_candidate_bytes − model_baseline_bytes). Break-even = 8 × extra_model_bytes/N_symbols.

| Quantile model | Gain vs boundary | u32 break-even bits/symbol | payload saving B | u32 net B | packed-u16 net B | sparse-u16 net B |
|---|---:|---:|---:|---:|---:|---:|
| K4 | 0.091354 | 0.120869 | 4690.6 | -1515.4 | 1556.6 | 3909.6 |
| K8 | 0.190532 | 0.281665 | 9782.8 | -4679.2 | 2488.8 | 8175.8 |
| K16 | 0.227571 | 0.603333 | 11684.6 | -19293.4 | -3933.4 | 8415.6 |

Для quantile-8 пороги окупаемости относительно boundary-only (среднее 3 random seeds):

| Storage | Extra model B | Break-even bits/symbol |
|---|---:|---:|
| dense_u32 | 14462.0 | 0.281665 |
| packed_u16 | 7294.0 | 0.142059 |
| sparse_default_u16 | 1607.0 | 0.031298 |

## Occupancy и отличие каналов

Все class train/validation/test counts, empty/tiny classes(<100 training rows), total variation и JS divergence относительно training IID: [class-occupancy.csv](class-occupancy.csv).

| Quantile-8, random seed0 | train rows по классам0..8 (последний OOB) |
|---|---|
| ch0 | [15604, 15604, 15604, 15604, 11308, 0, 35504, 15604, 6612] |
| ch1 | [15604, 15604, 15604, 15604, 12808, 0, 30892, 18716, 6612] |

Класс 5 пуст в обоих каналах этого представительного split из-за tied quantile boundaries; он всё равно оплачен dense model. Во всех splits пустые/малые классы маркированы явно.
Для spatial и boundary OOB distribution одинакова, поэтому пространственный дополнительный gain на OOB равен 0.

### In-bounds и OOB отдельно

Random holdout, среднее 3 seeds; bits/symbol внутри каждой указанной части, без смешивания её размера с полным test.

| Model | Channel | In-bounds bits/symbol | OOB bits/symbol | Interior gain vs boundary | OOB gain vs boundary |
|---|---|---:|---:|---:|---:|
| IID | 0 | 1.543649 | 0.543379 | -0.000919 | -0.483035 |
| Boundary | 0 | 1.542730 | 0.060344 | 0.000000 | 0.000000 |
| quantile-Spatial-8 | 0 | 1.326961 | 0.060344 | 0.215769 | 0.000000 |
| IID | 1 | 1.489849 | 0.550283 | -0.000776 | -0.489938 |
| Boundary | 1 | 1.489074 | 0.060344 | 0.000000 | 0.000000 |
| quantile-Spatial-8 | 1 | 1.303971 | 0.060344 | 0.185102 | 0.000000 |
| IID | total | 1.516749 | 0.546831 | -0.000847 | -0.486487 |
| Boundary | total | 1.515902 | 0.060344 | 0.000000 | 0.000000 |
| quantile-Spatial-8 | total | 1.315466 | 0.060344 | 0.200436 | 0.000000 |

### Training empirical MI

MI ниже оценена на training частотах без сглаживания; это in-sample диагностическая величина, не held-out выигрыш и не размер bitstream.

| Quantile-8 | I(class;q4), bits/symbol | I(coarse_class;q4|in_bounds), weighted bits/symbol |
|---|---:|---:|
| 0 | 0.252471 | 0.224774 |
| 1 | 0.222230 | 0.194172 |
| total | 0.237351 | 0.209473 |

## Устойчивость: Quantile-8

| Split | Channel | Gain vs boundary mean | Min..max по seeds | Std | u32 net vs boundary B |
|---|---|---:|---|---:|---:|
| random | 0 | 0.205108 | 0.203278..0.208480 | 0.002924 | -1965.4 |
| random | 1 | 0.175955 | 0.174025..0.178945 | 0.002626 | -2713.8 |
| random | total | 0.190532 | 0.189231..0.191253 | 0.001129 | -4679.2 |
| block-8 | 0 | 0.189688 | 0.170052..0.208830 | 0.019394 | -2361.3 |
| block-8 | 1 | 0.179237 | 0.174030..0.183889 | 0.004953 | -2629.6 |
| block-8 | total | 0.184463 | 0.172041..0.196360 | 0.012168 | -4990.8 |
| block-16 | 0 | 0.198343 | 0.176133..0.223748 | 0.023968 | -2139.1 |
| block-16 | 1 | 0.179689 | 0.151880..0.195343 | 0.024146 | -2618.0 |
| block-16 | total | 0.189016 | 0.164007..0.209546 | 0.023098 | -4757.0 |

## Выбор по validation

Dense-u32 выбирает IID для всех18 channel/split combinations. Packed-u16 выбирает quantile-8 либоquantile-4. Sparse-u16 выбирает quantile-8 либоquantile-16. Подробные validation objectives и независимые final test metrics: model-selection.json (внешний артефакт; см. каталог исключённых ссылок).
Прескриптивный критерий PROMISING: positive incremental CI lower bound и положительная mean-rate net projection vs обе baselines во всех9 splits хотя бы при одном явно указанном feasible storage scenario. Получены кандидаты: `{'dense_u32': [], 'packed_u16': ['quantile-Spatial-4', 'quantile-Spatial-8'], 'sparse_default_u16': ['quantile-Spatial-16', 'quantile-Spatial-4', 'quantile-Spatial-8']}`.
Это feasibility screening, не multiple-testing-corrected подтверждение выбранного нового метода. Net projection CI не гарантирован положительным для каждого scenario; confidence intervals не покрывают неизвестный actual stream overhead.

## Ответы на исследовательские вопросы

1. Измеримая зависимость есть: для quantile-8 training MI=0.237351, incremental MI given bounds=0.209473 bits/symbol (random, среднее 3 seeds). Только по этим in-sample величинам вывод не делался.
2. Она улучшает held-out prediction: quantile контексты дают положительный incremental gain сверх boundary во всех random/spatial splits; у quantile-8 все clustered CI lower bounds>0.
3. Дополнительный gain quantile-8 около0.19 bits/symbol, с явным разбросом по seeds и spatial regimes в таблице выше.
4. Current dense-u32 стоимость не окупается. Компактные mass representations дают положительную прогнозную net экономию; actual profitability ещё не измерена.
5. Каналы различаются: обычно gain ch0 больше, но оба канала дают воспроизводимый положительный gain; occupancy и CDF различаются.
6. Quantile bins существенно лучше uniform-width. Результат сохраняется при spatial holdout, но absolute rates и величина gain зависят от удержанных областей. Больше классов не означает больше net saving.
7. Имеет смысл отдельный небольшой actual coding эксперимент с существующим range engine и компактным хранением модели, если исследователь задаст такой следующий этап. Новый coder engine разрабатывать на основании этих данных не требуется.
8. Вывод нельзя переносить на L5+: collisions нарушают биекцию slot↔vertex, меняют соответствия и target weights; decoder causality и coverage потребуется проверить заново.
9. Альтернативы: spatial active/inactive regions, общий уровень амплитуды, квантование/outliers, shared initialization, tied float32 context values/ULP effects и локальная корреляция. Это не доказательство causal influence L3 на L4.

## Проверки и ограничения

Unit tests: {'tests': 8, 'failures': 0, 'errors': 0}; все integrity/leakage/probability/unit checks: [validation.json](validation.json), tests.log (внешний артефакт; см. каталог исключённых ссылок), validation.log (внешний артефакт; см. каталог исключённых ссылок).
Исправлена ошибка имени поля при построении sensitivity plot и ширина одноклассового графика; численные расчёты не менялись. Журнал: failure-history.json (внешний артефакт; см. каталог исключённых ссылок).
GPU indexing NOT RUN здесь: предыдущая exhaustive parity подтверждена и использована, повторных GPU операций не было. Декодированный контекст сравнен с сохранённым audited fresh-process replay.
Одна синтетическая сцена, один trained seed, одна пара уровней и table8 quantization; нет доказательства обобщения NVCC-style priors. Sparse MI biased и training-only; CI conditional-on-fit;12 spatial blocks в наиболее крупном holdout.
Canonical context — сохранённый GPU float32. Пороги quantile могут быть близки к tied values/ULP; предыдущая CPU/GPU tolerance не доказывает идентичность class assignments на других платформах. Для actual decoder потребуется фиксированная воспроизводимая context arithmetic.
Все savings estimated, actual_bitstream_bytes=null. Не выполнены actual entropy coding, новая модель Grid4D или обучение; это не незавершённые проверки данного диагностического этапа.
Полная повторяемость: PASS. Reproducibility evidence (внешний артефакт; см. каталог исключённых ссылок).

## Воспроизведение

```powershell
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.xyz34_feasibility.run --output research/interlevel_xyz34_feasibility_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.xyz34_feasibility.finish --output research/interlevel_xyz34_feasibility_new
.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.xyz34_feasibility.compare research/interlevel_xyz34_feasibility research/interlevel_xyz34_feasibility_new
.tools/phase2-plotting-env/Scripts/python.exe -m unittest research.hashgrid_analysis.xyz34_feasibility.tests -v
```
CPU compute: 6.18 s, environment `{'python': '3.12.14 (main, Aug 25 2026, 14:01:42) [MSC v.1944 64 bit (AMD64)]', 'numpy': '1.26.4', 'GPU_used': False}`. Existing matplotlib environment reused.

## Графики

Начать: crossentropy-quantile, overhead-sensitivity, stability-quantile; затем probability heatmaps и occupancy. Все PNG/SVG имеют exact source data/settings/SHA.
| Figure | Type | Source |
|---|---|---|
| IID, channel0: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| IID, channel0: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| IID, channel1: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| IID, channel1: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| Boundary, channel0: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| Boundary, channel0: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| Boundary, channel1: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| Boundary, channel1: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-4, channel0: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-4, channel0: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-4, channel1: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-4, channel1: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-8, channel0: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-8, channel0: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-8, channel1: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-8, channel1: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-16, channel0: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-16, channel0: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-16, channel1: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform-Spatial-16, channel1: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-4, channel0: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-4, channel0: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-4, channel1: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-4, channel1: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-8, channel0: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-8, channel0: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-8, channel1: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-8, channel1: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-16, channel0: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-16, channel0: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-16, channel1: training conditional histograms (внешний артефакт; см. каталог исключённых ссылок) | training empirical distributions | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile-Spatial-16, channel1: p(q4|class) (внешний артефакт; см. каталог исключённых ссылок) | training fitted finite probability model | representative-distributions.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform: held-out cross entropy, mean over3 seeds (внешний артефакт; см. каталог исключённых ссылок) | held-out measured predictive cost | results.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform: estimated payload benefit vs primary model cost (внешний артефакт; см. каталог исключённых ссылок) | estimated full-L4 extrapolation | results.json (внешний артефакт; см. каталог исключённых ссылок) |
| uniform: context occupancy, separate train/validation/test (внешний артефакт; см. каталог исключённых ссылок) | measured class counts | [class-occupancy.csv](class-occupancy.csv) |
| uniform: incremental predictive gain across fixed splits (внешний артефакт; см. каталог исключённых ссылок) | held-out gains with clustered bootstrap CI | results.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile: held-out cross entropy, mean over3 seeds (внешний артефакт; см. каталог исключённых ссылок) | held-out measured predictive cost | results.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile: estimated payload benefit vs primary model cost (внешний артефакт; см. каталог исключённых ссылок) | estimated full-L4 extrapolation | results.json (внешний артефакт; см. каталог исключённых ссылок) |
| quantile: context occupancy, separate train/validation/test (внешний артефакт; см. каталог исключённых ссылок) | measured class counts | [class-occupancy.csv](class-occupancy.csv) |
| quantile: incremental predictive gain across fixed splits (внешний артефакт; см. каталог исключённых ссылок) | held-out gains with clustered bootstrap CI | results.json (внешний артефакт; см. каталог исключённых ссылок) |
| Predicted profitability depends on how probability masses are stored (внешний артефакт; см. каталог исключённых ссылок) | estimated storage sensitivity | results.json (внешний артефакт; см. каталог исключённых ссылок) |
