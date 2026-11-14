> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Grid4D baseline — журнал воспроизведения

Дата: 2026-10-06 (Europe/Moscow). Рабочая папка: `<PROJECT_ROOT>`.

**Статус: PASS — минимальный рабочий baseline воспроизведён.**
Аудит 2026-10-07: **READY FOR PHASE 2**; отдельный clean environment/source/data
и новый smoke checkpoint прошли весь цикл. Отчёт: `research/AUDIT_PHASE1.md`,
machine-readable evidence: `research/audit/verification.json` и `identity.json`.
Первоначальные checkpoint/PLY/metrics artifacts не изменены.
Повторная проверка 2026-10-06 23:28: checkpoint загрузился, все 20 test views
отрендерены заново (12.60 s), evaluation завершилась (7.18 s), четыре метрики
совпали с первоначальными. Повторная проверка hashes dataset/artifacts и кадров PASS.
Последние logs/render-timing.json и metrics-timing.json относятся к этому повторному запуску;
таблица ниже сохраняет времена первоначального baseline.
Grid4D обучен на одной сцене D-NeRF: 200 итераций, checkpoint сохранён и загружен
в отдельном процессе, выполнены rendering и evaluation всех 20 test views.
Это smoke baseline с ограниченным качеством, не воспроизведение таблиц статьи.
Сжатие, квантование и изменения objective не реализованы.

## A. Официальный источник

- Project page: https://jiaweixu8.github.io/Grid4D-web/ — кнопка Code ведёт к репозиторию ниже.
- Repository: https://github.com/JiaweiXu8/Grid4D
- Commit: `3ab7b74482910d22fba7d51ac60c8cae1fe24bf1`.
- Clone: `git clone --recursive https://github.com/JiaweiXu8/Grid4D.git external/Grid4D`.
- Основной репозиторий содержит исходники расширений как обычные tracked files, а не gitlinks.
  В rasterizer есть `.gitmodules` для GLM; содержимое GLM присутствует в clone.
- README, environment.yaml, setup.py двух расширений и JIT backend изучены до изменения исходников.
- Официальные pretrained Grid4D checkpoints не найдены в README/project page;
  GitHub Releases API возвращает `[]`. Поэтому выполнено собственное короткое обучение.

## B. Окружение

Хост: Windows, Ubuntu 26.04.1 WSL2, kernel 6.18.33.2, RTX 5060 Laptop GPU,
8151 MiB, compute capability 12.0, NVIDIA driver 616.56.
Показатель CUDA UMD 13.4 из nvidia-smi **не является установленным CUDA Toolkit**.

Авторский environment.yaml: Python 3.7.16, torch 1.13.1, torchvision 0.14.1,
CUDA 11.x по README; pip NVIDIA runtime packages указывают CUDA 11.7.
Версия nvcc и фактического авторского компилятора не опубликованы;
libgcc-ng 11.2.0 в YAML не доказывает версию компилятора.

Причина необходимой адаптации: GPU sm_120. Официальная поддержка Blackwell
добавлена в PyTorch 2.7 / CUDA 12.8: https://pytorch.org/blog/pytorch-2-7/.
Python 3.7 не поддерживается этим PyTorch. Системный GCC 15 не выбран
для сборки CUDA 12.8; подготовлен отдельный GCC/G++ 13.

