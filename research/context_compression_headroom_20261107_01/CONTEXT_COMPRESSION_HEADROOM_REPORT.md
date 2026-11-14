> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Grid4D: ограниченный аудит резерва контекстного кодирования GLOBAL8

**Итог: WEAK_SIGNAL.** На validation заранее выбран **PREVIOUS8**; после check семейство не менялось. Диагностика оценивает три простых источника контекста на двух фиксированных development-сценах. Новый контекстный bitstream не создан; это не независимая проверка обобщения.

## 1. Неизменные входы и протокол

- bouncingballs: uint8[6098108,2], N=12,196,216 symbols; codes SHA256 `b6f2676efa4c33d0cf2506271bafe0db0b133d05baeabaeb07eca8e47e939de8`; canonical FP32 SHA256 `f4bb5aa577e232e1caa89c67125b261169b0fa77fecdebc1609ae2e25cb47c38`.
- hellwarrior: uint8[6098108,2], N=12,196,216 symbols; codes SHA256 `acd04fe37fcf727d3323c3fb9813ca04777381eaba8bbdf57039187de01e00ea`; canonical FP32 SHA256 `aeefc00dbbc1d785967341854c9c63358c598e83f71ad476838996b1baee6efa`.

Источники: `research/full_spatial_hashgrid_audit_20261029_01/<scene>/ZLIB8.npz`. Все16 уровней и каждый allocated slot сохранены. Новый input audit сверил bytes/SHA256 архива, metadata, массива и level records со старым FINAL_VALIDATION; затем сравнил декодированные codes с frozen mmap поэлементно и canonical reconstruction со старым SHA256. Checkpoints не загружались; min/max, precision, clipping и codes не менялись. Квантователь один GLOBAL8 для всего xyz, оба канала. Точные offsets, resolutions и quantizer находятся в INPUT_MANIFEST.json/INPUT_AUDIT.json.

PREREGISTERED_PROTOCOL.json сохранён до новых результатов. Фиксированы CHANNEL8 ch0→ch1 и PREVIOUS8 на L6–L10, MEAN8 только L6→L7 и L7→L8; отдельный Geometry4 контроль. Никаких L9–L15 correspondence enumeration, temporal grids, новых сцен/обучения/рендеров, PMF clustering или подбора дополнительных bins.

## 2. ACTUAL стандартные lossless-файлы

| scene | variant | actual_B | payload_B | level_framing_B | common_metadata_framing_B | fresh_exact |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | DEFLATE6_slot-major | 2077434 | 2074238 | 768 | 2428 | True |
| bouncingballs | DEFLATE6_channel-major | 2094411 | 2091212 | 768 | 2431 | True |
| bouncingballs | XZ6_slot-major | 1750275 | 1747084 | 768 | 2423 | True |
| bouncingballs | XZ6_channel-major | 1798450 | 1795256 | 768 | 2426 | True |
| bouncingballs | HISTORICAL_NPZ_DEFLATE6 | 2079708 | 2076637 | 1920 | 1151 | True |
| hellwarrior | DEFLATE6_slot-major | 1764798 | 1761603 | 768 | 2427 | True |
| hellwarrior | DEFLATE6_channel-major | 1820135 | 1816937 | 768 | 2430 | True |
| hellwarrior | XZ6_slot-major | 1504834 | 1501644 | 768 | 2422 | True |
| hellwarrior | XZ6_channel-major | 1558485 | 1555292 | 768 | 2425 | True |
| hellwarrior | HISTORICAL_NPZ_DEFLATE6 | 1766604 | 1763531 | 1920 | 1153 | True |

| scene | effect | from | to | saving_B | saving_percent |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | layout_DEFLATE | DEFLATE6_slot-major | DEFLATE6_channel-major | -16977 | -0.817210 |
| bouncingballs | layout_XZ | XZ6_slot-major | XZ6_channel-major | -48175 | -2.752425 |
| bouncingballs | compressor_slot | DEFLATE6_slot-major | XZ6_slot-major | 327159 | 15.75 |
| bouncingballs | compressor_channel | DEFLATE6_channel-major | XZ6_channel-major | 295961 | 14.13 |
| bouncingballs | wrapper_NPY_vs_raw | HISTORICAL_NPZ_DEFLATE6 | DEFLATE6_slot-major | 2274 | 0.109342 |
| hellwarrior | layout_DEFLATE | DEFLATE6_slot-major | DEFLATE6_channel-major | -55337 | -3.135600 |
| hellwarrior | layout_XZ | XZ6_slot-major | XZ6_channel-major | -53651 | -3.565244 |
| hellwarrior | compressor_slot | DEFLATE6_slot-major | XZ6_slot-major | 259964 | 14.73 |
| hellwarrior | compressor_channel | DEFLATE6_channel-major | XZ6_channel-major | 261650 | 14.38 |
| hellwarrior | wrapper_NPY_vs_raw | HISTORICAL_NPZ_DEFLATE6 | DEFLATE6_slot-major | 1806 | 0.102230 |

