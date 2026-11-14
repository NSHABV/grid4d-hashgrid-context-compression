> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Mean8 xyz L5→L6: указатель результатов

Запуск `mean8_l56_cross_scene_20261022_01`, protocol freeze22 октября, завершение23 октября2026. Считать запуск завершённым только при `FINAL_VALIDATION.json` со статусом `PASS_COMPLETED`.

| Документ | Содержание |
|---|---|
| EXPERIMENT_PROTOCOL.md (внешний артефакт; см. каталог исключённых ссылок) | Фиксированные модели, критерии, порядок измерений |
| [PREREGISTERED_PROTOCOL.json](PREREGISTERED_PROTOCOL.json) | Исходный frozen protocol |
| INPUT_AUDIT.md (внешний артефакт; см. каталог исключённых ссылок) | Checkpoints, SHA256, geometry, quantizers, pilot |
| CONTEXT_VALIDATION.md (внешний артефакт; см. каталог исключённых ссылок) | Lookup, арифметика, независимое воспроизведение классов |
| [HELDOUT_REPORT.md](HELDOUT_REPORT.md) | Train-only CE обеих сцен |
| [BITSTREAM_REPORT.md](BITSTREAM_REPORT.md) | Реальные файлы, все затраты, exact decode |
| CROSS_LEVEL_COMPARISON.md (внешний артефакт; см. каталог исключённых ссылок) | L4→L5 против L5→L6 |
| [PERFORMANCE_REPORT.md](PERFORMANCE_REPORT.md) | CPU encoder/decoder, компоненты времени, cold/warm и RSS |
| NEXT_RESEARCH_DECISION.md (внешний артефакт; см. каталог исключённых ссылок) | GO/NO-GO и один следующий диагностический эксперимент |
| [FINAL_VALIDATION.json](FINAL_VALIDATION.json) | Итоговая сохранность и manifest всех артефактов |

Physical streams: bouncingballs (внешний артефакт; см. каталог исключённых ссылок), hellwarrior (внешний артефакт; см. каталог исключённых ссылок). Каждый каталог содержит12 вариантов:4 модели ×3 транспорта. Лучшие варианты перечислены в `<scene>/actual/best.json`; полная physical стоимость — `actual-sizes.csv`, результаты всех transports — `<scene>/actual/results.csv`.

Исходный код: `source_snapshot/` с `source-snapshot.json`; среда: `environment.json`, `requirements-decoder.txt`, `requirements-analysis.txt`. Проверки: `v3-validation-001/validation.json`, `heldout-independent-001/audit.json`, `INDEPENDENT_AUDIT_001.json`, `REPORT_QA_001.json`, `FIGURE_QA_001.json`, `<scene>/corruption-001/corruption-checks.json`.

Точки продолжения сохраняют историю, не заменяют друг друга. Последняя завершённая — `CONTINUATION_005_COMPLETE.md`. Не перезапускать writing stages в завершённый каталог. Следующий опыт требует нового уникального run.
