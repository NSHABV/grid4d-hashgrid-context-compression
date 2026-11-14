> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Реальные standalone bitstreams xyz L5→L6 — две сцены

23 октября 2026. Actual scene-specific coding: вероятностные таблицы и thresholds fit по всем symbols соответствующей сцены и полностью переданы в файле. Held-out результаты приведены отдельно. Объект — только пара xyz L5+L6, а не весь Grid4D.

| Scene | Model | Coarse B | Fine payload B | Fine masses B | Metadata/framing B | Total B |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | IID | 187483 | 259148 | 443 | 2336 | 449410 |
| bouncingballs | Geometry4 | 187483 | 249612 | 1982 | 2348 | 441425 |
| bouncingballs | Canonical8 | 187483 | 251748 | 3701 | 2482 | 445414 |
| bouncingballs | Mean8 | 187483 | 248780 | 3065 | 2472 | 441800 |
| hellwarrior | IID | 125821 | 201116 | 347 | 2335 | 329619 |
| hellwarrior | Geometry4 | 125821 | 195488 | 1877 | 2347 | 325533 |
| hellwarrior | Canonical8 | 125821 | 196696 | 3494 | 2481 | 328492 |
| hellwarrior | Mean8 | 125821 | 194468 | 2576 | 2471 | 325336 |

Для каждого arm проверены dense_u32, packed_u16 и sparse_default_u16. Таблица выбирает минимальный физический размер отдельно для каждой модели. Все 24 физических варианта сохранены, прошли independent exact decode. Coarse bytes включают IID payload L5 и его модель; Fine masses — только переданные integer masses L6. Thresholds, specification, framing, digests и прочая обязательная информация включены в последний столбец расходов. CDF восстанавливается из masses и отдельно не хранится.

## Результат относительно сильных baseline

**bouncingballs: NO-GO** для фиксированного Mean8 L6. Лучший baseline Geometry4 = 441425 B; Mean8 = 441800 B; saving = -375 B (-0.084952% пары).

**hellwarrior: GO** для фиксированного Mean8 L6. Лучший baseline Geometry4 = 325533 B; Mean8 = 325336 B; saving = +197 B (+0.060516% пары).

| Scene | Mean8 vs | Standalone saving B | Saving % pair | Saving % incremental fine | Payload saving B | Extra masses B | Extra metadata B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | IID | 7610 | +1.693331 | +2.905390 | 10368 | 2622 | 136 |
| bouncingballs | Geometry4 | -375 | -0.084952 | -0.147672 | 832 | 1083 | 124 |
| bouncingballs | Canonical8 | 3614 | +0.811380 | +1.401150 | 2968 | -636 | -10 |
| hellwarrior | IID | 4283 | +1.299379 | +2.101591 | 6648 | 2229 | 136 |
| hellwarrior | Geometry4 | 197 | +0.060516 | +0.098642 | 1020 | 699 | 124 |
| hellwarrior | Canonical8 | 3156 | +0.960754 | +1.557204 | 2228 | -918 | -10 |

Saving > 0 означает меньший файл Mean8. Incremental fine budget = total − общий coarse prerequisite. При одинаковом coarse абсолютный выигрыш pair и incremental fine совпадает, но проценты имеют разные знаменатели. Стоимость предыдущего L4→L5 не включена; L4 decoder не требуется.

## Полный формат и декодирование

Изолированный G4DHPAIR V3 поддерживает только проверенные пары L4/L5 и L5/L6; это не универсальный codec произвольного HashGrid. В header находятся version, уровни, rows/channels, actual scale/resolution/offsets, uint32 hash, interpolation/domain/arithmetic convention, scene-specific quantizer, model ID/storage, integrity. Thresholds и masses переданы в fine model; slot→vertices map не передаётся.

Decoder сначала восстанавливает весь L5 из IID coarse payload, затем coarse-only контекст L6 и classes, затем все L6 symbols. Все allocated slots и оба channels включены один раз: 2097152 uint8 symbols на файл. Strict decoder проверяет hashes, положительные masses с суммой65536 и каноничность payload повторным entropy encode. Exact symbols означают отсутствие дополнительного искажения относительно frozen uint8; исходные float32 после прежнего квантования не восстанавливаются losslessly. Rendering/RD в этом задании не измерялись.

## Correctness

- bouncingballs: 12 bin-only fresh decodes; exact q5/q6/classes PASS; 16 byte-identical warmup/repeats; 594 malformed/corruption checks, failures=0; nine forbidden-read и18 read/write probes PASS.
- hellwarrior: 12 bin-only fresh decodes; exact q5/q6/classes PASS; 16 byte-identical warmup/repeats; 594 malformed/corruption checks, failures=0; nine forbidden-read и18 read/write probes PASS.

Общие проверки V3: 36 unit tests, 135 дополнительных malformed metadata probes, 51 synthetic corruption check; восемь старых V1/V2 файлов exact+byte-identical. Старые выигрыши8152 B и2873 B сохранены. Python read-audit контролирует конкретную реализацию decoder; это instrumentation, не OS security sandbox. Public source и установленные зависимости доступны decoder; исходные checkpoint/export/targets/context/model arrays недоступны.

