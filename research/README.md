# Карта исследовательских материалов

Автор НИР/ВКР: **Шабанов Н.А.** При реализации и оформлении использовались ИИ-агенты; [раскрытие помощи и ответственности](../docs/AI_ASSISTANCE.md). Измерения, исходные таблицы и проверки отделены от интерпретаций.

## Рекомендуемый порядок чтения

1. [Итоговая научная глава](context_coding_research_synthesis_20261108_01/CONTEXT_CODING_CHAPTER.md) и [исследовательская позиция](context_coding_research_synthesis_20261108_01/RESEARCH_POSITION.md).
2. [Закрывающий PREVIOUS8 reserve report](previous8_reserve_batch_20261108_01/PREVIOUS8_RESERVE_REPORT.md), [шесть сцен](previous8_reserve_batch_20261108_01/SIX_SCENE_SUMMARY.csv), [вклады уровней](previous8_reserve_batch_20261108_01/PER_LEVEL_COSTS.csv).
3. [Actual prototype](frozen_previous8_actual_20261108_01/FROZEN_PREVIOUS8_ACTUAL_REPORT.md) и [формат](frozen_previous8_actual_20261108_01/FORMAT_SPEC.md).
4. [Атрибуция](context_gain_attribution_20261107_01/CONTEXT_GAIN_ATTRIBUTION_REPORT.md) и [предшествующая диагностика](context_compression_headroom_20261107_01/CONTEXT_COMPRESSION_HEADROOM_REPORT.md). Их estimates и исторический WEAK_SIGNAL не заменяются поздними actual измерениями.

## Межуровневый контекст и H4

| Этап | Материалы |
|---|---|
| Пространственные соответствия | [Geometry/coarse contexts](hashed_context_diagnostic_20261013_01/DIAGNOSTIC_REPORT.md) |
| Разброс и held-out | [Mean/Std](hashed_dispersion_heldout_20261013_01/HELDOUT_REPORT.md), [Count6](hashed_multiplicity_study_20261014_01/MULTIPLICITY_REPORT.md) |
| Mean8 L4→L5 | [bouncingballs](hashed_mean8_bitstream_20261015_01/BITSTREAM_REPORT.md), [hellwarrior](mean8_hellwarrior_validation_20261020_01/BITSTREAM_REPORT.md) |
| Mean8 L5→L6 | [Две сцены, смешанный результат](mean8_l56_cross_scene_20261022_01/BITSTREAM_REPORT.md) |
| H4 clustering | [Development](pmf_clustering_evaluation_20261028_01/H4_EXPERIMENTAL_REPORT.md), [третья сцена](h4_independent_validation_20261029_02/H4_THIRD_SCENE_RESULTS.md), [четвёртая сцена](h4_fourth_scene_validation_20261029_01/H4_FOURTH_SCENE_RESULTS.md) |

Результаты отдельных пар, разных quantizers и контейнеров нельзя складывать в выигрыш полного spatial-файла. Отрицательные результаты сохранены. Материалы quantization/precision exchange включены как отдельная вспомогательная ветка; её distortion не является эффектом lossless entropy stage.

## Что можно запустить

Проверенный CPU-маршрут находится в [корневом README](../README.md). `experiment_bench`, `hashgrid_analysis` и `grid4d` сохраняют исходную структуру, поскольку некоторые codecs извлекают функции из других публичных файлов через AST. Удаление «неиспользуемого» файла может нарушить decoder.

Исторические runners и конфигурации не превращены в универсальный experiment manager. Для их полных запусков требуются внешние данные и прежние артефакты; наличие отчёта не означает наличие всех его входов в Git. Проверяемая синтетическая часть выделена явно. [Границы воспроизводимости](../docs/REPRODUCIBILITY.md).

Публичные копии документов имеют предисловие и отдельные хеши. Локальные оригиналы остаются неизменными. [Каталог исключённых ссылок](../docs/EXCLUDED_REFERENCES.json) объясняет замену ссылок на отсутствующие тяжёлые артефакты.
