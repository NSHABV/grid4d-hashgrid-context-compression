> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Mean8 на hellwarrior: независимая проверка реального bitstream

**22 октября 2026. Итог: GO в заранее установленной области опыта.**

Mean8: **156027 B**; сильнейший baseline Geometry4: **158900 B**. Фактическая экономия **2873 B (1.808055% standalone пары xyz L4→L5)** при точном независимом восстановлении всех q4/q5. Canonical8 здесь слабее Geometry4 по полному файлу, хотя лучше по CE и payload. Это actual scene-specific coding на второй независимо обученной сцене. Числа относятся к одной паре уровней и table-wise uint8 symbols.

## 1. Протокол, входы и сохранность

Исполнен подготовленный план (внешний артефакт; см. каталог исключённых ссылок). [PROTOCOL.json](PROTOCOL.json) заморожен до нового экспорта и fitting: SHA256 `98f698713b2ab311293773971fecf08e4c9d4784de19d43a22ae5f672494f868`. Фиксированы четыре модели, восемь bins/channel, split seeds и три способа сериализации; настройки после результатов не подбирались.

- Grid4D commit `3ab7b74482910d22fba7d51ac60c8cae1fe24bf1`, официальный hellwarrior config, seed0, iteration50000.
- Checkpoint: `../mean8_cross_scene_20261018_02/full/model/deform/iteration_50000/deform.pth`; SHA256 `4526ff7fe18a8570e97139dfa8d98882ab394ce49433113a4e29c36839ca6dc6`.
- Tensor `grid_state_dict["xyz_encoding.embeddings"]`, float32 `[6098108,2]`. Вся xyz таблица однократно обработана существующим `research/grid4d/codec.py::quantize`.
- Table8 quantizer: min `-4.029077053070068`, max `7.156888008117676`, step `0.04386652965171664`. Float64 affine, nearest-even, clip, uint8; dequantization float64 affine → float32.
- Замороженный `inputs/xyz.u8.bin`: 12196216 B, SHA256 `acd04fe37fcf727d3323c3fb9813ca04777381eaba8bbdf57039187de01e00ea`.
- q4 `[205379,2]` — slice `[125561:330940]`; q5 `[524288,2]` — `[330940:855228]`. Оба массива точно сверены с полным экспортом.
- Ни одного повторного quantize, обучения Grid4D, изменения checkpoint или temporal tables. Исторические отчёты сохраняются в прежних каталогах. 4776 прежних файлов входят в `protected-input-hashes.json`; окончательная проверка записывается в integrity-final.json (внешний артефакт; см. каталог исключённых ссылок) и [final-validation.json](final-validation.json).

Runtime и provenance получены из нового checkpoint, а не переименованы из bouncingballs: runtime.json (внешний артефакт; см. каталог исключённых ссылок), manifest.json (внешний артефакт; см. каталог исключённых ссылок). Исходный float32 baseline ранее имел PSNR42.840995789, SSIM0.990779281 — предыдущая оценка (внешний артефакт; см. каталог исключённых ссылок). Эти метрики не являются новой оценкой качества table8. Данный опыт проверяет lossless entropy stage относительно уже квантованных symbols; исходные float32 параметры не восстанавливаются точно после 8-bit quantization. Качество рендера в этом опыте не измерялось.

## 2. Причинный контекст и фактическая геометрия

L4 dense: resolution59³, actual scale57.3502311706543 по осям; L5 hashed: resolution81³, scale79.63493347167969, 524288 allocated rows. Official Grid4D indexing: uint32 wrap, stride-or-XOR, primes `[1,2654435761,805459861]`, modulo allocated rows. Повторная CUDA проверка128 запросов ×16 уровней дала exact index parity.

Для слота j множество E_j строится из nominal vertices `v<R`, отображаемых в j; допустимы `v<=floor(actual_scale)`. Нормализованные координаты `u=float32(v)/float32(scale)`. Признак coarse вычисляется только из декодированных и деквантованных q4: smoothstep, восемь corners0…7, отдельные float32 операции. Canonical8 использует минимальный допустимый x-fast ordinal. Mean8 использует anchored float64 mean по возрастающему x-fast ordinal. Пустые множества имеют фиксированный fallback.