Установлено: Python 3.10.21, torch 2.7.0+cu128, torchvision 0.22.0+cu128,
CUDA runtime 12.8, nvcc 12.8.93, GCC/G++ 13.4.0.
Отдельное окружение на ext4 WSL: `<USER_HOME>/.local/share/grid4d-baseline/env`.
`research/grid4d-env.sh` содержит этот prefix.
Спецификация: `environment-blackwell.yml`, `conda-explicit-linux64.txt` (точные builds+MD5),
`requirements-research.txt` (основные), `requirements-lock.txt` (точный pip lock),
`requirements-freeze.txt` (фактический freeze, включая editable CUDA extensions).
Editable строки freeze ссылаются на чистый upstream commit: для воспроизведения
нужно применить локальный patch и собрать расширения командами ниже.
Полный package/build inventory: `conda-installed-records.json`.
Все pip отличия/omissions/additions относительно авторского YAML: `environment-diff.json`.
Среди общих pip packages изменены только torch, torchvision и typing-extensions
4.7.1→4.12.2 (новый torch требует >=4.10). CUDA cu11 packages заменены closure cu12
от torch. Добавлены обязательные зависимости нового torch, включая Triton 3.3.0,
SymPy 1.14.0 и fsspec; точные версии NVIDIA runtime packages находятся в lock.
Основные зависимости сохранены с авторскими pin: NumPy 1.21.6, Pillow 9.5.0,
SciPy 1.7.3, OpenCV 4.9.0.80, imageio 2.31.2, imageio-ffmpeg 0.4.9,
plyfile 0.9, LPIPS 0.1.4, pytorch-msssim 1.0.0, tqdm 4.66.2,
cachetools 5.3.3, tensorboard 2.11.2, protobuf 3.20.3.
Неиспользуемые в пути D-NeRF GUI/Jupyter/open3d/mmcv/torchaudio не устанавливаются.

Расширения:
1. `submodules/depth-diff-gaussian-rasterization`: CUDAExtension `diff_gaussian_rasterization._C`, GLM headers.
2. `submodules/simple-knn`: CUDAExtension `simple_knn._C`, CUDA/CUB.
3. `hashencoder/backend.py`: JIT `torch.utils.cpp_extension.load`, `_hash_encoder`,
   `src/hashencoder.cu` + `bindings.cpp`, build dir `./tmp_build/`.
   Исходный backend явно задаёт `-std=c++14`; современный PyTorch требует C++17.

## C. Одна сцена D-NeRF

Источник, прямо указанный Grid4D: https://www.albertpumarola.com/research/D-NeRF/index.html.
Авторский GitHub https://github.com/albertpumarola/D-NeRF содержит Dropbox/Drive ссылки.
Использована Dropbox ссылка на `data.zip`:
https://www.dropbox.com/scl/fi/cdcmkufncwcikk1dzbgb4/data.zip?rlkey=n5m21i84v2b2xk6h7qgiu8nkg&dl=1.

Выбрана `bouncingballs`: простой синтетический динамический объект, официальный scene config имеется.
Скачано **только содержимое этой сцены** через byte ranges: 40,225,434 байт передачи,
41,154,147 байт распакованных данных, 193 файла. Полный удалённый ZIP 257,793,177 байт не скачивался.
SHA256/CRC32 каждого исходного файла: `dataset-manifest.json`.

Путь Windows: `<PROJECT_ROOT>\data\dnerf\bouncingballs`.
Путь WSL/Grid4D `-s`: `<PROJECT_ROOT>/data/dnerf/bouncingballs`.

```text
data/dnerf/bouncingballs/
  train/*.png                    # 150 images
  test/*.png                     # 20 images
  val/*.png                      # 20 images, не участвуют в этом тесте
  transforms_train.json
  transforms_test.json
  transforms_val.json
```

Изображения/JSON не изменялись. COLMAP preprocessing для этой сцены не требуется.
Исходные изображения 800×800 RGBA. `--resolution 2` даёт 400×400 внутри loader;
файлы dataset не переписываются. Background black, eval=True, seed=0 через upstream safe_state.
`readNerfSyntheticInfo` сам создаёт `points3d.ply` из 100000 случайных точек при первом запуске.
Это производный файл и не входит в original dataset manifest.
После выполнения SHA256 всех 193 исходных файлов повторно проверены: совпадают.
Hash производного points3d.ply и artifacts: `baseline-artifacts.json`.

## D–F. Проверки выполнения

