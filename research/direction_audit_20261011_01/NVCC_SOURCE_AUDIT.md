> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Проверка NVCC, Grid4D и непосредственно релевантных работ

Дата проверки: 2026-10-11. Это самостоятельное приложение к исследовательскому аудиту. Старые отчёты и snapshots не изменены. Обучение, установка чужих реализаций, загрузка datasets/checkpoints и новое кодирование не выполнялись.

## 1. Установленные факты о 4DGS-CC

[4DGS-CC, arXiv v2](https://arxiv.org/html/2504.18925v2) доступна полностью; проверены §§3.2–3.5, Appendix §§6.1–6.2 и сохранённая локальная версия (внешний артефакт; см. каталог исключённых ссылок). SHA256 локального HTML: `360f7da79c38f159ec6725d34a263d8907210d42391caff6f3c46f1ff1087720`.

NVCC работает с multi-resolution **HexPlane**, не с hashed 3D tables. Индекс `s` обозначает coarse-to-fine plane level, `t` — временную строку. Для символа используются уже восстановленный coarse feature и recurrent temporal state:

\[
p(\bar f_t^s\mid h_t^s,\hat f_t^{s-1}).
\]

Уравнение (1) обновляет состояние посредством cross-attention: `q=Wq h_prev`, `k=Wk f_prev`, `v=Wv f_prev`, `h=softmax(q kᵀ/√d)v+f_prev`. Начальное значение кодируется uniform; граничные случаи используют только доступный prior. Три purely spatial planes используют spatial prior. Уравнение (2) задаёт совместную оптимизацию rendering и compression losses. Отдельный передаваемый hyperprior `z` явно описан для **VQCC codebook**, а не как установленный дополнительный NVCC tensor. [Проверенные разделы](https://arxiv.org/html/2504.18925v2#S3.SS4).

**Hash collision probability aggregation в NVCC не обнаружено.** Это механизм CNC Hash Fusion; нельзя приписывать его 4DGS-CC. Не установлены точный codec syntax, integer CDF precision, coarse-resolution alignment, initialization recurrent state, детальные размеры entropy networks и полный учёт их передачи. Статья не заменяет executable reference implementation.

## 2. Доступность официального кода 4DGS-CC

Вердикт остаётся **OFFICIAL IMPLEMENTATION NOT FOUND IN CHECKED PUBLIC SOURCES**. Это ограниченный отрицательный результат поиска, не доказательство отсутствия частного кода.

Проверены заново:

- [arXiv abstract](https://arxiv.org/abs/2504.18925), HTML v2 с Appendix и ссылки статьи: подтверждённого author code/project/checkpoint link нет.
- [Публикации Zhenghao Chen](https://sites.google.com/view/zhenghaochen/publications): поисковое извлечение показывает эту работу с `[paper]`. Прямое открытие страницы возвратило ошибку; полнота содержимого сегодня не подтверждена.
- [Университетский профиль Zhenghao Chen](https://profiles.newcastle.edu.au/Zhenghao-Chen): доступен; не обнаружена ссылка на реализацию этой работы. [z-chen.net](https://z-chen.net/) возвращает JS shell без извлечённого текста; его актуальные динамические публикации не проверены полностью.
- Публичный GitHub Repository Search API `q=4DGS-CC`: свежий успешный ответ, `total_count=1`, `incomplete_results=false`. Единственный результат — [KyungdaePark/CC-4DGS](https://github.com/KyungdaePark/CC-4DGS).

**CC-4DGS — другая работа**: *Computational Deformation and Point-Cloud Compression for Storage-Efficient Dynamic Gaussian Splatting*, Kyungdae Park и Chae Eun Rhee. Наличие там pretrained links ничего не доказывает о 4DGS-CC Zicong Chen et al. Сторонние paper lists/notes исключены из доказательств официальности. Новые author accounts с совпадающими именами не объявлялись официальными. Авторам сообщения не отправлялись.

Предыдущий поиск сохранён в 4DGS_CC_AVAILABILITY.md (внешний артефакт; см. каталог исключённых ссылок); настоящее приложение его не заменяет.

## 3. Что реально представляет Grid4D

Официальность подтверждена цепочкой [статья §3.2](https://arxiv.org/html/2410.20815v1#S3.SS2) → [авторский project page](https://jiaweixu8.github.io/Grid4D-web/) → Code → [JiaweiXu8/Grid4D](https://github.com/JiaweiXu8/Grid4D). В статье четырёхмерный input раскладывается на `xyz,xyt,yzt,xzt`; три temporal encodings допускают anisotropic time resolution. Eq.(4) описывает XOR hashing. §§3.3–3.4 описывают directional attention и smooth regularization. Это механизм деформации, не entropy probability model.

**Для вычислительного протокола приоритет имеет реальный код:**

| Операция | Проверенный файл/функция | Следствие для будущего codec |
|---|---|---|
| Декомпозиция coordinates | scene/network.py:123 (внешний артефакт; см. каталог исключённых ссылок), `Grid4D.encode_spatial/encode_temporal` | Физические таблицы имеют разные axes и metadata |
| Integer slot mapping | hashencoder.cu:36 (внешний артефакт; см. каталог исключённых ссылок), `fast_hash`, `get_grid_index` | Dense index при достаточной capacity; иначе uint32 XOR с multipliers `{1,2654435761,805459861}`, затем modulo |
| Resolution/scale | `kernel_grid` того же файла | `scale=exp2f(level*per_level_scale)*base_resolution−1`, `R=ceil(scale)+1` |
| Lookup/interpolation | `kernel_grid`, `smoothstep` | 8 corners; weights строятся из `f²(3−2f)`; out-of-domain query возвращает zero |
| Parameter serialization | deform_model.py:139 (внешний артефакт; см. каталог исключённых ссылок), `save_weights` | Checkpoint — `(grid4d.state_dict(),deform.state_dict())`; entropy side data отсутствует |

В arXiv HTML Eq.(3) напечатана как `N_l=floor(N_min*b)` без явного `b^l`. Не исправляйте научную формулу молча и не используйте её как точную спецификацию lookup. Она не даёт фактические CUDA offsets/rounding. Также термин *trilinear interpolation* в статье не заменяет проверку smoothstep weights кода.

## 4. Прямо релевантные дополнительные методы

### SHACIRA, ICCV 2023

[Статья](https://arxiv.org/html/2309.15848v1), §§3.2–3.4, Appendix A: reparameterization `Z_l=d_theta(Q_l)`, integer latents, общий linear decoder, learned per-dimension probability models, rate-distortion optimization. После обучения latents entropy-coded; это не простое lossless сжатие заранее заданных table8 symbols. Appendix A задаёт PMF через разность CDF: `P_d(q)=c(q+1/2)−c(q−1/2)`. [Project page](https://shacira.github.io/) прямо связывает [официальный код](https://github.com/Sharath-girish/Shacira).

Для НИР это prior art на learned hash-grid compression и entropy regularization. Перепараметризация изменит целевые tensors и условия сравнения: сначала следует доказать преимущества постобучающего метода на неизменных uint8 targets. Progressive LOD также не является новой идеей само по себе.

### BiRF, NeurIPS 2023

[Официальная статья](https://proceedings.neurips.cc/paper_files/paper/2023/file/aebf6284fe85a8f44b4785d41bc8249a-Paper-Conference.pdf), §4.1 Eq.(4–7), §4.2: sign binarization `±1`, STE during training, interpolation binary grids, hybrid 3D+three 2D hash feature grids. Это меняет представление и training, а не восстанавливает исходные float32 features losslessly. Код [SAITPublic/BiRF](https://github.com/SAITPublic/BiRF) содержит связанный title/authors/project link. Его опубликованные binary storage numbers нельзя сравнивать непосредственно с 256-ary posthoc coder без matched rate-distortion protocol.

### CNC

[CNC, CVPR 2024](https://arxiv.org/html/2406.04101v1), §§3.3–3.4: learned level-wise probabilities and AOE-weighted Hash Fusion — непосредственный prior art для collision-aware probability fusion. Детальная проверка CNC делается отдельным приложением этого аудита; настоящая проверка не дублирует его. Наше применение известной inter-level conditioning к Grid4D пока не доказывает алгоритмическую новизну.

## 5. Отличие проверенного прототипа и decoder contract

В codec.py:101 (внешний артефакт; см. каталог исключённых ссылок), `quantize` использует float64 nearest-even affine min/max quantization, а `dequantize` — float32 reconstruction. context.py (внешний артефакт; см. каталог исключённых ссылок) получает только metadata и coarse symbols; `context` применим к dense L3, `classes` использует передаваемые quantile edges. format.py (внешний артефакт; см. каталог исключённых ссылок), `make/decode_data` передаёт finite probability masses и декодирует fixed targets; model_io.py (внешний артефакт; см. каталог исключённых ссылок) задаёт сериализацию. Context MLP, entropy-loss fine-tuning и recurrent temporal state отсутствуют.

context-validation.json (внешний артефакт; см. каталог исключённых ссылок): GPU/CPU max feature difference `1.1920928955078125e−7`, но `18648` differing class assignments при новых thresholds. Это установленная проблема **текущего** алгоритма, не экспериментальное обвинение CNC/NVCC. Нельзя заявлять, что чужие codecs имеют такую же ошибку без их запуска.

Следующие положения — математические требования к нашему будущему методу, а не утверждения о чужой реализации:

1. `slot j → set S_j={v:h(v)=j}` определяется геометрией, hash function и domain convention. Каждому сохранённому slot соответствует **одна** target row; вершины не создают дополнительные symbols.
2. Контекст должен вычисляться как `c_j=F({interp(dequant(Q_coarse),u_v):v∈S_j}, metadata)` без fine values. При пустом `S_j` необходим causal fallback; symbol всё равно учитывается при exact table restoration.
3. Prediction/weights должны быть одинаковыми на encoder/decoder. Если weights зависят от fine target, исходного float32 checkpoint, reference images или training occupancy, эти данные не становятся decoder-available автоматически.
4. Histogram/thresholds, probability model, occupancy/weights и geometry metadata, если передаются, входят в итоговые bytes. Learned network не является бесплатным prior.
5. `M(mean c_v)` и `mean M(c_v)` различаются для нелинейного probability mapping. Поэтому feature aggregation и probability fusion требуют отдельных ablations.

## 6. Проверяемое пространство новизны

Нельзя заявлять новыми inter-level context, collision probability fusion, occupancy weighting, quantization либо entropy coding как таковые. Проверяемая потенциальная методическая цель — **decoder-reproducible collision-set summary для фиксированных multi-valued posthoc HashGrid symbols при ограничении на total model+metadata cost**. Это пока гипотеза.

Чтобы отличить такую работу от адаптации, потребуется показать механизм и отрицательные ablations: сравнить canonical representative, equal-weight mean, dispersion/count summaries и probability fusion на одинаковых target symbols; установить режимы, где added summary помогает или мешает; затем проверить total bitstream на нескольких соседних levels и независимых сценах. При отсутствии выигрыша над deterministic representative либо при перекрывающем его overhead полезный результат может быть диагностическим, но заявление о новом эффективном compressor недопустимо.

Общий decoder contract не оправдывает перенос NVCC temporal row recurrence на hashed `xyt/yzt/xzt`: надо сначала построить соответствие slot ↔ space-time vertices, causal order и collision-aware handling. Эта работа не выполнена.

## 7. Библиографические ориентиры

- Xu J., Fan Z., Yang J., Xie J. **Grid4D: 4D Decomposed Hash Encoding for High-Fidelity Dynamic Gaussian Splatting.** NeurIPS 2024. [arXiv 2410.20815](https://arxiv.org/abs/2410.20815).
- Chen Y., Wu Q., Harandi M., Cai J. **How Far Can We Compress Instant-NGP-Based NeRF?** CVPR 2024. [arXiv 2406.04101](https://arxiv.org/abs/2406.04101).
- Chen Zicong et al. **4DGS-CC: A Contextual Coding Framework for 4D Gaussian Splatting Data Compression.** arXiv:2504.18925v2, 2025. Venue beyond this preprint is not established by this audit. [Article](https://arxiv.org/abs/2504.18925).
- Girish S., Shrivastava A., Gupta K. **SHACIRA: Scalable HAsh-grid Compression for Implicit Neural Representations.** ICCV 2023, 17513–17524. [Article](https://arxiv.org/abs/2309.15848).
- Shin S., Park J. **Binary Radiance Fields.** NeurIPS 2023. [Article](https://arxiv.org/abs/2306.07581).

Source registry, retrieval limits and current GitHub search result: NVCC_sources.json (внешний артефакт; см. каталог исключённых ссылок).
