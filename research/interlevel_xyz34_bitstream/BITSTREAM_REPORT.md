> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Actual inter-level entropy coding: G_xyz L3 → L4

**ACTUAL COMPRESSION VERIFIED** — лучший Spatial-8 превосходит обе strongest actual baseline-модели.

Полный файл Spatial-8/sparse_default_u16: **103272 B**. Лучший Boundary: **109564 B**, лучший IID: **110640 B**.
Экономия: 6292 B (5.743%) относительно Boundary и 7368 B (6.659%) относительно IID. Это реальные filesystem sizes после независимого точного декодирования.
Область вывода: bouncingballs-reference-50000, только плотная G_xyz L3/L4, table-wise 8-bit, два канала. Не весь checkpoint или renderable 4DGS scene.

## Протокол и реализация

Вероятностные таблицы fitted по всем кодируемым L4 symbols; все параметры переданы и оплачены. Это scene-specific two-pass кодирование; результат не заменяет предыдущую held-out оценку обобщения.
Повторного обучения Grid4D и квантования нет. Сохранены исходные 79507×2 L3 и 205379×2 L4 uint8 symbols; прежние pairs/quantized exports/checkpoint не менялись.
Реализация: `research/experiment_bench/interlevel/`. Общий engine: `experiment_bench/entropy.py`, новые encode_indexed/decode_indexed используют прежние constriction0.4.2 RangeEncoder/Decoder, Categorical(perfect=False), finite16-bit masses и внутреннюю24-bit модель. Нового arithmetic/range coder нет.
Порядок во всех моделях: весь ch0 по возрастанию slot, затем весь ch1 по возрастанию slot. Нет regrouping по классу. L3 — существующий IID engine, одинаковый dense-u32 model/payload во всех девяти файлах.
Файл G4DBENCH version2 сохраняет прежние prefix <8sHQQQ>, JSON directory и SHA256 trailer; scope нового envelope — только эта пара. Version1 API и результаты сохранены.

## Exact decoder context gate

PASS: все 410758 class assignments и canonical CPU features совпали побитово в отдельном процессе.
CPU/GPU max |feature difference| = 1.1920929e-07; при новых edges различаются **18648 class assignments**, при прежних seed0 edges — 18647. Приблизительный feature parity недостаточен.
Канонический режим: `cpu-f32-separate-ufuncs-corner-order-0-to-7-v1`. float64 affine dequantization → float32; координаты float32(v)/float32(s4); position, smoothstep, weight products и corner accumulation — отдельные float32 ufunc операции без FMA, corners0..7. Pinned Linux x86_64 / NumPy1.21.6. CPU/GPU не взаимозаменяемы; универсальная переносимость NOT VERIFIED.
Пространственные вершины x-fastest; lookup не обрезается. 195112 in-bounds, 10267 OOB. OOB context=0, class8. Quantile edges linear float64 по всем in-bounds CPU features; searchsorted(side=right); repeated thresholds сохраняются и передаются.
Количество уникальных edges: [6, 6]; число exact context/edge совпадений (с повторяющимися edges): 183141.
Полные class counts ch0: [24389, 24389, 24389, 24388, 20054, 0, 53114, 24389, 10267]; ch1: [24389, 24389, 24389, 24389, 22532, 0, 43818, 31206, 10267]. Class5 недостижим в обоих каналах.
Аудит gate разрешает только публичную metadata/decoded coarse symbols. Аудит каждого настоящего decoder разрешает чтение данных только из его .bin; checkpoint, pairs, original payloads, encoder cache/class IDs не доступны. Public code/runtime dependencies разрешены; аудит Python файловых чтений не заявляется системным sandbox.
Decoder сначала восстанавливает L3 и проверяет его digest, затем заново строит все классы и восстанавливает L4. Class IDs в .bin не сохранены; передан только SHA256 для проверки результата.

## Девять фактических файлов

