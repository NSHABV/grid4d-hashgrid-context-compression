> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Независимая репликация precision exchange: D-NeRF standup

Статус завершения и сохранности определяется FINAL_VALIDATION.json. PASS_COMPLETED означает корректно завершённый протокол, а не обязательный положительный результат.

## Происхождение и переносимый протокол

Standup заранее указан пользователем. INDEPENDENCE_AUDIT.json подтверждает отсутствие его использования для настройки exchange policy по доступным записям проекта и известного WSL storage; прежние конфиги, каталоги и capacity inventories не считаются измерением качества. Пять development-сцен не объединяются с новой сценой в шесть независимых подтверждений. Официальный источник и byte-range загрузка только standup: DATA_SOURCE_PROVENANCE.json и dataset-manifest.json.

One new fresh seed0 full run after separate pilot; completed iteration50000 fixed before quality; official standup config identical to prior mutant, unchanged pinned upstream numerical loop

Checkpoint: `research/precision_exchange_independent_20261103_01/full/model/deform/iteration_50000/deform.pth`; SHA256 `1eea264e8b8af42c020d42e5b60ef0b49fe3128b3f452d9c536e3812adea20a7`. Завершённая итерация 50000, seed 0. Training/test access audit: TRAINING_REPORT.md, full/model/TRAIN_LOADER.json и train_views.csv. Standup config совпадает с прежним mutant; capacity, schedule и Grid4D forward не менялись.

## Official split

Train/val/test: {'train': 150, 'val': 20, 'test': 20}. Strict split status PASS: отсутствуют val↔train/test совпадения по пути, image bytes/decoded pixels или полной observation. Все официальные observations сохранены; никаких exclusions. Metadata/image hashing до freeze не является quality evaluation. Фактический train-only loader проверен во время обучения. Подробности: SPLIT_AUDIT.md.

## Зафиксированный выбор

| scene | G8_B | feasible_D_of7 | feasible_E_of42 | D_best | E_best | D_matched | FINAL_choice | FINAL_KIND |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standup | 1736798 | 7 | 4 | G8 | G8 | — | G8 | G8 |


Перенесён алгоритм выбора, а не E_10_4. Все 50 конфигураций построены; в основном validation участвуют только файлы <= нового G8. Строгие SSIM≥G8 и LPIPS≤G8, максимум PSNR, затем при точном равенстве меньшие bytes, меньше изменённых уровней, числовой lexicographic tie. Диагностический D_matched не изменяет primary selection. Общий freeze предшествует test; одинаковые роли измеряются один раз.

## Validation

| state | roles | FINAL_choice | donor | recipient | bytes | feasible | diagnostic_only | delta_B_vs_G8 | delta_size_percent_vs_G8 | PSNR | SSIM | LPIPS_STANDARD_VGG | delta_PSNR | delta_SSIM | delta_LPIPS_STANDARD_VGG | PSNR_gap_R0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | reference | False | — | — | — | — | False | — | — | 46.2033424377 | 0.996551632881 | 0.00582035863772 | 2.02276229858 | 0.000995874404907 | -0.000586223322898 | 0 |
| G8 | G8+D_best+E_best | True | — | — | 1736798 | True | False | 0 | 0 | 44.1805801392 | 0.995555758476 | 0.00640658196062 | 0 | 0 | 0 | 2.02276229858 |


## Test

| state | roles | FINAL_choice | donor | recipient | bytes | feasible | diagnostic_only | delta_B_vs_G8 | delta_size_percent_vs_G8 | PSNR | SSIM | LPIPS_STANDARD_VGG | delta_PSNR | delta_SSIM | delta_LPIPS_STANDARD_VGG | PSNR_gap_R0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | reference | False | — | — | — | — | False | — | — | 46.6131057739 | 0.99690425396 | 0.00560451950878 | 2.34365081787 | 0.00106626749039 | -0.000651697162539 | 0 |
| G8 | G8+D_best+E_best | True | — | — | 1736798 | True | False | 0 | 0 | 44.2694549561 | 0.995837986469 | 0.00625621667132 | 0 | 0 | 0 | 2.34365081787 |


R0 — исходная FP32 модель, не quantized archive; её File B не подменяется размером другого объекта. Все metrics получены прямым новым rendering, включая G8 и R0; старое качество не переиспользовалось. Полные raw metrics: ALL_QUALITY_RESULTS.csv. FINAL_choice — отметка роли, а не дублирующий замер.

## Различные down-only сравнения

| split | comparison | candidate | baseline | delta_B | delta_size_percent | delta_PSNR | delta_SSIM | delta_LPIPS_STANDARD_VGG | PSNR_worse_views | SSIM_worse_views | LPIPS_worse_views |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| val | D_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| val | E_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| val | E_vs_D_best | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| test | D_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| test | E_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| test | E_vs_D_best | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |


