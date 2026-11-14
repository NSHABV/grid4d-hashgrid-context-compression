> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Исследовательское решение: контекстное кодирование HashGrid Grid4D

Дата: 11 октября 2026 года. Проект: `<PROJECT_ROOT>`. Объект: обученный `bouncingballs-reference-50000`. Все номера уровней ниже **zero-based**. Размеры — bytes; MiB = 2²⁰ bytes. Это аудит и постановка следующего эксперимента, а не реализация нового compressor.

## 1. Executive summary

**Следующее исследование: проверить, содержит ли разброс decoder-available coarse features полезную информацию о символе colliding fine slot сверх canonical representative, среднего и geometry-only prior.** Ограничить опыт двумя парами `xyz L4→L5` и `L5→L6`, существующими table-wise uint8 targets, небольшими histogram models и одинаковым бюджетом контекстных классов. Сначала проверить восстановимость контекста, затем held-out cross-entropy и стоимость модели. Настоящий bitstream — отдельное задание после GO.

Рабочая основа существует: Grid4D обучен; исходные таблицы экспортируются; quantization и range coder работают; dense `L3→L4` даёт реальный локальный выигрыш при exact-symbol decoding. Однако **собственная алгоритмическая новизна ещё не установлена**. Inter-level conditioning, collision probability fusion и occupancy weighting уже присутствуют в CNC. Применение этих идей к Grid4D само по себе — адаптация.

Подтверждены 103272 B Spatial-8/sparse-u16 против 109564 B лучшего Boundary и 110640 B лучшего IID: экономия 6292 B, или 5,742762% **standalone файла пары L3+L4**. Full-grid gain не измерен. Dense L4 охватывает лишь 3,120433% исходных HashGrid scalars; xyz L5–L15 — 87,623666%. Поэтому переход к хешированным уровням имеет бюджетное основание, но не гарантирует выигрыш.

Новая дешёвая геометрическая диагностика установила: в L5 коллизии имеют 26,9169% всех выделенных slots, в L6 — 78,1830%; при этом L5 содержит 183592 nominal geometry-empty slots. Это не training occupancy. Данные показывают, что нужно кодировать **slot один раз**, агрегируя множество его spatial correspondences и сохраняя отдельный fallback для пустых множеств.

**Запасной вариант:** integer geometry-only context по multiplicity и boundary-only correspondence. Он значительно дешевле floating-point aggregation и мотивирован наблюдением постоянного symbol 166 в geometry-empty strata данного checkpoint. Полезность для реального файла ещё не проверена; сам count prior не следует объявлять новым алгоритмом.

Не выполнены новые quantization, training, rendering, entropy fitting или coding. Новые вычисления ограничены CPU integer geometry и описанием готовых symbols. Старые результаты сохранены; новые материалы находятся в direction_audit_20261011_01 (внешний артефакт; см. каталог исключённых ссылок). Последний загруженный запрос обрывается после «Не скач»; его недостающая часть не восстанавливалась по догадке. Datasets/checkpoints не загружались.

## 2. Что мы действительно знаем

Используем пять меток доказательств: **MEASURED** — выполнено и проверено; **SINGLE-SCENE** — измерено только на bouncingballs; **CONFIG-DERIVED** — вычислено из конфигурации; **PREDICTED** — оценка без нового bitstream; **UNVERIFIED** — гипотеза или отсутствующее доказательство. Одна запись может иметь две метки.