| Model | Storage | L4 payload B | L4 model B | Shared L3 B | Total B | Gain vs best Boundary B | Decode |
|---|---|---:|---:|---:|---:|---:|---|
| iid | dense_u32 | 75132 | 2058 | 33774 | 111893 | -2329 | PASS |
| iid | packed_u16 | 75132 | 1034 | 33774 | 110870 | -1306 | PASS |
| iid | sparse_default_u16 | 75132 | 797 | 33774 | 110640 | -1076 | PASS |
| boundary | dense_u32 | 73788 | 4106 | 33774 | 112602 | -3038 | PASS |
| boundary | packed_u16 | 73788 | 2058 | 33774 | 110555 | -991 | PASS |
| boundary | sparse_default_u16 | 73788 | 1059 | 33774 | 109564 | 0 | PASS |
| spatial8 | dense_u32 | 63936 | 18442 | 33774 | 117201 | -7637 | PASS |
| spatial8 | packed_u16 | 63936 | 9226 | 33774 | 107985 | 1579 | PASS |
| spatial8 | sparse_default_u16 | 63936 | 4505 | 33774 | 103272 | 6292 | PASS |

[results.csv](results.csv) / results.json (внешний артефакт; см. каталог исключённых ссылок) содержат все секции, SHA256, same-storage/best-baseline gains, проценты, actual bits/symbol, compression ratios. Отрицательный gain означает больший файл.

## Полный учёт секций

Shared L3 включает неизменные geometry, quantization metadata, L3 info, L3 model и L3 payload. Их байты совпадают во всех файлах. Все outer prefix/header-directory/trailer байты консервативно назначены incremental L4.
Incremental L4 = total standalone − shared sections; включает L4 payload/model/info, thresholds и ВСЁ outer framing/integrity. Поэтому absolute gains по standalone и incremental совпадают, проценты и ratios имеют разные знаменатели. Это L4 при уже известных общих данных; shared block не объявляется отдельным самодостаточным файлом.

| Model / storage | L3 payload | L3 model | Geometry | Quantization | L3 info | L4 info | Thresholds | Framing/integrity | Incremental L4 | Bits/L4 symbol |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| iid/dense_u32 | 30716 | 2048 | 570 | 219 | 221 | 268 | 0 | 661 | 78119 | 1.521460 |
| iid/packed_u16 | 30716 | 2048 | 570 | 219 | 221 | 268 | 0 | 662 | 77096 | 1.501536 |
| iid/sparse_default_u16 | 30716 | 2048 | 570 | 219 | 221 | 268 | 0 | 669 | 76866 | 1.497057 |
| boundary/dense_u32 | 30716 | 2048 | 570 | 219 | 221 | 268 | 0 | 666 | 78828 | 1.535269 |
| boundary/packed_u16 | 30716 | 2048 | 570 | 219 | 221 | 268 | 0 | 667 | 76781 | 1.495401 |
| boundary/sparse_default_u16 | 30716 | 2048 | 570 | 219 | 221 | 268 | 0 | 675 | 75790 | 1.476100 |
| spatial8/dense_u32 | 30716 | 2048 | 570 | 219 | 221 | 268 | 112 | 669 | 83427 | 1.624840 |
| spatial8/packed_u16 | 30716 | 2048 | 570 | 219 | 221 | 268 | 112 | 669 | 74211 | 1.445347 |
| spatial8/sparse_default_u16 | 30716 | 2048 | 570 | 219 | 221 | 268 | 112 | 677 | 69498 | 1.353556 |

Для лучшего Spatial-8 incremental L4=69498 B; 1.353556 bits/symbol. CR vs raw uint8 L4=5.910; standalone CR vs raw uint8 pair=5.517. Raw baselines: 410758 и 569772 B; не исходные float32 параметры.
Сумма всех metadata/model/payload секций + prefix/directory/trailer проверена против filesystem size каждого файла. Диагностические decoded .npy, logs и plots не нужны decoder и не включены в стоимость .bin.

## Probability model formats

HGPM version1 header (10 B) хранит storage ID, число каналов/классов и alphabet256. Dense-u32 и packed-u16 хранят все masses, включая пустые классы. Максимальная individual mass≤65281; cumulative sums проверены вuint64 и заканчиваются65536.
Sparse: row tag0 (1 B), most-frequent default mass u16, exception count u16, ascending (symbol u8,mass u16). Ties выбирают меньшую default mass. Tag1 (1 B) восстанавливает uniform masses только при доказанной недостижимости класса из уже декодированного L3/геометрии/edges. Decoder независимо проверяет отсутствие всех назначений в этот класс до L4 decode.
Оmitted rows для spatial8 sparse: [[0, 5], [1, 5]]. Не удаляются классы только из-за отсутствия training targets. В этом full-scene fit недостижимые классы устанавливаются по context assignments, без использования fine values.
Все 256 masses строго положительны, сумма65536; после каждого из трёх transports проверена np.array_equal исходным masses. CDF производен и не оплачивается второй раз; coder24 rounding входит в реальный payload.