E vs G8 показывает итоговый обмен. E vs D_best сравнивает с лучшим down-only, выбранным прежним правилом. E vs D_matched меняет только recipient при том же donor. Эти эффекты не смешиваются. Положительная ΔLPIPS означает ухудшение; все дельты candidate−baseline. Более качественный, но больший E не означает Pareto dominance над D. Сравнение выполняется под одним cap, не при точно равном rate. PER_VIEW_METRICS.csv и PAIRED_VIEW_DIFFERENCES.csv сохраняют все signed покадровые различия без округления и новых допусков.

## Физические байты и оплата повышения точности

| state | donor | recipient | bytes | donor_saving_B | recipient_cost_B | metadata_delta_B | framing_delta_B | total_delta_B | unused_budget_B | net_saving_percent_vs_G8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G8 | — | — | 1736798 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |


Donor saving = минус фактическая разность compressed member; recipient cost = его фактическая разность. Net подтверждён размером одного полного файла. Metadata/framing учтены. P7 не предполагается автоматически меньшим, p10 — автоматически большим. RATE_AUDIT.csv содержит все 50 файлов, включая overbudget.

## Раздельные статусы

```json
{
  "TECHNICAL_COMPLETE": "MEASUREMENTS_PASS; final status in FINAL_VALIDATION.json",
  "NEW_SCENE_PROTOCOL": "PASS",
  "FEASIBILITY": "PASS",
  "CALIBRATION_GAIN": false,
  "TEST_TRANSFER": "NOT_APPLIED_G8",
  "ADDED_VALUE_VS_DOWN_ONLY": "NOT_APPLIED_G8",
  "MATCHED_RECIPIENT_EFFECT": "NOT_APPLICABLE",
  "FINAL_KIND": "G8",
  "FINAL_choice": "G8",
  "E_validation_preferred_to_D": false,
  "D_best": "G8",
  "E_best": "G8",
  "D_matched": null
}
```

CALIBRATION_GAIN и TEST_TRANSFER требуют положительный PSNR gain и неухудшение средних SSIM/LPIPS относительно G8. ADDED_VALUE и MATCHED_RECIPIENT_EFFECT проверяются отдельно относительно D_best и D_matched. G8 fallback или down-only FINAL не являются положительным подтверждением exchange. При TRANSFER_FAIL новые пары не подбираются.

## Encoder search и финальное кодирование без поиска

```json
{
  "feasible_primary_states_including_G8": 12,
  "feasible_D": 7,
  "feasible_E": 4,
  "validation_quality_states_including_R0_and_diagnostic": 13,
  "validation_render_frames": 260,
  "primary_candidate_render_frames": 240,
  "extra_overbudget_diagnostic_frames": 0,
  "test_quality_states": 2,
  "test_render_frames": 40,
  "selection_seconds": 0.12403729299995803,
  "shared_quantization_seconds": 0.11229171499962831,
  "compression_seconds": 36.57520420500441,
  "rebuild_seconds": 37.05148803099928,
  "cold_decode_seconds": 199.07259058099953,
  "internal_decode_seconds": 9.65060971099956,
  "validation_jobs_wall_seconds": 659.9929030329997,
  "test_jobs_wall_seconds": 76.90932367300002,
  "CPU_jobs_wall_seconds": 372.56334819500063,
  "final_encoding_without_search": {
    "status": "PASS",
    "state": "G8",
    "bytes": 1736798,
    "byte_identical_selected_archive": true,
    "sha256": "f8a3c3f293f36a00f8db0574cdefaf7dc07142f42476739bd80a975e6ae65c0e",
    "model_load_seconds": 0.3143510599999786,
    "quantization_and_range_seconds": 0.057322887999987415,
    "manifest_and_compression_seconds": 0.575197892999995,
    "write_seconds": 0.01123065100000531,
    "total_seconds": 1.3933612640000206,
    "freeze_verification_seconds": 0.12326150899997401,
    "wall_with_verification_seconds": 1.516626400000007,
    "search_performed": false,
    "calibration_images_read": false,
    "scope": "One encoding with supplied frozen precision map; includes its own original FP32 range and quantization. total_seconds excludes separate freeze verification, which rechecks choose on stored scores. No candidate search, new fitting or image/quality evaluation performed."
  }
}
```

Поиск оплачивает 50 compression/decode проверок и прямой validation render всех feasible вариантов. Финальный standalone encoding выполняет только заданную frozen precision map и заново получает range/codes из исходного FP32; он не читает calibration images и не ищет карту. Decoder читает только архив и публичный runtime, не выполняет поиск. Cold decode включает startup; internal decode вложен в него. Rebuild — отдельная проверка, не обязательная стоимость production encoding. Shared quantization учтена один раз. CPU_jobs/validation/test wall включают вложенные операции, поэтому их нельзя складывать повторно с отдельными внутренними таймерами.

