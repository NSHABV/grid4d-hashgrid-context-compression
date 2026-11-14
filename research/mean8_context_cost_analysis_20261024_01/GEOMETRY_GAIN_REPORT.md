> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Декомпозиция Mean8 по геометрии и каналам

Дата: 24 октября 2026. Run: `mean8_context_cost_analysis_20261024_01`.

Это FULL-SCENE FITTED PMF ANALYSIS: анализ уже переданных scene-specific integer PMFs, без нового fitting. В каждом из четырёх случаев учтены 524288 fine slots × 2 channels = 1048576 symbols. Файлы разных версий разобраны соответствующими декодерами V1/V2/V3. Новых entropy streams, квантования и обучения нет.

`L = −log2(mass/65536)`, `gain = L_baseline − L_Mean8`. Положительный gain означает меньшую длину Mean8. Вклад `/8` обозначен IDEAL PMF LENGTH CONTRIBUTION в byte-equivalents. Он не является физическими байтами отдельного участка range stream. ACTUAL FILE SIZE используется только для измеренных секций/целых файлов. Общий coder/finite-precision/framing residual не распределяется по категориям; его внутренние причины отдельно не идентифицированы.

Геометрия построена заново исключительно из container metadata и сверена с прежними diagnostics. G0: nominal-empty; G1: nominal-positive, eligible-point-empty; G2: point_count=1; G3: point_count≥2. G0/G1 остаются allocated slots; никакого вывода об их ненужности для rendering не делается.

## Покрытие

| Case | G0 slots | G1 slots | G2 slots | G3 slots | G3 % |
| --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 183592 | 7144 | 200128 | 133424 | 25.448608 |
| hellwarrior_L5 | 183592 | 7144 | 200128 | 133424 | 25.448608 |
| bouncingballs_L6 | 27888 | 3057 | 91014 | 402329 | 76.738167 |
| hellwarrior_L6 | 27888 | 3057 | 91014 | 402329 | 76.738167 |


## Mean8 vs Geometry4

| Case | G0 ideal B | G1 ideal B | G2 ideal B | G3 ideal B | Total ideal B |
| --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 0.000000 | 0.000000 | 11196.271336 | 4255.369184 | 15451.640520 |
| hellwarrior_L5 | 0.000000 | 0.000000 | 4742.543411 | 1450.551793 | 6193.095204 |
| bouncingballs_L6 | 0.000000 | 0.000000 | -1004.079135 | 1838.387559 | 834.308424 |
| hellwarrior_L6 | 0.000000 | 0.000000 | -359.632696 | 1381.459920 | 1021.827225 |


| Case | All ch0 ideal B | All ch1 ideal B | G2 ch0 | G2 ch1 | G3 ch0 | G3 ch1 |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 9756.481037 | 5695.159483 | 6636.645076 | 4559.626260 | 3119.835961 | 1135.533223 |
| hellwarrior_L5 | 3359.049517 | 2834.045688 | 2477.204572 | 2265.338839 | 881.844945 | 568.706848 |
| bouncingballs_L6 | 439.204759 | 395.103664 | -526.221475 | -477.857660 | 965.426234 | 872.961324 |
| hellwarrior_L6 | 627.566127 | 394.261097 | -164.238010 | -195.394685 | 791.804138 | 589.655782 |


geometry_Geometry4 (внешний артефакт; см. каталог исключённых ссылок)

channel_contributions (внешний артефакт; см. каталог исключённых ссылок)

## Фиксированные multiplicity groups

| Case | Group | Symbols (both) | Gain bits | Gain bits/symbol | Ideal B | Signed share total |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | K2 | 193920 | 29080.806754 | 0.149963 | 3635.100844 | 0.235257 |
| bouncingballs_L5 | K3 | 58560 | 4316.146444 | 0.073705 | 539.518305 | 0.034917 |
| bouncingballs_L5 | K4plus | 14368 | 646.000270 | 0.044961 | 80.750034 | 0.005226 |
| hellwarrior_L5 | K2 | 193920 | 9888.725684 | 0.050994 | 1236.090711 | 0.199592 |
| hellwarrior_L5 | K3 | 58560 | 1483.537588 | 0.025334 | 185.442198 | 0.029943 |
| hellwarrior_L5 | K4plus | 14368 | 232.151073 | 0.016158 | 29.018884 | 0.004686 |
| bouncingballs_L6 | K2 | 274802 | 10266.615973 | 0.037360 | 1283.326997 | 1.538193 |
| bouncingballs_L6 | K3 | 264992 | 4431.153798 | 0.016722 | 553.894225 | 0.663896 |
| bouncingballs_L6 | K4plus | 264864 | 9.330699 | 0.000035 | 1.166337 | 0.001398 |
| hellwarrior_L6 | K2 | 274802 | 4851.550209 | 0.017655 | 606.443776 | 0.593490 |
| hellwarrior_L6 | K3 | 264992 | 3097.984827 | 0.011691 | 387.248103 | 0.378976 |
| hellwarrior_L6 | K4plus | 264864 | 3102.144324 | 0.011712 | 387.768041 | 0.379485 |