## Estimated vs actual

| Storage | Previous estimated net vs Boundary B | Actual vs same Boundary B | Actual vs best Boundary B |
|---|---:|---:|---:|
| dense_u32 | -4679.2 | -4599 | -7637 |
| packed_u16 | 2488.8 | 2570 | 1579 |
| sparse_default_u16 | 8175.8 | 6292 | 6292 |

Прежний projected payload gain=9782.799 B. Full-scene GPU-context finite prediction=10176.851 B; canonical CPU=9853.714 B; actual range payload saving=9852 B.
Последовательное разложение: full-scene fitting +394.052 B; CPU arithmetic + refitted quantile thresholds -323.137 B; coder24/finalization -1.714 B. Это диагностическое разложение в заданном порядке, не причинная оценка. prediction-bridge.json (внешний артефакт; см. каталог исключённых ссылок).
При sparse реальный дополнительный overhead Spatial vs Boundary = 3560 B. Он учитывает больше exceptions у fitted scene histograms, row tags/headers, 112 B thresholds и metadata/framing. Предыдущая sparse estimate использовала training-split masses и другой metadata budget.
Dense-u32 по-прежнему не окупается. Packed-u16 и sparse остаются положительными даже против сильнейшего actual Boundary, а не только против того же storage.

## Производительность

Для каждой комбинации один прогрев + три измерения; medians и min/max. Таймеры включают обе стадии L3/L4, fitting, model IO, framing/integrity; исключают imports, process startup, disk IO и plots. L3 повторно fit/encode в каждом trial, без скрытого бесплатного cache.
| Model / storage | Encode median s (min..max) | Decode median s (min..max) | Context build median s | L4 fit median s | Serialize median s | Decoder context median s |
|---|---|---|---:|---:|---:|---:|
| iid/dense_u32 | 0.115975 (0.106556..0.118187) | 0.137887 (0.137135..0.166876) | 0.006719 | 0.001817 | 0.000035 | 0.006283 |
| iid/packed_u16 | 0.118815 (0.110082..0.132575) | 0.135688 (0.135464..0.140337) | 0.006942 | 0.001764 | 0.000035 | 0.005916 |
| iid/sparse_default_u16 | 0.126831 (0.114923..0.130766) | 0.150307 (0.143462..0.161352) | 0.010955 | 0.001885 | 0.000185 | 0.005943 |
| boundary/dense_u32 | 0.114093 (0.112252..0.119013) | 0.139581 (0.134871..0.144230) | 0.010506 | 0.002360 | 0.000037 | 0.007196 |
| boundary/packed_u16 | 0.113599 (0.108089..0.131580) | 0.137646 (0.134035..0.147484) | 0.010933 | 0.002361 | 0.000043 | 0.006458 |
| boundary/sparse_default_u16 | 0.129063 (0.116740..0.135426) | 0.172794 (0.142190..0.174721) | 0.007439 | 0.002428 | 0.000227 | 0.007051 |
| spatial8/dense_u32 | 0.240197 (0.237377..0.246965) | 0.200479 (0.196032..0.213842) | 0.129327 | 0.007739 | 0.000047 | 0.068029 |
| spatial8/packed_u16 | 0.233179 (0.226578..0.233305) | 0.194498 (0.188258..0.196215) | 0.126626 | 0.007739 | 0.000048 | 0.066706 |
| spatial8/sparse_default_u16 | 0.233048 (0.227685..0.238369) | 0.188905 (0.186980..0.190433) | 0.125099 | 0.007761 | 0.000619 | 0.060668 |

Peak process RSS=551.60 MiB (Linux getrusage SELF, включая imports/источники/benchmark, не суммарная RAM родителя+всех subprocess). VRAM NOT MEASURED; GPU не использовался. runtime.json (внешний артефакт; см. каталог исключённых ссылок), [runtime-samples.csv](runtime-samples.csv).

## Проверки