| Проверка | Результат |
|---|---|
| Clone official Grid4D | PASS |
| Download одной сцены | PASS |
| Download Python/CUDA/GCC conda packages | PASS, ~299 MB |
| Linux environment linking | PASS, ext4 WSL |
| GPU torch operation | PASS, finite CUDA matmul, torch 2.7.0+cu128, sm_120 |
| CUDA extensions build | PASS, rasterizer + simple-knn + JIT hashencoder |
| Training | PASS, 200 iterations; deformation + regularization после warm-up 10 |
| Save/load checkpoint | PASS, upstream render.py загрузил snapshot; отдельная сверка четырёх tensors bitwise |
| Rendering | PASS, 20 RGB + 20 GT + 20 depth PNG, 400×400 |
| Evaluation | PASS, 4 finite metrics и 20 per-view values для каждой |
| pip check | PASS, No broken requirements found |

### Реально выполненные команды

Из PowerShell в `<PROJECT_ROOT>` (каждая стадия в отдельном процессе):

```powershell
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/run_baseline.sh train
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/run_baseline.sh render
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/run_baseline.sh metrics
```

Эквивалентные upstream команды в WSL; wrapper добавляет только измерение времени/памяти:

```bash
source <PROJECT_ROOT>/research/env_common.sh
cd <PROJECT_ROOT>/external/Grid4D
python train.py -s <PROJECT_ROOT>/data/dnerf/bouncingballs \
  -m <PROJECT_ROOT>/outputs/grid4d/bouncingballs-smoke-200 \
  --conf arguments/dnerf/bouncingballs.py --iterations 200 --warm_up 10 \
  --save_iterations 200 --test_iterations 200 --resolution 2 --load2gpu_on_the_fly
python render.py --conf arguments/dnerf/bouncingballs.py \
  -m <PROJECT_ROOT>/outputs/grid4d/bouncingballs-smoke-200 \
  --iteration 200 --skip_train
python metrics.py -m <PROJECT_ROOT>/outputs/grid4d/bouncingballs-smoke-200
```

Отличия smoke CLI от defaults: iterations 50000→200; warm_up 3000→10;
resolution→2; test/save только на 200; load2gpu_on_the_fly. Короткий warm-up
нужен, чтобы проверить обучение самой деформации. Официальные grid/network config,
loss и веса regularization сохранены. Densification стартует с 500 и в этом тесте
не запускается; 100000 Gaussians. Полное обучение не выполнялось.

### Checkpoint и outputs

Windows model folder: `<PROJECT_ROOT>\outputs\grid4d\bouncingballs-smoke-200`.
Необходимый inference bundle:

```text
outputs/grid4d/bouncingballs-smoke-200/
  cfg_args
  deform/iteration_200/deform.pth                 # 52,908,789 bytes
  point_cloud/iteration_200/point_cloud.ply       # 24,801,531 bytes
  test/ours_200/{renders,gt,depth}/*.png
  test/ours_200/speed.txt
  results.json
  per_view.json
```

SHA256 deform.pth: `b52cb3cc4598e2bb8f1d761274cc85826b52efb00611cd5742522986ebac456a`.
Официальный save также создал iteration_best. Основной baseline закреплён на iteration_200.

### Полученные результаты

Среднее по 20 test views из **upstream metrics.py**, по сохранённым PNG:

| PSNR (dB) | SSIM | LPIPS (VGG) | MS-SSIM |
|---:|---:|---:|---:|
| 16.1287918091 | 0.8793266416 | 0.1673679948 | 0.8392906189 |

Встроенная train-time оценка до PNG: test PSNR 16.1509121418, L1 0.0869558567;
train subset PSNR 17.6748832703, L1 0.0752687864. Небольшое отличие PSNR ожидаемо:
metrics.py читает 8-bit PNG вместо float render. Протокол LPIPS сохранён как в upstream:
input `[0,1]`, `normalize=False`; его нельзя напрямую смешивать с оценкой, где inputs
переводятся в `[-1,1]`. Качество после 200 итераций низкое, изображения размыты;
пример GT/render: `baseline-preview.png`. Результаты статьи здесь не заявляются.

| Стадия | Время (s) | Peak torch allocated (MiB) | Peak torch reserved (MiB) |
|---|---:|---:|---:|
| Train, загрузка data + 200 iter + test + save | 34.49 | 1102.23 | 1358 |
| Load + render 20 views + PNG save | 14.65 | 505.29 | 712 |
| Evaluation | 9.63 | 515.47 | 548 |

