> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# CNC: проверка первоисточников и границ переноса в Grid4D

Дата аудита: 2026-10-11. Статус: **SOURCE VERIFIED; CNC RUNTIME NOT RUN**.

Это отдельный источниковый аудит. Старые документы и результаты не изменялись. Дatasets, checkpoints и зависимости CNC не скачивались; обучение не запускалось. Исходники читались через GitHub. Этот документ не является воспроизведением численных результатов CNC.

## 1. Официальность и закреплённая версия

Работа: Yihang Chen, Qianyi Wu, Mehrtash Harandi, Jianfei Cai, *How Far Can We Compress Instant-NGP-Based NeRF?*, CVPR 2024.

Официальность репозитория подтверждена ссылками из [страницы CVPR](https://openaccess.thecvf.com/content/CVPR2024/html/Chen_How_Far_Can_We_Compress_Instant-NGP-Based_NeRF_CVPR_2024_paper.html) и [project page первого автора](https://yihangchen-ee.github.io/project_cnc/). Репозиторий: [YihangChen-ee/CNC](https://github.com/YihangChen-ee/CNC).

Проверенный live `main`: **137c36595b7bad427b279cccdbb761106a39198a**. SHA получен через [GitHub commits API](https://api.github.com/repos/YihangChen-ee/CNC/commits/main); пути и Git blob hashes проверены через tree API. В приведённых ниже ссылках используется этот commit, а не изменяемый `main`.

[arXiv HTML v1](https://arxiv.org/html/2406.04101v1) доступен и содержит статью вместе с Supplementary Material A–C. Официальные CVF PDF/supplemental URL при непосредственном открытии возвращали HTTP 403; это ограничение доступа в данном аудите, а не отсутствие supplementary.

## 2. Проверенные положения статьи

Краткая карта с точными разделами; формула ниже непосредственно соответствует статье, а не предлагаемому алгоритму проекта.

- §3.2, Eq.(2): бинарные признаки `−1/+1`, Bernoulli и дифференцируемая оценка битов.
- §3.3, Fig.2: coarse-to-fine; контекст интерполируется в пространственной вершине из уже декодированных уровней; добавляется частота `f_G` текущего уровня.
- §3.4, Fig.3, Eq.(3): один slot может соответствовать нескольким вершинам. Для каждой строится прогноз; объединяются **вероятности**, с весами по Area of Effect.

\[
p_i=\sum_{k=1}^{K}w_i^k p_i^k,
\qquad w_i^k=\frac{AOE_i^k}{\sum_{j=1}^{K}AOE_i^j}.
\]

AOE связывает область влияния вершины с occupied cells; при отсутствии действительных вершин статья допускает исключение соответствующего параметра.

- §3.5: dimension-wise context идёт от 3D к пространственным 2D tri-planes через projected voxel features; это не временной контекст.
- Eq.(4): оптимизация сочетает image MSE и entropy loss; метод изменяет обучаемое представление.
- Supplementary A: inverse mapping строится перечислением вершин; Context Fuser и rendering MLP входят в систему; описана 13-битная квантизация rendering MLP.

Источник: [статья и supplementary](https://arxiv.org/html/2406.04101v1#S3).

## 3. Что непосредственно подтверждает официальный код

### 3.1 Probability fusion и причинный decoder

Источник: [examples/utils_bpp_acc.py](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/examples/utils_bpp_acc.py).

`CNC_context_models.__init__` строит `pos_grid_sorted_list`, `unique_value_list`, `unique_count_list` и cumulative offsets для группировки пространственных preimages по hash slot. `context_model_3D` содержит три Linear слоя и две LeakyReLU.

В `encode_binary_vxl_mixPg_3D2D`, [L811–854](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/examples/utils_bpp_acc.py#L811), сначала вычисляется контекст каждого действительного vertex, затем output MLP группируется `align_and_pack`, взвешивается AOE и суммируется. Это не усреднение coarse feature перед MLP. Реальный output MLP не ограничивается sigmoid: после fusion применяется clamp перед Bernoulli CDF.

`decode_binary_vxl_mixPg_3D2D`, [L937–978](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/examples/utils_bpp_acc.py#L937), повторяет grouping/weighting, читая coarse через `outspace_params=params_q_xyz_rec`. Восстановленные symbols записываются по `hash_indices_n_masked`.

`encoder`/`decoder` используют `torchac` с бинарным CDF; `Bernoulli_entropy.forward` оценивает соответствующую NLL. `get_pn_embed_frac` участвует в 3D→2D projection. Encoder возвращает `Pgs_dict`; decoder принимает его отдельным аргументом вместе с occupancy и Encoding objects. Таким образом, `.b` не содержит весь необходимый state.

### 3.2 AOE в CUDA и отличие от идеализированной формулы

Источник: [my_cuda_backen/aligner_kernel.cu, L162–241](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/my_cuda_backen/aligner_kernel.cu#L162), `query_mask_3D_kernel_3D`.

Для integer vertex `v` координата равна `(v−0.5)/(R−2)`. Область влияния — box с полушириной `1/(R−2)` по каждой оси. Kernel перечисляет пересекающиеся occupancy cells и суммирует объёмы пересечений с занятыми cells. Выход AOE масштабируется на `Rb³×1000` и приводится к integer. Выход validity mask задаётся OR проверенных occupied cells.

Это **объём в 3D**, хотя имя переменной содержит area. Описывать его как число colliding vertices или простое число occupied cells неверно. Bool mask и integer AOE являются разными выходами; mask не вычисляется непосредственным сравнением `AOE>0`.

В Python действительные integer weights дополнительно ограничиваются снизу единицей и нормируются внутри slot. Это реализационное приближение; идеальная непрерывная Eq.(3) и конкретная CUDA/Python arithmetic не тождественны. Exact reproduction требует выбрать конкретный контракт и проверить его на encoder/decoder.

### 3.3 Lookup не совпадает с Grid4D

Источник: [gridencoder/src/gridencoder.cu](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/gridencoder/src/gridencoder.cu).

`get_grid_index` [L63–86](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/gridencoder/src/gridencoder.cu#L63) использует dense indexing, затем XOR hash при переполнении размера таблицы; результат берётся по modulo и умножается на feature dimension. `fast_hash` содержит primes `1, 2654435761, 805459861` для 3D.

`kernel_grid` [L173](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/gridencoder/src/gridencoder.cu#L173) вычисляет позицию `u*(R−2)+0.5`. Fraction в показанном forward используется линейно: наличие определения `smoothstep` в файле не доказывает его вызов. При occupancy masking [L277–315](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/gridencoder/src/gridencoder.cu#L277) интерполяционные веса действительных corners перенормируются. Копирование Grid4D lookup или CNC lookup друг в друга без проверки меняет контекст.

### 3.4 Representation и подключение к rendering

Источник: [examples/radiance_fields/ngp.py](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/examples/radiance_fields/ngp.py).

`GridEncoder` содержит обучаемый `params[offset, n_features]` и buffers `offsets_list`, `resolutions_list`; allocation округляется до кратности восьми. `forward` принимает внешние восстановленные `outspace_params` и использует `STE_binary`, когда включён соответствующий режим. `forward_given_params` применяется для projection features.

`NGPRadianceField_mygrid_2D3D` создаёт xyz и xy/xz/yz encoders. `compose_3D_2D_embed.forward` конкатенирует их lookup features перед rendering network. `update_embedding_params` заменяет tensors восстановленными данными. Здесь 2D encoders являются пространственными плоскостями, а не аналогами Grid4D xyt/yzt/xzt.

### 3.5 Training, размеры и самостоятельность decoding

Источник: [examples/train_CNC_nerf_synthetic.py](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/examples/train_CNC_nerf_synthetic.py).

Entry point включает binary mode, 20K steps и отдельные Adam optimizers для radiance field/context model; MSE дополняется entropy term. Используется 12 xyz и 4 plane levels. Проверка decoding [L430–471](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/examples/train_CNC_nerf_synthetic.py#L430) обнуляет embeddings, но сохраняет текущие objects, occupancy и `Pgs_dict` в процессе, затем вызывает decoder.

Размер context models рассчитывается как `numel×32` bits. Occupancy size вычисляет Shannon estimate; rendering MLP size рассчитывается для выбранного количества digits. [L603](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/examples/train_CNC_nerf_synthetic.py#L603) суммирует эти величины с actual hash-stream bytes. Полный serialized container с model weights/occupancy/Pgs в этом entry point не обнаружен. Измерение полного файла, независимо декодируемого в новом процессе, здесь не подтверждено. Это не равнозначно опровержению статьи.

## 4. Decoder-side dependencies: проверено и что ещё требует проверки

Ниже — собственная инженерная классификация **на основе интерфейсов выше**, а не заявленный CNC container format.

| Данные | Наблюдаемое состояние в official demo | Что нужно для будущего standalone переноса |
|---|---|---|
| Binary feature streams | Реальные `.b` reads/writes | Include payload bytes |
| Resolution/allocation/hash convention | Encoding/context objects | Versioned metadata либо фиксированный публичный spec |
| Collision groups и порядок slots | Constructor state | Deterministic regeneration или оплаченный map/order |
| Coarse reconstructed symbols | Передаются через `params_q_xyz_rec` | Decode прежде dependent levels |
| Occupancy | Аргумент `binary_vxl` из running estimator | Serialize/cost либо доказать публичное восстановление |
| Per-level `f_G` | Аргумент `Pgs_dict` | Serialize/cost; нельзя вычислять из ещё не decoded fine |
| Probability model weights | Running context model | Serialize/cost или заранее известные shared weights |
| Rendering MLP, AABB, architecture | Running radiance field | Scene package; обязательны для самостоятельного rendering |

**Unknown / not tested:** полный official file-only decoder; exact bitwise portability между CUDA/CPU/GPU; сохранение constructor permutation между independent processes; реальные отдельные side-information bytes; exact identity всех неиспользуемых embeddings. Проверка этого документа статическая, не runtime.

На unused slots нельзя автоматически распространить claim lossless: восстановление всех исходных параметров и восстановление render-equivalent field — разные критерии. В нашем текущем проекте criterion именно exact восстановления existing quantized symbols.

## 5. Окружение и сложность прямого переноса

[README закреплённой версии](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/README.md) указывает Ubuntu 20.04.1, CUDA 11.8, GCC 9.4.0, Python 3.7.11; установку tiny-cuda-nn и собственных gridencoder/my_cuda_backen, замену nerfacc. Отдельного validated pretrained-only пути в прочитанном README нет. README отмечает отличие LR `0.006` от `0.01` в статье.

[requirements.txt](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/requirements.txt) закрепляет torch 1.13.1, torchvision 0.14.1, NumPy 1.21.6, torchac 0.9.3 и nerfacc 0.5.3. Дополнительные CUDA wheels относятся к cu11.

Собственная оценка для данного проекта: существующее Grid4D окружение на RTX 5060 и CUDA 12.8 не является автоматически проверенным CNC окружением. Компиляция старого CUDA stack здесь может потребовать отдельной работы. Но исходный перенос контекстной идеи можно исследовать в существующем экспортном стенде, не запуская CNC и не меняя Grid4D training objective. Эквивалентность скорости/качества CNC при этом заявлять нельзя.

## 6. Сопоставление с выполненным Grid4D экспериментом

Собственные сохранённые результаты: BITSTREAM_REPORT.md (внешний артефакт; см. каталог исключённых ссылок), context.py (внешний артефакт; см. каталог исключённых ссылок).

Выполненный эксперимент кодирует existing post-training table-wise uint8 symbols, два канала; бинаризации и RD training нет. L3→L4 xyz collision-free. Full pair file Spatial-8/sparse: **103272 B**, Boundary/sparse: **109564 B**; разница **6292 B**. Independent decode подтверждает exact symbols, а не новый PSNR. CPU canonical context закреплён; approximate CPU/GPU feature parity не обеспечивает exact class identity.

Текущий результат подтверждает саму работоспособность малого conditional codec и полный учёт его metadata. Он не показывает, как кодировать большие collision-heavy levels, и не демонстрирует выигрыша всего checkpoint. Нельзя называть этот experiment Hash Fusion: у fine slot единственная spatial preimage; mixture по нескольким collision vertices не выполнялась.

Существующий Grid4D code contract — vertex coordinate `v/s`, smoothstep interpolation; использовать CNC half-cell shift без нового parity test нельзя. Также наличие deformation field не даёт автоматически NeRF occupancy. Occupancy, построенная encoder из original scene, стала бы дополнительными передаваемыми данными, если её не может воспроизвести decoder из уже decoded scene components.

## 7. Ограничения научной новизны и минимальный следующий вопрос

Следующие идеи **не следует заявлять как новую общую концепцию**: causal inter-level hash context; spatial inverse mapping для colliding slots; occupancy-aware vertex weighting; объединение probability predictions per preimage. Источниковые основания даны выше. Замена применения NeRF на Grid4D сама по себе ещё не доказывает научного преимущества.

Предлагаемый узкий дальнейший эксперимент имеет смысл как собственная проверяемая адаптация: **постобучающее многосимвольное кодирование exact существующих Grid4D tables**, где context строится из восстановленного coarse и публичной geometry. Это постановка с иными критериями, но само различие критериев ещё не результат и не доказанная новизна.

Для hashed L5/L6 разумно сравнить при одинаковом бюджете классов:

1. заранее определённую canonical preimage;
2. aggregation mean с восемью классами;
3. mean×spread с сеткой 4×2 классов.

Mean/std — обычные статистические признаки; считать их самостоятельным новым методом по этому аудиту нельзя. Это **предложенная ablation**, а не Eq.(3) CNC. Feature aggregation перед классификацией и probability mixture после prediction математически различаются; положительный результат первого не доказывает преимущество второго.

Обязателен baseline, использующий только geometry, включая slots без nominal preimages и boundary status. Иначе predictor может лишь обнаруживать structurally unused/default symbols. Нужно сначала проверить unique coverage всех stored rows, decoder-only inputs, exact class assignments, held-out gains над geometry baseline и цену state. До этого переход к новому coder не обоснован.

Потенциально защищаемый будущий вклад: проверенный static multisymbol mapping contract, cost-aware выбор aggregation/model storage и воспроизводимая причинность без original fine parameters. **На сегодня это направление, а не доказанный научный результат.** Положительное подтверждение потребует нескольких scenes/levels и честного matched-budget сравнения с простыми baselines и probability-fusion адаптацией. Зафиксированная здесь работа не гарантирует полноту поиска всей позднейшей литературы.

## 8. Итог проверки

**CNC official source found; collision/occupancy probability fusion and causal coarse context verified.** Direct application «усреднить coarse features» не является буквальным Hash Fusion из статьи. Перенос требует явно определить многосимвольную probability model, metadata budget, valid/unused policy и exact decoder arithmetic. Official runtime, полный standalone CNC scene package и новые Grid4D gains не проверялись.

Машиночитаемые источники и Git blob hashes: cnc_sources.json (внешний артефакт; см. каталог исключённых ссылок).