Четыре новых варианта используют один diagnostic wrapper:16 независимо сжатых raw uint8 sections, фиксированные48B descriptors, общий JSON/prefix/SHA256. DEFLATE6 использует raw DEFLATE как ZIP, XZ — stdlib LZMA2 preset6/CRC64. Slot-major и channel-major обратимы. Исторический NPZ DEFLATE6 включает сжатые NPY headers и ZIP framing, поэтому различие между ним и новым DEFLATE wrapper не является чистым эффектом layout. Его фактический файл тоже свежедекодирован и участвует в выборе сильнейшего контроля. Эффекты compressor/layout не называются выигрышем контекста. BASELINE_LEVEL_SECTIONS.csv содержит точный per-level breakdown.

## 3. Где сосредоточена стоимость

| scene | best_baseline | largest_levels | L6_L10_sections_B | L6_L10_percent_full_file |
| --- | --- | --- | --- | --- |
| bouncingballs | XZ6_slot-major | L7=315408B, L8=298400B, L6=254304B, L9=184680B, L5=158992B | 1210420 | 69.16 |
| hellwarrior | XZ6_slot-major | L8=275076B, L7=264980B, L9=262684B, L6=208776B, L10=205868B | 1217384 | 80.90 |

LEVEL_ENTROPY_AUDIT.csv содержит все16 уровней ×2 канала ×2 сцены: marginal H0 и finite-IID оценку, использующие уже сохранённые full-scene counts/masses, без нового fitting. H0 — характеристика безконтекстной модели, **не универсальная нижняя граница lossless compression**. DEFLATE/XZ используют иные зависимости; разность с H0 не доказывает резерв всех возможных методов. Actual IID range payload в этом аудите не измерялся.

## 4. Held-out и decoder availability

| scene | level | seed | blocks | block_counts | slot_counts |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | 6 | 0 | 128 | {'fit': 83, 'validation': 20, 'check': 25} | {'fit': 339968, 'validation': 81920, 'check': 102400} |
| bouncingballs | 6 | 1 | 128 | {'fit': 83, 'validation': 20, 'check': 25} | {'fit': 339968, 'validation': 81920, 'check': 102400} |
| bouncingballs | 6 | 2 | 128 | {'fit': 83, 'validation': 20, 'check': 25} | {'fit': 339968, 'validation': 81920, 'check': 102400} |
| hellwarrior | 6 | 0 | 128 | {'fit': 83, 'validation': 20, 'check': 25} | {'fit': 339968, 'validation': 81920, 'check': 102400} |
| hellwarrior | 6 | 1 | 128 | {'fit': 83, 'validation': 20, 'check': 25} | {'fit': 339968, 'validation': 81920, 'check': 102400} |
| hellwarrior | 6 | 2 | 128 | {'fit': 83, 'validation': 20, 'check': 25} | {'fit': 339968, 'validation': 81920, 'check': 102400} |

Блоки4096 последовательных hash slots не являются пространственными блоками. На L6–L10:128блоков,83 fit/20 validation/25 check, то есть339968/81920/102400 slots. Два канала и все correspondences одного slot вместе. Thresholds и PMF fit только на fit; quantile8 linear, duplicate thresholds сохранены, searchsorted right; alpha1 и строго положительные integer masses суммой65536. Seeds не являются независимыми сценами и не обосновывают статистическую значимость.

CHANNEL8 оплачивает channel0 IID и channel1 conditional. PREVIOUS8 сбрасывается на каждом4096-м slot, отдельные start PMF fit на all-fit marginal, а symbol кодируется один раз. MEAN8 использует полный eligible mean от деквантованных coarse GLOBAL8, прежнюю arithmetic/geometry, G0/G1 fallbacks; одинаковые slot indices разных уровней не считаются координатным соответствием. Полный coarse prerequisite уже включён в полном spatial-файле и учитывается один раз.