| Утверждение | Статус и точная область | Проверяемый источник |
|---|---|---|
| Официальный Grid4D: `JiaweiXu8/Grid4D`, commit `3ab7b74482910d22fba7d51ac60c8cae1fe24bf1` | Проверена авторская цепочка project→code; локальный commit | BASELINE_GRID4D (внешний артефакт; см. каталог исключённых ссылок), [Grid4D project](https://jiaweixu8.github.io/Grid4D-web/), [репозиторий](https://github.com/JiaweiXu8/Grid4D) |
| Reference training 50000 завершён, checkpoint загружался, rendering/evaluation выполнены | MEASURED/SINGLE-SCENE; около 97,9 min прежнего training | EXPERIMENT_BENCH_REPORT (внешний артефакт; см. каталог исключённых ссылок), deform.pth (внешний артефакт; см. каталог исключённых ссылок) |
| Reference PSNR 42,492241; SSIM 0,9958137; LPIPS 0,0074352; MS-SSIM 0,9973624 | MEASURED/SINGLE-SCENE; 20 test views, 800×800 | reference-float32 results (внешний артефакт; см. каталог исключённых ссылок); ограничения LPIPS protocol — старый bench report |
| Table8 PSNR 38,751659; level8 41,030331 | MEASURED/SINGLE-SCENE; одинаковый upstream evaluation, ΔPSNR −3,740582/−1,461910 dB | reference-table-8 results (внешний артефакт; см. каталог исключённых ссылок), reference-level-8 (внешний артефакт; см. каталог исключённых ссылок) |
| Четыре обучаемые embeddings: xyz `[6098108,2]`, каждый temporal `[161213,2]`, float32 | MEASURED; 52653976 B, xyz 92,651814%, temporal 7,348186% | HASHGRID_MAP (внешний артефакт; см. каталог исключённых ссылок), MEMORY_AUDIT_REPORT (внешний артефакт; см. каталог исключённых ссылок) |
| Full-grid table8 IID файл 2815553 B; channel_context 2863145 B | MEASURED/SINGLE-SCENE; четыре полные таблицы, не вся renderable scene | reference-iid bitstream (внешний артефакт; см. каталог исключённых ссылок), reference-channel_context (внешний артефакт; см. каталог исключённых ссылок) |
| Все stored rows L4 представлены один раз в dense pair, contexts получены из dequantized q3 | MEASURED; 205379 rows, оба channels | pairs REPORT (внешний артефакт; см. каталог исключённых ссылок), decoder.py (внешний артефакт; см. каталог исключённых ссылок) |
| Held-out quantile8 gain сверх Boundary ≈0,19 bits/symbol | MEASURED/SINGLE-SCENE; seeds 0/1/2, random/block8/block16, conditional-on-fit screening | FEASIBILITY_REPORT (внешний артефакт; см. каталог исключённых ссылок), core.py (внешний артефакт; см. каталог исключённых ссылок) |
| Spatial sparse actual pair 103272 B, выигрыш 6292 B, девять exact decodes и byte-identical repeats | MEASURED/SINGLE-SCENE; сцена-специфические передаваемые гистограммы fit по всему target | BITSTREAM_REPORT (внешний артефакт; см. каталог исключённых ссылок), LOCAL_EVIDENCE_AUDIT.json (внешний артефакт; см. каталог исключённых ссылок) |
| GPU/CPU features allclose, но classes различаются | MEASURED: max feature error 1,1920929e−7; 18648 channel-class mismatches | context-validation (внешний артефакт; см. каталог исключённых ссылок), context.py (внешний артефакт; см. каталог исключённых ссылок) |
| L5/L6 exact geometry coverage и multiplicity | MEASURED сейчас, из actual GPU resolution/scale; CPU integer enumeration | geometry-diagnostic.json (внешний артефакт; см. каталог исключённых ссылок), geometry_diagnostic.py (внешний артефакт; см. каталог исключённых ссылок) |
| Temporal raw share HyperNeRF 61,64–83,65%, Neu3D 64,35–82,51% | CONFIG-DERIVED; нет обученных checkpoints/actual rates этих сцен | MEMORY_AUDIT_REPORT (внешний артефакт; см. каталог исключённых ссылок) |
| ≈9782,8 B gross q8 saving и разные net по transport | PREDICTED в прежнем feasibility, не actual 6292 B | FEASIBILITY_REPORT (внешний артефакт; см. каталог исключённых ссылок) |
| Новый hashed-level context уменьшит файл/обобщится на другие сцены | UNVERIFIED; таких streams и held-out studies пока нет | Отсутствие результата, не отрицательный эксперимент |

### 2.1. Что перепроверено непосредственно в этом аудите

Локальное приложение (внешний артефакт; см. каталог исключённых ссылок) проверяет девять v2 streams: реальные lengths, SHA trailer, секции, byte-identical shared L3, независимый сохранённый repeat; existing decoded q3/q4 сверены с исходными symbols, masses с сохранёнными/повторно подсчитанными frequencies, классы — с saved canonical CPU context и transmitted edges. Три full-grid v1 streams разобраны read-only. Шесть input hashes, включая trained checkpoint, и десять source hashes actual coding совпали.

Это **не новый запуск entropy decoder**: подтверждение самостоятельного decoding process опирается на прежние fresh-process/read-audit результаты. Их Python read hook — инструмент проверки доступов данного decoder, не OS sandbox. Не следует переименовывать проверку сохранённых outputs в независимое повторное декодирование.

Путь `research/ANALYSIS_REPORT.md` отсутствует; фактический ANALYSIS_REPORT (внешний артефакт; см. каталог исключённых ссылок) расположен в `analysis_results`. Старый sampled vertex-domain interlevel analysis с raw coarse float32 и возможными repeated target slots не является доказательством decoder-available slot-level prediction. Более поздние dense pairs/feasibility/bitstream имеют другую, более строгую область.

## 3. Ограничения и научная ценность текущего результата

### 3.1. Что означает экономия 5,74%

| Величина | Проверенный размер/расчёт | Правильная интерпретация |
|---|---:|---|
| Spatial sparse standalone L3+L4 | 103272 B | Настоящий файл со всеми его секциями |
| Best Boundary standalone | 109564 B | Один и тот же набор q3/q4 symbols |
| Best IID standalone | 110640 B | Spatial экономит 7368 B |
| Общая часть L3 | 33774 B | Одинакова во всех девяти streams |
| Boundary incremental L4 | 75790 B | Включая outer framing/integrity |
| Spatial incremental L4 | 69498 B | Условная экономия 8,301887% |
| Полный raw HashGrid | 52653976 B | 50,214745 MiB; float32, не размер scene |
| Полный table8 IID HashGrid | 2815553 B | Сравнение общего бюджета, другой envelope/model granularity |

`6292/109564 = 5,742762%`; `6292/75790 = 8,301887%`. `6292/2815553 = 0,223473%` — только арифметическая иллюстрация малого абсолютного масштаба. **Нельзя вычесть 6292 из прежнего full-grid файла и объявить новый full-grid rate:** v1 использует pooled per-grid/channel fits, v2 — отдельные per-level models; общие секции и range state различаются. Нужен новый полный envelope и сопоставимый baseline.

103272 = 33774 shared + 63936 fine payload + 4505 fine probability model + 268 fine info + 112 thresholds + 677 outer framing/integrity. Fine payload уменьшился на 9852 B против Boundary, дополнительный overhead вырос на 3560 B: net 6292 B. Shared L3 = 30716 payload + 2048 model + 570 geometry + 219 quantizer metadata + 221 info. Производный CDF не передаётся второй раз.

Spatial/dense-u32 занимает 117201 B, то есть проигрывает best Boundary; packed-u16 — 107985 B. **Статистический контекст оказался полезен только вместе с оплаченной компактной сериализацией probability model.** Аналогично full-grid channel_context немного уменьшает payload, но увеличивает файл на 47592 B из-за model overhead. Это законченные результаты о механизме и ограничении; научная ценность не сводится к одному положительному проценту.

### 3.2. Что можно защищать и что нужно подтвердить независимо

Закончено техническое доказательство: decoder получает coarse symbols и side information, воспроизводит выбранные finite probabilities и точно восстанавливает fixed uint8 targets; actual range stream даёт положительный net на конкретной dense паре. Held-out screening показывает локальную predictive dependence; actual all-symbol fit подтверждает возможность scene-specific paid coding. Эти два утверждения различны.

Не доказаны: эффективность на hashed levels; выигрыш whole scene; лучшая RD curve; переносимость между CPU/GPU; generalization на новых scenes/checkpoints; самостоятельная алгоритмическая новизна; устойчивость выбора многих моделей после multiple comparisons. Три split seeds одного snapshot не равны трём training seeds или сценам.

Для независимого подтверждения нужны: новые fine levels; frozen protocol до чтения test; хотя бы второй независимо обученный checkpoint/scene на финальном этапе; независимый decoder из одного нового stream; воспроизводимая class selection; одинаковые target symbols и full cost accounting. Новое обучение для нынешнего выбора гипотезы не требуется.

Table8 уже снижает PSNR на 3,74 dB. Entropy coding фиксированных symbols добавляет нулевое искажение к quantized model, но не устраняет это исходное искажение. Успех table8 context не автоматически переносится на более качественный level8/table12. Проверка другого quantizer scope/precision нужна перед сильным практическим compressor claim.

Самый опасный ближайший источник ложного выигрыша: model узнаёт geometry-empty/default-symbol strata, а результат приписывается collision feature aggregation. Поэтому IID и geometry-only baseline обязательны.

## 4. Соотношение с научной литературой

### 4.1. Grid4D: представление, а не entropy model

Авторская [статья §§3.2–3.4](https://arxiv.org/html/2410.20815v1#S3.SS2) задаёт decomposition `(x,y,z,t)→xyz,xyt,yzt,xzt`, multi-resolution hashing и directional attention для Gaussian deformation. Обучаемые tensors — embeddings, а не условные probability tables. Напечатанные формулы разрешений в HTML и термин trilinear не заменяют computational specification: actual CUDA использует `exp2f`, `ceil` и smoothstep. Проверка исходников (внешний артефакт; см. каталог исключённых ссылок).

### 4.2. CNC: Hash Fusion уже охватывает probability aggregation

[CNC, CVPR 2024, §§3.3–3.4, Eq.(3)](https://arxiv.org/html/2406.04101v1) кодирует binary grid features, оптимизируя entropy model совместно с rendering. Для hash entry i множество spatial correspondences k даёт несколько предсказаний; в статье:

\[
p_i=\sum_{k\in S_i}w_i^k p_i^k,\qquad
w_i^k=\frac{AOE_i^k}{\sum_{j\in S_i}AOE_i^j}.
\]

`AOE` — пересечение области влияния vertex с occupied voxels; occupancy-aware веса отражают geometric support там, где занято пространство. Это не веса по fine symbol и не обычное арифметическое среднее coarse features. Context Fuser — небольшой MLP; probabilities используют coarse-to-fine восстановленные features и scalar `f_G^l`: частоту символа +1 текущего уровня. Это не learned global feature. Encoder знает эту частоту, decoder должен получить её как оплачиваемую side information; из coarse level она не следует. Bernoulli loss и binary features оптимизируются во время training. Decoder нуждается в той же entropy network, occupancy и geometric correspondence/weight specification. Подробнее с exact source anchors — CNC_SOURCE_AUDIT (внешний артефакт; см. каталог исключённых ссылок).

В official code commit `137c36595b7bad427b279cccdbb761106a39198a` encoder и decoder агрегируют outputs `context_model_3D` одними AOE weights, затем clamp в `[1e−6,1−1e−6]` и Bernoulli CDF. Между linear output и fusion в этой ветви нет sigmoid; поэтому буквально называть every raw code output probability до clamp неточно. Paper-level convex probability formula и actual implementation следует различать. Occupancy пересечения в CUDA масштабируются и приводятся к integer с усечением; valid weights clamp min1 и нормируются. CNC координатная convention `(v−0.5)/(R−2)` и interpolation не совпадают с Grid4D `v/scale` + smoothstep.

Official demo `utils_bpp_acc.py` восстанавливает coarse params, но получает `binary_vxl`, `Pgs_dict` и модели от вызывающего процесса. Найденный `.b` хранит symbol streams; standalone serialization всех этих inputs в проверенной ветви не установлена. `train_CNC_nerf_synthetic.py` считает total rate смешанно: actual hash streams, FP32 context weights, Shannon estimate occupancy и theoretical MLP precision. Это ограничение воспроизведённого **demo accounting**, а не утверждение, что научная идея недействительна. Не копировать этот смешанный budget в наш actual-file comparison. Недоступный CVF PDF заменён доступным primary arXiv HTML с supplementary; неизвестные детали отмечены в приложении.

Из CNC уже известны inter-level prior, множество correspondences на один slot, fusion предсказаний, occupancy/AOE weights, обучение probability network. Equal-weight fusion — упрощение известного механизма. Mean/std и count — общие статистические summaries, их новизна также не возникает от переименования.

### 4.3. 4DGS-CC: NVCC не является Hash Fusion

[4DGS-CC arXiv v2 §§3.2–3.5 и Appendix](https://arxiv.org/html/2504.18925v2#S3.SS4) использует multi-resolution HexPlane. NVCC conditionals имеют вид

\[
p(\bar f_t^s\mid h_t^s,\hat f_t^{s-1}),
\]

где coarse plane уже восстановлен, temporal recurrent state получает ранее восстановленный temporal feature. Eq.(1) использует cross-attention `q=Wq h_prev`, `k=Wk f_prev`, `v=Wv f_prev`, `h=softmax(qkᵀ/√d)v+f_prev`. Initial/gраничные случаи ограничиваются доступными priors; три purely spatial planes используют spatial prior. Eq.(2) — joint rate/render training.

Hyperprior `z` явно относится к VQCC codebook; отдельный NVCC hyperprior здесь не подтверждён. Hash collision fusion в NVCC не обнаружен. Не проверены portable integer CDF, bitstream syntax, coarse-plane alignment, recurrent initialization и полный weight storage. **Hash-table row `xyt` не равен temporal row HexPlane**: slot может соответствовать разным временам, поэтому причинную temporal recurrence переносить напрямую нельзя.

На 11.10.2026 официальный implementation/pretrained 4DGS-CC **не найден в проверенных публичных источниках**: arXiv/article links, доступные author pages, свежий GitHub API search. `KyungdaePark/CC-4DGS` — другая статья/авторы. Часть author pages недоступна напрямую или выдаёт JS shell, поэтому отрицательный поиск ограничен; это не доказательство отсутствия private code. Новый source audit (внешний артефакт; см. каталог исключённых ссылок), старый availability report (внешний артефакт; см. каталог исключённых ссылок) сохранён.

### 4.4. Другие непосредственные prior art

[SHACIRA, ICCV 2023 §§3.2–3.4, Appendix A](https://arxiv.org/html/2309.15848v1): learned integer latents `Z_l=d_θ(Q_l)`, shared decoder, per-dimension PMF через CDF difference, rate-distortion training. [Project→official code](https://shacira.github.io/) подтверждён. [BiRF, NeurIPS 2023 §4](https://proceedings.neurips.cc/paper_files/paper/2023/file/aebf6284fe85a8f44b4785d41bc8249a-Paper-Conference.pdf): binary features, STE, hybrid 3D/2D grids; [официальный code](https://github.com/SAITPublic/BiRF). Оба меняют training/representation и не являются matched posthoc lossless coding готовых table8 targets. Их rates без quality/target/side-info alignment нельзя объявлять хуже или лучше наших.

### 4.5. Сравнение механизмов

| Механизм | CNC | NVCC | Наш проверенный прототип | Предлагаемый следующий опыт |
|---|---|---|---|---|
| Представление/alphabet | Static NGP hash, trained binary | Dynamic HexPlane, quantized voxels | Grid4D xyz dense L3/L4, fixed uint8×2 | Fixed Grid4D hashed L5/L6 uint8×2 |
| Spatial context | Decoded coarse features, learned fuser | Decoded coarse plane | Smoothstep dequantized q3, histogram bins | Same causal lookup q4/q5 + collision-set summary |
| Несколько vertices/slot | AOE-weighted output/probability fusion | Не hash collision mechanism | Их нет в L3/L4 | Canonical vs mean vs mean+std |
| Temporal prior | Отсутствует, static scenes | Recurrent decoded temporal state | Нет | Нет |
| Occupancy | Влияет на support weights/discard | Не доказан аналог CNC AOE | Нет training occupancy | Geometry-only counts; не occupancy |
| Обучение entropy model | Joint neural/binary optimization | Joint neural/RD optimization | Encoder histogram fit, transmitted masses | Train-only histogram screening, без Grid4D retraining |
| Decoder dependencies | Weights, occupancy, correspondence, coarse decode | Weights/state/coarse plane; code неизвестен | Coarse symbols, geometry, quantizer, edges, integer masses | То же + deterministic inverse hash/aggregation |
| Actual cost evidence | Demo смешивает actual и estimates | Статья; official codec не найден | Complete subset file и exact decode | Сначала CE/overhead forecast; actual file позже |
| Новизна | Опубликовано | Опубликовано | Проверенная адаптация/engineering result | Гипотеза о cost-aware collision summary; не доказана |

## 5. Устройство HashGrid и коллизий в нашем checkpoint

### 5.1. Реальные allocation, lookup и checkpoint

Grid4D.encode_spatial/encode_temporal (внешний артефакт; см. каталог исключённых ссылок) выбирает axes четырёх encodings. Spatial normalizes coordinates относительно bound; time нормализуется для temporal triples. Feature lookup даёт xyz `[N,16×2]`, temporal triples `[N,32×2]`; последующая directional attention/MLP формирует deformation, не probabilities будущего codec. HASHGRID_MAP (внешний артефакт; см. каталог исключённых ссылок) фиксирует весь путь до Gaussian position/scale/rotation deformation.

HashEncoder allocation (внешний артефакт; см. каталог исключённых ссылок) рассчитывает `b=exp2(log2(desired/base)/(L−1))`, integer allocation `ceil(base*b**l)`, `N_l=min(2**log2_hashmap_size,prod(R_l))`, cumulative offsets. Padding до 8 в этой реализации закомментирован. Spatial: L=16, F=2, base16, desired2048, cap2¹⁹; temporal: L=32, F=2, base(8,8,8), desired(32,32,16), cap2¹⁹.

В CUDA `fast_hash/get_grid_index/kernel_grid` (внешний артефакт; см. каталог исключённых ссылок):

\[
s_{l,a}=\operatorname{exp2f}(l\log_2 b_a)B_a-1,\quad
R_{l,a}=\lceil s_{l,a}\rceil+1.
\]

Dense index — x-fast `v_x+R_x v_y+R_xR_y v_z`, пока `uint32 stride≤N_l`; иначе

\[
h_l(v)=((v_x\cdot1)\oplus(v_y\cdot2654435761)\oplus(v_z\cdot805459861))\bmod N_l
\]

с **uint32 wrapping** операций. Lookup uses `p=u*s`, floor(p), 8 corners и separable smoothstep `a=f²(3−2f)`, вес произведения a/1−a. Input вне `[0,1]^3` возвращает zero. Allocation float64 и runtime float32 могут различаться, особенно near integer resolution; offsets всегда брать из checkpoint, actual lookup resolution из подтверждённой geometry specification.

Тензоры для сжатия — `xyz_encoding.embeddings`, `xyt_encoding.embeddings`, `yzt_encoding.embeddings`, `xzt_encoding.embeddings` в `checkpoint[0]`; level slice `[offset_l:offset_{l+1},:]`. deform_model.save_weights (внешний артефакт; см. каталог исключённых ссылок) сохраняет `(grid4d.state_dict(),deform.state_dict())`. `offsets/base_resolution/per_level_scale` — reconstruction buffers; deformation network, Gaussian PLY и `cfg_args` — отдельные необходимые scene dependencies. HashGrid codec не заменяет полный checkpoint/PLY. SHA trained `deform.pth`: `3306dabf8057728abfa7cda87d78c723b27a357f968fd7d721ea727ebd043090`.

### 5.2. Exact CPU geometry: только L4–L6

В xyz dense L0–L4; hash indexing начинается L5. **Здесь реальные коллизии L5 доказаны перечислением, а не только превышением capacity.** Для L6 они также измерены. Для L7–L15 mode/hash и product>N доказывают наличие хотя бы коллизий по pigeonhole, но точные slot distributions не измерялись этим опытом.

У всех трёх temporal tables данного checkpoint dense lookup на L0–L30; hash indexing только L31. Table8 manifest (внешний артефакт; см. каталог исключённых ссылок) и prior GPU geometry фиксируют runtime resolution `(33,33,16)` при allocation `(32,32,16)` и16384 slots. Nominal product17424>16384 доказывает наличие collisions, но exact multiplicity/unused distribution temporal L31 этим аудитом не измерялась. Это следствие floating-point resolution mismatch, а не исчерпания cap2¹⁹; нельзя объявлять все temporal levels collision-heavy.

| Level | Actual resolution | Vertices nominal | Allocated slots | Nominal empty | Singleton | Colliding | Colliding/all | Max multiplicity |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| L4 | 59³ | 205379 | 205379 | 0 | 205379 | 0 | 0% | 1 |
| L5 | 81³ | 531441 | 524288 | 183592 | 199574 | 141122 | 26,916885% | 7 |
| L6 | 112³ | 1404928 | 524288 | 27888 | 86496 | 409904 | 78,182983% | 9 |

L5 средняя multiplicity по всем slots 1,01364 скрывает 41,421678% colliding **среди занятых** slots. Для L6 это 82,575342%. Нельзя оценивать collision severity только отношением vertices/capacity. XOR hash не гарантирует равномерную coverage конкретной finite lattice.

Exact nominal slot coverage (внешний артефакт; см. каталог исключённых ссылок)

Источники: CSV (внешний артефакт; см. каталог исключённых ссылок), JSON (внешний артефакт; см. каталог исключённых ссылок); vector SVG (внешний артефакт; см. каталог исключённых ссылок).

### 5.3. Correspondence, boundary и «unused»

Nominal set `S_j={v:0≤v_a<R_a,h(v)=j}` описывает все interpolation lattice corners. Point-context set `E_j={v∈S_j:v_a≤floor(s_a)}` допускает `u=v/s∈[0,1]³`. **E-empty не означает rendering-unused.** При нецелом scale верхний corner `ceil(s)` используется interpolation внутри domain, хотя его собственная vertex coordinate `v/s` выходит за domain. Ни training history, ни occupied volume этим перечислением не измеряются.

| Level | Eligible point vertices | E-empty slots | Nominal-positive, E-empty slots | Eligible colliding/all |
|---|---:|---:|---:|---:|
| L4 | 58³ = 195112 | 10267 | 10267 | 0% |
| L5 | 80³ = 512000 | 190736 | 7144 | 25,448608% |
| L6 | 111³ = 1367631 | 30945 | 3057 | 76,738167% |

Следующий основной опыт **явно использует E_j для point contexts**, а nominal sets хранит для coverage и отдельной boundary-only fallback category. Это выбранная approximation: информация upper-corner correspondences может теряться. Все arms используют одну convention, без clamp coordinates. Sensitivity к boundary support — возможный поздний контроль, не повод выбирать posthoc лучший domain.

У nominal-empty L5/L6 и E-empty L4/L5/L6 существующие table8 symbols обоих channels всегда 166. Это SINGLE-SCENE наблюдение готовых uint8 values, не разрешение удалять строки или заменять исходный float32. У colliding nominal slots доля 166 L5 ≈50,76/51,78%, L6 ≈47,96/49,08%; у singleton заметно выше. Geometry-only prior поэтому обязателен. Без него aggregation gain может быть следствием разного состава constant-background targets.

Пример реального dense mapping: L4 slot0 ↔ `(0,0,0)`, u=(0,0,0); slot58 ↔ `(58,0,0)`, `u_x≈1,01133>1`, point context zero. Для hashed L5/L6 **не существует единственной обратной vertex**: нужно инвертировать функцию на заранее заданной lattice и группировать по slot.

### 5.4. Проверки и стоимость диагностики

diagnostic-validation.json (внешний артефакт; см. каталог исключённых ссылок) PASS: три synthetic grids с independent scalar uint32 reference; 1024 indices/level, включая axis boundaries; dense L4 closed-form; суммы multiplicities/cardinalities; nominal/eligible distinction; consistency прежних sample lower bounds. CUDA geometry из mapping-validation (внешний артефакт; см. каталог исключённых ссылок) ранее проверена на GPU. **Новый GPU lookup и coarse aggregation сейчас не выполнялись.**

Enumeration L4/L5/L6 заняла 0,0506/0,1473/0,2542 s; весь диагностический запуск с input hashing — 9,03 s. Peak RSS в Windows не измерялся; scratch bounded chunks65536 и небольшими count arrays. L7–L15 вместе ≈13,84 млрд nominal vertices: грубая экстраполяция ≈48 min CPU только integer enumeration, без interpolation. Она не учитывает cache/platform и не является benchmark. Полный высокий перебор не запускался.

Зафиксированы hashes 1428 существующих входных файлов; на конце диагностики изменения отсутствуют. Скрипт защищает outputs от overwrite. Для повторения скопировать **только** `geometry_diagnostic.py` в новый sibling-каталог `research/<unique_run>/` и запустить Windows plotting Python; существующий каталог результатов не переиспользовать.

### 5.5. Decoder-available и unavailable данные

| Доступно из stream/public specification | Не становится доступным автоматически |
|---|---|
| Offset/shape/hash constants/axes/scale и domain convention | Fine-level undecoded embeddings/symbols |
| Multiplicity, nominal/E sets, canonical ordinal | Training query frequency, original float32 values |
| Уже восстановленные q coarse и переданный quantizer | Reference images/visibility/real occupancy |
| Coarse-only interpolated features, их mean/std | Fine-derived importance weights или feature-trained occupancy |
| Transmitted histogram masses/edges/model choice | Encoder train counts до их передачи |

Гистограмма может fit по fine targets на encoder и передаваться целиком; это не fine leakage в context. В held-out research evaluation fit по test labels недопустим. «Можно вычислить geometry» и «можно бесплатно вычислить geometry быстро» — разные вопросы: decoder enumeration time нужно измерить.

## 6. Кандидаты на алгоритмический вклад

### 6.1. Общие определения и бюджет

Для target row j channel c символ `q_{j,c}∈{0,…,255}`. `f_v=Lookup_{l−1}(Dequant(Q_{l−1}),u_v)∈R²`, `v∈E_j`. Coarse level L5 в паре L5→L6 **сам hashed**: lookup обращается по actual XOR slots, а не dense index. `n_j=|E_j|`. Каждый target row появляется ровно один раз; все vertices одного slot — только sources of context.

Fallback G0: nominal-empty; G1: nominal-positive/E-empty. Active strata G2: eligible singleton; G3: eligible multi. Это integer geometry, не occupancy. Для fixed-class main comparison active models получают 8 classes/channel + G0/G1, всего C=10; IID C=1 и geometry-only C=4 — простые обязательные baselines. Все используют те же targets, finite 16-bit masses, Laplace α=1 и train-only fitting. Geometry baseline определён без labels.

Dense-u16 C=10 стоит `2×10×256×2=10240 B` до header; sparse cost зависит от actual masses и в будущем должен **измеряться новым dry serializer**, а не считаться бесплатным. Нынешний `model_io.serialize/deserialize` поддерживает только C∈{1,2,9}; C10 и hashed envelope ещё не реализованы. Это план, не работающий сегодня интерфейс. Canonical8, Mean8 и Mean4×Std2 имеют C10. Secondary Mean4 имеет4 active+2 fallback, C6: она отделяет добавление dispersion от простого увеличения capacity; matched-C claim относится к трём основным feature arms. Tied edges могут сделать classes недостижимыми; отсутствие train samples не доказывает geometric unreachability.

### 6.2. A — Canonical representative

**Определение:** выбрать `v*=argmin_{v∈E_j}(v_x+R_xv_y+R_xR_yv_z)`, context `f_{v*}`; пустые множества → G0/G1. Это x-fast ordinal, не минимум hash value и не случайная vertex. Quantile8/channel превращает feature в category.

**Информация/мотивация:** одна локальная decoded coarse feature; минимальный feature storage и baseline известного spatial prior. Может быть бесполезна, если slot объединяет далёкие несовместимые regions, а lexicographic vertex нерепрезентативна. Encoder и decoder одинаково enumerate geometry и query decoded coarse; выбор не читает q fine. Требуются transmitted edges/masses и convention ID; representative table не передаётся при восстановимом rule. Enumeration ещё нужна, если нет доказанного быстрого inverse map. Для n>1 информация большинства vertices теряется; пустые slots всё равно coded.

**Prior art:** deterministic representative — естественный engineering baseline; inter-level probabilities уже CNC. **Проверяемая гипотеза:** representative превосходит geometry-only по held-out CE и net budget. **Опровержение:** нет gain сверх geometry или gain исчезает после overhead; «одна vertex работает» не доказывает superiority над aggregation.

### 6.3. B — Mean aggregation

\[
\mu_{j,c}=\frac1{n_j}\sum_{v\in E_j}f_{v,c}.
\]

**Информация/мотивация:** центральный coarse response collision set, устраняет arbitrary vertex choice. Может лучше представлять shared fine slot; может усреднить несколько modes в значение, которому не соответствует никакая region, или стать почти constant. Fine symbol — оптимизированный общий parameter, не обязательно арифметическое среднее underlying vertex features.

Encoder/decoder требуют все E vertices, decoded coarse, одинаковый reduction order/precision, train-only mean quantile edges и paid histogram masses. Дополнительная metadata мала при fixed rule; interpolation O(8·|E|) и streaming accumulators на slot, без хранения всех correspondences. n=1 совпадает с canonical, n=0 fallback; fine target не влияет на mean. Это общеизвестный summary; probability averaging CNC не равнозначно mean feature. **Гипотеза:** Mean8 лучше Canonical8 при matched C. **Опровержение:** paired held-out gain ≤0 либо budget loss. Частная победа одной seed не достаточна.

### 6.4. C — Mean + Std

\[
\sigma_{j,c}=\sqrt{\max(0,n_j^{-1}\sum_{v\in E_j}f_{v,c}^2-\mu_{j,c}^2)}.
\]

Population std, не unbiased sample estimate; при n=1 σ=0. Main class `k=2·bin4(μ)+bin2(σ)` для каждого channel, плюс G0/G1. Mean/std накопление должно иметь pinned canonical order; численно устойчивый алгоритм фиксируется до study.

**Информация/мотивация:** heterogeneity, которую mean скрывает. Если одинаковое μ при большом/малом σ связано с разным fine distribution, есть conditional information. Если coarse features почти одинаковы, σ≈0; если target определяется fine learning/visibility, σ coarse может ничего не объяснять. Equal total C означает уменьшение разрешения mean с8до4: dispersion должна компенсировать эту потерю.

Encoder/decoder используют только decoded coarse и geometry. Стоимость: 3 mean edges +1 std edge/channel вместо7 mean edges; C10 histogram budget такой же, но sparse complexity и reduction compute могут отличаться. Не добавлять n×μ×σ Cartesian grid без контроля: classes растут multiplicatively. Unused fallback одинаков с A/B, singleton zero std обрабатывается явно. **Prior art:** mean/std общие statistics, collision-set conditioning известно; самостоятельная новизна не установлена. **Гипотеза:** Mean4×Std2 beats Mean8 и Canonical8 сверх geometry на held-out при равном C. **Опровержение:** σ≈constant, gain≤0, gain лишь от capacity/empty strata, либо model overhead уничтожает net.

### 6.5. D — Collision count context

`c_j=bucket(n_nominal,n_eligible)`; first fixed buckets G0/G1/G2/G3, затем только при отдельном обосновании `n=0,1,2,3,≥4`. Count — exact integer geometry. Мотивирован измеренными distribution differences и постоянным q166 empty strata. Может быть бесполезен beyond geometry defaults или менять correlation при иной scene/training schedule.

Encoder/decoder нужны только shape/hash/scale/domain и transmitted per-class masses; coarse values не нужны. Count maps не передаются при deterministic enumeration. Metadata — bucket specification и C×2×256 masses; compute enumeration намного дешевле interpolation. Все empty targets сохраняются; нельзя заменить count training occupancy. **Prior art:** categorical/statistical prior — обычный механизм, не новый Hash Fusion. **Гипотеза:** finite count prior beats IID after full cost. **Опровержение:** entropy gain≤model bytes, нестабилен на test или исчезает при отдельной nonempty evaluation. Это выбранный backup, не доказанная замена primary.

### 6.6. E — Probability fusion

Общий shared predictor даёт categorical distribution `P_θ(a|f_v,c)`; для slot:

\[
P_j(a)=\sum_{v\in E_j}w_vP_\theta(a\mid f_v,c),\quad
w_v\ge0,\ \sum_vw_v=1.
\]

Равные weights `1/n` decoder-available; CNC-inspired AOE weights требуют support∩occupancy. Geometry support∩domain weights computable, но это **не CNC occupied-volume AOE**. Training occupancy в существующем checkpoint не подтверждена как сериализованный input; собственные coarse-derived weights — новая непроверенная surrogate гипотеза, не восстановление CNC.

**Мотивация:** смесь сохраняет modes разных vertices; `M(mean f) ≠ mean M(f)` при nonlinear predictor. Может ухудшить prediction shared optimized slot; rare-tail mixtures могут завысить entropy; weights/model expensive. Encoder/decoder нужны same shared predictor, decoded coarse, weights, canonical fusion и mass rounding; trained θ или histogram counts оплачиваются. При n=1 обычный predictor, n=0 fallback. Integer positive CDF total65536 должен совпасть exact; floating distributions allclose недостаточно.

Стоимость нельзя списать как C10: per-slot varying distribution потребует adapter к существующему class-based coder. Хранить 524288×256 distributions нельзя. Возможен streaming build integer CDF, но это отдельная реализация с time/memory budget; occupancy/model weights добавляют side information. **Prior art:** основной механизм уже CNC. **Гипотеза:** equal fusion beats mean при одном predictor capacity и full cost. **Опровержение:** no heldout gain, gain только дополнительной network capacity, либо finite CDF/weights cost уничтожает net. Сейчас не первый experiment.

### 6.7. F — две дополнительные, обоснованные гипотезы

**F1. Cost-aware regime gating.** Public geometry/coarse dispersion определяет заранее ограниченное переключение canonical↔mean↔mean+std: `c_j=F_r(j)`, `r=g(n_j,σ_j;τ)`. Мотивация — σ и collision count могут помогать только в некоторых regimes. Encoder/decoder нужны transmitted thresholds τ и separate paid models либо один bounded joint model. Gate не может выбирать для slot по его undecoded fine target. Cost включает decision rule/model partitions; n=0 fallback. Это комбинация известных summaries/model selection, потенциальная методическая цель, не установленная новизна. Проверить against лучший fixed arm при matched total bytes; опровергается отсутствием stable conditional gain или оплатой лишних partitions. В следующий primary опыт gate не включён.

**F2. Boundary-support correspondence.** Upper corners можно представлять integration points внутри их support∩domain, вместо исключения из E. `f_v=Σ_mω_m Lookup_coarse(u_{v,m})`, nodes/weights только из geometry. Основание — actual smoothstep upper corners участвуют в valid rendering, хотя v/s OOB. Encoder/decoder требуют фиксированную quadrature convention, больше queries, paid rule ID; все S vertices остаются, empty nominal fallback. Это близко к geometric support/AOE идеям CNC и требует строгого разграничения occupancy. Гипотеза — upper-corner handling улучшает heldout boundary strata; опровергается no gain послеcompute/model cost. Не кодировать/не тестировать posthoc десятки quadrature вариантов.

Обе дополнительные идеи отложены. Они не превращают нынешний audit в разработку нескольких новых методов.

## 7. Четыре узкие гипотезы и способы проверки

Cross-entropy (CE) вычислять по **positive integer masses /65536**, а не по идеальной density: `CE=−Σlog₂p(q)/N`, где N — число scalar target symbols, `ΔCE=CE_baseline−CE_candidate`. Теоретическая экономия, serializer cost и actual file length — разные результаты.

### H1. Dispersion полезна сверх mean и geometry

**Мотивация:** collision slot объединяет разные пространственные regions; среднее может скрывать heterogeneity. **H0:** Mean4×Std2 не уменьшает held-out CE сверх Canonical8 и Mean8 при одинаковом C и не даёт оплачиваемого выигрыша сверх geometry-only baseline. **H1:** dispersion даёт устойчивую дополнительную predictive information, которая сохраняется после оплаты модели.

**Минимальный эксперимент:** existing table8, две пары L4→L5/L5→L6; arms IID, geometry4, Canonical8, Mean8, Mean4, Mean4×Std2. Main feature comparison: 8 active classes/channel +2 fallback, C10. Mean4 — secondary ablation. Geometry4 имеет меньшую capacity и сравнивается с учётом полной стоимости. Split64/16/20 по fine slots, seeds0/1/2; edges/counts только train, выбор только validation, test после freeze.

**Измерения:** CE по channels/levels/geometry strata; paired gains на тех же slots; distribution σ; effective classes; serialized sparse/dense bytes; time/RSS и replay. **Compute:** CPU, без training, pilot64k vertices; ожидаются минуты, но новое aggregation время пока не измерено. Предел после пилота —30 min, RSS1GiB.

**GO:** exact coverage/replay; positive gain над Canonical8, Mean8 и geometry4 на обеих парах, одинаковый знак по трём seeds; conservative net forecast положителен. **STOP:** σ точно постоянна в объявленном arithmetic contract, extra held-out gain нет, gain объясняется empty strata/capacity или уничтожается overhead. Лишь малая величина σ не основание early STOP: она может быть информативна после binning. Если mean полезен, а σ нет — отклонить H1; это иной результат. Если помогает одна пара — сузить claim к её regime и провести независимый контроль.

**Ценность/литература:** характеристика режима полезности дешёвого collision-set summary для multi-valued posthoc targets. Общие mean/std и collision conditioning известны, CNC — прямой prior art. Positive CE само по себе не означает новый compressor.

### H2. Multiplicity даёт самостоятельный оплачиваемый prior

**Мотивация:** actual distributions singleton/multi/default strata различаются. **H0:** finer multiplicity buckets внутри multi не помогают сверх mandatory geometry4. **H1:** группы `n=2,3,≥4` добавляют information, окупающую probability masses.

**Минимальный опыт/baselines:** тот же target/split; IID, geometry4, count6 с заранее фиксированными buckets G0/G1/n1/n2/n3/n≥4. Coarse interpolation отсутствует. **Метрики:** held-out CE, serialized model bytes, constant-symbol share, exact integer count replay и CPU time. **Compute:** секунды–минуты CPU, GPU не нужен.

**GO:** устойчивый gain над geometry4, покрывающий model cost. **STOP:** эффект только от default/empty categories, finer buckets не помогают или cost больше saving. **Ценность:** простой deterministic fallback и честная граница полезности counts; novelty без дополнительного механизма ограничена. Categorical geometry priors не новая концепция. Это выбранный backup, а не доказанный новый метод.

### H3. Probability fusion лучше feature pooling

**Мотивация:** nonlinear predictor of mean и mixture per-vertex predictions различаются. **H0:** equal-weight fusion не улучшает finite held-out CE/full cost относительно mean при одном shared predictor capacity. **H1:** смесь сохраняет modes, полезные для prediction shared slot, и её стоимость окупается.

**Минимальный будущий опыт:** одна hashed пара, один train-only lightweight histogram predictor; canonical, predictor(mean) и equal fusion per-vertex predictions. Vertices не превращать в отдельные independent targets: общий вес каждого fine slot в fitting должен быть1. **Метрики:** CE до/после integer rounding, predictor/model bytes, runtime/RSS, empty/boundary outcomes. **Compute:** CPU O(vertices×256), дороже H1; streaming и pilot обязательны.

**GO:** advantage сохраняется после finite CDF/metadata и превосходит geometry. **STOP:** no gain, capacity confound, time/memory excess либо model cost уничтожает gain. Occupancy/neural model не добавлять одновременно. **Ценность:** controlled feature-vs-probability aggregation study. General probability fusion уже CNC; положительный результат Grid4D не доказывает изобретение Hash Fusion.

### H4. Более переносимый arithmetic contract сохранит полезность

**Мотивация:** в прежнем прототипе 18648 CPU/GPU class mismatches. **H0:** explicit integer/fixed-point class specification теряет net gain или не обеспечивает exact replay на заявленных platforms. **H1:** classes совпадают, predictive/net loss остаётся приемлемым.

**Минимальный отдельный опыт:** small dense/hashed batch near thresholds; pinned CPU reference, новая canonical specification, integer geometry baseline. **Метрики:** exact class mismatches, margins к edges, ΔCE/net, spec bytes, cross-process/chunk/backend equality. **Compute:** небольшая CPU/GPU проверка, без training.

**GO:** zero mismatch на объявленных supported runtimes и положительный budget. **STOP:** replay failure либо исчезновение net gain. **Ценность:** необходимый reproducibility/engineering contribution, не новизна fixed-point rounding сама по себе. H1 допускает ограниченный pinned CPU contract, но не universal portability claim.

## 8. Критическое сравнение направлений и оборудования

Среда: RTX5060 Laptop8GB, WSL2; существующий Grid4D runtime Python3.10/torch2.7+cu128. Старый context codec закрепляет NumPy1.21.6/constriction0.4.2. Текущий read-only/geometry audit — Windows Python3.12.14/NumPy1.26.4, без GPU codec. Полная environment specification — в baseline report. Качественные оценки ниже основаны на API; произвольные численные вероятности успеха не назначаются.

| Направление | Вклад и инженерная реализуемость | Нужные опыты/данные | GPU и основные риски | Значимость полного бюджета |
|---|---|---|---|---|
| A. Spatial context hashed xyz | Продолжение dense proof; mapping есть, generalized context отсутствует | Unique slots, hashed coarse lookup, held-out/cost; existing checkpoint достаточен для начала | Small parity полезен; одна scene; overlap CNC высокий | L5–L15 raw87,62%; actual rate по levels неизвестен |
| B. Feature aggregation | Дешёвый проверяемый механизм; streaming CPU реализация возможна | Canonical/mean/std matched C +geometry | Training не нужен; averaging modes/constant σ | Большой xyz охват, но gain ещё не измерен |
| C. Probability fusion | Expressive, требует per-row CDF adapter | Fair shared predictor, finite CDF/time/weights | CPU256-ary смеси дороже; CNC overlap очень высокий | Тот же xyz budget, overhead может перекрыть gain |
| D. Set statistics | μ/σ/count доступны; joint bins быстро растут | Conditional gains, effective classes, sparse costs | Selection overfit/default confound | Полезно только сверх простых baselines |
| E. Temporal tables | Axes известны; hashed time causality не решена | Geometry/IID сначала; другой checkpoint для больших temporal shares | Neural training не обязателен; прямой перенос NVCC некорректен | Здесь raw7,35%, coded components11,92%; Hyper/Neu только CONFIG-DERIVED |
| F. Determinism/compactness | Высокая реализуемость engineering работы; есть failures/cost evidence | Exact backend classes, versioned format, paid compact model | Small parity; самостоятельная scientific novelty ограничена | Защищает любой gain, сама не расширяет охват |
| G. Count/gating/boundary support | Count дешёвый backup; gate/support более speculative | Count6 vsgeometry4; gate после fixed arms; boundary ablation | Mostly CPU; support overlap с AOE | Default-heavy budget возможен, actual saving неизвестен |

Следующим выбрать B/D внутри A. C добавляет machinery при сильном prior-art overlap; E пока имеет малый текущий rate budget и новый causal problem. F нужен как correctness gate, но один refactor не решит вопрос algorithmic contribution.

После положительного результата для расширения предпочтительно искать авторский checkpoint другой scene и проверять provenance/architecture/quantizer. При его отсутствии — отдельное решение о baseline training. Сейчас HyperNeRF/Neu3D datasets не нужны; architecture shares не дают прогноз actual savings. Малый temporal budget ограничивает saving temporal tables самих, но не доказывает бесполезность их значений как cross-grid context для xyz: это не проверено.

## 9. Основная рекомендация и один запасной вариант

**Следующий опыт — H1, matched-budget collision-set dispersion study на xyz L4→L5 и L5→L6.** Canonical, mean и μ+σ — контрольные arms одного исследования. Проверяемый вопрос: объясняет ли dispersion fine-slot symbol сверх representative/mean/geometry, когда каждый symbol учтён один раз и context доступен decoder?

Почему сейчас: q8 input, checkpoint, index reference, finite masses и range engine готовы. Измерены два collision regimes. Coarse L4 dense, coarse L5 hashed — содержательный контроль усложнения. CPU tables малы; retraining/large entropy network не нужны.

Не хватает: slot→E grouping/aggregation artifacts, canonical hashed coarse lookup, fresh decoder replay, held-out models и C10 transport. **Dense V2 format не готов к hashed524288 rows/C10.** Нельзя объявить generalized method, переименовав metadata.

После опыта станет ясно, нужна ли aggregation beyond representative, где она полезна и сколько model bytes доступно. Если σ не помогает, не писать большой codec. Полезный mean при бесполезной σ — другой результат с отдельным решением, не подтверждение H1.

Fusion/neural/temporal не первые: predictor capacity, occupancy, temporal order и CDF effects сразу смешают причины. Минимальная цена отрицательного результата — одна bounded CPU study, без retraining/coding; затем STOP.

**Единственный backup — H2: finer integer multiplicity prior внутри multi slots**, а не повтор geometry4. Он дешёв, не зависит от coarse float arithmetic и имеет явное основание в данных. Если и он не окупится — оформить отрицательное сравнительное исследование, не увеличивать сложность без нового evidence.

## 10. Пошаговый экспериментальный протокол

Этапы ниже — будущие отдельные задания. Ничего не запускается автоматически этим документом. Каждый run получает уникальный каталог и explicit GO/NO-GO; completed outputs immutable. Предлагаемые новые modules `research/hashgrid_analysis/hashed_context/` и `research/experiment_bench/hashed_interlevel/` пока отсутствуют.

### Этап 0. Frozen inputs и specification

| Пункт | Конкретное действие/результат |
|---|---|
| 1. Цель | Неизменные targets, geometry convention и budget до model selection |
| 2. Входы | Checkpoint SHA; saved table8 manifest/bin; geometry JSON; allocation buffers |
| 3. Existing scripts | codec.py (внешний артефакт; см. каталог исключённых ссылок), mapping.py (внешний артефакт; см. каталог исключённых ссылок), geometry diagnostic (внешний артефакт; см. каталог исключённых ссылок) |
| 4. Реализовать | New run manifest: scope, offsets, axes, hash, scale, domain, runtime; exclusive output guard; coarse-only bundles отдельно для каждой пары |
| 5. Таблицы/графики | Manifest/hashes/indexing table; графики не нужны |
| 6. Correctness tests | SHA, q4/q5/q6 shapes/offsets, original sources unchanged, write targets только новые |
| 7. Увидеть | q4 `[205379,2]`, q5/q6 `[524288,2]`; фиксированный quantizer |
| 8. Интерпретация | Объект опыта определён; эффективности пока нет |
| 9. Решение | Допустить context extraction |
| 10. GO/NO-GO | All hashes/shapes PASS; несовпадение → STOP |

### Этап 1. Decoder-reproducible contexts, без probability fitting

| Пункт | Конкретное действие/результат |
|---|---|
| 1. Цель | Одна row/slot; canonical/μ/σ/count только из decoder inputs |
| 2. Входы | Для L4→L5 только coarse q4 bundle, для L5→L6 только coarse q5 bundle; quantizer/geometry. Whole xyz bin child не читает |
| 3. Existing scripts | Diagnostic slots/corners/lookup; dense pinned context.py (внешний артефакт; см. каталог исключённых ссылок) как numerical reference; prior GPU mapping-validation (внешний артефакт; см. каталог исключённых ссылок) |
| 4. Реализовать | Canonical hashed coarse lookup, bounded inverse enumeration, streaming μ/σ, G0/G1. Lookup float32; aggregation precision/order явно закрепить. Ascending x-fast vertex order, chunking не меняет summation order |
| 5. Таблицы/графики | Slot NPZ/CSV, multiplicity, canonical/μ/σ summaries, σ histograms/scatter, source hashes. Fine labels присоединяет parent после freeze context |
| 6. Correctness tests | Independent synthetic collisions/empty/boundary/uint32; all slots once; read audit; chunk1 только synthetic/small batch, полные arrays4096/65536 equality; fresh-process SHA; 512 GPU queries каждого coarse level |
| 7. Увидеть | Exact replay из coarse+metadata; counts совпали с аудитом; no fine reads |
| 8. Интерпретация | Nonzero σ — heterogeneity, не compression gain. E-empty не rendering-unused. GPU allclose отдельно от exact class parity |
| 9. Решение | Точно constant σ → early STOP H1; merely near-zero σ → всё равно короткий held-out study |
| 10. GO/NO-GO | Coverage/replay PASS; leak/пропуск/несовпадение → STOP всей оценки |

При global table-wise quantization min/max могли быть fit по всей таблице: они переданы и оплачены, поэтому decoder-available. Запрет fine leakage относится к недоступным target-dependent features/choices, не к легитимной transmitted quantizer metadata.

### Этап 2. Held-out usefulness

| Пункт | Конкретное действие/результат |
|---|---|
| 1. Цель | Проверить H1 на untouched symbols при matched feature capacity |
| 2. Входы | Frozen contexts +existing q5/q6, одинаковые fine row IDs |
| 3. Existing scripts | feasibility/core.py (внешний артефакт; см. каталог исключённых ссылок): fit_edges/fit_histogram/costs/bootstrap; models.frequencies (внешний артефакт; см. каталог исключённых ссылок) |
| 4. Реализовать | Slot split64/16/20 seeds0/1/2; все preimages и оба channels в одном split; six arms H1. Train-only edges/masses, validation selection, freeze, test один раз |
| 5. Таблицы/графики | Split hashes, edges/masses, CE по arms/levels/channels/strata, occupied classes, paired gains/σ plots |
| 6. Correctness tests | Same targets/N/order; disjoint slots; vertex duplication не target rows; positive CDF для unseen classes; decoder exact classes после передачи edges |
| 7. Увидеть | Mean4Std2 против Mean8/Canonical8/geometry4, обе пары и worst seed, G0/G1/G2/G3 отдельно |
| 8. Интерпретация | Within-checkpoint predictability. Shared decoded coarse допустим; random slots не пространственно независимы. Bootstrap exploratory/conditional-on-fit, seeds не независимые scenes |
| 9. Решение | Выбрать frozen arm по validation либо отклонить H1; изменения после test → новый опыт |
| 10. GO/NO-GO | Stable positive incremental dispersion gain; no gain → STOP H1. Любая causality failure → STOP study |

На hashed slots naive spatial block split по canonical representative не гарантирует independent spatial holdout: другой preimage того же slot далёк. Более сильный контроль может группировать graph components по shared coarse neighbours, но hash aliases могут создать огромные components. Его независимость/стоимость надо проверить отдельно, не обещать автоматически.

### Этап 3. Model/metadata cost, без actual coding

| Пункт | Конкретное действие/результат |
|---|---|
| 1. Цель | Отделить CE gain от оплаченной стоимости модели |
| 2. Входы | Frozen arm, integer masses/edges, scores/counts |
| 3. Existing scripts | model_io.serialize/deserialize (внешний артефакт; см. каталог исключённых ссылок) как exact transport reference; поддерживает лишь C1/2/9 |
| 4. Реализовать | Isolated versioned bounded-C dry serializer; threshold/runtime/geometry sections. Старый format не менять, entropy encoder не запускать |
| 5. Таблицы/графики | Actual model/metadata section bytes и roundtrip; break-even table; forecast payload, actual stream=null |
| 6. Correctness tests | `[2,C,256]` positive masses/sum65536; exact roundtrip; omission только proven unreachable; CDF не double-count; same coarse budget |
| 7. Увидеть | `ΔB_pred≈N_full·ΔCE_test/8−ΔB_side`, label PREDICTED. Sparse bytes измерены; payload estimate не файл |
| 8. Интерпретация | Test→full-scene перенос и range overhead неизвестны; equal C не equal sparse bytes. Будущий full-scene refit меняет models |
| 9. Решение | Только при cost-covered gain запросить отдельный actual experiment |
| 10. GO/NO-GO | Exact replay PASS; gross forecast >extra side bytes +max(4096B,20%extra side bytes); иначе STOP/новый меньший model study |

Этот safety margin — заранее выбранный инженерный критерий расхода времени, не statistical law. Full-scene fit/actual code не подменять extrapolation.

### Этап 4. Actual bitstream — отдельная задача после GO

| Пункт | Конкретное действие/результат |
|---|---|
| 1. Цель | Проверить actual net и independent exact decode |
| 2. Входы | Explicit GO этапов1–3; frozen arm, original uint8 targets encoder/validation parent only |
| 3. Existing scripts | entropy.encode_indexed/decode_indexed (внешний артефакт; см. каталог исключённых ссылок): symbols/classes `[N,2]`, masses `[2,C,256]`; format.py (внешний артефакт; см. каталог исключённых ссылок) dense V2 только как reference |
| 4. Реализовать | Новый hashed schema/version, coarse IID shared section, fine payload/model/metadata. L5→L6 coarse L5 coded IID независимо от нового L4→L5 codec |
| 5. Таблицы/графики | Matched baseline/candidate streams, section bytes, decoded SHA/read audit/repeat, runtime/RSS/report |
| 6. Correctness tests | Child читает один.bin+code/libs, не checkpoint/export/context/targets; all rows×channels exact; malformed input tests; independent repeat bytes |
| 7. Увидеть | Complete actual file length, gain против лучших storage вариантов baselines; cold/warm timing отдельно |
| 8. Интерпретация | SINGLE-SCENE pair result. Exact entropy reconstruction не устраняет quantizer distortion; full scene требует all4 tables/PLY/deformation |
| 9. Решение | Positive → отдельный independent checkpoint/control; negative → объяснить/STOP candidate |
| 10. GO/NO-GO | All tests PASS и actual net positive против лучших IID, geometry4 и Canonical8/Mean8 baselines; каждый gain>0 (`min(gains)>0`), не старый `max` |

### 10.1. Compute и сроки

| Работа | Измерение или прогноз | Предел |
|---|---|---|
| Integer L4–L6 diagnostic | MEASURED9,03s с hashing; enumeration0,452s | CPU, no VRAM; peak RSS не измерен |
| Context extraction | UNMEASURED; pilot64k, ожидаются секунды–минуты | Chunk≤65536, RSS≤1GiB, estimated compute≤30min; иначе отчёт/STOP |
| Held-out histogram study | PREDICTED несколько минут CPU | Не создавать N×C×256 probability tensor; RSS≤1GiB |
| Optional GPU parity | Tiny batch, без training | Actual VRAM измерить; planned working data малы, overhead torch/context отдельно; 8GB не целевой allocation |
| Dry model budget | Секунды–минуты CPU | Serialization only |
| Actual codec | Оценка только после pilot нового context path | Не переносить скорость dense benchmark на hashed aggregation |
| Implementation/review | Предварительно1–2 рабочих дня для этапов0–3, отдельный день для container/tests | Engineering estimate, не обещание Codex wall time и не GPU hours |

Прежние best dense encoder≈0,233s/decoder≈0,189s, CPU peak551,6MiB относятся к warm protocol; imports/IO не включены. В hashed path дороже aggregation и enumeration, их время оплачивается. Обучение больших entropy networks/full Grid4D здесь не требуется. Проценты Codex5h/week из compute не выводились.

## 11. Как исследователь принимает решения по результатам эксперимента

**Все сценарии и числа ниже вымышлены. Это учебные примеры, не новые результаты проекта.**

| Сценарий | Значение и допустимый вывод | Недопустимый вывод | Следующий тест / когда остановиться |
|---|---|---|---|
| Collisions0,2% | Collision mechanism имеет малый охват данной пары | Hash grids никогда не коллидируют | Другой уровень с budget; STOP здесь, если maximum gain мал |
| Collisions60%, σ≈0 у99% sets | Coarse contexts почти одинаковы, dispersion неинформативна | Fine features тоже одинаковы, сжатие невозможно | Count/correlation; STOP Std addition |
| Collisions60%, широкая σ | Mean скрывает heterogeneity | Std точно уменьшит entropy | Conditional CE; STOP при no fine prediction gain |
| Std gain0,04b/s при equal C | Есть predictive increment; при1m symbols gross≈5kB | Файл уже уменьшился на5kB | Serializer/actual coder; STOP при excessive overhead |
| CE gain6kB, model+9kB | Лучше prediction, хуже net на3kB | Лучший compressor | Compact/smaller model новый study; STOP без окупаемости |
| Fusion лучше mean, same predictor | Mixture сохраняет полезные modes | Мы изобрели Hash Fusion | Finite CDF/runtime/paid weights; CNC prior art; STOP при cost loss |
| Никто не лучше Canonical8 | Эти summaries не дают extra information | Все collision-aware методы всегда бесполезны | Зафиксировать negative result, count backup; STOP complexity без нового evidence |
| Gain только G0 | Обнаружены constant defaults | Полезна dispersion coarse features | Geometry baseline; STOP collision-feature claim |
| L5 gain+, L6 gain− | Механизм зависит от режима/coarse hashing | Средний gain доказывает universality | Сузить scope и independent control |
| Decoder class различается на1row | Probability selection не exact | Float error1e−7 не важна | Исправить canonical contract; STOP coding/efficacy до PASS |

Отрицательный результат с контролями — знание о границах механизма. Он не обязывает строить более сложную сеть. Цель опыта — получить решение, не положительный процент любой ценой.

## 12. Угрозы достоверности и контроли

| Риск | Техническая проверка |
|---|---|
| Разные target symbols/scopes | Один readonly table8; level SHA, same N/order/channels; не requantize |
| Fine leakage в context | Coarse-only child bundles/read audit; target join после freeze; representatives/weights не fine-derived |
| Test labels в fitting | Train-only edges/counts. All-scene fit разрешён лишь как paid scene-specific actual codec, отдельно от held-out evidence |
| Model overhead забыто | Все section bytes/final file; weights/occupancy/edges/header/checksum/runtime оплачены; derived CDF один раз |
| Неправильная vertex/index | Actual scale/offset/hash uint32, scalar/GPU parity; v/scale, не v/(R−1); canonical rule заранее |
| Повторное coding slot | IDs ровно arange(N), оба channels; vertices — context sources, не targets |
| Empty/boundary rows пропущены | All allocated rows; nominal/E/support различать; deletion не разрешена |
| Float thresholds | Exact fresh class SHA/chunk parity/right-edge rule; allclose не gate |
| Leakage через hash aliases | Split по fine slot, все preimages/channels вместе; random vertex split запрещён |
| Shared coarse объявлен независимым | Context доступен всем arms, но correlation/CI limitations явно описать; spatial independence не доказана |
| Tune на test/multiple comparisons | Six arms заранее, validation choice, test once; новый arm → новый study |
| Capacity confound | Main Mean8 vsMean4Std2 C10; Mean4 secondary; actual sparse cost/effective classes отдельно |
| Default symbol confound | IID+geometry4, G0/G1/G2/G3 отдельно, extra dispersion effect внутри multi |
| Одна сцена → universal claim | SINGLE-SCENE; новые levels, independent scene/quantizer нужны позже; seeds не scenes |
| Entropy estimate → actual bytes | PREDICTED label, stream=null до coding; старый levels.csv payload_bytes — raw container |
| Нечестное CNC/NVCC сравнение | Binary/RD/HexPlane ≠ fixed posthoc uint8; matched targets/quality/side-info до SOTA claims |
| Quantization distortion скрыта | Float32/table8/level8 quality отдельно; entropy exact не восстанавливает float32 качество |
| Compute измерен частично | Enumeration/context/model/IO/cold startup оплачены; warm dense speed не forecast |
| Старые outputs потеряны | Fresh exclusive output, hashes before/after, no old workflow writing commands |

Два findings оставлены без правки прежнего кода. workflow.py:170 (внешний артефакт; см. каталог исключённых ссылок) использует `max(gain_iid,gain_boundary)>0`: победа хотя бы над одной baseline. Для обеих нужен `min>0`. Текущие оба gains положительны, прежний вывод верен. Некоторые `gate/validate/benchmark/finish` могут писать fixed filenames в existing output; старые README examples для завершённых outputs не запускать. Новый adapter должен иметь exclusive guard.

## 13. Три уровня формулировки новизны

### A. Подтверждённый результат сейчас

«Для обученного Grid4D bouncingballs-reference-50000 реализовано и проверено постобучающее lossless coding фиксированных table-wise uint8 symbols collision-free пары xyz L3/L4. Decoder использует восстановленный coarse level и переданные metadata. Spatial-8/sparse-u16 уменьшил standalone pair file с109564 до103272 B против лучшего Boundary baseline с exact reconstruction. Установлены существенная роль compact model storage и ограничение floating-point context reproducibility».

Это экспериментальный/engineering результат одной сцены, **не доказанная общая алгоритмическая новизна** и не5,74% всего Grid4D.

### B. Потенциальная научная новизна — пока гипотеза

«Исследовать ограниченный по стоимости decoder-reproducible summary spatial correspondences одного HashGrid slot, использующий coarse-feature dispersion для categorical post-training prediction неизменных quantized targets. Установить collision/dispersion regimes, где added information окупает probability-model metadata, и отделить её от geometry priors».

Новизна может появиться в конкретном **cost-aware selection mechanism и доказанном режиме**, а не в стандартной Std. Пока механизм не реализован/подтверждён. Если единственная добавка — μ+σ, корректнее говорить об ablation/adaptation даже при positive gain.

### C. Условный итог магистерской

«Предложен и исследован постобучающий контекстный метод кодирования многосимвольных HashGrid-параметров поля деформаций, причинно воспроизводимо агрегирующий coarse correspondences с учётом multiplicity/dispersion при ограничении стоимости модели. На нескольких hashed levels и независимых сценах показано снижение полного bitstream против IID, geometry-only, canonical и mean baselines при exact restoration одинаковых quantized tensors; установлены режимы применимости и случаи отсутствия выигрыша».

Только при выполнении условий: H1/иной заранее зафиксированный механизм; actual bytes и independent decoder; как минимум две пары и две независимые сцены/checkpoints; untouched test; другие quantizers/quality budgets; fair probability-fusion ablation; полный HashGrid container/render parity; complete cost/time; повторный поиск поздней литературы. Две сцены — минимальный контроль, не гарантия универсальности.

Различие с CNC: fixed multi-valued posthoc symbols вместо binary joint RD training, exact all allocated symbols без occupancy discard, bounded histograms/model budget, specified decoder arithmetic. Эти различия сами не доказывают superiority/novelty. Нужен содержательный mechanism beyond platform transfer.

Если summaries не превосходят representative после оплаты, допустима магистерская как rigorous comparative negative study/reproducible bench/границы механизма; нельзя обещать несуществующий эффективный compressor.

## 14. Формулировка для научного руководителя

«Baseline Grid4D и post-training range codec получены. На одной dense паре условный context даёт реальный6,3КБвыигрыш, но это малая часть модели и адаптация известного prior. Geometry показала разные collision regimes L5/L6. Предлагаю проверить, добавляет ли dispersion восстановленных coarse features информацию о shared fine symbol сверх representative, mean и geometry. Опыт без retraining: matched class budget, fine-slot held-out, independent context replay, model cost. Positive result разрешит отдельный bitstream test; negative ограничит направление и оставит count-only backup. Новизну будем формулировать после ablations и независимой сцены, не присваивая известный CNC fusion».

## 15. Три готовых промпта для отдельных сессий Codex

Новые proposed modules отсутствуют сейчас: это явная часть задания. WSL paths преобразовать из абсолютных Windows paths; native plotting env не содержит автоматически torch/constriction. Старые outputs не менять.

### Промпт 1 — minimal diagnostic и decoder contexts

```text
В <PROJECT_ROOT> выполни только этапы0–1 research\RESEARCH_DIRECTION_DECISION.md
для xyz L4→L5 иL5→L6. Прочитай AGENTS.md. Создай новый уникальный каталог
research\hashed_context_diagnostic_<date>_<run> с exclusive output guard.
Не перезаписывай предыдущие отчёты, CSV/JSON/plots и direction_audit_20261011_01.

Входы:
<PROJECT_ROOT>\outputs\grid4d\bouncingballs-reference-50000\deform\iteration_50000\deform.pth
SHA3306dabf8057728abfa7cda87d78c723b27a357f968fd7d721ea727ebd043090;
<PROJECT_ROOT>\research\experiment_bench\reference-study\table-8\manifest.json
и xyz_encoding.u8.bin;
<PROJECT_ROOT>\research\direction_audit_20261011_01\geometry-diagnostic.json;
<PROJECT_ROOT>\research\analysis_results\mapping-validation.json.
Сначала проверь наличие, SHA, quantizer scope, offsets и actual scale.
Не выполняй новое quantization. Parent подготовит coarse-only bundle каждой пары;
context child не читает целый xyz bin/checkpoint/fine targets.
Для L4→L5 child имеет только q4; для L5→L6 только q5, плюс metadata.

Используй research\grid4d\codec.py dequantize и research\hashgrid_analysis\mapping.py
slots/corners/lookup как reference. Проверяй actual CUDA
external\Grid4D-audit-clean\hashencoder\src\hashencoder.cu.
experiment_bench\interlevel\context.py dense-only: coarseL5 требует нового canonical
hashed lookup adapter в research\hashgrid_analysis\hashed_context\.

На каждый allocated fine slot сохрани ID, nominal/E counts, geometry category,
minimum x-fast eligible representative, canonical coarse features, mean/population std
обоих channels. E vertices: v<=floor(actual scale), u=float32(v)/float32(scale), без clamp.
S nominal — вся R lattice. E-empty — chosen point-context fallback, не rendering-unused.
G0 nominal-empty/G1 nominal-positive,E-empty; все slots учесть ровно один раз.
Fine symbols присоединяет parent отдельно после context freeze.
Зафиксируй lookup float32 stages и aggregation precision/order; chunk invariance.

Нужны independent synthetic collisions/empty/boundary/uint32 tests, all-slot coverage,
fresh-process context replay/read audit без original checkpoint/fine inputs,
chunk1 только small synthetic batch, full arrays4096/65536 parity,
small GPU lookup parity512 queries/coarse level.
GPU allclose отдельно от exact context classes; GPU не подменяет codec CPU arithmetic.
Повторный expensive xyzL7–15 enumeration не запускать.
Pilot64k vertices, processRSS≤1GiB, estimated compute≤30min; превышение → отчёт/STOP.
Не fit probability models, не code, не train/render/download.
Сохрани NPZ/CSV, σ diagnostics/scatter, hashes и новый DIAGNOSTIC_REPORT.md.
После проверок STOP: correctness и dispersion, без вывода compression gain по графикам.
```

### Промпт 2 — held-out H1 и model overhead

```text
В <PROJECT_ROOT> выполни этапы2–3 research\RESEARCH_DIRECTION_DECISION.md
только после DIAGNOSTIC_REPORT первого задания с coverage/replay PASS.
Сначала найди его новый unique output и проверь manifest/hashes. Если данных нет,
не подменяй их dense xyz34 pairs: сначала выполнить diagnostic или сообщить gap.
Прочитай AGENTS.md; новый research\hashed_dispersion_heldout_<date>_<run>, exclusive guard.

Fixed targets — reference-study\table-8\xyz_encoding.u8.bin, без requantization.
Две пары L4→L5/L5→L6. Freeze six arms:
IID; geometry4(G0 nominal empty/G1 nominal positive,E empty/G2 E singleton/G3 E multi);
Canonical8; Mean8; Mean4 secondary ablation; Mean4×Std2.
Canonical8/Mean8/Mean4Std2:8 active classes/channel +G0/G1, C10;
secondary Mean4:C6, geometry baseline:C4, IID:C1.
Mean4Std2 class=2*mean_bin4+std_bin2; singleton population std0.
Одинаковые geometry convention/rows/symbols во всех arms.
Split64/16/20 seeds0/1/2 по fine slot; оба channels и все preimages в одном split.
Random vertex split запрещён. Train-only edges/counts, validation choice, freeze,
test один раз. Fine-derived representatives/weights запрещены.

Reuse research\hashgrid_analysis\xyz34_feasibility\core.py fit_edges/fit_histogram/costs
через новый slot adapter и research\experiment_bench\models.py frequencies α1,
positive16-bit masses. Старый spatial vertex split не доказывает независимость collisions.
Измерь finite CE по channels/levels/strata, paired gains, effective classes,
stability3 seeds и exploratory conditional bootstrap limitations.
Fresh decoder из coarse+metadata+train edges воспроизводит exact classes.
Shared coarse context across splits допустим; spatial independence не claim.

Для budget создай isolated versioned bounded-C dry serializer:
experiment_bench\interlevel\model_io.py сейчас C∈{1,2,9}, неC10.
Reuse exact dense/packed-u16/sparse masses principle, positive/sum65536/roundtrip tests.
Измерь models/edges/metadata bytes. Entropy encoder не запускать;
ΔB_pred=N_full*ΔCE_test/8−ΔB_side label PREDICTED, actual stream=null.
GO: exact replay/coverage, stable MeanStd advantage над Mean8/Canonical8/geometry
на обеих парах, gross forecast>extra side bytes+max(4096B,20%extra side bytes).
Если std не помогает, отклонить H1; mean result отдельно, coding автоматически не начинать.
Сохрани splits/SHAs/models/CSV/plots и новый HELDOUT_REPORT.md с GO/NO-GO.
No training/new quantization/download/neural entropy/coding; после отчёта STOP.
```

### Промпт 3 — actual coding только после отдельного GO

```text
В <PROJECT_ROOT> начать stage4 research\RESEARCH_DIRECTION_DECISION.md
только при explicit GO HELDOUT_REPORT и exact replay всех предыдущих gates.
Сначала найди/проверь unique output/frozen arm/SHA; absent/NO-GO → STOP с объяснением.
AGENTS.md; новый research\hashed_interlevel_bitstream_<date>_<run>, exclusive guard.
Не менять upstream Grid4D и завершённый dense V2 experiment.

Reuse research\experiment_bench\entropy.py encode_indexed/decode_indexed:
symbols/classes(N,2), positive uint32 masses(2,C,256), total65536, constriction0.4.2;
channel0 все ascending rows, затем channel1 все ascending rows.
Создать separate research\experiment_bench\hashed_interlevel\ adapter/schema.
Existing interlevel\format.py/workflow.py hardcode dense xyzL3/L4/table8;
model_io C1/2/9, поэтому hashed rows/C10 нужен явный новый versioned format.
Decode coarse IID shared bundle прежде fine. Для L5→L6 coarseL5 coded IID автономно,
не зависеть от нового L4→L5 codec. Передать geometry/hash/scale/axes/offsets,
domain/arithmetic spec, quantizer, edges, masses, version/runtime/checksum.
Сохранить все allocated fine symbols ровно один раз; no pruning.

Сравнить одинаковые targets с best IID, geometry и best simple feature baseline;
проверить storage варианты для честного full cost. All-target histogram refit допустим
как scene-specific paid codec: явно отделить его от held-out phase.
Context только restored coarse/public metadata; no free occupancy/weights.
Оплатить payload+models+edges+coarse+metadata+framing; actual filesystem lengths.
Не распространять старый5.74% на full Grid4D.

Independent fresh decoder читает один.bin+code/libs, без checkpoint/export/contextNPZ/
fine targets. Read audit, exact decoded symbols/SHA, all-slot coverage, malformed tests.
Independent повтор в другом новом output должен дать byte-identical streams.
Cold startup/IO и warm timing отдельно; CPU/RSS/optional VRAM measured.
GO только allPASS и positive net против лучших IID, geometry4, Canonical8/Mean8
baselines: каждый gain>0, min(gains)>0, не max criterion прежнего workflow.
Pair stream не full renderable scene. Если нужен full scene parity, сначала явно собрать
все4 tables через codec.substitute с unchanged buffers/deformation/PLY и existing
bouncingballs bundle; отдельная проверка, без нового training.
Сохрани streams/components/read audit/repeat/runtime/new BITSTREAM_REPORT.md;
после отчёта STOP. Не начинать new scene/neural/temporal pipeline автоматически.
```

## 16. Источники и сохранённые артефакты

### 16.1. Первичные источники

1. Xu J. et al. **Grid4D**, NeurIPS2024. [Статья](https://arxiv.org/abs/2410.20815), [HTML](https://arxiv.org/html/2410.20815v1), [project](https://jiaweixu8.github.io/Grid4D-web/), [official code](https://github.com/JiaweiXu8/Grid4D). Computational specification — actual local commit/code, не HTML shorthand.
2. Chen Y., Wu Q., Harandi M., Cai J. **How Far Can We Compress Instant-NGP-Based NeRF?**, CVPR2024. [Article+supplementary](https://arxiv.org/html/2406.04101v1), [CVF](https://openaccess.thecvf.com/content/CVPR2024/html/Chen_How_Far_Can_We_Compress_Instant-NGP-Based_NeRF_CVPR_2024_paper.html), [project](https://yihangchen-ee.github.io/project_cnc/), [official commit](https://github.com/YihangChen-ee/CNC/tree/137c36595b7bad427b279cccdbb761106a39198a). CVF PDF403, primary HTML доступен; runtime не запускался.
3. Chen Zicong et al. **4DGS-CC: A Contextual Coding Framework for 4D Gaussian Splatting Data Compression**, arXiv2504.18925v2,2025. [Статья](https://arxiv.org/abs/2504.18925), [HTML](https://arxiv.org/html/2504.18925v2). Venue beyond preprint не установлен аудитом; public official implementation/checkpoints не найдены в проверенных источниках11.10.2026.
4. Girish S., Shrivastava A., Gupta K. **SHACIRA**, ICCV2023. [Статья](https://arxiv.org/html/2309.15848v1), [project](https://shacira.github.io/), [official code](https://github.com/Sharath-girish/Shacira).
5. Shin S., Park J. **Binary Radiance Fields**, NeurIPS2023. [Primary paper](https://proceedings.neurips.cc/paper_files/paper/2023/file/aebf6284fe85a8f44b4785d41bc8249a-Paper-Conference.pdf), [official code](https://github.com/SAITPublic/BiRF).

Выборка релевантна, но не доказывает полноту literature search до2026. Новизна требует повторного поиска перед финальным claim. Недоступные детали отмечены; implementation не заменялась догадкой.

### 16.2. Старые материалы, оставленные доступными

- BASELINE_GRID4D (внешний артефакт; см. каталог исключённых ссылок), HASHGRID_MAP (внешний артефакт; см. каталог исключённых ссылок), PHASE2_REPORT (внешний артефакт; см. каталог исключённых ссылок): installation/training/export/quantizer.
- EXPERIMENT_BENCH_REPORT (внешний артефакт; см. каталог исключённых ссылок), bench CLI (внешний артефакт; см. каталог исключённых ссылок): full-grid/quality experiments.
- ANALYSIS_REPORT (внешний артефакт; см. каталог исключённых ссылок), levels.csv (внешний артефакт; см. каталог исключённых ссылок), GPU mapping-validation (внешний артефакт; см. каталог исключённых ссылок): diagnostics; levels payload_bytes — raw container.
- Pairs REPORT (внешний артефакт; см. каталог исключённых ссылок), pairs.npz (внешний артефакт; см. каталог исключённых ссылок), FEASIBILITY_REPORT (внешний артефакт; см. каталог исключённых ссылок), BITSTREAM_REPORT (внешний артефакт; см. каталог исключённых ссылок): разные области evidence.
- MEMORY_AUDIT_REPORT (внешний артефакт; см. каталог исключённых ссылок):40 checkpoint files/copies,24 scene configs+default,12 parameter architectures,47 hypothetical variants. Copies не independent scenes; config/hypothetical не actual compressed rate.
- Table8 manifest (внешний артефакт; см. каталог исключённых ссылок), xyz uint8 (внешний артефакт; см. каталог исключённых ссылок): saved future targets. SHA bin `b6f2676efa4c33d0cf2506271bafe0db0b133d05baeabaeb07eca8e47e939de8`.
- AGENTS.md (внешний артефакт; см. каталог исключённых ссылок): постоянное требование сохранности прежних результатов.

### 16.3. Новое evidence настоящего аудита

- LOCAL_EVIDENCE_AUDIT.md (внешний артефакт; см. каталог исключённых ссылок), JSON (внешний артефакт; см. каталог исключённых ссылок): численные read-only checks/API/findings.
- CNC_SOURCE_AUDIT.md (внешний артефакт; см. каталог исключённых ссылок), cnc_sources.json (внешний артефакт; см. каталог исключённых ссылок): official source anchors, decoder/budget limits.
- NVCC_SOURCE_AUDIT.md (внешний артефакт; см. каталог исключённых ссылок), NVCC_sources.json (внешний артефакт; см. каталог исключённых ссылок): primary references и fresh code availability.
- geometry_diagnostic.py (внешний артефакт; см. каталог исключённых ссылок), JSON (внешний артефакт; см. каталог исключённых ссылок), CSV (внешний артефакт; см. каталог исключённых ссылок), validation (внешний артефакт; см. каталог исключённых ссылок): новый CPU integer diagnostic; aggregation/entropy fit/coding не выполнялись.
- Input hashes (внешний артефакт; см. каталог исключённых ссылок):1428 защищённых старых файлов; final-validation.json (внешний артефакт; см. каталог исключённых ссылок): final preservation/links/report-copy checks.

Запрошенный research/RESEARCH_DIRECTION_DECISION.md (внешний артефакт; см. каталог исключённых ссылок) создаётся впервые. Идентичный snapshot — в unique audit directory. Будущий пересмотр: сначала archive copy с verified SHA или новый dated report; старое evidence остаётся неизменным.
