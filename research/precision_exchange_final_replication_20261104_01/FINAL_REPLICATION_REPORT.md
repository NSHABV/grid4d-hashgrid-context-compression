> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Заключительная репликация precision exchange: trex — RESOURCE_BLOCKED

**Технический исход E. Полное обучение не завершено; эффективность compression на trex не измерена.** Это не G8 fallback, не TRANSFER_FAIL и не отрицательный научный результат precision exchange. Финальный аудит сохранности отражается отдельно в FINAL_VALIDATION.json; PASS_COMPLETED научной репликации не заявляется.

## Происхождение и splits

Trex заранее выбрана пользователем для ровно одной заключительной репликации после известного результата standup. INDEPENDENCE_AUDIT.json: PASS / NEW_SCENE_PROTOCOL по доступному проекту и известному WSL storage. Совместная пререгистрация обеих проверочных сцен до начала серии не утверждается.

Из ранее проверенного официального D-NeRF источника получена только trex: 243 файлов, 46444349 B передачи; каталог, CRC и SHA256 сохранены в dataset-manifest.json/download-attempt-004.json. Источник: DATA_SOURCE_PROVENANCE.json. Фактические official splits **200/20/20**, все observations сохранены; отличие от первоначального ожидания 150 train зафиксировано до обучения. Strict split audit PASS, без val↔train/test совпадений по прежнему contract. Фактический full loader PASS, только 200 train observations; автоматические quality evaluations отключены.

## Почему остановлено обучение

Одна разрешённая fresh seed0 full-попытка должна была завершить 50000 итераций. Pilot с исходным schedule завершил 5000 отдельно. Full завершил **9999 training bodies**; loss проверен на конечность 10000 раз. Во время сохранения iteration10000 supervisor послал SIGTERM. Traceback фиксирует `scene.save` → `GaussianModel.save_ply` → `elements[:] = list(map(tuple, attributes))`.

Последняя telemetry-запись содержит точный текст `RuntimeError('RESOURCE_BLOCKED: available RAM below1GiB')`. Исходный supervisor обозначил это **MONITOR_FAILURE**; исследовательская классификация — **RESOURCE_BLOCKED**, поскольку конкретное исключение сообщает crossing RAM guard 1 GiB. Исходные статусы и traceback сохранены без исправления. Это не ошибка entropy coder и не доказательство OS OOM.

Числовое значение available RAM в неуспешном sample **не записано**: исключение возникло до append. Последнее успешное sample: 1311059968 B; минимум успешных записей 1187536896 B. Эти числа нельзя подставлять вместо отсутствующего failed sample. Лимит времени 10800 s не достигнут; sampled GPU peak ниже 7168 MiB. Причина и evidence: full/monitor/telemetry.jsonl, supervisor-final.json, worker-final.json; хеши — BLOCKED_REPLICATION_SUMMARY.json.

Имеются только weight/PLY exports **iteration5000** этой full-попытки; обязательного checkpoint50000 нет. Это диагностические сохранённые файлы, не допустимый checkpoint эксперимента и не доказанный resume optimizer/RNG/scheduler. Одна full-попытка уже израсходована: restart, другой seed, сокращение iterations, ослабление guards и загрузка только весов как эквивалентного resume не выполняются. Предыдущая отдельная prelaunch GPU-блокировка сохранена в RESOURCE_BLOCKED_20261107_01.json; после явного продолжения пользователя она была преодолена до этой единственной full-попытки. Она не является второй training-попыткой.

## Измерения precision exchange

Все 50 конфигураций и неизменные selector/quantizer/transport definitions зарегистрированы, но их вычислительная стадия не началась. G8 budget, feasible D/E, выбранные уровни, actual archive bytes, validation/test quality, R0 gaps, matched-donor effect, compression/decode/search/final-encoding time — **NOT_MEASURED / null**. Ноль созданных candidate archives не означает нулевой размер или неуспех codec.

FEASIBILITY и CALIBRATION_GAIN — NOT_MEASURED; TEST_TRANSFER — NOT_MEASURED_RESOURCE_BLOCKED; FINAL_KIND — NOT_MEASURED. D_best/E_best/FINAL/D_matched отсутствуют. Selection freeze и test rendering не выполнялись. Готовая модель другой сцены или checkpoint5000 не подставлялись. Read-only rejection summary по quality также неприменим: новых validation scores нет.

## Выполненные проверки и стоимость

Пройдены 25 training guard/loader tests, 12 split tests, 24 selection tests и 6 reporting tests. Сохранены source equality и runtime/preflight evidence. Новая scalar/storage stage, один старый codec-file regression, 50 fresh-process decodes, rebuild и unchanged-weights rendering checks **не запускались**; их успех не приписывается trex. Исторические sealed-результаты читаются только для заключения серии.

| Величина | Измеренное значение |
| --- | ---: |
| Pilot wall | 286.571686356 s |
| Full attempt wall | 1126.605895823 s |
| Full sampled total-device peak | 3957 MiB |
| Full sampled process-tree RSS peak | 6484115456 B |
| Worker RSS peak | 6742798336 B |
| Minimum recorded available RAM before failed sample | 1187536896 B |
| Exact available RAM at failing sample | NOT RECORDED |

Resource telemetry неполна для failed sample; process-tree RSS может повторно учитывать shared pages, total-device включает desktop. Pilot forecast был оценкой, не гарантией full training. Training отдельно от compression; compression procedure не измерена. Время подготовки этих двух отчётов записано в BLOCKED_REPORT_COMPLETE.json, итоговый hashing — в отдельном root preservation record.

## Сохранность и закрытие

Исходные logs, checkpoint5000, данные, snapshots и предыдущие документы сохранены. BLOCKED_REPLICATION_SUMMARY.json содержит точные статусы и source hashes; EXCHANGE_SERIES_RESULTS.csv/EXCHANGE_SERIES_SUMMARY.json — семь строк с trex null; EXCHANGE_SERIES_CONCLUSION.md — научное заключение. Полный финальный аудит защищённых файлов выполняется root один раз отдельно; обычный finalize.py, требующий checkpoint50000, здесь не применяется.

Серия текущей версии закрывается с технически незавершённой trex. Новая сцена/checkpoint/seed, корректировка правил и H5 не предлагаются и не запускаются. Дальнейшая НИР требует отдельного стратегического решения.

CURRENT_EXCHANGE_REPLICATION_SERIES_CLOSED
