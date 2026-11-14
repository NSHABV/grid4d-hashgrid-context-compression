> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

> При разработке и оформлении исследования использовались ИИ-агенты; [область помощи и ответственность автора](../../../docs/AI_ASSISTANCE.md). Этот исторический интерфейс может требовать внешних артефактов; проверенный публичный запуск описан в корневом README.

# H4: технический модуль PMF clustering

Реализация от 28.10.2026. Технические проверки: VALIDATION.json (внешний артефакт; см. каталог исключённых ссылок), 40 тестов PASS. Полный clustering сцен и новые H4 scene bitstreams в этом задании **не запускались**. Старые кодеры и исследовательские результаты не изменены.

## Интерфейсы и входы

CLI: `python -B -m research.experiment_bench.pmf_clustering {optimize,inspect,encode,decode,test}`.

- `optimizer.py`: `histogram(symbols, classes)`, `optimize(counts, original, thresholds, mode, metadata_bytes)`, `objective(counts, model, metadata_bytes)`.
- `transport.py`: `Model(pool, mapping, thresholds, mode)`, `serialize`, `deserialize`, `choose`, `sizes`, `route`.
- `geometry.py`: восстановление Mean8 из coarse symbols и metadata по прежней canonical CPU arithmetic.
- `codec.py`: `encode(..., original_masses=..., original_thresholds=...)`, `decode(data, strict=True)` и физический разбор `sizes`.
- `bundle.py`: read-only adapter к sealed H3 bundle. Проверяет SHA256 четырёх файлов по `FINAL_VALIDATION.json` до/после чтения, coarse payload и точное совпадение восстановленных Mean8 IDs.
- `replay.py`: самостоятельный decoder process, вход — только `.bin` и публичный код/зависимости.

Исходные arrays: `counts[2,10,256]` — целые raw counts; `original[2,10,256]` — uint32 masses; `thresholds[2,7]` — float64. В `encoder_inputs.npz` adapter использует только `coarse`, `fine`, `mean_classes`, `mean_pmf`, `edges`; geometry и исходный IID coarse prerequisite берёт из соседних файлов bundle. Нового quantization или refit исходных PMF нет.

`optimize` сохраняет план, `model.h4pm`, raw histograms и SHA256 всех входов. `encode` требует совпадения модели и входов с этим планом и повторно проверяет J. `inspect --counts` получает фактически измеренную стоимость внешней metadata из связанного плана; для независимого histogram API её можно явно передать через `--metadata-bytes`.

## Идентификаторы, режимы и objective

В каждом feature channel локальные Mean8 IDs: **0=G0, 1=G1, 2..9=восемь feature bins**. G2/G3 используют общие восемь bins, а не отдельные PMF для каждой геометрической группы. Глобальный ID источника для optimizer: `10*channel + local_id`. Decoder получает физический ID строки через `mapping[channel, local_id]`; это другой индекс. Значение 255 означает неактивный исходный класс.

| Режим | Правило |
| --- | --- |
| C0 | Одна переданная исходная PMF на каждый активный класс, без refitting и sharing. |
| C1 | Побитно одинаковые PMF физически разделяют строку; вероятности и raw fine entropy payload совпадают с C0. |
| C2 | Начальная модель как C1; статистические слияния только активных bins 2..9 внутри одного канала. |

G0/G1 всегда сохраняют исходные PMF и не участвуют в статистических слияниях. Побитно одинаковые строки, в том числе между каналами и G0/G1, разделяют физическое хранение в C1/C2. Это sharing не меняет статистические кластеры. Неиспользуемые строки не передаются. Порядок pool rows — первое появление при обходе channel, затем local class.

Для каждого кандидата вычисляется:

```text
L = sum_c sum_s n[c,s] * (16 - log2(mass[M[c],s])) / 8
J_bytes = L + len(complete_serialized_H4PM) + outer_metadata_bytes
```

`len(H4PM) = pmf_bytes + mapping_bytes + threshold_bytes + header_bytes`.
`outer_metadata_bytes` — точная длина canonical JSON, внешнего prefix и SHA256, измеренная сериализатором; содержимое семи fixed-width digests не меняет её длину. Общий coarse prerequisite не участвует в выборе слияния как неизменная константа; `predicted_pair_bytes` добавляет его полностью. `model_bytes` здесь означает **всю H4PM section**, а не только массы. Mode/storage IDs уже включены в header, их нельзя учитывать повторно.

