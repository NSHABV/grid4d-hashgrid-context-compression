> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Физическая стоимость probability models

Дата: 24 октября 2026. Run: `mean8_context_cost_analysis_20261024_01`.

Во всех 16 фактически выбранных контейнерах storage — `sparse_default_u16`. Это проверено по header каждого файла. Исследуются прежние best files; оптимизация storage заново не выполнялась.

Fine masses имеют shape [2,C,256], uint32 после десериализации, C=1/4/10/10 для IID/Geometry4/Canonical8/Mean8. Все entries положительны, каждая строка суммируется в 65536, CDF вычисляется с uint64 и не передаётся повторно.

Каждая sparse row: **2 B default mass + 2 B exception count + E×(1 B symbol index + 2 B mass)**, то есть 4+3E B. Default — наиболее частое значение MASS среди 256 entries, при равной частоте выбирается наименьшее; это не «самый частый symbol». Отдельные поля `modal_mass`, `PMF_argmax_symbol`, `target_mode_symbol`, `target_mode_frequency` и `entries_at_minimum` доступны в probability-row-costs.csv/json. В данном формате нет глобального row dictionary или бесплатного sharing. Header модели 26 B, thresholds, specification и общая metadata показаны отдельно; они не размазываются по rows.

В physical-sections `model_bytes` означает только fine probability masses, а `fine_model_bytes` — всю fine model section. `coarse_bytes` включает coarse payload и полную coarse model section. Это важно для исключения двойного счёта.

| Case | Model | Rows | Occupied | Mass B | Default B | Count B | Exceptions | Exception B | Whole fine model B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | IID | 2 | 2 | 470 | 4 | 4 | 154 | 462 | 683 |
| bouncingballs_L5 | Geometry4 | 8 | 8 | 2465 | 16 | 16 | 811 | 2433 | 2684 |
| bouncingballs_L5 | Canonical8 | 20 | 18 | 6053 | 40 | 40 | 1991 | 5973 | 6404 |
| bouncingballs_L5 | Mean8 | 20 | 19 | 6515 | 40 | 40 | 2145 | 6435 | 6861 |
| hellwarrior_L5 | IID | 2 | 2 | 428 | 4 | 4 | 140 | 420 | 641 |
| hellwarrior_L5 | Geometry4 | 8 | 8 | 2390 | 16 | 16 | 786 | 2358 | 2609 |
| hellwarrior_L5 | Canonical8 | 20 | 20 | 6431 | 40 | 40 | 2117 | 6351 | 6782 |
| hellwarrior_L5 | Mean8 | 20 | 20 | 5585 | 40 | 40 | 1835 | 5505 | 5931 |
| bouncingballs_L6 | IID | 2 | 2 | 443 | 4 | 4 | 145 | 435 | 656 |
| bouncingballs_L6 | Geometry4 | 8 | 8 | 1982 | 16 | 16 | 650 | 1950 | 2201 |
| bouncingballs_L6 | Canonical8 | 20 | 20 | 3701 | 40 | 40 | 1207 | 3621 | 4052 |
| bouncingballs_L6 | Mean8 | 20 | 20 | 3065 | 40 | 40 | 995 | 2985 | 3411 |
| hellwarrior_L6 | IID | 2 | 2 | 347 | 4 | 4 | 113 | 339 | 560 |
| hellwarrior_L6 | Geometry4 | 8 | 8 | 1877 | 16 | 16 | 615 | 1845 | 2096 |
| hellwarrior_L6 | Canonical8 | 20 | 20 | 3494 | 40 | 40 | 1138 | 3414 | 3845 |
| hellwarrior_L6 | Mean8 | 20 | 20 | 2576 | 40 | 40 | 832 | 2496 | 2922 |


## По каналам

| Case | Model | ch | Rows/occupied | Mass B | Exceptions | Min-mass entries | Modal-mass entries |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | Geometry4 | 0 | 4/4 | 1219 | 401 | 417 | 623 |
| bouncingballs_L5 | Geometry4 | 1 | 4/4 | 1246 | 410 | 423 | 614 |
| bouncingballs_L5 | Mean8 | 0 | 10/10 | 3280 | 1080 | 1102 | 1480 |
| bouncingballs_L5 | Mean8 | 1 | 10/9 | 3235 | 1065 | 1073 | 1495 |
| hellwarrior_L5 | Geometry4 | 0 | 4/4 | 1201 | 395 | 440 | 629 |
| hellwarrior_L5 | Geometry4 | 1 | 4/4 | 1189 | 391 | 443 | 633 |
| hellwarrior_L5 | Mean8 | 0 | 10/10 | 2809 | 923 | 912 | 1637 |
| hellwarrior_L5 | Mean8 | 1 | 10/10 | 2776 | 912 | 1150 | 1648 |
| bouncingballs_L6 | Geometry4 | 0 | 4/4 | 964 | 316 | 482 | 708 |
| bouncingballs_L6 | Geometry4 | 1 | 4/4 | 1018 | 334 | 473 | 690 |
| bouncingballs_L6 | Mean8 | 0 | 10/10 | 1489 | 483 | 1972 | 2077 |
| bouncingballs_L6 | Mean8 | 1 | 10/10 | 1576 | 512 | 1943 | 2048 |
| hellwarrior_L6 | Geometry4 | 0 | 4/4 | 943 | 309 | 494 | 715 |
| hellwarrior_L6 | Geometry4 | 1 | 4/4 | 934 | 306 | 499 | 718 |
| hellwarrior_L6 | Mean8 | 0 | 10/10 | 1297 | 419 | 2036 | 2141 |
| hellwarrior_L6 | Mean8 | 1 | 10/10 | 1279 | 413 | 2042 | 2147 |


