> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Ограниченный выбор точности: независимая сцена mutant

**PASS_COMPLETED** означает завершённый протокол. Technical:PASS; calibration:FEASIBLE; test:TRANSFER_PASS.

Frozen решение: уровень **L4** (zero-based), вариант **M10**. Бюджет **1613635 B**, PSNR target=M16−0.05 dB того же уровня, SSIM>=R2, LPIPS_STANDARD_VGG<=R2. Параметры1.25/0.05 — заранее заданные исследовательские условия, не требования приложения.

## Входы и разделение

D-NeRF mutant загружен только из ранее проверенного официального источника (dataset-manifest.json, source_snapshot).193 файла,38,236,228 B распаковано. Прежнее использование mutant найдено только в config inventory и неисполненном fallback; качество этой сцены при разработке процедуры не использовалось. Checkpoint — fresh seed0, фиксированная итерация50000; SHA256 376d0d19d1c01241c3f4972244c043d675e37ce1abbfe09ab2cd953d1b0f3480.

150 train /20 calibration /20 test. Ни одной общей пары по path, SHA256 изображения или точной observation(camera matrix,intrinsics,time). Все calibration observations сохранены. Timestamps совпадают между splits, intrinsics общие, basename IDs локальны split; это не тождественные наблюдения. Кадры одной сцены остаются коррелированными, статистическая независимость не заявляется. Подробности SPLIT_AUDIT.md. Test до freeze использовался только для hashes/metadata; никакого test quality fitting.

## Calibration: выбор уровня

| level | PSNR | gain |
| --- | --- | --- |
| 4 | 39.26704407 | 0.3582420349 |
| 10 | 39.18372345 | 0.2749214172 |
| 7 | 39.11901855 | 0.2102165222 |
| 9 | 39.07740021 | 0.168598175 |
| 8 | 39.06798553 | 0.1591835022 |
| 5 | 38.99901581 | 0.09021377563 |
| 6 | 38.96457672 | 0.05577468872 |

Выбран максимальный прирост RESTORE относительно R2; exact tie — меньший индекс. После выбора уровень не изменён. Это sensitivity-first процедура, не глобальный optimum по level×precision.

## Calibration: выбор точности

| variant | bytes | PSNR | SSIM | LPIPS_STANDARD_VGG | budget_pass | PSNR_pass | SSIM_pass | LPIPS_pass | all_constraints_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R2 | 1290908 | 38.90880203 | 0.990441978 | 0.008548079059 | True | False | True | True | False |
| M10 | 1359477 | 39.22925949 | 0.9912142754 | 0.008262714371 | True | True | True | True | True |
| M12 | 1431970 | 39.26680374 | 0.9912900925 | 0.008236875758 | True | True | True | True | True |
| M16 | 1568645 | 39.2669487 | 0.9912868738 | 0.008241853677 | True | True | True | True | True |

Выбор минимального файла среди feasible; exact byte tie R2,M10,M12,M16. Никаких posthoc численных допусков. Mean metrics из FP32 per-view reductions; primary PSNR — mean(per-view PSNR). Freeze с контрольной суммой:SELECTION_FREEZE.json + SHA256, проверенный test runner.

## Test: только фиксированные контроли

| variant | is_frozen_choice | bytes | PSNR | SSIM | LPIPS_STANDARD_VGG | budget_pass | PSNR_gap_to_M16 | quality_pass | all_constraints_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R2 | False | 1290908 | 38.6794548 | 0.989810288 | 0.008672310039 | True | 0.3119468689 | False | False |
| M10 | True | 1359477 | 38.95095062 | 0.9903510809 | 0.008405282162 | True | 0.0404510498 | True | True |
| M12 | False | 1431970 | 38.99059296 | 0.9904348254 | 0.008389599621 | True | 0.0008087158203 | True | True |
| M16 | False | 1568645 | 38.99140167 | 0.9904336929 | 0.008389635012 | True | 0 | True | True |

Итог переноса: **TRANSFER_PASS**. Контрольные test scores не использовались для переизбрания варианта. Если chosen совпадает с fixed strategy, их результаты идентичны; это не превосходство selector над этой стратегией.

## Rate и остаточная потеря относительно R0

| variant | saving_vs_M16_B | extra_vs_R2_B | PSNR_loss_to_R0 | SSIM_loss_to_R0 | LPIPS_excess_to_R0 |
| --- | --- | --- | --- | --- | --- |
| R2 | 277737 | 0 | 5.3019104 | 0.006552278996 | 0.002899710555 |
| M10 | 209168 | 68569 | 5.030414581 | 0.006011486053 | 0.002632682677 |
| M12 | 136675 | 141062 | 4.990772247 | 0.005927741528 | 0.002617000137 |
| M16 | 0 | 277737 | 4.989963531 | 0.005928874016 | 0.002617035527 |

| variant | views | PSNR | SSIM | LPIPS_STANDARD_VGG |
| --- | --- | --- | --- | --- |
| R0 | 20 | 43.9813652 | 0.9963625669 | 0.005772599485 |
| RESTORE_L4 | 20 | 38.99154282 | 0.9904340506 | 0.008388958871 |