Mean8 и Canonical8: восемь quantile bins/channel плюс отдельные G0/G1, десять serialized classes. Повторные пороги сохраняются, boundary=`searchsorted(right)`. При actual coding thresholds fit по всем активным G2/G3, probability masses — по всем target symbols; все переданные параметры оплачены. Fine targets не участвуют в выборе вершин, агрегировании или вычислении class IDs.

Геометрия совпала с прошлым audit: nominal vertices531441; valid point vertices512000; nominal collision slots141122; point collision slots133424. G0/G1/G2/G3 = **183592 / 7144 / 200128 / 133424**. Все524288 slots кодируются ровно один раз для каждого канала, включая empty и boundary. Context checks (внешний артефакт; см. каталог исключённых ссылок).

Каноническая арифметика: `cpu-f32-separate-ufunc-corner0to7-anchor-f64-addat-xfast-popstd-v1`, NumPy1.26.4. Два coarse-only replay процесса с chunk4096/65536 дали побитово одинаковые context arrays SHA256 `8c1cf47e68a77f590cf530b6d73b46f13c9378f2feee21f7cab5eb44e1fecbb7`. Windows encoder classes, сохранённые WSL CPU contexts и каждый fresh decoder class array совпали точно. Близость GPU float features не использовалась как замена exact classes.

## 3. Формат и честное сравнение

Изолированный `research/experiment_bench/hashed_pair_v2/` содержит G4DHPAIR V2. Основное отличие от V1 — проверяемый передаваемый scene-specific table8 quantizer вместо буквальных extrema bouncingballs. Геометрия ограничена проверенной L4→L5; старые V1 coder/results не изменены. Регрессия подтверждает byte-identical старые V1 файлы и одинаковые V2 payload/model/classes при старых входах.

Prefix `<8sH5Q>` (50 B), пять секций metadata/coarse_model/fine_model/coarse_payload/fine_payload, SHA256 trailer32 B. Внутри есть geometry/hash/domain/offsets/scales, arithmetic, quantizer, thresholds, integer masses, model/engine specification и integrity. CDF выводится из masses и не дублируется. Таблица slot→vertices и массивы context classes не передаются; decoder восстанавливает их самостоятельно.

Один engine: существующий indexed range coder из entropy.py, constriction0.4.2, Categorical(perfect=False), finite16 masses с суммой65536 и внутренней coder precision24. Все masses положительны; Laplace1 и stable integer rounding. Порядок: ch0 ascending slots, затем ch1. Coarse prerequisite одинаков во всех12 файлах: **44579 B =43692 B payload +887 B полный coarse model**.

Каждая модель проверена с dense_u32, packed_u16, sparse_default_u16; выбран минимальный физический размер независимо для каждой. Это минимум среди трёх протестированных transports, не доказанный глобальный оптимум сериализации.

## 4. Физические размеры файлов

Во всех лучших файлах transport=`sparse_default_u16`. Model B ниже — только fine probability masses. Thresholds, model headers/specifications, центральная metadata и framing входят в следующую колонку; coarse model уже учтён в Coarse B. Сумма четырёх компонент точно равна filesystem size.

| Модель | Coarse B | Fine payload B | Model B | Metadata/framing B | Total B |
|---|---:|---:|---:|---:|---:|
| IID | 44579 | 125180 | 428 | 2303 | **172490** |
| Geometry4 | 44579 | 109616 | 2390 | 2315 | **158900** |
| Canonical8 | 44579 | 106424 | 6431 | 2449 | **159883** |
| Mean8 | 44579 | 103424 | 5585 | 2439 | **156027** |

| Модель | dense_u32 B | packed_u16 B | sparse_default_u16 B |
|---|---:|---:|---:|
| IID | 174101 | 173078 | 172490 |
| Geometry4 | 164693 | 160598 | 158900 |
| Canonical8 | 173923 | 163684 | 159883 |
| Mean8 | 170913 | 160674 | 156027 |

Точные данные: actual/results.csv (внешний артефакт; см. каталог исключённых ссылок), actual/best.json (внешний артефакт; см. каталог исключённых ссылок). Все12 `.bin` сохранены в actual/streams (внешний артефакт; см. каталог исключённых ссылок).

