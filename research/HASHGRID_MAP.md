> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Grid4D: путь данных и границы будущего extraction interface

Commit `3ab7b74482910d22fba7d51ac60c8cae1fe24bf1`.
Статический анализ подтверждён после успешного training/save/load/render/evaluation.
`hashgrid-runtime.json` содержит shapes/keys, bitwise loading verification, coordinate
trace и lookup resolutions, вычисленные GPU-диагностикой. Сжатие не реализовано.
Повторный аудит 2026-10-07 в чистом prefix/source подтвердил всю metadata и data flow:
`research/audit/hashgrid-runtime.json`, `research/audit/identity.json`, `AUDIT_PHASE1.md`.
Дополнительно весь grid/network state (parameters и buffers) strict/bitwise load PASS;
missing/unexpected keys пусты, outputs/state finite.

## Путь координат до изображения

1. `train.py` передаёт `gaussians.get_xyz.detach()` `[N,3]` и camera.fid,
   expanded `[N,1]`, в `DeformModel.step` (`scene/deform_model.py`).
2. `xyz *= scale_xyz` (scene config по умолчанию 1.0 по всем осям).
   `t' = (2*bound*t - bound)*0.9`, где `bound=1.6` и исходное время D-NeRF `[0,1]`.
   `xyzt=cat(xyz,t')` `[N,4]`.
3. `Grid4D.forward` (`scene/network.py`) выделяет spatial xyz и вызывает `encode_temporal`:
   xyt = columns `[0,1,3]`; yzt = `[1,2,3]`; xzt = `[0,2,3]`.
   Это подтверждение семантики по slicing/concatenation, а не только имена модулей.
4. Каждый `HashEncoder.forward` (`hashencoder/hashgrid.py`) нормализует координаты:
   `u=(input+bound)/(2*bound)`. Для времени в итоге `u_t=0.9*t+0.05`.
   XYZ за пределами `[-bound,bound]` не clamp: CUDA kernel возвращает нулевой feature.
5. `_hash_encode.forward` вычисляет `s=torch.log2(per_level_scale)` на GPU в float32,
   затем передаёт inputs, embeddings, offsets, s и base_resolution в `_backend.hash_encode_forward`;
   временный output `[L,N,C]`, затем permute/reshape `[N,L*C]`.
6. CUDA `kernel_grid` (`hashencoder/src/hashencoder.cu`) для уровня l и оси d:
   `scale_d=exp2f(l*s_d)*base_resolution_d-1`,
   `resolution_d=ceil(scale_d)+1`, `pos_d=u_d*scale_d`, целая часть floor,
   дробная часть `a_d`. Здесь отсутствует half-cell offset (`+0.5` закомментирован).
7. Интерполяция по 8 вершинам 3D ячейки. Вес каждой оси — `smoothstep(a)=a*a*(3-2*a)`
   или `1-smoothstep(a)`; веса перемножаются, затем суммируются weighted features.
   Это tensor-product interpolation с cubic smoothstep, а не обычная линейная trilinear.
8. `get_grid_index`: при `prod(resolution)<=table_rows` dense индекс x-fastest;
   иначе `fast_hash`: XOR произведений uint32 координат с primes
   `[1,2654435761,805459861]`, с переполнением uint32, modulo table_rows.
   В обоих случаях индекс `(index % table_rows)*C + channel`.
   Границы/численные округления следует воспроизводить точно, включая modulo.
9. Уровни concatenated, spatial `[N,32]`. Три temporal encodings `[N,64]`
   concatenated в порядке xyt,yzt,xzt → `[N,192]`.
10. `DeformNetwork`: spatial Linear 32→256 → sigmoid → `2*a-1` (directional attention).
    Temporal Linear 192→256 → ReLU. Features умножаются elementwise.
    Официальный `bouncingballs.py` задаёт depth=0, поэтому `grid_mlp` — identity.