## Forecast и actual

| Scene | Mean8 vs | PREDICTED gross B | PREDICTED extra side B | PREDICTED net B | Actual payload saving B | Actual extra side B | Actual net B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | IID | 9791.682 | 5809.000 | 3982.682 | 10368 | 2758 | 7610 |
| bouncingballs | Geometry4 | 451.591 | 4538.000 | -4086.409 | 832 | 1207 | -375 |
| bouncingballs | Canonical8 | 2931.920 | -123.000 | 3054.920 | 2968 | -646 | 3614 |
| hellwarrior | IID | 6194.460 | 5700.000 | 494.460 | 6648 | 2365 | 4283 |
| hellwarrior | Geometry4 | 720.618 | 4450.000 | -3729.382 | 1020 | 823 | 197 |
| hellwarrior | Canonical8 | 2270.389 | -24.000 | 2294.389 | 2228 | -928 | 3156 |

Forecast переносит train-fit/test CE на все1048576 fine symbols и вычитает измеренный dry-model overhead. Actual использует all-scene fit, иные thresholds/masses, полное container framing и range payload. Finite16 masses поступают constriction0.4.2 Categorical(perfect=False), с coder precision24; конечный payload не обязан равняться Shannon estimate. Разница между прогнозом и файлом не подменяется одним числом. Отрицательный прогноз bouncingballs относительно Geometry4 проверен фактическим файлом.

В sparse_default_u16 каждая probability row хранит modal mass и число исключений (4 B), затем3 B на каждый symbol с иной mass. Поэтому изменение training sample size и integer normalization может заметно изменить стоимость транспорта даже при неизменном числе классов. Это проверено разбором уже сохранённых масс (sparse-transport-accounting.csv), без нового fitting:

| Scene | Model | Sample | Mass bytes | Exceptions |
| --- | --- | --- | --- | --- |
| bouncingballs | Geometry4 | heldout_train_seed0 | 1772 | 580 |
| bouncingballs | Geometry4 | actual_all_scene | 1982 | 650 |
| bouncingballs | Mean8 | heldout_train_seed0 | 6221 | 2047 |
| bouncingballs | Mean8 | actual_all_scene | 3065 | 995 |
| hellwarrior | Geometry4 | heldout_train_seed0 | 1709 | 559 |
| hellwarrior | Geometry4 | actual_all_scene | 1877 | 615 |
| hellwarrior | Mean8 | heldout_train_seed0 | 6044 | 1988 |
| hellwarrior | Mean8 | actual_all_scene | 2576 | 832 |

## Артефакты и повторение

- bouncingballs: все physical .bin (внешний артефакт; см. каталог исключённых ссылок); 12 transport budgets (внешний артефакт; см. каталог исключённых ссылок); best file manifests (внешний артефакт; см. каталог исключённых ссылок); независимые восстановленные массивы (внешний артефакт; см. каталог исключённых ссылок); malformed checks (внешний артефакт; см. каталог исключённых ссылок).
- hellwarrior: все physical .bin (внешний артефакт; см. каталог исключённых ссылок); 12 transport budgets (внешний артефакт; см. каталог исключённых ссылок); best file manifests (внешний артефакт; см. каталог исключённых ссылок); независимые восстановленные массивы (внешний артефакт; см. каталог исключённых ссылок); malformed checks (внешний артефакт; см. каталог исключённых ссылок).

```powershell
Set-Location '<PROJECT_ROOT>'
$py = '.tools/phase2-plotting-env/Scripts/python.exe'
$runRoot = 'research/mean8_l56_cross_scene_20261022_01'
& $py -B "$runRoot/run_actual.py" --scene bouncingballs
& $py -B "$runRoot/run_actual.py" --scene hellwarrior
```

Это команды выполненного запуска; они намеренно отказываются перезаписывать результаты. Для воспроизведения нового полного опыта создаётся новый уникальный run с копиями runner/protocol, новой проверкой hashes и подготовкой inputs. `--resume` проверяет прежние frozen inputs/source и продолжает только тот же незавершённый запуск. Для чтения готового файла:

```powershell
$checkRoot = Join-Path 'research' ('l56_decode_check_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
& $py -B -m research.experiment_bench.hashed_pair_v3.replay --input "$runRoot/hellwarrior/actual/streams/Mean8__sparse_default_u16.bin" --output $checkRoot
```

Fresh decode не требует outputs предыдущей пары. Совпадение с targets проверяет внешний auditor; decoder самостоятельно проверяет transmitted hashes. Публичный код сохранён в source_snapshot, версии — environment.json и requirements-decoder.txt. Контроль сохранности5153 прежних файлов и всех frozen inputs — FINAL_VALIDATION.json/integrity-final.json.

Actual sizes (внешний артефакт; см. каталог исключённых ссылок)
Overhead tradeoff (внешний артефакт; см. каталог исключённых ссылок)