Время измерено wrapper после CUDA initialization, до завершения entrypoint; первая
компиляция и установка не включены. Training loop ~18.5 s. GPU memory — счётчики
PyTorch allocator, не полный nvidia-smi peak процесса: внешние CUDA allocations/driver
могут добавлять память. Авторский speed.txt показывает ~19.02 FPS, но timer не делает
CUDA synchronize; это не надёжный самостоятельный benchmark throughput.

Логи: `logs/train-smoke.log`, `logs/render-smoke.log`, `logs/metrics-smoke.log`;
точные команды/время/память: `logs/{train,render,metrics}-timing.json`.
`verify_baseline_artifacts.py` проверяет dataset hashes, count/size кадров,
finite aggregate/per-view metrics и checkpoint hash. Итог: `baseline-artifacts.json`.

### Повторная установка

Для текущей машины окружение уже готово: достаточно трёх команд run_baseline выше.
Для восстановления установки сохраняются package archives/wheelhouse в `.tools/`.
Подготовка на машине с Windows internet и WSL без internet:

```powershell
git clone --recursive https://github.com/JiaweiXu8/Grid4D.git external/Grid4D
git -C external/Grid4D checkout 3ab7b74482910d22fba7d51ac60c8cae1fe24bf1
git -C external/Grid4D apply ../../research/grid4d-blackwell-compat.patch
# Windows bundled Python; допустим другой Python для download-only scripts.
$pythonRuntime = '<USER_HOME>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
powershell -File research/bootstrap_environment.ps1
curl.exe -L --fail https://micro.mamba.pm/api/micromamba/linux-64/latest -o .tools/micromamba.tar.bz2
& $pythonRuntime research/generate_conda_locks.py
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/link_environment.sh
powershell -File research/download_wheels.ps1
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/setup_grid4d.sh install
& $pythonRuntime research/download_dnerf_scene.py --scene bouncingballs --output data/dnerf
# LPIPS requires the official VGG16 weights. TORCH_HOME configured by env_common.sh.
New-Item -ItemType Directory -Force .tools/torch/hub/checkpoints
curl.exe -L --fail https://download.pytorch.org/models/vgg16-397923af.pth -o .tools/torch/hub/checkpoints/vgg16-397923af.pth
```

Первоначальная установка выполнена этими стадиями с промежуточным устранением ошибок
из раздела L. Аудит 2026-10-07 восстановил отдельный prefix с нуля из exact locks,
собрал чистую копию upstream и повторно скачал сцену; весь runtime цикл PASS.
Fresh install выявил порядок CPATH refresh: исправлено в setup_grid4d.sh, затем
сборка успешно завершена в новом prefix через audit_build.sh. Повторный полный
fresh reinstall уже исправленного install script не выполнялся; все шаги/логи сохранены.
Для точного нового download conda предпочтительнее `conda-explicit-linux64.txt`, а не
повторный solve environment-blackwell.yml; YAML задаёт необходимые версии, explicit —
фактические builds. На Linux с интернетом micromamba может напрямую create prefix
по этому explicit file, после чего записать prefix в grid4d-env.sh. Pip —
`requirements-lock.txt` с `--extra-index-url https://download.pytorch.org/whl/cu128`,
затем `setup_grid4d.sh build`. Linux compiler environment обязательно хранить на ext4.
Research shell/PowerShell scripts вычисляют workspace root из своего расположения.
generate_conda_locks.py сохраняет public exact lock, проверяет MD5 и генерирует local URIs
для текущего workspace. GRID4D_PREFIX можно явно переопределить, либо link_environment.sh
запишет новый Linux prefix. При переносе snapshot передать новые `-s`/`-m` renderer,
поскольку cfg_args хранит source_path конкретного запуска.
VGG16 SHA256: `397923af8e79cdbb6a7127f12361acd7a2f83e06b05044ddf496e83de57a5bf0`.

## G–J. Найденные места реализации и runtime подтверждение