Реальные размеры и trade-off (внешний артефакт; см. каталог исключённых ссылок)

## 5. Экономия Mean8 с полным учётом overhead

| Baseline | Saving B | Pair % | Incremental fine % | Payload saving B | Extra masses B | Extra metadata B |
|---|---:|---:|---:|---:|---:|---:|
| IID | 16463 | 9.544321% | 12.870668% | 21756 | +5157 | +136 |
| Geometry4 | 2873 | 1.808055% | 2.513099% | 6192 | +3195 | +124 |
| Canonical8 | 3856 | 2.411764% | 3.344203% | 3000 | -846 | -10 |

Incremental fine budget консервативно включает всё кроме общего coarse prerequisite. Mean8: **111448 B**; Geometry4: **114321 B**. Экономия2873 B одинакова по абсолютной величине; знаменатель у pair и incremental различен.

Против Geometry4 Mean8 экономит6192 B payload, платит3195 B дополнительных masses и124 B metadata, оставляя2873 B. Против Canonical8 Mean8 одновременно уменьшает payload на3000 B и side cost на856 B. Canonical8 экономит3192 B payload относительно Geometry4, но платит4175 B дополнительного side cost и поэтому проигрывает983 B полного файла. Это измеренное свидетельство важности стоимости модели.

Экономия старой пары L3→L4 сюда не добавляется. 1.808055% нельзя интерпретировать как сжатие всей модели Grid4D. Численное разложение (внешний артефакт; см. каталог исключённых ссылок).

## 6. Вторичный held-out результат

Слоты PCG64 seeds0/1/2, train335545 / validation83886 / test104857; оба канала каждого slot вместе. Thresholds и гистограммы fit только train; validation не меняла настройки. Все12 моделей и36 dry transports заморожены до test. Это отдельная оценка prediction; actual coding использует refit по полной сцене и оплачивает его.

| Model | CE mean seeds | Channel0 | Channel1 | G3 |
|---|---:|---:|---:|---:|
| IID | 0.956027250 | 0.961682416 | 0.950372085 | 1.613990115 |
| Geometry4 | 0.838146688 | 0.844008537 | 0.832284839 | 1.521894808 |
| Canonical8 | 0.816735460 | 0.820597050 | 0.812873870 | 1.552377340 |
| Mean8 | 0.793564712 | 0.795459517 | 0.791669908 | 1.482466170 |

Primary ΔCE Canonical8−Mean8 = **+0.023170747 bits/symbol**; по seeds +0.022981770 / +0.022681021 / +0.023849451. Знак положительный в3/3 seeds. В colliding slots средний ΔCE против Geometry4 =+0.039428638, против Canonical8 =+0.069911169 bits/symbol. Полные channel/seed/stratum данные и описательные paired intervals — в heldout/HELDOUT_REPORT.md (внешний артефакт; см. каталог исключённых ссылок). Три split seeds одного checkpoint не являются тремя независимыми сценами; spatial dependence не устраняется этими разбиениями.

Held-out gains отдельно от actual bytes (внешний артефакт; см. каталог исключённых ссылок)

| Mean8 vs | PREDICTED gross mean B | PREDICTED extra side B | PREDICTED net mean B | Actual payload gain B | Actual extra side B | Actual net B |
|---|---:|---:|---:|---:|---:|---:|
| IID | 21294.290 | 5147.000 | 16147.290 | 21756 | 5293 | 16463 |
| Geometry4 | 5843.449 | 2976.000 | 2867.449 | 6192 | 3319 | 2873 |
| Canonical8 | 3037.036 | -1205.000 | 4242.036 | 3000 | -856 | 3856 |

PREDICTED — экстраполяция held-out CE на1048576 fine symbols с измеренным dry side cost. Actual — реальные файлы. Различия обусловлены full-scene refit thresholds/masses и sparse exceptions, полным framing нового container и округлением/finalization range coder. Например finite16 full-scene gross против Geometry4 =6193.095 B, actual payload gain6192 B. Prediction bridge (внешний артефакт; см. каталог исключённых ссылок). Близость predicted net2867.449 B к actual2873 B не означает тождественность методов оценки.

