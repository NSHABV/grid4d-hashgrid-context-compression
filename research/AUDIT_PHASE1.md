> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Аудит фазы 1 Grid4D baseline

Дата: 2026-10-07, Europe/Moscow. Вердикт: **READY FOR PHASE 2**.

Аудит выполнен повторными запусками, включая восстановление отдельного чистого
окружения, сборку чистой копии upstream, повторную загрузку одной сцены и новый
training snapshot. Исходный baseline сохранён без изменения его artifacts.
Никакие функции export/import, quantization, entropy estimation или compression
не реализованы. Следующая фаза автоматически не запускалась.

## 1. Repository и воспроизводимость окружения

- Official project: https://jiaweixu8.github.io/Grid4D-web/, Code → https://github.com/JiaweiXu8/Grid4D.
- Main clone: `external/Grid4D`, origin `https://github.com/JiaweiXu8/Grid4D.git`.
- Commit: `3ab7b74482910d22fba7d51ac60c8cae1fe24bf1`.
- Для аудита `git archive HEAD` извлечён в `external/Grid4D-audit-clean`, применён
  только `research/grid4d-blackwell-compat.patch`. Это копия исходников pinned
  official revision, без `.git`; основной официальный clone остаётся доступен.
- 1620 файлов исходников/ресурсов сравнены с archive и тремя известными patches.
  Tracked pycache исключены из source comparison; Windows CRLF нормализован в LF.
  Никаких дополнительных изменений алгоритма в audit copy не найдено.
- Доказательство commit/source/patch identity и сохранности оригинальных artifacts:
  `research/audit/identity.json`.

Чистое окружение: `<USER_HOME>/.local/share/grid4d-baseline/audit-env` на ext4 WSL2.
Основной prefix `<USER_HOME>/.local/share/grid4d-baseline/env` не заменялся.

| Компонент | Восстановленная версия |
|---|---|
| Python | 3.10.21 |
| PyTorch | 2.7.0+cu128 |
| torchvision | 0.22.0+cu128 |
| CUDA runtime | 12.8 |
| nvcc toolkit | 12.8.93 |
| GCC/G++ | 13.4.0, conda-forge build 20 |
| GPU | NVIDIA RTX 5060 Laptop, sm_120, 8151 MiB |
| Host driver | 616.56; CUDA UMD 13.4 не равен Toolkit |

Основные packages: NumPy 1.21.6, SciPy 1.7.3, Pillow 9.5.0, OpenCV 4.9.0.80,
imageio 2.31.2, imageio-ffmpeg 0.4.9, plyfile 0.9, tqdm 4.66.2, cachetools 5.3.3,
LPIPS 0.1.4, pytorch-msssim 1.0.0, tensorboard 2.11.2, protobuf 3.20.3.

Восстановление выполнено **offline** из `conda-explicit-local.txt` и
`requirements-lock.txt`, используя сохранённые `.tools/mamba/pkgs` и `.tools/wheels`.
60 conda archives проверены по MD5 из неизменённого `conda-explicit-linux64.txt`.
Все pip pins восстановленного окружения совпали с lock; `pip check` PASS.
Свежая сборка rasterizer, simple-knn и JIT hashencoder PASS.
Exact versions: `research/audit/environment-restored.json`;
final freeze: `research/audit/requirements-freeze.txt`.

Установка с сетью описана в BASELINE_GRID4D.md: public conda explicit URLs + pip lock
с PyTorch cu128 index; offline mirror не является обязательной неизвестной зависимостью.
Системные prerequisites: рабочий WSL2 с доступом к GPU, NVIDIA host driver,
libGL.so.1/libglib-2.0.so.0 для OpenCV, Linux prefix на ext4.
Системные версии Python/GCC не используются вместо pinned compiler/environment.

Обнаружена и устранена ошибка порядка установки: env_common вычислял CPATH до
установки NVIDIA wheels, поэтому clean JIT build не находил cusparse.h.
Теперь setup_grid4d.sh повторно source env_common после pip install. После исправления
JIT собран, train.py --help и весь runtime цикл прошли. Исходники encoder не менялись.
Нет незафиксированных ручных шагов. Первая неуспешная попытка сохранена в restore.log;
успешное завершение сборки отдельной командой — в build.log. Второй полный fresh
reinstall после исправления не выполнялся; восстановление packages с нуля и успешная
сборка с исправленной CPATH проверены последовательно в новом prefix.

## 2. Dataset с чистой папки