11. Heads: `gaussian_warp` 256→7 + bias `[1,0,0,0,0,0,0]`,
    `gaussian_rotation` 256→4, `gaussian_scaling` 256→3.
    `d_xyz` фактически `[N,7]`, quaternion+translation, а не `[N,3]` displacement.
12. `gaussian_renderer/__init__.py`: `means3D=quaternion_to_matrix(warp[:4]) @ xyz + warp[4:]`;
    scales=`pc.get_scaling+d_scaling`, rotations=`pc.get_rotation+d_rotation`.
    Canonical opacity и SH напрямую поступают в rasterizer; эти heads их не деформируют.
    `diff_gaussian_rasterization` возвращает RGB, radii, depth.

При `fixed_attention=True` rendering кэширует spatial attention для фиксированного списка
Gaussians; последующие views вычисляют temporal grids и используют этот cache.
После будущей замены grid weights cache надо сбросить либо создать новый DeformModel.

## Четыре фактических grids

| Математический объект | Live parameter | Grid state_dict key | L | C | Base | Desired | Cap/level |
|---|---|---|---:|---:|---|---|---:|
| G_xyz | deform.grid4d.xyz_encoding.embeddings | xyz_encoding.embeddings | 16 | 2 | 16³ | 2048³ | 2¹⁹ |
| G_xyt | deform.grid4d.xyt_encoding.embeddings | xyt_encoding.embeddings | 32 | 2 | 8³ | 32×32×16 | 2¹⁹ |
| G_yzt | deform.grid4d.yzt_encoding.embeddings | yzt_encoding.embeddings | 32 | 2 | 8³ | 32×32×16 | 2¹⁹ |
| G_xzt | deform.grid4d.xzt_encoding.embeddings | xzt_encoding.embeddings | 32 | 2 | 8³ | 32×32×16 | 2¹⁹ |

`HashEncoder.__init__` вычисляет в NumPy float64:
`q_d = exp2(log2(desired_d/base_d)/(L-1))`,
`R_ld = ceil(base_d*q_d**l)`, `T_l=min(2**19,prod(R_l))`.
Offsets — cumulative sum T_l, `int32[L+1]`; embeddings — `nn.Parameter float32[sum(T_l),2]`.
`per_level_scale`, `base_resolution` — float32 buffers `[3]`.
Float64 allocation resolutions и CUDA float32 lookup resolutions имеют разные пути округления;
metadata должна хранить реальные offsets и buffers, а не заново вычислять их только из desired.

Temporal grids не достигают allocation hash cap, но **последний lookup уровень 31
использует hashing**: GPU float32 rounding даёт `[33,33,16]` при allocation `[32,32,16]`,
то есть 17424 vertices при 16384 table rows. Уровни 0–30 dense.
Spatial levels 0–4 dense, 5–15 hashed. Это подтверждено `inspect_lookup_resolutions.cu`:
diagnostic принимает именно результат GPU torch.log2 buffer, выполняет ту же
exp2f/ceil формулу на sm_120 с -O3. Encoder не изменялся. Нельзя предполагать одинаковое
количество collision или temporal-row topology для всех четырёх grids.

Trainable HashGrid weights — **только embeddings**. Buffers не обучаются.
Gradient по embeddings суммируется CUDA atomicAdd, включая colliding indices;
код поддерживает backward и отдельный second-backward path. Неизменённые CUDA atomics
могут влиять на bitwise reproducibility training между запусками.

## Checkpoint

`DeformModel.save_weights` сохраняет tuple `(grid4d.state_dict(), deform.state_dict())`
в `<output>/deform/iteration_<n>/deform.pth`.
Т.е. embeddings принадлежат элементу `[0]` tuple, а не сети `[1]`.
Первый state_dict содержит четыре набора embeddings+offsets+per_level_scale+base_resolution
(всего 16 entries). Attention cache и `quat_bias` не являются зарегистрированными buffers.
`bound`, `scale_xyz`, L/C/desired/cap, directional/depth/width восстановить из scene config/cfg_args.
`Scene.save` отдельно сохраняет Gaussian PLY. Для rendering нужен весь bundle:
`cfg_args`, PLY, deform.pth, scene data/cameras и правильный конфиг.
Optimizer state отсутствует: upstream train.py не предлагает exact resume из этого snapshot.

