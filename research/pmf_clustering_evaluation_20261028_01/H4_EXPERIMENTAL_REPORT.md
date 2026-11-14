> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# H4 PMF clustering: эксперимент 28.10.2026

**Итог: EXPLORATORY GO для L5; NO-GO для H4 clustering на приоритетном L6. STRONGER GO не достигнут.**

Две сцены обучены независимо, но ранее многократно исследовались. Это actual scene-specific coding, не новая held-out проверка, не статистическое подтверждение переносимости. Результаты относятся к отдельным standalone xyz-парам, не всему Grid4D.

| case | C0 | C1 | C2 | sharing_B | clustering_B | combined_B | H3 | vs_H3_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L6 | 441801 | 441319 | 441319 | 482 | 0 | 482 | 440635 | -684 |
| hellwarrior_L6 | 325337 | 324855 | 324855 | 482 | 0 | 482 | 324655 | -200 |
| bouncingballs_L5 | 229252 | 228833 | 225822 | 419 | 3011 | 3430 | 228642 | 2820 |
| hellwarrior_L5 | 156050 | 155631 | 152691 | 419 | 2940 | 3359 | 155440 | 2749 |

| case | PMF_C0 | PMF_C1 | PMF_C2 | payload_penalty_B | model_saving_B | predicted_B | clustering_B | actual_minus_predicted_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L6 | 20 | 18 | 18 | 0 | 0 | 0.000000 | 0 | 0.000000 |
| hellwarrior_L6 | 20 | 18 | 18 | 0 | 0 | 0.000000 | 0 | 0.000000 |
| bouncingballs_L5 | 19 | 17 | 9 | -96 | 2915 | 3010.687592 | 3011 | 0.312408 |
| hellwarrior_L5 | 20 | 18 | 12 | 216 | 3156 | 2940.807722 | 2940 | -0.807722 |

На L6 каждый optimizer оценил 56 допустимых пар и не принял ни одного merge. C2 и C1 используют одинаковые PMF/mapping/payload, отличаются mode identifier и checksum; размеры равны. Экономия 482 B C1 против C0 на каждой сцене — только exact sharing, не статистический clustering.

Дополнительная read-only проверка всех 112 начальных L6-кандидатов подтвердила отрицательный J gain. Лучший отвергнутый кандидат bouncingballs: global IDs 2+8 (channel0), ideal penalty +13.156084 B, модель **растёт** на119 B, J ухудшается на132.156084 B. Hellwarrior: IDs12+19 (channel1), ideal улучшается на14.237887 B, но модель растёт на158 B; J ухудшается на143.762113 B. Меньшее число rows не гарантирует меньшую sparse model: меняются modal default и набор exceptions. Все данные в L6_rejected_candidates.csv.

На L5 bouncingballs приняты8 merges: PMF17→9 после sharing; PMF экономия2915 B и payload дополнительно уменьшается на96 B. Hellwarrior:6 merges, PMF18→12, PMF экономия3156 B компенсирует увеличение payload на216 B. Mapping остаётся20 B во всех файлах; thresholds/header/outer framing неизменны внутри каждого случая. Эти расходы полностью оплачены, но не являются дополнительными затратами C2 против C1.

Pooled fitting использует исходные counts и один smoothing. Исходные PMF дискретны и сглажены; они не обязаны минимизировать empirical log loss. Поэтому некоторые merges уменьшают даже ideal length. Это наблюдение о переданных scene-specific distributions, а не улучшение held-out prediction.

Относительно прежнего H3 C2 выигрывает2820/2749 B на L5 и проигрывает684/200 B на L6. H3 имеет другое routing/framing, поэтому это сравнение целых кодеров. Обе L5 экономии меньше инженерной цели4096 B; L6 имеет нулевой gain против C1. Нет основания заменять H3 на H4 для L6.

## Correctness
12/12 fresh-process bin-only strict decodes PASS; внешнее exact equality coarse/fine/context/pool IDs, byte-identical повторное encode, canonical model roundtrip, positive masses/sum65536/CDF, полное покрытие allocated slots.36 повреждённых контейнеров отклонены. Regression четырёх прежних H3 файлов PASS. Ни одного изменения optimizer/serializer/codec; profiling — отдельный наблюдательный hook. Source/frozen artifact hashes проверены до/после; окончательный статус и SHA256 в FINAL_VALIDATION.json.

## Цена выполнения
C2 optimizer: L6 0.906/0.792s; L5 4.574/5.308s. Strict C2 decode: L6 3.359/3.071s; L5 1.930/1.988s. Peak subprocess RSS≤137.55MiB. Это измерения с instrumentation, подробные определения и все C0/C1/C2 в PERFORMANCE_REPORT.md.

## Воспроизводимость и данные
EXPERIMENT_PROTOCOL.md зафиксирован до первого fitting. INPUT_AUDIT.md и protected-input-hashes.json сохраняют исходные hashes; environment.json и source_snapshot — код/окружение. L6 запущен неизменённым launcher, L5 через run_l5.py, analysis через analyze.py, диагностическая проверка отвергнутых L6 candidates через rejections.py. JSON/CSV: physical, comparisons, merges, performance, checks, channel_contributions. L6/L5 case directories содержат12 .bin, исходные counts, планы, модели, mappings, independent decoded arrays/audits и performance records. Повторное encode сравнивалось в памяти, без дополнительных standalone файлов.

Подробности: [Actual](ACTUAL_BITSTREAM_REPORT.md), Clustering (внешний артефакт; см. каталог исключённых ссылок), Prediction (внешний артефакт; см. каталог исключённых ссылок), [Performance](PERFORMANCE_REPORT.md), Interpretation (внешний артефакт; см. каталог исключённых ссылок), Next (внешний артефакт; см. каталог исключённых ссылок).
