> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Actual hashed inter-level bitstream: xyz L4 → L5

**Дата: 15 октября 2026. Статус: GO.** Проверены реальные standalone файлы и независимое exact-symbol декодирование.
Mean8 **229233 B**, сильнейший baseline Canonical8 **237385 B**: экономия **8152 B (3.434084%)**.
Это actual scene-specific coding одной пары уровней одного checkpoint. Не whole-Grid4D compression ratio и не held-out generalization. Отрицательный результат Count6 и прежний NO-GO Mean4×Std2 сохраняются.

## 1. Входы и причинный контракт

Checkpoint `bouncingballs-reference-50000`; неизменный table-wise uint8 экспорт. q4 `[205379,2]`, q5 `[524288,2]`. SHA256 исходного checkpoint `3306dabf8057728abfa7cda87d78c723b27a357f968fd7d721ea727ebd043090`; полного xyz uint8 `b6f2676efa4c33d0cf2506271bafe0db0b133d05baeabaeb07eca8e47e939de8`. Все q4/q5 сверены с точными slices полного экспорта; повторного quantize/training нет. [Проверка входов](input-validation.json).
L4: offsets [125561,330940), scale 57.3502311706543, R=59³, dense. L5: offsets [330940,855228), scale 79.63493347167969, R=81³, allocated rows 524288. uint32 stride/XOR hashing с primes 1,2654435761,805459861 и modulo allocated rows. Quantizer min −5.548852920532227, max 2.9999356269836426, step 0.03352466097065047; восстановление float64 affine → float32.
Для каждого fine slot j: E_j — вершины его hash-preimage с v≤floor(scale); координаты float32(v)/float32(scale). Coarse lookup: smoothstep, восемь corners0…7, отдельные float32 операции без FMA. Mean8 использует anchored float64 mean по возрастающему x-fast ordinal, затем 8 quantile bins/channel + отдельные G0/G1. Canonical8 использует минимальный eligible ordinal. Пороговые равенства направляются вправо; repeated thresholds сохраняются.
Encoder строит correspondences и coarse context без q5. Decoder сначала декодирует q4, самостоятельно восстанавливает context classes, затем декодирует q5. Fine symbols используются только encoder histogram fitting. Классы и таблица slot→vertices не передаются; class SHA служит integrity check. Fine targets не нужны для выбора класса. Все allocated rows, включая G0=183592, G1=7144, G2=200128, G3=133424, кодируются один раз, ch0 ascending slots затем ch1.

## 2. Формат и честное сравнение

Новый G4DHPAIR V1 изолирован от dense V2. Prefix `<8sH5Q>`; пять секций metadata/coarse_model/fine_model/coarse_payload/fine_payload; SHA256 trailer32 B. Metadata закрепляет обе geometry, hash/domain/interpolation, quantizer, arithmetic, model/engine version и integrity. Модели HDPM передают masses и binary float64 thresholds; CDF однозначно производен и не дублируется. [Точная спецификация и API](../experiment_bench/hashed_pair/README.md).
Существующие indexed functions entropy.py используются verbatim через AST, без нового range coder. constriction0.4.2, Categorical(perfect=False), положительные finite16 masses суммой65536; внутренняя coder24 модель. Для actual fitting использованы все q5 symbols с прежним Laplace α=1 и stable integer rounding. Все fitted параметры оплачены.
Каждый arm проверен с dense_u32, packed_u16 и sparse_default_u16; минимум выбран по реальному размеру файла независимо для каждой модели. Это минимум среди трёх проверенных transports, не доказанный глобальный optimum. Count6 не включён: A дал NO-GO, но B выполнен независимо.
Общий coarse prerequisite 76130 B =75132 B q4 payload +998 B полный coarse IID model. Эти bytes идентичны во всех файлах. Центральная geometry и всё framing консервативно включены в incremental fine budget. Старый выигрыш L3→L4 сюда не добавлялся.

## 3. Реальные физические размеры

В колонке Model bytes указаны именно fine probability masses. Thresholds, model headers/specifications, центральная metadata и framing включены в последнюю расходную колонку. Сумма четырёх колонок точно равна filesystem size.