DECODER_CONTEXT_VALIDATION.json: **PASS**. Это fresh-process context replay с разрешёнными decoder inputs, exact class IDs и synthetic no-leak checks, а не самостоятельное декодирование нового contextual bitstream. Стандартные baseline files действительно самостоятельно декодированы. Аудит file-open действует на уровне Python, не является OS sandbox для произвольного native кода.

## 5. Что дали три семейства

| scene | family | control | check_CE_mean3 | gain_CE_mean3 | paid_gain_B_seed0 | paid_gain_B_seed1 | paid_gain_B_seed2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | CHANNEL8 | IID | 1.754898 | 0.051163 | 28986.24 | 29257.45 | 28678.11 |
| bouncingballs | PREVIOUS8 | IID | 1.737041 | 0.069019 | 33619.67 | 33533.22 | 32654.72 |
| bouncingballs | MEAN8 | Geometry4 | 2.245881 | -0.004594 | -14249.70 | -14586.09 | -14395.00 |
| hellwarrior | CHANNEL8 | IID | 1.683492 | 0.039069 | 22314.80 | 22736.30 | 22299.70 |
| hellwarrior | PREVIOUS8 | IID | 1.694326 | 0.028235 | 9468.46 | 9502.23 | 8970.72 |
| hellwarrior | MEAN8 | Geometry4 | 1.908383 | -0.003320 | -13549.43 | -13764.74 | -13783.86 |

Положительный gain означает меньшую длину кандидата. Paid gain здесь — held-out CE, экстраполированная на все заранее заданные уровни семейства, с полной измеренной стоимостью модели; это **ESTIMATED**, не размер entropy payload. Все уровни, включая отрицательные вклады, учтены. Подробные validation/check CE каждого канала, суммы bits, signed paired differences и G0/G1/G2/G3 для spatial-контекста сохранены в HELDOUT_CONTEXT_RESULTS.csv. Validation ranking и hashes зафиксированы в FAMILY_SELECTION_FREEZE.json до check/full-scene fitting.

## 6. Shuffled negative control выбранного семейства

| scene | seed | split | family | correct_CE | shuffled_CE | simple_control_CE | shuffled_minus_correct_bits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 0 | validation | PREVIOUS8 | 1.751560 | 1.889243 | 1.820417 | 112789.65 |
| bouncingballs | 0 | check | PREVIOUS8 | 1.738509 | 1.875486 | 1.807878 | 140264.77 |
| bouncingballs | 1 | validation | PREVIOUS8 | 1.750794 | 1.888094 | 1.820232 | 112476.67 |
| bouncingballs | 1 | check | PREVIOUS8 | 1.736043 | 1.872279 | 1.804987 | 139504.94 |
| bouncingballs | 2 | validation | PREVIOUS8 | 1.761919 | 1.898871 | 1.830066 | 112191.55 |
| bouncingballs | 2 | check | PREVIOUS8 | 1.736572 | 1.873261 | 1.805315 | 139969.27 |
| hellwarrior | 0 | validation | PREVIOUS8 | 1.695259 | 1.751185 | 1.722489 | 45814.88 |
| hellwarrior | 0 | check | PREVIOUS8 | 1.694285 | 1.751493 | 1.722774 | 58580.65 |
| hellwarrior | 1 | validation | PREVIOUS8 | 1.704550 | 1.761964 | 1.732835 | 47033.22 |
| hellwarrior | 1 | check | PREVIOUS8 | 1.690494 | 1.747972 | 1.719021 | 58857.19 |
| hellwarrior | 2 | validation | PREVIOUS8 | 1.695649 | 1.752459 | 1.723552 | 46538.24 |
| hellwarrior | 2 | check | PREVIOUS8 | 1.698200 | 1.754697 | 1.725888 | 57852.78 |

На check правильное соответствие имеет меньшую estimated длину, чем shuffle, в **6/6** scene×seed случаях. После shuffle положительный gross gain против простого контроля остаётся в **0/6** случаях. Это описательное сравнение фиксированных моделей, не тест статистической значимости.