Каждый шаг перебирает все допустимые пары и сериализует **всю** модель с mapping во всех трёх transports; выбирает минимальный размер. Аддитивной оценки строк нет. PMF нового кластера строится действующей `models.frequencies` из суммы **raw** counts всех участников: Laplace smoothing один раз, затем прежнее преобразование в положительные integer masses с суммой 65536. Нет суммирования сглаженных PMF. Необъединённые классы сохраняют исходные PMF.

При равном float64 J выбирается лексикографически минимальная пара кортежей исходных global IDs. При равном физическом размере транспорта приоритет: dense_u32, packed_u16, sparse_default_u16. Слияние принимается только при строгом уменьшении J, без tolerance. Последний полный перебор должен не найти улучшения. Для суммы class costs используется `math.fsum`; внутри класса — фиксированный NumPy float64 reduction. Это greedy local optimum, не глобальный оптимум partition.

J содержит ideal payload, а не длину range payload. Строгое уменьшение J **не гарантирует** уменьшения actual `.bin`: последнее проверяется отдельно будущим экспериментом.

## Binary formats v1

Все integer/float поля little-endian. Старые V1/V2/V3/H3 контейнеры не меняются.

**H4PM v1:** prefix `<4sBBBBHIII>` (22 B): magic `H4PM`, version=1, storage ID=1..3, mode ID=0..2, channels=2, pool row count uint16, длины masses/thresholds/mapping uint32. Затем:

1. Masses: dense_u32 (`R*256*4 B`), packed_u16 (`R*256*2 B`) либо sparse_default_u16.
2. Исходные thresholds float64[2,7], 112 B, побитно сохранённые.
3. Mapping uint8[2,10], 20 B, channel-major.

Sparse row: default uint16, exception count uint16, затем отсортированные пары `(symbol uint8, mass uint16)`. Default — наиболее частое значение mass, при равенстве минимальное; exceptions не повторяются и не равны default. Максимальная mass=65281, поэтому uint16 достаточно. CDF не дублируется. Валидация проверяет positivity, сумму 65536, канонический порядок и support mapping, отсутствие неиспользуемых/лишних строк и точный reserialization roundtrip.

**H4G4PAIR v1:** prefix `<8sH5Q>` (50 B): magic `H4G4PAIR`, version=1, пять длин секций uint64. Секции: canonical JSON metadata; исходная IID coarse model; H4PM fine model; coarse payload; fine payload. В конце SHA256 всех предыдущих байтов (32 B).

Metadata содержит level geometry/offsets/scales, hash/interpolation/domain conventions, table-wise quantizer, arithmetic/runtime/order/engine contract и семь digests массивов. Limits: JSON 64000 B, coarse model 1 MiB, fine model ≤20634 B, каждый payload ≤4 MiB. Parse отклоняет неизвестные contracts, неверные длины, checksum, mapping и malformed masses. Strict decode дополнительно re-encodes оба payload и отклоняет лишние/неканонические words.

Encoder кодирует все allocated fine slots ровно один раз, channel-major, включая G0/G1. Coarse payload не перекодируется для хранения, но его exact decode и canonical re-encoding проверяются. PMF pool в памяти адаптируется к прежнему engine; на диске каждая строка pool хранится один раз.

## Decoder и arithmetic

Decoder: `.bin → coarse symbols → coarse dequantization → прежние Mean8 IDs → transmitted mapping → pool PMF → fine symbols`. Thresholds, geometry, quantizer, PMF и mapping находятся внутри `.bin`; targets и encoder histograms не нужны. Никакого optimizer/refitting при decode.

Используется неизменённая `cpu-f32-separate-ufunc-corner0to7-anchor-f64-addat-xfast-popstd-v1`: uint32 indexing/hash, smoothstep с прежним порядком float32 операций, x-fast correspondences и anchor-based float64 aggregation. Mean8 использует `searchsorted(..., side='right')`, включая повторяющиеся thresholds. G0/G1 overrides сохраняются.