multiplicity_contributions (внешний артефакт; см. каталог исключённых ссылок)

## Mean8 vs Canonical8

| Case | G2 ideal B | G3 ideal B | Total ideal B | Actual payload B | Actual net B |
| --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 2485.130874 | 6116.945156 | 8602.076030 | 8604 | 8152 |
| hellwarrior_L5 | 700.402452 | 2300.051246 | 3000.453698 | 3000 | 3856 |
| bouncingballs_L6 | 777.971277 | 2192.582858 | 2970.554135 | 2968 | 3614 |
| hellwarrior_L6 | 451.771432 | 1777.597022 | 2229.368453 | 2228 | 3156 |


geometry_Canonical8 (внешний артефакт; см. каталог исключённых ссылок)

## Интерпретация

На L5 G2 даёт 72.46% / 76.58% идеального выигрыша (bouncingballs / hellwarrior), G3 — оставшиеся 27.54% / 23.42%. На L6 знак G2 меняется: −1004.079 / −359.633 byte-equivalents. G3 остаётся положительным: +1838.388 / +1381.460. Поэтому signed share G3 превышает 100%; это компенсация потерь G2, а не ошибка нормировки.

В обеих сценах и на обоих уровнях суммарный gain канала 0 больше канала 1. Для L6 оба канала теряют на G2 и выигрывают на G3. Для отдельных K-групп знак неоднороден: bouncingballs K≥4 channel1 отрицателен как на L5, так и на L6. Полные channel/K sums и means сохранены в gain-contributions.csv/json.

При одинаковой геометрии больший выигрыш G3 наблюдается на bouncingballs: как total, так и bits/symbol. На L6 colliding slots больше (76.74% вместо 25.45%), но средний G3 gain падает с 0.127574 до 0.018277 bit/symbol для bouncingballs и с 0.043487 до 0.013735 для hellwarrior. Само число коллизий не определяет пользу контекста.

Mean8 не сохраняет G2/G3 как отдельные PMF strata: класс равен 2 + quantile_bin(mean), а семь порогов каждого канала ранее определены совместно по G2∪G3. Поэтому Mean8 не является уточнением Geometry4, и преимущество full-scene fit на G2 математически не гарантировано. Этот факт реализации согласуется с отрицательным G2 на L6, однако причинную роль смешивания можно проверить только отдельной абляцией.

На singleton вершине mean и canonical features совпадают математически, но глобальные quantile thresholds и обученные PMFs Mean8/Canonical8 различаются из-за G3. Поэтому ненулевой G2 gain относительно Canonical8 нельзя приписывать усреднению нескольких вершин. Улучшение относительно Canonical8 на L6 существенно больше улучшения относительно Geometry4: выбор сильного baseline меняет вывод об эффективности.

Не выявлен общий закон «больше K — больше выигрыш». На L5 gain/symbol убывает K2→K3→K≥4 в обеих сценах. На bouncingballs L6 K≥4 почти нейтрален: 0.000035 bit/symbol (1.166 идеального байта суммарно); на hellwarrior L6 K3 и K≥4 близки, около 0.0117. Это фиксированные exploratory подгруппы известных checkpoints, а не новая независимая проверка или причинный эксперимент.

## Точные distributions

`category-statistics.csv/json`: counts, %, target mode/frequency, distinct target symbols, занятые Mean8 classes и counts назначений отдельно по каналам. `<case>/category_target_counts.npz`: полные 256-bin target histograms для all/G0–G3/K2/K3/K4plus. `<case>/Mean8_class_assignments.npz`: полные 10-class assignment histograms. `<case>/symbol_contributions.npz`: все slot IDs, geometry, multiplicities, symbols, classes и индивидуальные costs/gains. Каждый слот представлен ровно один раз и содержит оба канала; итог G0–G3 восстановлен с tolerance 1e−7 bit. G0/G1 PMFs Geometry4/Mean8/Canonical8 побитно совпадают, gain равен нулю для каждого символа.