Полная карта coordinate→decomposition→lookup→interpolation→aggregation→deformation→render:
`research/HASHGRID_MAP.md`. Runtime shapes, все offsets/resolutions/buffers и coordinate
trace записаны в `hashgrid-runtime.json`; `inspect_hashgrid.py` загрузил snapshot через
upstream load_weights и проверил bitwise совпадение всех четырёх обучаемых tensors.

- `scene/network.py`: `Grid4D`, `encode_spatial`, `encode_temporal`, `DeformNetwork`.
- `scene/deform_model.py`: `DeformModel.step`, `save_weights`, `load_weights`.
- `hashencoder/hashgrid.py`: `HashEncoder`, `_hash_encode` и autograd backward.
- `hashencoder/src/hashencoder.cu`: `fast_hash`, `get_grid_index`, `kernel_grid`.
- `gaussian_renderer/__init__.py`: применение quaternion warp и translation.

Объект сжатия в будущем — только четыре `nn.Parameter`:
`xyz_encoding.embeddings`, `xyt_encoding.embeddings`,
`yzt_encoding.embeddings`, `xzt_encoding.embeddings` в `deform.grid4d.state_dict()`.
Offsets/base_resolution/per_level_scale — buffers, необходимые для восстановления.

| Grid | Shape float32 | Levels | Features/level | Raw bytes |
|---|---|---:|---:|---:|
| G_xyz | [6098108, 2] | 16 | 2 | 48,784,864 |
| G_xyt | [161213, 2] | 32 | 2 | 1,289,704 |
| G_yzt | [161213, 2] | 32 | 2 | 1,289,704 |
| G_xzt | [161213, 2] | 32 | 2 | 1,289,704 |

Всего 13,163,494 float32 values, 52,653,976 bytes (~50.21 MiB), без buffers/network.
Это реальные nn.Parameter embeddings, а не features, полученные после lookup.
В checkpoint они расположены в первом элементе tuple `torch.load(...)[0]`.
Runtime predicted head shapes для N=3: d_xyz [3,7], d_rotation [3,4], d_scaling [3,3].
Spatial levels 5–15 используют hashing. Temporal allocation не достигает cap, но
последний уровень 31 hashed из-за float32 lookup resolution 33×33×16 при allocation
32×32×16. Это проверено GPU diagnostic; все уровни приведены в HASHGRID_MAP.md.

`save_weights`: `torch.save((grid4d.state_dict(), deform.state_dict()), deform.pth)`.
Путь: `<model>/deform/iteration_<n>/deform.pth`.
Gaussian attributes сохраняются отдельно в `<model>/point_cloud/iteration_<n>/point_cloud.ply`.
Это inference snapshot; optimizer/RNG state для точного training resume не сохраняется этим кодом.

## K. 4DGS-CC

Статья: https://arxiv.org/abs/2504.18925, latest v2 2025-04-30.
Проверены HTML статьи и appendix/supplementary sections, arXiv external links,
поиск полного названия, GitHub и авторских страниц. На данный момент
**подтверждённый официальный implementation/project page/checkpoints не найдены**.
Это ограниченный результат поиска, а не доказательство отсутствия кода.
`KyungdaePark/CC-4DGS` относится к другой статье с другими авторами и не используется.
NVCC не реализуется; 4DGS-CC остаётся архитектурным reference.
Подробный аудит первичных источников: `research/4DGS_CC_AVAILABILITY.md`.

## L. Известные проблемы и отличия

- Песочница блокирует сеть/WSL inspection; операции выполнены с отдельным разрешением.
- WSL outbound HTTPS timeout даже вне песочницы; Windows HTTPS работает.
  Временный CONNECT bridge на виртуальном адаптере WSL тоже недоступен и остановлен.
  Системные firewall/WSL/VPN настройки не изменены.
- Установка Linux compiler sysroot на NTFS вызвала case collisions (`ipt_ECN.h`/`ipt_ecn.h`).
  Эта попытка оставлена как неиспользуемая в `.envs/grid4d`; рабочий prefix установлен
  заново на Linux ext4, с hash-verified package archives, без изменения конфигурации WSL.