| Модель / лучший transport | Coarse B | Fine payload B | Model B | Metadata/framing B | Total B |
|---|---:|---:|---:|---:|---:|
| IID / sparse_default_u16 | 76130 | 186800 | 470 | 2304 | 265704 |
| Geometry4 / sparse_default_u16 | 76130 | 159600 | 2465 | 2316 | 240511 |
| Canonical8 / sparse_default_u16 | 76130 | 152752 | 6053 | 2450 | 237385 |
| Mean8 / sparse_default_u16 | 76130 | 144148 | 6515 | 2440 | 229233 |

Все 12 фактических вариантов:

| Model | dense_u32 B | packed_u16 B | sparse_default_u16 B |
|---|---:|---:|---:|
| IID | 267273 | 266250 | 265704 |
| Geometry4 | 246229 | 242134 | 240511 |
| Canonical8 | 251803 | 241564 | 237385 |
| Mean8 | 243189 | 232950 | 229233 |

Точные секции и SHA каждого файла (внешний артефакт; см. каталог исключённых ссылок) · [CSV](results.csv) · Лучшие файлы (внешний артефакт; см. каталог исключённых ссылок).

Физические размеры (внешний артефакт; см. каталог исключённых ссылок)

## 4. Экономия и стоимость модели

| Mean8 относительно | Standalone saving B | Pair % | Incremental fine % | Payload saving B | Extra model B | Extra metadata B |
|---|---:|---:|---:|---:|---:|---:|
| IID | 36471 | 13.726176 | 19.238398 | 42652 | 6045 | 136 |
| Geometry4 | 11278 | 4.689183 | 6.860890 | 15452 | 4050 | 124 |
| Canonical8 | 8152 | 3.434084 | 5.055347 | 8604 | 462 | -10 |

Incremental Mean8 L5 =229233−76130=153103 B; Canonical8 =161255 B. Числитель экономии одинаков8152 B, знаменатели pair и incremental различны. Mean8 выигрывает8604 B payload у Canonical8, платит462 B дополнительных masses и экономит10 B прочей metadata: net8152 B.
Dense Mean8243189 B проигрывает лучшему Canonical8 sparse237385 B; компактная сериализация имеет практическое значение. Нельзя обосновывать выигрыш одним payload. Все gains (внешний артефакт; см. каталог исключённых ссылок).

## 5. Held-out прогноз и actual результат

| Baseline | Старый PREDICTED gross B | Старый measured extra side B | Старый PREDICTED net B | Full-scene finite gross B | Actual payload gain B | Actual extra side B | Actual net B |
|---|---:|---:|---:|---:|---:|---:|---:|
| Geometry4 | 15035.225 | 3885.000 | 11150.225 | 15451.641 | 15452.000 | 4174.000 | 11278.000 |
| Canonical8 | 8539.932 | 521.000 | 8018.932 | 8602.076 | 8604.000 | 452.000 | 8152.000 |

Прогноз был экстраполяцией test CE и train-fitted model costs. Actual refit использует всю сцену: меняются quantile thresholds, histogram masses и число sparse exceptions. Новый container учитывает свои реальные headers/thresholds/metadata. Разность full-scene finite и actual payload дополнительно отражает coder24 rounding/finalization. CPU arithmetic не менялась; GPU approximation здесь не участвовала. Численное разложение (внешний артефакт; см. каталог исключённых ссылок). Старые Mean8/Mean4×Std2 результаты не переименованы в новый независимый held-out опыт.

## 6. Correctness и устойчивость

- 12 первоначальных fresh processes +12 повторных после исправления обработки ошибок: только один bin как experiment data input; checkpoint/export/targets/parent contexts/models не читаются.
- Exact q4/q5 для1459334 symbols на файл, оба канала и все slots; class IDs также exact. 16 warm encodes и12 повторных encodes дают byte-identical файлы.
- Все masses strictly positive, sums65536, transports exact; общие coarse bytes идентичны. Внешняя проверка сверяет все массивы, а не только hashes.
- 15 unit tests PASS; 594 malformed/corrupted cases PASS с исправленным внешним SHA для semantic attacks. Включены geometry, quantizer, hash, threshold, mass, payload truncation/extra words/bitflip.
- 7 явных запрещённых чтений отклонены. Python open audit — проверка поведения данного decoder, не OS security sandbox; public software imports/version metadata загружаются отдельно.
- Независимый reviewer отдельно разобрал framing и физические lengths, проверил decoded arrays, classes, masses, storage selection и учёт расходов без fitting/encoding.

