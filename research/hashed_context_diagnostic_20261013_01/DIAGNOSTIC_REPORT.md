> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Decoder-available контексты хешированных уровней G_xyz: L4→L5 и L5→L6

Дата: 2026-10-13. Выполнены только этапы 0–1 исследовательского протокола. **Статус: PASS.**

Для каждой из 524288 выделенных строк L5 и L6 сохранены геометрия, canonical context, двухканальные mean и population Std. Два независимых decoder process на каждую пару побитно восстановили все массивы из coarse symbols и metadata. Fine targets сохранены отдельно после расчёта и replay; при построении контекстов они не читались.

Вероятностные модели, энтропийное кодирование, bitstream, новое квантование и обучение Grid4D не выполнялись. Предиктивная полезность Std и выигрыш сжатия пока не измерены.

## 1. Входы и границы эксперимента

Исходный протокол: RESEARCH_DIRECTION_DECISION.md (внешний артефакт; см. каталог исключённых ссылок), разделы 5, 6, 10. Результаты сравниваются с сохранённым geometry audit (внешний артефакт; см. каталог исключённых ссылок). Предыдущие отчёты и upstream Grid4D не менялись.

Использован официальный [Grid4D](https://github.com/JiaweiXu8/Grid4D), commit `3ab7b74482910d22fba7d51ac60c8cae1fe24bf1`. Checkpoint: `outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth`.

- SHA256 checkpoint: `3306dabf8057728abfa7cda87d78c723b27a357f968fd7d721ea727ebd043090`.
- SHA256 готового `xyz_encoding.u8.bin`: `b6f2676efa4c33d0cf2506271bafe0db0b133d05baeabaeb07eca8e47e939de8`.
- SHA256 официального `hashencoder.cu`: `11daddbfe2bf33dd7d2a9ad50f909c6bd14de16d06c1c7e36894bdcf915c58d0`.
- Manifest входов этапа 0 (внешний артефакт; см. каталог исключённых ссылок) и хеши защищённых прежних файлов (внешний артефакт; см. каталог исключённых ссылок).

Quantizer взят из существующего table-wise 8-bit экспорта, shape xyz `[6098108,2]`: min=-5.548852920532227, max=2.9999356269836426, Δ=0.033524660970650468. Исходные uint8 symbols копируются точными level slices. Никакого повторного quantize нет. Dequantization — существующий `research/grid4d/codec.py::dequantize`: тело функции загружается через AST без импорта несвязанных torch/checkpoint loaders.

Coarse symbols являются decoder-equivalent сохранёнными кодами. Этот этап не извлекал их из entropy bitstream. Глобальные min/max — metadata существующего quantizer: они должны быть известны decoder. Они не являются fine-derived выбором correspondence.

## 2. Проверенные факты о структуре коллизий

Нумерация уровней zero-based. Slot index локален уровню; global row = offset_start + slot. Actual scale взят из ранее подтверждённого CUDA geometry и ещё раз проверен текущим probe.

| Level | Роль | Actual scale по каждой оси | Resolution | Rows | Offsets [start,end) | Lookup |
|---|---|---:|---|---:|---|---|
| L4 | coarse | 57.350231170654297 | 59³ | 205379 | 125561, 330940 | dense |
| L5 | fine / coarse | 79.634933471679688 | 81³ | 524288 | 330940, 855228 | hash |
| L6 | fine | 110.43045806884766 | 112³ | 524288 | 855228, 1379516 | hash |

| Fine level | Slots | Nominal vertices | Eligible point vertices | Nominal colliding slots | Point colliding G3 | Max nominal multiplicity |
|---|---:|---:|---:|---:|---:|---:|
| L5 | 524288 | 531441 | 512000 | 141122 | 133424 | 7 |
| L6 | 524288 | 1404928 | 1367631 | 409904 | 402329 | 9 |

| Fine level | G0: nominal empty | G1: nominal>0, E empty | G2: n=1 | G3: n>1 |
|---|---:|---:|---:|---:|
| L5 | 183592 | 7144 | 200128 | 133424 |
| L6 | 27888 | 3057 | 91014 | 402329 |

Все cardinalities, полные multiplicity histograms и категории **точно совпадают** с предыдущим geometry audit. Перебор выполнен по всему nominal lattice: 531441 и 1404928 вершин. Результат содержит все 524288 slots каждого уровня ровно один раз, включая G0/G1.

Nominal множество `S_j={v: 0≤v_a<R_a, h(v)=j}`; допустимое point-context множество `E_j={v∈S_j: v_a≤floor(scale_a)}`. Coordinates вычисляются как float32 `u=v/scale`, без clamp. Верхний corner `ceil(scale)` при нецелом scale имеет `u>1` по данной оси и не входит в E. **E-empty не означает rendering-unused**: такой corner всё ещё может участвовать в interpolation внутри куба. Occupancy и training frequency не измерялись.

Multiplicity и geometry (внешний артефакт; см. каталог исключённых ссылок)

## 3. Математическое соответствие и decoder contract

CUDA scale `s=exp2f(level·log2(per_level_scale))·base_resolution−1`; `R=ceil(s)+1`. Allocation и runtime resolution — разные сущности. Offsets и cap берутся из сохранённой specification, без пересчёта allocation float64.

Официальный `get_grid_index` накапливает dense x-fast index с uint32 stride. Если stride превышает rows, используется XOR hash `((x·1) XOR (y·2654435761) XOR (z·805459861)) mod rows`; умножения и stride оборачиваются по модулю 2³². На L4 dense index, на L5/L6 hash. В L5→L6 coarse lookup сам обращается к хешированной L5; dense substitution не используется.

Coarse lookup: `p=u·s_coarse`, `b=floor(p)`, `f=p−b`, smoothstep `a=f²(3−2f)`, сумма восьми corners с произведением a/1−a по осям. При выходе query за [0,1]³ возвращается zero. Boundary weights и zero-weight corner indices сохраняют CUDA modulo semantics. CPU использует отдельные float32 операции без FMA, corners 0…7 и axes 0…2.

Для непустого E representative — `v*=argmin (v_x+R_x·v_y+R_xR_y·v_z)`, минимальный **x-fast ordinal в E**, не minimum hash. `f_v=Lookup_coarse(Dequant(Q_coarse),v/s_fine)`.

Зафиксировано численно устойчивое накопление: anchor `a_j=f_v*`, `δ_v=float64(f_v)−float64(a_j)`; `μ_j=a_j+Σδ_v/n_j`, `σ_j=sqrt(max(0,Σδ_v²/n_j−(Σδ_v/n_j)²))`. Это population Std по каждому каналу, без поправки n−1. Обновления np.add.at идут в возрастающем x-fast порядке. Chunk меняет только буфер, порядок сложения остаётся тем же. Singleton Std принудительно равен точному нулю.

При E-empty canonical ordinal −1, vertex (−1,−1,−1), coordinates (0,0,0), canonical features/mean/Std (0,0), representative_valid=false. Это sentinel, а не допустимая вершина. G0/G1 сохраняются раздельно.

Идентификатор арифметики: `cpu-f32-separate-ufunc-corner0to7-anchor-f64-addat-xfast-popstd-v1`. Decoder должен закрепить эту specification, coarse uint8 symbols, quantizer, scale/resolution/rows/offsets, hash constants, geometry convention и fallback. Зависимости от checkpoint, undecoded fine targets, изображений или occupancy нет.

L4→L5 получает только q(L4); L5→L6 только уже доступный q(L5). То, что q(L5) также является target предыдущей пары, корректно для последовательного decoder. Fine symbols не участвуют в выборе вершины, mean/Std или примеров.

## 4. Проверенные свойства coarse features

Ниже статистика по **всем G3 slots**. Singleton G2 имеет Std=0 в обоих каналах, mean=canonical точно; G0/G1 используют явный fallback. Δ — существующий quantization step.

| Fine level | G3 slots | Хотя бы один Std>0 | Median σ₀ | Median σ₁ | P90 σ₀ | P90 σ₁ |
|---|---:|---:|---:|---:|---:|---:|
| L5 | 133424 | 126293 (94.655384%) | 0.00848593672 | 0.00857532682 | 0.031214451 | 0.0265196516 |
| L6 | 402329 | 402121 (99.948301%) | 0.0142865167 | 0.0136134056 | 0.0646199729 | 0.0514913538 |

| Fine level | Both σ exactly zero in G3 | Median norm(σ) | P90 norm(σ) | norm(σ)>Δ |
|---|---:|---:|---:|---:|
| L5 | 7131 | 0.014130176 | 0.0551243615 | 19071 (14.293530%) |
| L6 | 208 | 0.0215335368 | 0.0903989791 | 125937 (31.301994%) |

В данном checkpoint L6 имеет большую долю colliding slots и более высокую медиану разброса coarse responses. Это измеренная характеристика двух уровней одной сцены. Coarse tables также разные: L4 dense против L5 hash; причинный эффект только числа коллизий здесь не выделен.

Строго положительный Std включает значения порядка 10⁻⁹: часть различий может быть округлением float32 interpolation. Даже constant nonzero table иногда даёт такую вариацию через сумму weights. Поэтому доля Std>0 сама по себе не доказывает существенную неоднородность. Сравнение ||σ|| с Δ — только диагностический масштаб, не тест predictive usefulness.

Распределения Std по каналам и G2/G3 (внешний артефакт; см. каталог исключённых ссылок)

Mean и Std coarse features (внешний артефакт; см. каталог исключённых ссылок)

Multiplicity и одномерные распределения используют полные strata. Mean/Std hexbin показывает 80000 равномерно выбранных G3 slots/level с fixed seed; точные численные summaries вычислены без sampling. `describe.population_std` в summary JSON описывает разброс статистики между slots и отличается от σ внутри одного collision set.

### Реальные slots с похожими mean и различными Std

Поиск использовал только coarse-only arrays: допуск ||μ_A−μ_B||₂≤Δ/4 =0.008381165242662617. Выбраны три непересекающиеся пары/level. Поиск ограничен candidate sampling, глобальная оптимальность не утверждается.

| Fine | Slots A / B | n_A / n_B | distance(μ_A,μ_B) | norm(σ_A) / norm(σ_B) | Δσ norm / Δ |
|---|---|---|---:|---|---:|
| L4_to_L5 | 257240 / 146530 | 2 / 2 | 0.00731726589 | 0.0122322127 / 0.227302704 | 6.41529 |
| L4_to_L5 | 267099 / 357739 | 2 / 2 | 0.00686231579 | 0.000132470143 / 0.201093075 | 5.99441 |
| L4_to_L5 | 506067 / 237235 | 2 / 4 | 0.00769438117 | 0.0134049613 / 0.20289826 | 5.65236 |
| L5_to_L6 | 274945 / 321768 | 2 / 5 | 0.00254596794 | 0.00981801725 / 0.497577725 | 14.5493 |
| L5_to_L6 | 91265 / 83862 | 3 / 3 | 0.00339159103 | 0.00863018793 / 0.448200013 | 13.1118 |
| L5_to_L6 | 274950 / 321771 | 2 / 5 | 0.00527216065 | 0.0214344566 / 0.434838495 | 12.3313 |

Все 12 slots проверены повторно независимым scalar uint32 lookup и суммированием math.fsum: 34 nominal correspondences, canonical indices/features exact, mean error=0, maximum Std error=5.5511151231257827e-17 (tolerance 1e−14). Похожие mean могут скрывать различный разброс coarse responses. Связь этого различия с fine-symbol distribution остаётся непроверенной.

Полные примеры с mean/Std каждого канала (внешний артефакт; см. каталог исключённых ссылок); scalar-проверка (внешний артефакт; см. каталог исключённых ссылок); все correspondences выбранных slots (внешний артефакт; см. каталог исключённых ссылок).

## 5. Проверки воспроизводимости и причинности

| Проверка | Результат | Область доказательства |
|---|---|---|
| Synthetic collisions / dense / uint32 wrap / boundary / empty / population Std | PASS: 16 tests | Independent scalar oracle, controlled small grids |
| Все allocated slots | PASS | 524288/level, без gaps/duplicates; NPZ и CSV |
| Geometry audit | PASS exact | Полные nominal/point counts, histograms, G0–G3 |
| Fresh decoder replay | PASS bitwise | 2 processes/level, chunks 4096 и 65536, все arrays |
| Запрещённые чтения | PASS | Checkpoint, full xyz bin, fine_symbols.npy, parent contexts.npz блокируются отдельно |
| Independent real examples | PASS | 12 slots, scalar indexing exact; moment tolerance 1e−14 |
| CUDA indexing / runtime geometry | PASS exact | 512 indices/coarse и fine на пару, включая uint32 overflow |
| CPU/GPU features | PASS tolerance, не bitwise | 512 queries/pair; max abs 2.9802322387695312e−8 |
| Windows/WSL CPU lookup sample | PASS bitwise | Те же sampled queries; не полный aggregate portability test |
| Context classes CPU/GPU | NOT RUN | Classes/edges ещё не строились |
| Предыдущие artifacts и исходники | PASS SHA256 | 2967 защищённых файлов неизменны |

Каждый replay process читает только `decoder_bundle/decoder_metadata.json` и `decoder_bundle/coarse_symbols.npy` как данные. Импорты, stdlib и public source code допустимы. Normal replay имеет blocked_reads=[] и false checkpoint/fine-target flags. Четыре отдельные negative probes на пару дают четыре запрещённых чтения. Python audit hook проверяет этот decoder; это не OS security sandbox.

CPU encoder и CPU decoder совпали побитно для geometry и floating context arrays. Приблизительный GPU feature parity **не доказывает точного совпадения будущих контекстных классов**. Будущие bin edges/CDF требуют отдельного точного контракта. Sampled CPU bitwise parity между NumPy 1.26.4 и 1.21.6 не заменяет проверку полного aggregation на другой платформе.

Synthetic results (внешний артефакт; см. каталог исключённых ссылок); все context checks (внешний артефакт; см. каталог исключённых ссылок); artifact integrity (внешний артефакт; см. каталог исключённых ссылок); Windows/WSL CPU parity (внешний артефакт; см. каталог исключённых ссылок).

## 6. Оценка compute и фактические затраты

Предварительный pilot по 65536 nominal vertices/pair: 6.390 s для трёх context passes (parent + два decoder replay на каждую пару), conservative projected peak 256 MiB. GO относительно лимитов 1800 s CPU и 1024 MiB. Это оценка context compute; CSV, hashing, plots и import startup не входили в экстраполяцию.

| Пара | Parent context wall / CPU, s | CSV wall, s | Parent peak RSS, MiB |
|---|---|---:|---:|
| L4_to_L5 | 0.486 / 0.500 | 5.507 | 120.54 |
| L5_to_L6 | 0.873 / 0.844 | 6.250 | 132.23 |

Четыре replay: суммарно 4.033 s wall / 4.016 s CPU внутри расчёта; отдельный startup/NPZ IO не включён. Графики и summaries: 7.182 s, peak total RSS=249.08 MiB. Независимые реальные примеры: 3.844 s. Единого end-to-end таймера всей сессии нет: длительность обсуждения/реализации не равна вычислительным затратам.

GPU использован только для небольшого parity probe в существующем WSL audit-env: Python 3.10.21, NumPy 1.21.6, PyTorch 2.7.0+cu128, CUDA 12.8, RTX 5060 Laptop. Max allocated GPU memory=10.53 MiB; max total CPU RSS этого процесса=651.62 MiB (включая torch runtime). CUDA modules уже были собраны; rebuild не запускался. CPU replay и plots выполнялись отдельно. Измеренный total process RSS является консервативной верхней границей дополнительной памяти процесса; существующий WSL runtime/shared resident memory не измерялся отдельно.

Данные geometry/context: по 55574528 B массивов/level. CSV потоковый; полный список correspondences или slot×256 probability arrays не хранится. Бюджет 30 min CPU / 1 GiB не превышен.

## 7. Точные данные и воспроизведение

Для каждой пары NPZ содержит следующие массивы (N=524288):

| Массивы | Shape | Dtype |
|---|---|---|
| slot_index, global_embedding_row, nominal_count, point_count, canonical_ordinal | [N] | int64 |
| geometry | [N] | uint8 (0…3) |
| canonical_vertex | [N,3] | int32 |
| canonical_coordinates | [N,3] | float32 |
| canonical_features | [N,2] | float32 |
| mean, std | [N,2] | float64 |
| representative_valid | [N] | bool |

CSV разворачивает два канала и три координаты; Python round-trip float representations сохраняют precision. Отдельный `fine_symbols.npy` [N,2] uint8 — существующие labels для будущего этапа; contexts.npz/CSV их не содержат. Join выполняется по slot_index.

**L4_to_L5:** NPZ (внешний артефакт; см. каталог исключённых ссылок); CSV (внешний артефакт; см. каталог исключённых ссылок); fine labels (внешний артефакт; см. каталог исключённых ссылок); metadata (внешний артефакт; см. каталог исключённых ссылок); coarse symbols (внешний артефакт; см. каталог исключённых ссылок); CUDA parity (внешний артефакт; см. каталог исключённых ссылок).

Array SHA256 (sorted keys/dtype/shape/bytes): `d53f8f9a3f431703ee6af61eb2be534b786720ee4e5b9812325e2b9b645559e4`. Coarse NPY SHA256: `b3e7b40e747b60b129d1353a5858d10a554aec89c757fd4a016aaa42d77672e8`.

**L5_to_L6:** NPZ (внешний артефакт; см. каталог исключённых ссылок); CSV (внешний артефакт; см. каталог исключённых ссылок); fine labels (внешний артефакт; см. каталог исключённых ссылок); metadata (внешний артефакт; см. каталог исключённых ссылок); coarse symbols (внешний артефакт; см. каталог исключённых ссылок); CUDA parity (внешний артефакт; см. каталог исключённых ссылок).

Array SHA256 (sorted keys/dtype/shape/bytes): `3b75ba795b9448556b00797376b6f77ea60810063ebfdfd85b10b821f235eb38`. Coarse NPY SHA256: `f34ada55aa7e2225bb349692db6f07466a8ef052bda5b2388d5673e6bf88f0bc`.

CPU environment: Windows Python 3.12.14, NumPy 1.26.4; существующий `.tools/phase2-plotting-env`, Matplotlib для plots. Новые зависимости не установлены.

Команды выполняются из <PROJECT_ROOT>. Используйте **новый пустой каталог**; этот завершённый run не переиспользовать. Отчёт и результаты защищены от overwrite.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$py='<PROJECT_ROOT>\.tools\phase2-plotting-env\Scripts\python.exe'
$run='research/hashed_context_diagnostic_<NEW_UNIQUE_ID>'
New-Item -ItemType Directory -Path $run
& $py -m research.hashgrid_analysis.hashed_context.diagnostic prepare --output $run
& $py -m research.hashgrid_analysis.hashed_context.diagnostic pilot --output $run
# Proceed only when pilot.json status is GO.
& $py -m research.hashgrid_analysis.hashed_context.diagnostic compute --output $run
& $py -m research.hashgrid_analysis.hashed_context.visualize $run
& $py -m research.hashgrid_analysis.hashed_context.verify_real_examples --run $run
# Optional CUDA probes: commands below. Then integrity checks and final report:
& $py -m research.hashgrid_analysis.hashed_context.integrity $run
& $py -m research.hashgrid_analysis.hashed_context.report $run
& $py -m research.hashgrid_analysis.hashed_context.finalize $run
```

Optional GPU commands внутри существующего WSL checkout `<PROJECT_ROOT>` (перед report, новые выходные каталоги):

```bash
run="research/hashed_context_diagnostic_<NEW_UNIQUE_ID>"
bash research/hashgrid_analysis/hashed_context/run_gpu_parity.sh --bundle "$run/L4_to_L5/decoder_bundle" --output "$run/gpu_checks/L4_to_L5"
bash research/hashgrid_analysis/hashed_context/run_gpu_parity.sh --bundle "$run/L5_to_L6/decoder_bundle" --output "$run/gpu_checks/L5_to_L6"
```

Cross-CPU sample check выполняется Windows Python: `-m research.hashgrid_analysis.hashed_context.cross_cpu_parity --results <run> --output <run>/gpu_checks/cross-cpu-parity.json`; report требует результаты этих проверок для данного verified run. Для CPU-only новой среды GPU section необходимо оформить отдельно как unavailable, не подменяя её вымышленным PASS.

Исходники нового модуля и использованные public dependencies сохранены в `source_snapshot/`, их SHA — `source-hashes.json`; итоговые artifact hashes и ссылки проверяются `final-validation.json`. Эти файлы создаются отдельным finalize. Исходный driver этапа 0 сохранён как `source_stage0/diagnostic.py`; до pilot исправлен только вызов synthetic unittest suite. Hash manifest этапа 0 сохранён без изменений. Core алгоритм и все protected inputs остались прежними.

## 8. Пока не проверенные гипотезы об эффективности сжатия

Пока неизвестно, помогает ли Std предсказывать fine symbols сверх mean, canonical и geometry-only baseline; сохраняется ли эффект на held-out slots/других сценах; компенсирует ли выигрыш model/metadata bytes и decoder time. Ни scatter/hexbin, ни найденные mean-similar pairs не отвечают на эти вопросы. Compression ratio, conditional entropy, actual stream length и научная новизна этим этапом не установлены.

## 9. Возможные препятствия и граница следующего этапа

Технического препятствия для следующего CPU held-out исследования на этих данных не найдено. Следующие ограничения нужно учитывать:

- Future context classes должны воспроизводиться точно; GPU allclose features не разрешают заменять canonical CPU арифметику без отдельной проверки classes.
- C10/C6 model metadata и hashed envelope ещё не поддержаны прежним interlevel serializer; этот этап их не реализует. Для model/metadata costs потребуется отдельная разрешённая работа.
- Split выполняется по slot: все correspondences данного target остаются вместе. Edges и probabilities fit только по train; geometry-only и fallback strata обязательны.
- Boundary convention исключает верхние corner vertices из E; это явное ограничение point-context approximation, а не разрешение pruning.
- Имеются только одна сцена, два соседних перехода и existing table8 quantizer. Переносимость на другие сцены/levels и устойчивость к precision пока не доказаны.

Рекомендуемый следующий минимальный шаг — отдельный held-out тест H1: сравнить Canonical8, Mean8 и Mean4×Std2 при matched capacity, с IID/geometry-only controls, сохранёнными split seeds и train-only edges. Сейчас эта работа **не начата**.

**Остановка после этапов 0–1.** Все старые результаты остаются доступны по прежним путям; новый diagnostic run имеет собственные data, graphs, validations и source snapshots.