## Ресурсы

```json
{
  "training_full_wall_seconds": 4550.099646873001,
  "training_pilot_wall_seconds": 191.818997982,
  "training_peak_process_tree_RSS_bytes": 5645520896,
  "training_minimum_available_RAM_bytes": 2073223168,
  "training_peak_total_device_MiB": 3311.0,
  "training_peak_torch_allocated_bytes": 1227548672,
  "training_peak_torch_reserved_bytes": 1916796928,
  "post_training_peak_process_tree_RSS_bytes": 4310216704,
  "post_training_peak_total_device_MiB": 2835,
  "post_training_minimum_available_RAM_bytes": 2651643904,
  "quality_peak_torch_allocated_bytes": 1685593088,
  "quality_peak_torch_reserved_bytes": 1742733312,
  "dependency_preparation_and_hashing_seconds": 0.3846906000399031,
  "final_hashing_seconds_source": "PRESERVATION_FINAL.json (written only after this report is reviewed)"
}
```

Training, CPU compression/decode, GPU quality и hashing разделены. GPU jobs последовательны, одна модель за раз. Sampled process-tree RSS может повторно учитывать shared pages; total-device VRAM включает другие процессы/desktop. Точные per-job guards: RESOURCES.csv; CUDA allocated/reserved по фазам: TORCH_RESOURCES.csv. Финальный protected-file hashing и отчётность не входят в codec/runtime speed claims.

## Точность и сохранность

50 полных exchange-v5 ZIP/NPY DEFLATE6, 800 exact level arrays, exact metadata/canonical FP32, unchanged masks/other weights и byte-identical rebuild. 43 прежних scalar/storage fixtures и один read-only regression прежнего E_10_4; прежний поиск или training не повторялись. Selection core имеет exact source equality с прежним. Fresh decoder имеет Python read audit, который не является OS sandbox. Исходный GLOBAL range общий для всех 16 уровней и p7/p8/p10; FP64 step/divide/rint nearest-even/clip-before-cast и FP32 reconstruction прежние. P7/p8 uint8, p10 little-endian uint16, без bitpacking. Renderer, SSIM и LPIPS_STANDARD_VGG с normalize=True один раз неизменны.

## Ограничения и следующий шаг

Один новый checkpoint не доказывает универсальность или статистическую значимость на уровне сцен. Кадры одной сцены коррелированы. Результат относится ко всему spatial xyz, не ко всей сцене и не к ускорению FP32 renderer. Улучшение при p7 само по себе не доказывает регуляризацию, безвредность уровня или возможность pruning. Проверены только один donor7/recipient10, L4–L10, GLOBAL scope и данный DEFLATE transport. Ни H5, ни новые p/ranges/compressors не реализованы.

Следующий шаг: заранее зарегистрированная независимая репликация этой же процедуры и matched-donor контроля на ещё одном checkpoint, без изменения rules по результатам standup. Она не запускается автоматически.

## Воспроизведение

SOURCE_REQUEST.txt, PREREGISTERED_PROTOCOL.json, INPUT_MANIFEST.json, frozen_source/, runtime_snapshot/, TRAINING_CONFIGURATION.json и исходные guards задают точный запуск. Все прежние документы неизменяемы; новое воспроизведение требует нового уникального каталога. Текущие команды после входного/training этапа:

```text
bash <PROJECT_ROOT>/research/precision_exchange_independent_20261103_01/python.sh run.py setup
bash <PROJECT_ROOT>/research/precision_exchange_independent_20261103_01/python.sh run.py rate
bash <PROJECT_ROOT>/research/precision_exchange_independent_20261103_01/python.sh run.py seal
bash <PROJECT_ROOT>/research/precision_exchange_independent_20261103_01/python.sh run.py pilot
bash <PROJECT_ROOT>/research/precision_exchange_independent_20261103_01/python.sh run.py validation
bash <PROJECT_ROOT>/research/precision_exchange_independent_20261103_01/python.sh run.py matched
bash <PROJECT_ROOT>/research/precision_exchange_independent_20261103_01/python.sh run.py freeze
bash <PROJECT_ROOT>/research/precision_exchange_independent_20261103_01/python.sh run.py test
bash <PROJECT_ROOT>/research/precision_exchange_independent_20261103_01/python.sh run.py final_encoding
bash <PROJECT_ROOT>/research/precision_exchange_independent_20261103_01/python.sh run.py runtime_after
bash <PROJECT_ROOT>/research/precision_exchange_independent_20261103_01/python.sh report.py
.tools/phase2-plotting-env/Scripts/python.exe -B research/precision_exchange_independent_20261103_01/finalize.py
```

Фактические shell wrappers и stage names проверить по run.py/python.sh; команды здесь не разрешают перезаписывать готовые результаты. Final seal запускается только после проверки отчёта, один полный protected SHA audit. После завершения — STOP.