[Decode validation](decode-validation.json) · Повтор после исправления (внешний артефакт; см. каталог исключённых ссылок) · Corruption PASS (внешний артефакт; см. каталог исключённых ссылок) · Независимый аудит (внешний артефакт; см. каталог исключённых ссылок).
Первый adversarial run сохранён:24/594 checks получили AssertionError библиотеки вместо требуемого ValueError API. Ни один повреждённый файл не был принят; valid decode не расходился. Новый adapter нормализует только эту ошибку. Старый engine и bytes не изменены; полный набор проверок повторён. История (внешний артефакт; см. каталог исключённых ссылок).

## 7. Время и память

Один warmup +3 measured repeats каждого лучшего файла. Warm time исключает startup/import/disk IO; strict decode включает canonical re-encoding для выявления игнорируемых trailing words. Этот overhead показан отдельно. Cold column — отдельный fresh process вместе с imports/IO; это не измерение пустого OS disk cache.

| Model | Encode median s | Strict decode s | Context encode / decode s | Canonical validation s | Decode без re-encode s | Cold process s |
|---|---:|---:|---:|---:|---:|---:|
| IID | 0.7222 | 1.5259 | 0.0006 / 0.0002 | 0.7020 | 0.8031 | 1.7687 |
| Geometry4 | 0.7531 | 1.5378 | 0.0522 / 0.0517 | 0.6918 | 0.8361 | 1.8984 |
| Canonical8 | 1.0245 | 1.7623 | 0.3282 / 0.3092 | 0.6751 | 1.0798 | 2.1531 |
| Mean8 | 0.9964 | 1.7533 | 0.3200 / 0.3115 | 0.6696 | 1.0833 | 2.1149 |

Peak encoder parent RSS 136.76 MiB; peak fresh decoder max 123.71 MiB. Это process working set, не сумма всей системы. GPU не использован, выделено0 VRAM. Не приписывается GPU ускорение. Canonical8 пока вызывает полный context builder с лишними mean/Std: его runtime характеризует текущую реализацию, не оптимальную lower bound.
[Medians/min/max](runtime-summary.json) · Все repeats (внешний артефакт; см. каталог исключённых ссылок) · Pilot (внешний артефакт; см. каталог исключённых ссылок). Повтор после error-wrapper служит correctness check и не заменяет исходный benchmark.

CPU runtime (внешний артефакт; см. каталог исключённых ссылок)

## 8. Воспроизведение и пределы вывода

Windows x86_64, Python3.12.14, NumPy1.26.4, constriction0.4.2; существующий plotting env. Новый Windows constriction установлен отдельно в `.tools/hashed-pair-deps` без обновления старого окружения. Runtime контракт закреплён; универсальная CPU/GPU portability не заявляется. Runtime metadata (внешний артефакт; см. каталог исключённых ссылок) и requirements (внешний артефакт; см. каталог исключённых ссылок).
Из `<PROJECT_ROOT>` для нового уникального run:

```powershell
.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.hashed_pair.run prepare --run research/hashed_mean8_bitstream_NEW
.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.hashed_pair.run execute --run research/hashed_mean8_bitstream_NEW
.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.hashed_pair.replay --input research/hashed_mean8_bitstream_NEW/streams/Mean8__sparse_default_u16.bin --output research/decoded_NEW
.tools/phase2-plotting-env/Scripts/python.exe -m unittest research.experiment_bench.hashed_pair.test_format -v
.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.hashed_pair.corruption --run research/hashed_mean8_bitstream_NEW --output research/hashed_mean8_bitstream_NEW/corruption_checks_NEW
```

Изменения только в новом исследовательском модуле hashed_pair и новых каталогах результатов. Upstream Grid4D, dense V2, квантованные symbols и прежние исследования сохранены. [Финальная проверка сохранности и source snapshot](final-validation.json).
Точное entropy decoding добавляет нулевое искажение относительно frozen table8, но не устраняет прежнюю quantization error. Не кодируются остальные xyz levels, temporal tables, Gaussian PLY и deformation MLP. Нет проверки независимого checkpoint, всей сцены или RD-кривой. Mean8 не объявляется научной новизной.
Следующий минимальный опыт: заранее зафиксированный Mean8 против тех же сильных baselines на независимом checkpoint с прежними scope/precision/arithmetic/transport rules. Новые count buckets на изученном test не подбирались. Этот следующий опыт здесь не запускался.