Только D-NeRF `bouncingballs`, источник авторов, указанный Grid4D:
https://www.albertpumarola.com/research/D-NeRF/index.html,
https://github.com/albertpumarola/D-NeRF.
Dropbox source URL записан в обоих dataset manifests.

Повторная загрузка:

```powershell
& $pythonRuntime research/download_dnerf_scene.py --scene bouncingballs `
  --output research/audit/data/dnerf --manifest research/audit/dataset-manifest.json
```

193 файла, unpacked 41154147 bytes; по byte ranges передано 40225434 bytes,
полный ZIP 257793177 bytes не скачивался. SHA256 всех файлов новой сцены совпадают
с original manifest. Другая сцена/dataset не загружались.

```text
research/audit/data/dnerf/bouncingballs/
  train/*.png             # 150, 800×800 RGBA
  test/*.png              # 20
  val/*.png               # 20, не используются
  transforms_{train,test,val}.json
  points3d.ply            # производный файл первого запуска
```

COLMAP/конвертация исходных PNG/JSON не нужны. Upstream safe_state(seed=0) и
readNerfSyntheticInfo автоматически создают random 100000-point initialization.
SHA256 generated points3d.ply в audit и original dataset **точно совпали**.
Downsample 400×400 выполняется только loader через `--resolution 2`.
Research .sh вычисляют root относительно собственного файла; dataset передаётся
явным `-s`. Исходные dataset files не содержат absolute workspace paths.
`cfg_args` хранит абсолютный source_path текущего запуска: при переносе checkpoint
нужно передать новый `-s`/`-m` renderer, это явная CLI override, без изменения dataset.

## 3–6. Реальный повторный runtime цикл

Выполнено последовательно:

```powershell
# Из <PROJECT_ROOT>; $pythonRuntime — Python, доступный на Windows.
& $pythonRuntime research/generate_conda_locks.py
git -C external/Grid4D archive --format=tar --output=../../research/audit/grid4d-upstream.tar HEAD
wsl -d Ubuntu -- bash research/audit_restore.sh
# В первой попытке обнаружена CPATH ошибка; после исправления:
wsl -d Ubuntu -- bash research/audit_build.sh
wsl -d Ubuntu -- bash research/audit_run.sh train
wsl -d Ubuntu -- bash research/audit_validate.sh
& $pythonRuntime research/audit_identity.py
```

WSL на этой машине выполняет relative paths из Windows cwd; фактически tool calls
использовали `<PROJECT_ROOT>/research/<script>.sh`. Restore/train guards
требуют новую prefix/source/output directory: повторно их поверх существующего
audit output не запускать. Render/metrics/inspect и validate можно повторять.
Для нового независимого аудита выбрать новые prefix/source/model paths в audit scripts;
обычный повтор baseline выполняется run_baseline.sh.

Upstream команды аудита, после source env_common в audit prefix:

```bash
cd "$root/external/Grid4D-audit-clean"
python train.py -s "$root/research/audit/data/dnerf/bouncingballs" \
  -m "$root/outputs/grid4d/bouncingballs-audit-200" \
  --conf arguments/dnerf/bouncingballs.py --iterations 200 --warm_up 10 \
  --save_iterations 200 --test_iterations 200 --resolution 2 --load2gpu_on_the_fly
python render.py --conf arguments/dnerf/bouncingballs.py \
  -m "$root/outputs/grid4d/bouncingballs-audit-200" --iteration 200 --skip_train
python metrics.py -m "$root/outputs/grid4d/bouncingballs-audit-200"
```

Training запускался через audit_entrypoint.py, который проверяет scalar loss перед
**каждым** backward и записывает значения; loss/objective/optimizer/gradient computation
не менялись. 200 checks PASS, no NaN/Inf. First loss 0.5125927925, last 0.0841365010,
minimum 0.0593446493. Все float tensors сохранённого grid/network state и Gaussian PLY finite.

Checkpoint audit:
`outputs/grid4d/bouncingballs-audit-200/deform/iteration_200/deform.pth`, 52908789 bytes.
SHA256 `729f0e8b86a2b867e8e1bdcead85722f7b0b2b96a3b3f58d641e43cc14cf22a9`.
Canonical Gaussians: `point_cloud/iteration_200/point_cloud.ply`, 24801531 bytes.

Загрузка выполнена upstream render.py и DeformModel.load_weights. Дополнительный
strict load обоих state_dicts: missing_keys=[], unexpected_keys=[].
**Все** grid/network parameters и buffers после load сравнивались bitwise с snapshot.
Runtime deformation outputs finite. Rendering создал 20 renders, 20 GT и 20 depth PNG
400×400; проверены count/shape/nonempty values. Визуальный осмотр audit/preview.png:
видны три цветных шара и платформа, изображение осмысленное, размыто из-за 200 iterations.

| Метрика, mean 20 test views | Audit result |
|---|---:|
| PSNR, dB | 16.1258316040 |
| SSIM | 0.8790394068 |
| LPIPS, VGG upstream protocol | 0.1675904095 |
| MS-SSIM | 0.8387571573 |

Все 80 per-view values конечны. PSNR независимо пересчитан по PNG на CPU/NumPy:
mean 16.1258318943; каждый view совпал с metrics.py с tolerance <1e-4 dB.
metrics.py скрывает exceptions, поэтому дополнительно проверяется наличие и содержание
results.json, а не только exit code. LPIPS inputs [0,1], normalize=False оставлены
как в upstream; это ограничение протокола сравнения со стандартным [-1,1] input.

Время entrypoints: train 28.00 s, load+render 12.17 s, evaluation 6.76 s.
Torch peak reserved: train 1358 MiB, render 712 MiB, metrics 548 MiB.
Compilation/initial CUDA init вне этих timers; это не полный nvidia-smi process peak.

Логи и доказательства: `research/audit/logs/{restore,build,train,render,metrics,inspect,verification}.log`,
`research/audit/{train,render,metrics}-timing.json`, `research/audit/verification.json`.
Original baseline metrics остаются 16.1287918091 / 0.8793266416 / 0.1673679948 / 0.8392906189.
Свежий training имеет немного другие weights/metrics: seed=0 не устраняет CUDA atomicAdd
nondeterminism. Не заявляется bitwise равенство разных training runs; save/load одного
snapshot bitwise проверен. Original artifacts SHA256 не изменились.

## 7–10. Code trace и однозначный объект будущего сжатия

Повторно прочитаны фактические constructors, slicing и вызовы CUDA backend;
runtime forward hooks подтверждают coordinate decomposition на xyz/t test inputs.
Полные allocation/lookup resolutions и row counts каждого уровня:
`research/HASHGRID_MAP.md` и свежий `research/audit/hashgrid-runtime.json`.
Все metadata четырёх grids совпали с original runtime inspection.

| Grid | Constructor / class | Forward route | Live nn.Parameter / checkpoint[0] key |
|---|---|---|---|
| G_xyz | scene/network.py Grid4D.__init__ → HashEncoder.__init__ | encode_spatial(xyz) | xyz_encoding.embeddings |
| G_xyt | те же constructors | encode_temporal selects [x,y,t] | xyt_encoding.embeddings |
| G_yzt | те же constructors | encode_temporal selects [y,z,t] | yzt_encoding.embeddings |
| G_xzt | те же constructors | encode_temporal selects [x,z,t] | xzt_encoding.embeddings |

HashEncoder создаёт parameters в `hashencoder/hashgrid.py:160`, buffers :153–155.
Live prefix `deform.grid4d.<encoder>.embeddings` (DeformModel instance).

| Tensor | Shape | dtype | Elements | Bytes | Levels |
|---|---|---|---:|---:|---|
| xyz_encoding.embeddings | [6098108,2] | float32 | 12196216 | 48784864 | 0–15 |
| xyt_encoding.embeddings | [161213,2] | float32 | 322426 | 1289704 | 0–31 |
| yzt_encoding.embeddings | [161213,2] | float32 | 322426 | 1289704 | 0–31 |
| xzt_encoding.embeddings | [161213,2] | float32 | 322426 | 1289704 | 0–31 |

Все четыре trainable=True в live модели, сохраняются в checkpoint и могут читаться
без изменения inference: CPU torch.load(snapshot, weights_only=True)[0][key].
State_dict snapshot tensors сами по себе detached, это не отменяет trainability live parameters.
Каждый tensor объединяет все уровни; level l = embeddings[offsets[l]:offsets[l+1], :],
shape [rows_l,2], bytes rows_l*8. Всего 13163494 float32 values, 52653976 bytes.
MLP, canonical Gaussians, buffers не входят в эти четыре будущих входных tensors.

Для всех grids input_dim=3, feature_dim=2, cap=2^19=524288 rows/level.
Spatial L=16, base=[16,16,16], desired=[2048,2048,2048], total rows=6098108.
Temporal каждый L=32, base=[8,8,8], desired=[32,32,16], total rows=161213.
Allocation: R_l=ceil(base*q^l) NumPy float64; rows_l=min(cap,prod(R_l)); offsets cumulative int32.
Saved q/base buffers float32[3], offsets spatial int32[17], temporal int32[33].

End-to-end фактический путь:

1. `train.py`/`render_set` → `DeformModel.step(xyz.detach(), camera.fid)`.
   xyz*=scale_xyz=1; t'=(2*bound*t-bound)*0.9; concat [N,4], bound=1.6.
2. `Grid4D.forward` → `encode_spatial` / `encode_temporal`; xyz and xyt/yzt/xzt slicing.
3. `HashEncoder.forward`: u=(coord+bound)/(2*bound); normalized time 0.9*t+0.05.
4. `_hash_encode.forward`: contiguous arrays, GPU torch.log2(q),
   `_backend.hash_encode_forward` → `hash_encode_forward_cuda` → `kernel_grid`.
5. CUDA lookup resolution: scale=exp2f(l*log2_q)*base-1; R=ceil(scale)+1.
   `get_grid_index` dense x-fastest if cumulative stride fits table; otherwise `fast_hash`:
   uint32 XOR of coordinate*{1,2654435761,805459861}, overflow uint32, modulo rows.
6. `kernel_grid` interpolates 8 corners with tensor-product weights from
   `smoothstep(a)=a²(3-2a)`. Реальный код использует cubic smoothstep weights;
   формулировка trilinear не заменяет проверку фактической реализации.
7. Output [L,N,C] → [N,L*C]; xyz [N,32], temporal concat xyt/yzt/xzt → [N,192].
8. `DeformNetwork.forward`: spatial Linear32→256, sigmoid*2-1;
   temporal Linear192→256, ReLU; elementwise product; grid_mlp identity (depth=0).
9. gaussian_warp head256→7 (+ identity quaternion bias), rotation256→4, scaling256→3.
   Returned d_xyz [N,7] — quaternion+translation, не [N,3] displacement.
10. `gaussian_renderer.render`: quaternion_to_matrix(warp[:4])@canonical_xyz+warp[4:],
    canonical activated scale+d_scaling, canonical rotation+d_rotation → CUDA rasterizer.

GPU lookup diagnostic проверен на fresh environment: spatial hashing levels 5–15;
temporal hashing level31, потому что GPU lookup R=[33,33,16], allocation R=[32,32,16]
и table rows=16384. Остальные temporal levels dense. Это rounding, а не изменение
encoder; восстановление требует **фактических offsets и buffers**, не только desired R.

`DeformModel.save_weights`: torch.save((grid4d.state_dict(), deform.state_dict()), deform.pth).
Grid state_dict содержит 16 entries: 4 embeddings + 12 buffers. Network state_dict —
второй элемент tuple. Отдельно нужны Gaussian PLY, config/cameras, bound/scale_xyz,
time convention, network architecture. Attention cache не сохраняется; после будущей
замены weights нужен fresh DeformModel/reset cache. Optimizer/RNG не сохраняются:
checkpoint пригоден для inference, exact resume training этим кодом не обеспечен.

## 11. Повторная проверка 4DGS-CC

2026-10-07 повторно проверены arXiv abstract, HTML v2 с Appendix,
author Zhenghao Chen homepage/JS bundle, GitHub Repository Search API и web search
точного названия с code/project/checkpoint и именами авторов.
https://arxiv.org/abs/2504.18925, https://arxiv.org/html/2504.18925v2.

**Подтверждённый официальный repository/project page, код Neural Voxel Contextual
Coding (NVCC) и pretrained checkpoints не найдены.** Нельзя воспроизвести отдельный
официальный 4DGS-CC baseline по найденным источникам. Это ограниченный отрицательный
результат поиска, не доказательство отсутствия private/unindexed code.
GitHub search q=4DGS-CC по-прежнему total_count=1, KyungdaePark/CC-4DGS — другая
работа/авторы. GitHub links в HTML статьи — arXiv/LaTeXML tooling, не implementation.
Связанные именно с этой работой GitHub accounts авторов надёжно не установлены.
Snapshots/hash/timestamps: `research/audit/sources/manifest.json`.
Отсутствие подтверждённого кода **не блокирует Grid4D-based фазу 2**.

## 12. Все исправления и ограничения

Новых upstream patches нет: только прежние C++17, cstdint, cfloat из compatibility patch.
Architecture, training objective, hashing/interpolation и dataset не менялись.
Исправлены мелкие research startup/documentation issues:

- env_common.sh: root от расположения файла; optional GRID4D_PREFIX override для чистого env.
- run_baseline.sh, inspect_runtime.sh, setup_grid4d.sh, link_environment.sh: root от script path.
- setup_grid4d.sh: refresh CPATH после pip install; та же поправка audit_restore.sh.
- bootstrap_environment.ps1 / download_wheels.ps1: workspace от PSScriptRoot,
  bundled Python от USERPROFILE вместо имени пользователя.
- generate_conda_locks.py: сохранить существующий public exact lock, проверить MD5,
  выводить local archive URIs для текущего root вместо hardcoded /mnt/d path.
- download_dnerf_scene.py / fetch_references.py: optional manifest/output path для отдельного audit;
  source snapshots теперь содержат fetched_at_utc.
- inspect_hashgrid.py: explicit repo/model/record/iteration args, strict/bitwise check всех
  model state tensors, finite states/outputs; только read-only checkpoint diagnostics.
- BASELINE_GRID4D.md, HASHGRID_MAP.md, 4DGS_CC_AVAILABILITY.md: ссылки на аудит и уточнения.
- Добавлены отдельные audit_restore/build/run/validate shell scripts, audit_entrypoint.py,
  verify_audit.py, audit_identity.py и этот отчёт; никаких кодеков или quantization функций.

Неблокирующие ограничения: smoke quality низкое; full paper-quality baseline не получен;
CUDA training не bitwise deterministic; upstream LPIPS protocol специфичен;
inference checkpoint без optimizer/RNG; external NVIDIA driver/system libraries нужны;
4DGS-CC official implementation не подтверждён. Статистика/quantization на smoke
weights может проверять инструменты, но не обосновывать исследовательские RD conclusions.

## 13–14. Readiness assessment

| Критерий | Статус | Доказательство | Блокирует фазу 2 |
|---|---|---|---|
| Grid4D clone/revision зафиксирован | PASS | identity.json: official origin, commit, 1620 source files | no |
| Environment воспроизводим | PASS | clean audit-env из 60 conda packages + exact pip lock, fresh builds, pip check | no |
| D-NeRF scene подготовлена | PASS | повторная download, 193 SHA256 совпали, points3d initialization exact | no |
| Training smoke test | PASS | новый train: 200 iterations, 200 finite losses, сохранение snapshot | no |
| Checkpoint save/load | PASS | strict keys empty, весь grid/network state bitwise equal; fresh render process | no |
| Rendering | PASS | 20 meaningful RGB + GT + depth frames 400×400, визуальный осмотр | no |
| Evaluation | PASS | 4 finite means/80 per-view values; independent CPU PSNR совпадает | no |
| HashGrid parameters найдены | PASS | 4 nn.Parameters, shapes/dtypes/levels/offsets в fresh runtime JSON | no |
| Data flow прослежен | PASS | повторный source trace + forward hooks + GPU resolution diagnostic | no |
| Объект сжатия определён | PASS | 4 embeddings из checkpoint[0], 52653976 bytes, exact metadata | no |
| Baseline задокументирован | PASS | BASELINE_GRID4D.md + HASHGRID_MAP.md + этот отчёт и machine-readable evidence | no |

Вердикт: **READY FOR PHASE 2**. Готовность относится к технической фазе export/statistics/
проверки reconstruction и простого quantization study; не к заявлению качества статьи.

## 15. Следующая фаза — только план

Разместить отдельный research-код в `research/grid4d/`; upstream остаётся pinned dependency.

1. Read copy of Grid4D checkpoint → export именно четырёх embeddings и metadata.
2. Metadata: format version, source commit/patch/env hashes, ordered keys, shapes/dtypes,
   offsets/row counts, q/base buffers, allocation/lookup resolutions, decomposition,
   bound/scale_xyz/time normalization, hash rule, interpolation, config/network state,
   Gaussian PLY и camera/render settings.
3. Statistics по grid/level/channel: диапазон/variance/distribution/zeros; никаких
   contextual assumptions по линейному порядку hash slots.
4. Lossless export/import → strict load fresh model → bitwise tensor/buffer equality
   и render parity на фиксированных views; canonical Gaussians/network фиксированы.
5. Простейший uniform quantization study по нескольким step sizes на копии weights:
   dequantize → render → PSNR/SSIM/LPIPS относительно reference snapshot.
6. Нулевая-order entropy estimation quantized symbols по empirical frequencies;
   чётко отделить estimated bits от реально полученного codec size.

Не включать contextual neural models, entropy coders, temporal/collision-aware/cross-grid
context, CUDA optimization. До содержательных RD выводов нужен качественно обученный
reference checkpoint этой же сцены. Этот план **не реализован** в ходе аудита.