## 7. Correctness и независимость декодера

- **12/12 fresh-process decodes PASS.** Вход каждого decoder — только готовый `.bin` и публичный код/зависимости. Checkpoint, export, targets, contexts и parent probability arrays не читаются. Внешняя проверка сравнивает все массивы q4/q5/classes, не только SHA.
- **1459334 symbols на файл exact**, включая оба канала и все allocated slots. Исходные q4/q5 и code/input freezes остались неизменными.
- Все masses strictly positive, sums65536; три transports дают exact masses/thresholds. Shared coarse sections идентичны.
- **16 повторов byte-identical**: один warmup +три measured repeats на модель. Это четыре warmups и12 измеренных повторов.
- **594/594 malformed/corruption checks PASS**, failures0; время93.737 s. Semantic attacks включают пересчитанный внешний SHA; проверяются geometry, quantizer, thresholds, masses, truncation, extra words и payload damage. Strict decode делает canonical re-encode, чтобы отвергать игнорируемые хвосты.
- Семь явных запрещённых чтений bitstream decoder отклонены. В context preparation отдельно пять probes. В held-out replay12 class arrays восстановлены **одним** свежим процессом; ещё один процесс отклонил шесть forbidden probes.
- V2 unit tests22 PASS, context synthetic tests16 PASS, held-out bounded tests8 PASS. Alternate/constant/nonfinite quantizer, неверные scope/step/geometry и legacy regression проверены до real coding.
- Два независимых artifact audits PASS: actual (внешний артефакт; см. каталог исключённых ссылок), held-out (внешний артефакт; см. каталог исключённых ссылок). Actual reviewer самостоятельно разобрал framing и transports без codec imports; проверил masses/thresholds/classes, saved decoded arrays и121 unchanged actual artifacts. Held-out reviewer подтвердил train-only данные и118 unchanged heldout files.

Доказательства: decode-validation (внешний артефакт; см. каталог исключённых ссылок), corruption-checks (внешний артефакт; см. каталог исключённых ссылок), v2-review (внешний артефакт; см. каталог исключённых ссылок), heldout final validation (внешний артефакт; см. каталог исключённых ссылок). Контроль чтения использует Python open audit и является проверкой поведения этого декодера, а не системной security sandbox.

## 8. Время, CPU/GPU и память

Windows11, Python3.12.14, NumPy1.26.4, constriction0.4.2; processor AMD64 Family25 Model117,16 logical CPUs. Environment (внешний артефакт; см. каталог исключённых ссылок), decoder requirements (внешний артефакт; см. каталог исключённых ссылок). WSL export: Python3.10.21, Torch2.7.0+cu128, isolated NumPy1.26.4. Main codec/held-out работают на CPU.

Warm medians — три повтора после одного warmup; startup/import/IO исключены. Encode context включает вычисление quantile thresholds. Strict decode включает canonical re-encode; эта проверка показана отдельно. Cold process включает startup/import/IO, но OS disk cache не сбрасывался.

| Model | Encode s | Strict decode s | Context enc/dec s | Canonical check s | Cold process s | Fresh decoder peak MiB |
|---|---:|---:|---:|---:|---:|---:|
| IID | 0.6672 | 1.3907 | 0.0007 / 0.0002 | 0.6514 | 1.7620 | 49.11 |
| Geometry4 | 0.7108 | 1.4284 | 0.0531 / 0.0526 | 0.6421 | 1.8405 | 52.45 |
| Canonical8 | 1.0453 | 1.7193 | 0.3503 / 0.3317 | 0.6490 | 2.3155 | 123.71 |
| Mean8 | 1.0079 | 1.7019 | 0.3472 / 0.3310 | 0.6393 | 2.1249 | 123.17 |

Mean8 warm encode range1.0022–1.0107 s; strict decode1.6988–1.8187 s. CPU medians1.0000/1.7031 s. Decode за вычетом измеренного canonical validation: median1.0655 s, это арифметическое разложение того же strict run, не отдельный небезопасный режим. Encoder parent peak RSS135.289 MiB; fresh Mean8 decoder123.172 MiB. Это per-process peaks, не измерение суммарной памяти всей системы.