Перемешивание context assignments выполнено единожды по заранее указанному правилу внутри split, независимо по каналам; для MEAN8 также внутри geometry category. PMF не refit. **120 certificates EXACT_MARGINALS** подтверждают поэлементное равенство before/after class histograms, их hashes и точный slot count; slot/assignment hashes сохранены в SHUFFLED_MARGINAL_VALIDATION.csv и CHECK_COMPLETE.json. Положительное shuffled−correct означает полезность правильного соответствия для данного предиктора; само по себе это не доказательство practical compression. Shuffled вариант не decoder-available codec и не кандидат для выбора.

## 7. Полная цена модели

| scene | level | family | storage | pmf_rows | pmf_bytes | threshold_bytes | mapping_bytes | specification_bytes | framing_bytes | side_information_bytes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 6 | CHANNEL8 | sparse_default_u16 | 9 | 1161 | 70 | 11 | 514 | 56 | 1812 |
| bouncingballs | 6 | PREVIOUS8 | sparse_default_u16 | 18 | 2169 | 130 | 20 | 641 | 56 | 3016 |
| bouncingballs | 7 | CHANNEL8 | sparse_default_u16 | 9 | 1446 | 70 | 11 | 514 | 56 | 2097 |
| bouncingballs | 7 | PREVIOUS8 | sparse_default_u16 | 18 | 3249 | 130 | 20 | 641 | 56 | 4096 |
| bouncingballs | 7 | MEAN8 | sparse_default_u16 | 20 | 2951 | 130 | 22 | 820 | 56 | 3979 |
| bouncingballs | 8 | CHANNEL8 | sparse_default_u16 | 9 | 1143 | 70 | 11 | 514 | 56 | 1794 |
| bouncingballs | 8 | PREVIOUS8 | sparse_default_u16 | 18 | 2181 | 130 | 20 | 641 | 56 | 3028 |
| bouncingballs | 8 | MEAN8 | sparse_default_u16 | 20 | 1835 | 130 | 22 | 820 | 56 | 2863 |
| bouncingballs | 9 | CHANNEL8 | sparse_default_u16 | 9 | 1020 | 70 | 11 | 514 | 56 | 1671 |
| bouncingballs | 9 | PREVIOUS8 | sparse_default_u16 | 18 | 1689 | 130 | 20 | 641 | 56 | 2536 |
| bouncingballs | 10 | CHANNEL8 | sparse_default_u16 | 9 | 957 | 70 | 11 | 515 | 56 | 1609 |
| bouncingballs | 10 | PREVIOUS8 | sparse_default_u16 | 18 | 1872 | 130 | 20 | 642 | 56 | 2720 |
| hellwarrior | 6 | CHANNEL8 | sparse_default_u16 | 9 | 1002 | 70 | 11 | 514 | 56 | 1653 |
| hellwarrior | 6 | PREVIOUS8 | sparse_default_u16 | 18 | 2082 | 130 | 20 | 641 | 56 | 2929 |
| hellwarrior | 7 | CHANNEL8 | sparse_default_u16 | 9 | 1461 | 70 | 11 | 514 | 56 | 2112 |
| hellwarrior | 7 | PREVIOUS8 | sparse_default_u16 | 18 | 2949 | 130 | 20 | 641 | 56 | 3796 |
| hellwarrior | 7 | MEAN8 | sparse_default_u16 | 20 | 2309 | 130 | 22 | 820 | 56 | 3337 |
| hellwarrior | 8 | CHANNEL8 | sparse_default_u16 | 9 | 1497 | 70 | 11 | 514 | 56 | 2148 |
| hellwarrior | 8 | PREVIOUS8 | sparse_default_u16 | 18 | 2907 | 130 | 20 | 641 | 56 | 3754 |
| hellwarrior | 8 | MEAN8 | sparse_default_u16 | 20 | 1430 | 130 | 22 | 820 | 56 | 2458 |
| hellwarrior | 9 | CHANNEL8 | sparse_default_u16 | 9 | 1245 | 70 | 11 | 514 | 56 | 1896 |
| hellwarrior | 9 | PREVIOUS8 | sparse_default_u16 | 18 | 2517 | 130 | 20 | 641 | 56 | 3364 |
| hellwarrior | 10 | CHANNEL8 | sparse_default_u16 | 9 | 669 | 70 | 11 | 515 | 56 | 1321 |
| hellwarrior | 10 | PREVIOUS8 | sparse_default_u16 | 18 | 1332 | 130 | 20 | 642 | 56 | 2180 |

