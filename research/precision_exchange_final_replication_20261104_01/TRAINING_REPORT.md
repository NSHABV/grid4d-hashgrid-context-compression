> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Training report: trex — RESOURCE_BLOCKED

Одна fresh seed0 full-попытка остановлена без завершения обязательной итерации50000. Pilot отдельно завершил5000 с исходным schedule50000; его optimizer state не переиспользовался. Официальный trex config и совместимость со standup зафиксированы до обучения в TRAINING_CONFIGURATION.json; capacity, forward, optimizer и schedule не менялись.

Full worker: completed_steps=9999, finite_loss_checks=10000, все проверенные loss конечны. Прерывание внутри сохранения iteration10000 Gaussian PLY: `scene.save` → `save_ply` → `elements[:] = list(map(tuple, attributes))`. Supervisor послал SIGTERM; raw status MONITOR_FAILURE, worker TERMINATED. Последняя telemetry содержит `RuntimeError('RESOURCE_BLOCKED: available RAM below1GiB')`, поэтому итог классифицирован RESOURCE_BLOCKED. Числовое available RAM в failed sample отсутствует; нельзя заменять его предыдущим sample или считать это доказанным OS OOM.

| Величина | Измеренное значение |
| --- | ---: |
| Pilot wall | 286.571686356 s |
| Full attempt wall | 1126.605895823 s |
| Full sampled total-device peak | 3957 MiB |
| Full sampled process-tree RSS peak | 6484115456 B |
| Worker RSS peak | 6742798336 B |
| Minimum recorded available RAM before failed sample | 1187536896 B |
| Exact available RAM at failing sample | NOT RECORDED |

Официальный train-only loader проверен:200наблюдений, official val/test20/20. Phase training data не содержит val/test images; автоматические quality evaluations отключены. Сохранился экспорт iteration5000 (deform.pth/point_cloud.ply/cfg_args); допустимого checkpoint50000 нет. Экспорт весов/PLY не является проверенным resume optimizer/RNG/scheduler. Исходные журналы и traceback сохранены; повторное обучение, меньший iteration count, другой seed и попытка weight-only resume не выполняются.

Источники: full/monitor/supervisor-final.json, worker-final.json, telemetry.jsonl; full/model/TRAIN_LOADER.json; TRAINING_CONFIGURATION.json, FULL_RUN_GATE.json. Точные хеши и ограничения — BLOCKED_REPLICATION_SUMMARY.json. Общий разбор — FINAL_REPLICATION_REPORT.md. Финальная сохранность будет отражена в PRESERVATION_FINAL.json; этот отчёт не утверждает, что полный аудит уже завершён.

Compression, validation, freeze, test и final encoding trex не начались. Это техническая незавершённость, не научный отрицательный результат. Текущая серия закрывается; новая full-попытка автоматически не разрешена.