- Решение загрузки: Windows micromamba `--platform linux-64 --download-only`,
  затем Linux offline linking; Windows pip download Linux wheels и Linux offline install.
- Windows pip с `--python-version 310` всё равно оценивает некоторые markers как Python 3.12
  и Windows; первый resolve дал ложный конфликт NumPy/OpenCV. Поэтому отдельно загружается
  pinned wheelhouse без dependency resolution; окончательный resolve выполняется Linux pip.
- Git ownership sandbox differs; использован command-local `-c safe.directory=...`,
  global Git config не менялся.
- Первая сборка rasterizer на CUDA 12.8/GCC13: undefined std::uintptr_t/uint32_t.
  Исправлено одним явным `#include <cstdint>` в `cuda_rasterizer/rasterizer_impl.h`.
  Алгоритм rasterization не изменён. Лог исходной ошибки: `logs/setup-grid4d-first.log`.
- Simple-knn: `FLT_MAX` undefined → явный `<cfloat>` в `simple_knn.cu`.
- JIT encoder: PyTorch требует C++17 → два flags c++14→c++17 в backend.py.
  ATen headers требуют cusparse/cublas/cusolver headers → CPATH указывает include dirs
  уже установленных NVIDIA wheels; дополнительные runtime версии не устанавливались.
- **Все tracked source changes** содержатся в `grid4d-blackwell-compat.patch`: ровно
  три файла выше, плюс terminal newlines. Hash/interpolation/training objective не менялись.
  Сборка создала untracked binaries/build caches. Tracked pycache восстановлены из HEAD;
  PYTHONDONTWRITEBYTECODE=1 предотвращает дальнейшие изменения этих tracked artifacts.
- requests-oauthlib восстановлен на авторский 1.4.0; PyPI помечает этот релиз yanked
  из-за package metadata, wheel доступен, final pip check проходит.
- Deprecation warnings torch.cuda.amp/torchvision сохранены: они не мешают запуску.
- Аудит clean installation выявил: CPATH вычислялся до установки NVIDIA wheels.
  setup_grid4d.sh теперь повторно source env_common после pip install; это исправление
  research startup script, новых upstream patches нет. Полный список мелких исправлений
  и отдельно сохранённые audit artifacts приведены в AUDIT_PHASE1.md.
- Read-only resolution diagnostic сохранена отдельно в research: она выявила hashing
  последнего temporal уровня из-за rounding. Первая попытка inline вызова nvcc из
  PowerShell/WSL не передала host compiler корректно; вызов перенесён в Linux .sh,
  после чего сборка/запуск успешны. Никакой CUDA optimization не выполнялось.
- metrics.py скрывает exceptions: wrapper отдельно проверяет реально созданные finite
  результаты, поэтому exit code 0 сам по себе не используется как доказательство evaluation.
- Upstream safe_state seed=0; CUDA atomicAdd делает bitwise повтор training не гарантированным.
  Сохранённый snapshot и его exact loading проверены. Здесь нет exact training resume
  (нет optimizer/RNG); восстановление для inference работает.
- Журнал источников и hashes: `sources/manifest.json`; результаты не зависят от стороннего fork.

## M. Следующий этап (только после завершения baseline)

Первый шаг — lossless round-trip четырёх HashGrid tensors из копии inference checkpoint,
проверка bitwise равенства и render parity. Research-код разместить в `research/grid4d/`,
не внутри CUDA encoder. До PASS training/save/load/render/metrics этот шаг не выполнять.
Нужные metadata: commit, grid/network config, buffer offsets/scales/base resolutions,
tensor shapes/dtypes/key ordering, coordinate decomposition и normalization,
bound/scale_xyz/time convention, interpolation/hash rule, Gaussian PLY + cfg_args,
deformation network weights и iteration. Ни квантования, ни энтропийного pipeline пока нет.
Smoke weights не подходят для оценки итогового rate-distortion: после проверки lossless
интерфейса нужен один качественно обученный reference checkpoint той же сцены, прежде
чем делать выводы об эффективности будущего сжатия. Другие datasets пока не нужны.