Проверенное окружение: Windows Python **3.12.14**, NumPy **1.26.4**, constriction **0.4.2**, существующий indexed range engine. Запускать `.tools/phase2-plotting-env/Scripts/python.exe -B`; wrapper `hashed_pair.engine` выбирает Windows dependency из `.tools/hashed-pair-deps`. GPU не нужен. Runtime проверяется перед encode/decode.

Fresh decoder audit ставится после загрузки доверенного публичного кода/runtime; во время decode разрешает чтение только входного `.bin` и public source/runtime files, блокирует fitting, проверяет отсутствие optimizer import и пять запрещённых data probes. Это контроль Python file-access и dependency causality доверенной реализации, **не OS sandbox для враждебных native libraries**.

## Проверки и границы

40 тестов: 25 optimizer/transport, 8 независимых scalar geometry oracle, 7 integration. Полный suite: 21.26 s с двумя SHA256 audit; сами unittest: 8.95 s. Synthetic standalone fixture: coarse 11 rows, fine 61 rows, два канала. C0/C1/C2 независимо декодированы с exact array equality; repeated encoding byte-identical; C0/C1 raw fine payload совпадает. Положительный C2 test объединяет **неидентичные** PMF. Есть независимый полный pair-evaluation oracle, тесты запрета невыгодного merge, empty/rare, overflow, повреждённых models/payload/mapping и plan binding.

Regression: strict decode двух существующих H3 L6 файлов (bouncingballs mask0100, hellwarrior mask1100), сравнение всех восстановленных массивов. Проверены 7200 прежних файлов; SHA256 не изменились.

Production validator поддерживает только xyz L4→L5 и L5→L6 с прежней Grid4D geometry. Adapter принимает sealed H3 bundles. Тестовая geometry имеет отдельный профиль `synthetic-test-v1` и малые bounds; она не ослабляет production validator. Всего не более 20 активных исходных классов, два канала, алфавит 256; сумма raw counts ограничена `2**53-256`. Полностью пустой histogram допустим для dry optimizer, но не является валидной непустой Grid4D парой.

Прямой library caller отвечает за передачу genuine source PMF/counts; CLI дополнительно связывает план с frozen bundle SHA256. Межплатформенная bit identity не доказана; используйте закреплённый runtime. Нет научного вывода об эффективности C2 или замеров полной сцены.

## Точные команды

Из `<PROJECT_ROOT>`, новый уникальный test output:

```powershell
$py = '.tools/phase2-plotting-env/Scripts/python.exe'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
& $py -B -m research.experiment_bench.pmf_clustering test --output "research/h4_technical_tests_$stamp"
```

Один будущий case (это обработка сцены; в текущем задании не запускалась):

```powershell
$py = '.tools/phase2-plotting-env/Scripts/python.exe'
$mod = 'research.experiment_bench.pmf_clustering'
$bundle = 'research/hybrid_context_selection_20261027_01/bouncingballs_L6'
$job = 'research/h4_manual_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')
& $py -B -m $mod optimize --bundle $bundle --mode C2 --output $job
& $py -B -m $mod inspect --model "$job/model.h4pm" --counts "$job/histograms.npz"
& $py -B -m $mod encode --bundle $bundle --model "$job/model.h4pm" --output "$job/pair.bin"
& $py -B -m $mod decode --input "$job/pair.bin" --output "$job/decoded"
```

Готовый будущий batch **двух сцен на L5→L6**, все C0/C1/C2 (шесть новых файлов), с остановкой при ошибке и сохранением partial results:

```powershell
& '<PROJECT_ROOT>\research\experiment_bench\pmf_clustering\run_two_scenes.ps1' -OutputRoot ('<PROJECT_ROOT>\research\h4_batch_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
```

Скрипт последовательно вызывает optimize, inspect, encode и новый decoder process для каждого режима на `bouncingballs_L6` и `hellwarrior_L6`; сохраняет stdout JSON, модели/планы и decoded arrays. Любой существующий output path отклоняется. Сам batch пока **не выполнен**; его команды предназначены для следующего задания. На будущий научный анализ следует отдельно добавить сравнение actual physical sizes и ресурсные измерения.