Это **ACTUAL dry-model bytes**: masses, thresholds, mapping, context/start/fallback specification, identifiers, framing и checksum. Для каждого фиксированного PMF измерены dense_u32, packed_u16, sparse_default_u16, выбран кратчайший корректный transport без clustering; CDF не дублируется. MODEL_SIDE_BYTES.csv содержит все transports и fit phases. Full-scene PMF построены один раз после check; это scene-specific compression forecast, не held-out generalization. Сумма −log2(mass/65536)/8 называется ideal payload estimate. FULL_SCENE_LEVEL_TRADEOFFS.csv разделяет ideal payload, measured side cost и заменяемые фактические sections каждого уровня.

## 8. FULL-GRID PROJECTION, не actual full-grid codec

| scene | family | baseline_role | actual_baseline_B | removed_actual_section_B | ideal_payload_B | measured_model_side_B | extra_mode_framing_reserve_B | projected_full_grid_B | saving_B | saving_percent |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | CHANNEL8 | strongest_actual | 1750275 | 1210420 | 1154537.18 | 8983 | 4416 | 1707791.18 | 42483.82 | 2.427265 |
| bouncingballs | CHANNEL8 | historical_DEFLATE | 2079708 | 1418211 | 1154537.18 | 8983 | 4416 | 1829433.18 | 250274.82 | 12.03 |
| bouncingballs | PREVIOUS8 | strongest_actual | 1750275 | 1210420 | 1142469.87 | 15396 | 4416 | 1702136.87 | 48138.13 | 2.750318 |
| bouncingballs | PREVIOUS8 | historical_DEFLATE | 2079708 | 1418211 | 1142469.87 | 15396 | 4416 | 1823778.87 | 255929.13 | 12.31 |
| bouncingballs | MEAN8 | strongest_actual | 1750275 | 613808 | 588806.22 | 6842 | 4224 | 1736339.22 | 13935.78 | 0.796205 |
| bouncingballs | MEAN8 | historical_DEFLATE | 2079708 | 698822 | 588806.22 | 6842 | 4224 | 1980758.22 | 98949.78 | 4.757869 |
| hellwarrior | CHANNEL8 | strongest_actual | 1504834 | 1217384 | 1104619.38 | 9130 | 4416 | 1405615.38 | 99218.62 | 6.593326 |
| hellwarrior | CHANNEL8 | historical_DEFLATE | 1766604 | 1419243 | 1104619.38 | 9130 | 4416 | 1465526.38 | 301077.62 | 17.04 |
| hellwarrior | PREVIOUS8 | strongest_actual | 1504834 | 1217384 | 1111506.13 | 16023 | 4416 | 1419395.13 | 85438.87 | 5.677628 |
| hellwarrior | PREVIOUS8 | historical_DEFLATE | 1766604 | 1419243 | 1111506.13 | 16023 | 4416 | 1479306.13 | 287297.87 | 16.26 |
| hellwarrior | MEAN8 | strongest_actual | 1504834 | 540056 | 498783.16 | 5795 | 4224 | 1473580.16 | 31253.84 | 2.076896 |
| hellwarrior | MEAN8 | historical_DEFLATE | 1766604 | 626684 | 498783.16 | 5795 | 4224 | 1648722.16 | 117881.84 | 6.672794 |

Формула: actual whole baseline − actual replaced sections + estimated candidate sections + резерв4096B общего нового режима и64B на каждый заменяемый уровень. Резерв — заранее объявленный инженерный бюджет будущего bounded manifest/coder termination/framing, не измеренный новый формат и не доказанная верхняя граница любого будущего codec. Model-only envelope уже полностью оплачен; новые framing расходы не спрятаны. Каждое семейство проектируется отдельно: CHANNEL8/PREVIOUS8 заменяют L6–L10, MEAN8 только L7/L8; прочие sections сохраняются. Нет hybrid, scene-specific subset или повторно оплаченного coarse. CSV также отдельно содержит validation/check extrapolations.

## 9. Решение и ограничения

Выбранное семейство: **PREVIOUS8**. Replay PASS=True; paid check gain положителен на обеих сценах во всех3seeds=True; full-fit projection≥3% против сильнейшего actual baseline на обеих сценах=False. Итог доступных семейств: **WEAK_SIGNAL**; общий статус: **WEAK_SIGNAL**. 3% — фильтр будущих инженерных затрат, не научная граница и не обещание actual экономии. Недоступная из-за ресурсов проверка никогда не считается отрицательным научным результатом; список отсутствующего приведён в HEADROOM_DECISION.json.