Target относительно M16 одного уровня не означает восстановление R0. Все signed per-view differences сохранены в PER_VIEW_METRICS.csv; ни отрицательные значения, ни малые различия не обнулены.

## Файлы, correctness и ресурсы

| variant | filesystem_bytes | level_member_bytes | metadata_member_bytes | framing_bytes |
| --- | --- | --- | --- | --- |
| R2 | 1290908 | 1287999 | 1185 | 1724 |
| M10 | 1359477 | 1356534 | 1219 | 1724 |
| M12 | 1431970 | 1429025 | 1221 | 1724 |
| M16 | 1568645 | 1565699 | 1222 | 1724 |

Четыре physical standalone spatial ZIP/NPY schema v2 файла, DEFLATE6, все16 уровней. Полный размер включает metadata/framing. p10/p12/p16 — коды uint16, без bitpacking; остальные15 уровней — те же frozen uint8. Общие scene-specific min/max исходного full xyz, прежний порядок FP64 arithmetic и nearest-even. Файл содержит per-level precision map; R2 означает все8бит без специального улучшенного уровня. Алгоритм выбора/quality данные decoder не нужны. Это spatial tensor only, не весь Grid4D.

4 fresh-process standalone decodes,64 exact arrays, exact canonical metadata/full dequantization,byte-identical rebuild,15 unchanged levels,p8/p16 regression,synthetic arithmetic/corruption tests:PASS. Python read audit разрешает только archive/code/dependencies; это access check, не OS sandbox. Отдельная renderer integration читает исходные Gaussian/MLP/temporal параметры, проверяет их неизменность и hash xyz перед каждым forward.240 calibration и120 test renders. STANDARD VGG normalize=True один раз; LPIPS_LEGACY не используется.11 selector и17 watchdog tests пройдены.

Training wall 9739.018s; total GPU peak 4353.0MiB. Sequential postprocessing wall 575.835s; sampled maximum process-tree RSS 3.992GiB. Точные времена encode/decode — FILE_SIZES.csv; guards/resources — RESOURCES.csv и pipeline_logs. RSS sum может повторно считать shared pages. Размеры физические, не entropy forecast.

## Воспроизведение и границы вывода

Pinned WSL audit-env: Python3.10.21,PyTorch2.7.0+cu128,NumPy1.26.4,zlib1.3.2. Исходники/runtime hashes — PREREGISTERED_PROTOCOL.json,RUNTIME.json,UNCHANGED_HELPERS.json,SELECTION_FREEZE.json; полный input bundle — full/model. После подготовки dataset и split audit: train.sh pilot pilot_retry_01; approve_full_from_pilot.py; train.sh full. Затем pipeline.sh setup,calibration,precision,freeze,test; report_completed.py; finalize_completed.py. Каждый этап пишет новый marker, повторный запуск завершённого этапа без анализа состояния не допускается. Прежние артефакты не перезаписывались.

Один новый checkpoint не доказывает статистическую значимость или новизну стандартного constrained selector. Никаких BD-rate, новых coders/H4/H5, новых bit depths/minmax, multilayer optimization, scene/seed selection по результату. Один следующий научный шаг: независимая репликация уже замороженного правила с теми же1.25/0.05 на заранее выбранной новой сцене, без изменения policy по текущему test. Она здесь не запускается.

## Отклонения запуска, без изменения научного протокола

Обучение было приостановлено пользователем около42789 и продолжено в том же живом процессе, с прежними optimizer/RNG. Watchdog заменён внешним наблюдателем с тем же лимитом10800s активного времени; пауза исключена, исходный worker не перезапускался. Raw worker elapsed включает паузу; приведённое training time — консервативно учтённое активное время. Проверки и PID/start-time — RESUME_VALIDATION.json/RESUME_LAUNCH.json.

Первая подготовка calibration завершилась SyntaxError до исполнения кода: в записи checkpoint metadata не хватало одной закрывающей скобки. Автоматический общий classifier назвал любой child failure BLOCKED_NEEDS_ULTRA; минимальная диагностика однозначно установила parse-only ошибку orchestration, без вызова quantizer/codec/forward. Исходники, маркеры и traceback сохранены в orchestration_fix_001; исправлена только скобка, весь новый код повторно проверен AST, retry имеет отдельный лог. Integrity checks не отключались. Подробности ORCHESTRATION_SYNTAX_CORRECTION.json. Старые отчёты неизменны; начальная версия INPUT_MANIFEST сохранена и проверена перед разрешением фактических dataset/checkpoint paths.

После завершения всех четырёх архивов и exact checks обнаружена отдельная ошибка финального print: имя argparse namespace было перекрыто индексом цикла. Архивы/параметры уже были корректно записаны; они не пересоздавались. Исправлено только имя служебной переменной, выполнена независимая read-only проверка64 массивов,metadata,canonical xyz,p16 и всех архивных hashes. ORCHESTRATION_LOGGING_CORRECTION.json,POST_LOGGING_ARTIFACT_VALIDATION.json и orchestration_fix_002 сохраняют доказательства; математические helpers не изменялись. RESOURCES.csv включает измеренные короткие неудачные orchestration attempts отдельно от успешных стадий.