## Только проектирование следующего интерфейса

Research code: `research/grid4d/`, upstream repo использовать как зависимость с pinned commit.
Первый будущий контракт: read snapshot → named four-tensor mapping + metadata;
reconstruct mapping → заменять только четыре embeddings в копии grid state_dict;
`load_state_dict(strict=True)` → свежий DeformModel → upstream render/metrics.
Сначала lossless identity round-trip и image parity, затем отдельный эксперимент quantization.

Metadata: format version/commit, keys/ordering, tensor dtype/shape, level offsets,
buffers float32, allocation resolutions, bound/scale_xyz/time mapping, decomposition order,
hash uint32 rule/primes/modulo, interpolation, network config/state, canonical PLY/SH degree,
camera/image resolution/background, iteration, seed, environment and hashes of source artifacts.
Будущие step size / symbols / context traversal / coding format сюда не добавлены.
MLP и canonical Gaussians должны оставаться фиксированными при исследовании только HashGrid.
Hash slots не дают уникальных пространственно-временных координат; HexPlane temporal-row
context из 4DGS-CC нельзя перенести механически на high-resolution spatial hash tables.

## Runtime подтверждение и навигация по исходникам

Основные точки pinned upstream:

- `scene/network.py:58` Grid4D; `:123` encode_spatial; `:126` encode_temporal;
  `:138` forward; `:143` DeformNetwork; `:180` attention/aggregation/heads.
- `scene/deform_model.py:59` координаты/time/step; `:130` save_weights; `:141` load_weights.
- `hashencoder/hashgrid.py:14` _hash_encode; `:110` HashEncoder;
  `:153` buffers; `:160` nn.Parameter embeddings; `:171` normalization/forward.
- `hashencoder/src/hashencoder.cu:36` fast_hash; `:55` get_grid_index;
  `:87` smoothstep; `:104` kernel_grid; `:264` embedding gradients.
- `gaussian_renderer/__init__.py` transforms Gaussian attributes and calls rasterizer.

| State key в checkpoint[0] | Shape | Scalar count | Raw bytes |
|---|---|---:|---:|
| xyz_encoding.embeddings | [6098108,2] | 12196216 | 48784864 |
| xyt_encoding.embeddings | [161213,2] | 322426 | 1289704 |
| yzt_encoding.embeddings | [161213,2] | 322426 | 1289704 |
| xzt_encoding.embeddings | [161213,2] | 322426 | 1289704 |

Все — обучаемые float32 parameters; всего 52653976 bytes без buffers/network.
`inspect_hashgrid.py` сравнил каждый с CPU checkpoint через torch.equal после
официального load_weights: все exact. Runtime hook подтвердил decomposition
на трёх точках со временем 0/0.5/1: xyz output [3,32], каждый temporal output [3,64],
d_xyz [3,7], d_rotation [3,4], d_scaling [3,3].

Повторить read-only анализ после baseline:
`wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/inspect_runtime.sh`.
Скрипт собирает маленькую диагностическую программу в research/bin, затем читает
checkpoint; не меняет веса, objective, CUDA encoder или изображения baseline.

Spatial buffer q = [1.3819128274917603]×3, base=[16]×3.
Temporal q = [1.045734167098999,1.045734167098999,1.022611379623413], base=[8]×3.
Offsets spatial int32[17], temporal int32[33]; q/base float32[3] у каждого encoder.
Точные offsets и GPU log2(q) находятся в hashgrid-runtime.json.

## Уровни: allocation и фактический GPU lookup

Индексы уровней начинаются с 0. Allocation R вычислено Python/NumPy float64;
lookup R — CUDA float32 по фактическим buffers. Rows = offsets[l+1]-offsets[l].
Таблица ниже generated из runtime JSON; три temporal grids имеют одинаковую metadata.