Результат ограничен двумя development checkpoints, GLOBAL8 и тремя заданными простыми семействами. Он не устанавливает бесполезность всего contextual compression, не доказывает новизну, не даёт процент сжатия всего Grid4D и не подменяет exact uint8 reconstruction восстановлением исходных FP32 weights. Размер нового контекстного файла, coder redundancy и его independent decode пока не измерены.

**Одно следующее решение:** Остановить этот ограниченный аудит; не создавать контекстный кодер по текущему фильтру. Зафиксировать зависимость и её стоимость; отдельное решение о следующем исследовании требуется до новых вычислений.

## 10. Ресурсы, корректность и воспроизведение

Standard compression четырёх вариантов обеих сцен: 20.421s; cold decode десяти файлов: 6.197s; вложенный internal decode: 2.348s. Максимальный measured baseline-process RSS: 78.11MiB, decoder RSS: 71.62MiB.

| source | nominal_vertices | eligible_vertices | wall_seconds | cpu_seconds | process_peak_RSS_MiB |
| --- | --- | --- | --- | --- | --- |
| mean/bouncingballs/L6_L7/computed/validation.json | 3652264 | 3581577 | 2.774473 | 2.703125 | 131.75 |
| mean/bouncingballs/L7_L8/computed/validation.json | 9663597 | 9528128 | 7.639059 | 7.515625 | 132.34 |
| mean/hellwarrior/L6_L7/computed/validation.json | 3652264 | 3581577 | 2.502055 | 2.484375 | 131.53 |
| mean/hellwarrior/L7_L8/computed/validation.json | 9663597 | 9528128 | 7.311257 | 7.281250 | 131.53 |

Отдельная обязательная проверка causality/context replay: **360.12s wall**, включая строгий sequential-prefix child и coarse-only replay. Это затраты correctness, не время fitting и не повторный вклад в initial Mean8 construction. Held-out stage wall: validation=10.54s, check=11.45s, full-scene dry fit=13.41s; соответствующие CPU времена и каждый completion peakRSS сохранены в TIMING_SUMMARY.json. Максимальный heldout process lifetime peak=138.05MiB.

TIMING_SUMMARY.json отдельно разделяет context construction, histogram fitting, held-out evaluation, serialization и input hashing. CPU, sequential jobs; GPU/обучение/рендеры не использовались. Cold decode включает startup, internal decode вложен в cold; component times вложены в stage wall, replay components вложены в общий correctness wall: времена не складываются повторно. Resource peaks — per-process lifetime high-water marks, не stage-incremental память и не одновременный system peak. Полный preservation audit и окончательный статус корректного завершения диагностики публикует root в FINAL_VALIDATION.json; данный генератор не утверждает результат ещё не выполненного финального аудита.

Первая baseline synthetic-попытка остановилась только из-за Windows ctypes HANDLE в измерителе RSS; traceback и прежний каталог сохранены. RESOURCE_HELPER_FIX.json подтверждает изменение исключительно helper; весь остальной module AST сохранился. Успешный bouncingballs output имеет уникальный суффикс_v02. Codec core/PMF math не исправлялись, проверки не отключались.

Первая synthetic Mean8 попытка завершила5проверок, а шестая получила PermissionError при создании bundle в Windows TEMP до запуска replay. Исправлено только место временной fixture на уникальный writable каталог run. Повторена исключительно эта незавершённая проверка:1PASS; общий итог5previous PASS +1fixture PASS =6cases. MEAN8_SYNTHETIC_ATTEMPT_001_PATH_ERROR.json сохраняет первоначальную ошибку; TEST_MEAN_CONTEXT.json и MEAN8_SYNTHETIC_FIXTURE_002.log — итог. Это ошибка пути окружения, не hashing/interpolation или decoder arithmetic.

Команды и source/runtime snapshots находятся в logs/, execution_sources/, INPUT_MANIFEST.json и PREREGISTERED_PROTOCOL.json. Порядок: input audit → standard baselines → bounded Mean8 pilots/construction → validation → context replay → FAMILY_SELECTION_FREEZE → check/shuffle → full-scene fit → reporting → preservation. Для воспроизведения нужен новый уникальный каталог; завершённые run artifacts не перезаписываются. После этого отчёта остановиться: никаких новых моделей/precision exchange/сцен/trex/actual contextual bitstreams автоматически.