Подготовка: однократный xyz export1.562 s, из них quantize0.144 s, процесс с Torch peak880.953 MiB. Coarse-only context replays0.422/0.442 s, peaks119.781/117.344 MiB. Pilot projected two replays с3× запасом4.334 s и256 MiB, ниже заданных30 минут/1 GiB.

GPU использован только для scale/resolution/index probe: RTX5060 Laptop,128 queries ×16 levels,0.276 s; Torch allocated peak4608 B, reserved peak2097152 B. Это allocator counters маленькой проверки, не полная память CUDA context/драйвера. GPU acceleration кодеру не приписывается. Все расходы и ranges — [runtime-summary.json](runtime-summary.json), raw samples (внешний артефакт; см. каталог исключённых ссылок).

## 9. Возникшие проблемы и сохранённые изменения

Первый export остановился до quantization: исходный audit-env содержит NumPy1.21.6, тогда как канонический contract требует1.26.4. WSL network оказался недоступен. Официальный NumPy wheel получен через Windows и установлен offline в локальный `.deps/numpy126`; исходное окружение не обновлялось. SHA wheel и точные версии — environment.json; неудачный `prepare-export.log` сохранён. Failure history (внешний артефакт; см. каталог исключённых ссылок).

Изменения ограничены новым scene-explicit runner, отдельным V2 container, независимыми tests/replay/review и данным каталогом. Алгоритм Mean8, старые context/model/engine и V1 не изменялись. Снимок использованного публичного кода и его SHA — `source_snapshot/`, `source-snapshot.json`. Принципиальных препятствий exact decoding не обнаружено.

## 10. Научный вывод и следующий шаг

**Проверенные факты:** fixed Mean8 дал меньший реальный файл относительно сильнейшего из трёх baseline на hellwarrior; все symbols exact; весь overhead оплачен. На bouncingballs исторический выигрыш составлял8152 B (3.434084%) против Canonical8; на hellwarrior2873 B (1.808055%) против Geometry4. [Сохранённый прежний отчёт](../hashed_mean8_bitstream_20261015_01/BITSTREAM_REPORT.md), [две сцены в CSV](cross-scene-comparison.csv). Hellwarrior была выбрана до её entropy results.

**Подтверждено только prediction:** train-only Mean8 снижает held-out CE, включая G3. Это дополнительное свидетельство связи агрегированных coarse features с fine symbols, но не прямое доказательство универсального причинного механизма.

**Не проверено:** другие уровни, temporal tables, quantizer precision/scope, whole-model rate-distortion, независимость от training seed, универсальность и научная новизна. Из двух сцен не следует, что выигрыш сохранится везде. Простые Mean8/Count6 не объявляются самостоятельной новой научной разработкой. Старые NO-GO Count6 и Mean4×Std2 не пересматриваются этим опытом.

**Один рекомендуемый следующий эксперимент:** зарегистрировать проверку неизменённого Mean8 на паре **xyz L5→L6** в двух уже имеющихся checkpoint, с самостоятельным bitstream, hashed coarse lookup и теми же тремя baseline, без подбора bins. Проверяемая гипотеза — сохраняется ли оплачиваемый выигрыш после того, как и coarse level становится hashed. Опыт может дать полезный отрицательный результат: на прежнем L6 преимущество CE над Geometry4 было небольшим. Сейчас этот эксперимент не выполнялся.

Текущий этап завершён; автоматического перехода к новой модели нет. [Команды и карта артефактов](REPORT_INDEX.md).

## SHA256 лучших потоков

| Model | SHA256 |
|---|---|
| IID | `ddaca6825371240cd62a97d2f0c07e0e584c776f6a27f150d986f25278f923da` |
| Geometry4 | `61ac5b4267ad2ad874c1ab460fd06df40b613c8c2d42236bf1e6a3eb10e41e54` |
| Canonical8 | `56d44baa4eca549f025c4f17e55bc45422f26229a8844eb11b11efec57c3823f` |
| Mean8 | `a6c914da9ad5d0eccfcc7e7eae6ada4f1c938ba8f4665c3e92442b1b77085a57` |