Unit/regression tests: {'tests': 22, 'failures': 0, 'errors': 0}. Context gate PASS; девять fresh decoder processes PASS; np.array_equal для L3/L4 обоих каналов, всех class IDs и восстановленных probability masses PASS. Каждому child разрешён ровно один input .bin.
Real-file integrity/semantic rejection: 54 cases PASS; дополнительно synthetic tests покрывают CDF/overflow, повторяющиеся edges, OOB, invalid models, omitted reachable classes и запрет чтения original pairs.
Каждый прогрев и timed encoding побитово совпал с сохранённым .bin. SHA256 всех девяти файлов и исходных artifacts проверены. Отдельный полный повтор: PASS, девять SHA256/размеров совпали.
[validation.json](validation.json), tests.log (внешний артефакт; см. каталог исключённых ссылок), [decode-validation.json](decode-validation.json), [corruption-validation.json](corruption-validation.json), [context-validation.json](context-validation.json).

При подготовке исправлены runtime-version check внутри read audit и ошибочная классификация создания output w+ как чтения input. Gate и tests повторены; source symbols и .bin bytes не менялись. Журнал исправлений (внешний артефакт; см. каталог исключённых ссылок).

## Ответы на исследовательские вопросы

1. Да, автономный .bin содержит все scene-specific данные для восстановления этой quantized пары. External bundle/checkpoint не нужен; public decoder/library code нужен.
2. Да, все symbols обоих уровней/каналов восстановлены точно во всех девяти вариантах.
3. Да, все class IDs совпадают в pinned CPU режиме. GPU substitution и универсальная переносимость не обеспечены.
4. L4 payload: IID=75132, Boundary=73788, Spatial8=63936 B. Spatial saving vs Boundary=9852 B.
5. Sparse L4 model вырос с 1059 до 4505 B; остальные threshold/metadata/framing байты тоже включены.
6. Да: полный Spatial меньше best Boundary на 6292 B.
7. Да: меньше best IID на 7368 B.
8. Sparse-default-u16 — минимальный фактический файл для всех трёх probability models. Packed тоже даёт выигрыш Spatial; dense проигрывает.
9. Прогнозы и actual отличаются из-за scene fitting, CPU context/tied thresholds, реальных model transport/framing и coder24 rounding; количественное разложение приведено выше.
10. Да, при compact probability storage для этой пары; не при текущем dense-u32.
11. Перед L5+ заново определить decoder-available representatives/weights для colliding slots, coverage и causal schedule; нельзя применять dense slot↔vertex mapping без проверки.
12. Одна сцена/пара/quantizer, two-pass scene-specific fitted histograms, pinned CPU arithmetic, зависимость размеров от alphabet/mass transport, отсутствие проверки переноса на другие сцены и уровни. Gaussian/MLP/другие grids не кодируются.

Следующий этап здесь не запускался: L5+, temporal/collision-aware/neural модели и обучение не выполнялись.

## Воспроизведение

Из <PROJECT_ROOT>, fresh directory:

```powershell
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh gate --output research/interlevel_xyz34_bitstream_new
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh run --output research/interlevel_xyz34_bitstream_new
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh compare --output research/interlevel_xyz34_bitstream_new
wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh compare --output research/interlevel_xyz34_bitstream_new --against research/interlevel_xyz34_bitstream
.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.interlevel.cli finish --output research/interlevel_xyz34_bitstream_new
```

Encode/decode/benchmark/validate/compare CLI и точная binary spec: [module README](../experiment_bench/interlevel/README.md). Existing audit-env и Windows plotting env; installation dependencies не менялись.

## Графики

- Nine real files, all independently decoded (внешний артефакт; см. каталог исключённых ссылок) / SVG (внешний артефакт; см. каталог исключённых ссылок) / results.json (внешний артефакт; см. каталог исключённых ссылок)
- Every byte accounted for: payload and overhead (внешний артефакт; см. каталог исключённых ссылок) / SVG (внешний артефакт; см. каталог исключённых ссылок) / results.json (внешний артефакт; см. каталог исключённых ссылок)
- Spatial-8: forecasts versus measured full-file savings (внешний артефакт; см. каталог исключённых ссылок) / SVG (внешний артефакт; см. каталог исключённых ссылок) / results.json (внешний артефакт; см. каталог исключённых ссылок)
- Net file savings against the best measured IID and Boundary baselines (внешний артефакт; см. каталог исключённых ссылок) / SVG (внешний артефакт; см. каталог исключённых ссылок) / results.json (внешний артефакт; см. каталог исключённых ссылок)
- One warmup + three timed runs; imports, disk I/O and plots excluded (внешний артефакт; см. каталог исключённых ссылок) / SVG (внешний артефакт; см. каталог исключённых ссылок) / runtime.json (внешний артефакт; см. каталог исключённых ссылок)