### Spatial xyz

| Level | Allocation R | GPU lookup R | Table rows | Indexing |
|---:|---|---|---:|---|
| 0 | 16×16×16 | 16×16×16 | 4096 | dense |
| 1 | 23×23×23 | 23×23×23 | 12167 | dense |
| 2 | 31×31×31 | 31×31×31 | 29791 | dense |
| 3 | 43×43×43 | 43×43×43 | 79507 | dense |
| 4 | 59×59×59 | 59×59×59 | 205379 | dense |
| 5 | 81×81×81 | 81×81×81 | 524288 | hash |
| 6 | 112×112×112 | 112×112×112 | 524288 | hash |
| 7 | 154×154×154 | 154×154×154 | 524288 | hash |
| 8 | 213×213×213 | 213×213×213 | 524288 | hash |
| 9 | 295×295×295 | 295×295×295 | 524288 | hash |
| 10 | 407×407×407 | 407×407×407 | 524288 | hash |
| 11 | 562×562×562 | 562×562×562 | 524288 | hash |
| 12 | 777×777×777 | 777×777×777 | 524288 | hash |
| 13 | 1073×1073×1073 | 1073×1073×1073 | 524288 | hash |
| 14 | 1483×1483×1483 | 1483×1483×1483 | 524288 | hash |
| 15 | 2048×2048×2048 | 2048×2048×2048 | 524288 | hash |

### Temporal xyt / yzt / xzt

| Level | Allocation R | GPU lookup R | Table rows | Indexing |
|---:|---|---|---:|---|
| 0 | 8×8×8 | 8×8×8 | 512 | dense |
| 1 | 9×9×9 | 9×9×9 | 729 | dense |
| 2 | 9×9×9 | 9×9×9 | 729 | dense |
| 3 | 10×10×9 | 10×10×9 | 900 | dense |
| 4 | 10×10×9 | 10×10×9 | 900 | dense |
| 5 | 11×11×9 | 11×11×9 | 1089 | dense |
| 6 | 11×11×10 | 11×11×10 | 1210 | dense |
| 7 | 11×11×10 | 11×11×10 | 1210 | dense |
| 8 | 12×12×10 | 12×12×10 | 1440 | dense |
| 9 | 12×12×10 | 12×12×10 | 1440 | dense |
| 10 | 13×13×11 | 13×13×11 | 1859 | dense |
| 11 | 14×14×11 | 14×14×11 | 2156 | dense |
| 12 | 14×14×11 | 14×14×11 | 2156 | dense |
| 13 | 15×15×11 | 15×15×11 | 2475 | dense |
| 14 | 15×15×11 | 15×15×11 | 2475 | dense |
| 15 | 16×16×12 | 16×16×12 | 3072 | dense |
| 16 | 17×17×12 | 17×17×12 | 3468 | dense |
| 17 | 18×18×12 | 18×18×12 | 3888 | dense |
| 18 | 18×18×12 | 18×18×12 | 3888 | dense |
| 19 | 19×19×13 | 19×19×13 | 4693 | dense |
| 20 | 20×20×13 | 20×20×13 | 5200 | dense |
| 21 | 21×21×13 | 21×21×13 | 5733 | dense |
| 22 | 22×22×14 | 22×22×14 | 6776 | dense |
| 23 | 23×23×14 | 23×23×14 | 7406 | dense |
| 24 | 24×24×14 | 24×24×14 | 8064 | dense |
| 25 | 25×25×14 | 25×25×14 | 8750 | dense |
| 26 | 26×26×15 | 26×26×15 | 10140 | dense |
| 27 | 27×27×15 | 27×27×15 | 10935 | dense |
| 28 | 28×28×15 | 28×28×15 | 11760 | dense |
| 29 | 30×30×16 | 30×30×16 | 14400 | dense |
| 30 | 31×31×16 | 31×31×16 | 15376 | dense |
| 31 | 32×32×16 | 33×33×16 | 16384 | hash |