sparse_row_costs (внешний артефакт; см. каталог исключённых ссылок)

## Общие служебные поля

| Case | Model | Mass B | Threshold B | Spec B | Model header B | Model meta B | Central meta B | Prefix/trailer B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | IID | 470 | 2 | 183 | 26 | 2 | 2009 | 50/32 |
| bouncingballs_L5 | Geometry4 | 2465 | 2 | 189 | 26 | 2 | 2015 | 50/32 |
| bouncingballs_L5 | Canonical8 | 6053 | 132 | 191 | 26 | 2 | 2017 | 50/32 |
| bouncingballs_L5 | Mean8 | 6515 | 132 | 186 | 26 | 2 | 2012 | 50/32 |
| hellwarrior_L5 | IID | 428 | 2 | 183 | 26 | 2 | 2008 | 50/32 |
| hellwarrior_L5 | Geometry4 | 2390 | 2 | 189 | 26 | 2 | 2014 | 50/32 |
| hellwarrior_L5 | Canonical8 | 6431 | 132 | 191 | 26 | 2 | 2016 | 50/32 |
| hellwarrior_L5 | Mean8 | 5585 | 132 | 186 | 26 | 2 | 2011 | 50/32 |
| bouncingballs_L6 | IID | 443 | 2 | 183 | 26 | 2 | 2041 | 50/32 |
| bouncingballs_L6 | Geometry4 | 1982 | 2 | 189 | 26 | 2 | 2047 | 50/32 |
| bouncingballs_L6 | Canonical8 | 3701 | 132 | 191 | 26 | 2 | 2049 | 50/32 |
| bouncingballs_L6 | Mean8 | 3065 | 132 | 186 | 26 | 2 | 2044 | 50/32 |
| hellwarrior_L6 | IID | 347 | 2 | 183 | 26 | 2 | 2040 | 50/32 |
| hellwarrior_L6 | Geometry4 | 1877 | 2 | 189 | 26 | 2 | 2046 | 50/32 |
| hellwarrior_L6 | Canonical8 | 3494 | 132 | 191 | 26 | 2 | 2048 | 50/32 |
| hellwarrior_L6 | Mean8 | 2576 | 132 | 186 | 26 | 2 | 2043 | 50/32 |


## Повторы и сходство

| Case | Rows | Unique | Unused B | Equal pairs | Close feature pairs / tested | Min feature TV |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 20 | 18 | 4 | 2 | 1/105 | 0.009918 |
| hellwarrior_L5 | 20 | 18 | 0 | 2 | 9/120 | 0.002625 |
| bouncingballs_L6 | 20 | 18 | 0 | 2 | 0/120 | 0.013763 |
| hellwarrior_L6 | 20 | 18 | 0 | 2 | 10/120 | 0.003296 |

Разность fine mass bytes Mean8−Geometry4 точно равна 4×(20−8)+3×ΔE. Для bouncingballs L5: 48+3×1334=4050 B; hellwarrior L5: 48+3×1049=3195 B; bouncingballs L6: 48+3×345=1083 B; hellwarrior L6: 48+3×217=699 B. Следовательно, главная статья — exceptions, а не 48 B дополнительных row headers.

При одинаковых 20 rows Mean8 bouncingballs дороже hellwarrior на L5 на 930 B = 3×310 дополнительных exceptions, а на L6 на 489 B = 3×163. На L6 абсолютный размер модели меньше, чем на L5: больше entries принимают modal mass, меньше exceptions. Это свойство представления PMFs; его нельзя выдавать за прямую оценку энтропии targets.

У Mean8 во всех четырёх случаях 18 уникальных rows из 20. Две пары точных дубликатов — (ch0:G0,ch1:G0) и (ch0:G1,ch1:G1), те же пары присутствуют в Geometry4. Их суммарная повторная стоимость 419 B на L5 и 482 B на L6 до оплаты mapping/framing; относительный эффект общего удаления таких повторов сократился бы в сравнении с Geometry4. Это не измеренный выигрыш нового формата. Неиспользованная row Mean8 имеется только у bouncingballs L5 (ch1:8, 4 B). Дорогих пустых rows на L6 не найдено.

TV=0.5Σ|P−Q|, descriptive threshold TV≤0.01 зафиксирован заранее. Ни одной близкой неидентичной пары feature PMFs на bouncingballs L6 по этому порогу нет; на hellwarrior L6 их 10. Сравниваются occupied feature rows, включая cross-channel pairs; точные G0/G1 повторы исключены из feature subset. Это свидетельство локального сходства для одной сцены, не доказательство выгодного объединения: даже малая TV не ограничивает coding loss на редких symbols. Полный список пар и within-channel summaries сохранён. Никакие rows не объединялись.
