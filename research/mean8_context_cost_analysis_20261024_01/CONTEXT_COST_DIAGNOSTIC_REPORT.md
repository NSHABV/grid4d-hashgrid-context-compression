> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Mean8: декомпозиция выигрыша и стоимости

Дата: 24 октября 2026. Run: `mean8_context_cost_analysis_20261024_01`.

Это FULL-SCENE FITTED PMF ANALYSIS: анализ уже переданных scene-specific integer PMFs, без нового fitting. В каждом из четырёх случаев учтены 524288 fine slots × 2 channels = 1048576 symbols. Файлы разных версий разобраны соответствующими декодерами V1/V2/V3. Новых entropy streams, квантования и обучения нет.

`L = −log2(mass/65536)`, `gain = L_baseline − L_Mean8`. Положительный gain означает меньшую длину Mean8. Вклад `/8` обозначен IDEAL PMF LENGTH CONTRIBUTION в byte-equivalents. Он не является физическими байтами отдельного участка range stream. ACTUAL FILE SIZE используется только для измеренных секций/целых файлов. Общий coder/finite-precision/framing residual не распределяется по категориям; его внутренние причины отдельно не идентифицированы.

Геометрия построена заново исключительно из container metadata и сверена с прежними diagnostics. G0: nominal-empty; G1: nominal-positive, eligible-point-empty; G2: point_count=1; G3: point_count≥2. G0/G1 остаются allocated slots; никакого вывода об их ненужности для rendering не делается.

## Основной результат

На L6 наблюдается сочетание малого gross gain, отрицательного G2-вклада и затрат на PMFs. На L5 большой положительный G2 обеспечивает основную часть выигрыша.

| Case | Ideal gain /8 | Actual payload gain B | Residual B | Extra masses B | Extra meta B | Actual net B |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 15451.640520 | 15452 | 0.359480 | 4050 | 124 | 11278 |
| hellwarrior_L5 | 6193.095204 | 6192 | -1.095204 | 3195 | 124 | 2873 |
| bouncingballs_L6 | 834.308424 | 832 | -2.308424 | 1083 | 124 | -375 |
| hellwarrior_L6 | 1021.827225 | 1020 | -1.827225 | 699 | 124 | 197 |


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

physical_waterfall_v2 (внешний артефакт; см. каталог исключённых ссылок)
## Ответы на исследовательские вопросы

1. **Где улучшение?** На L5 — G2 и G3; на L6 — G3 при отрицательном G2. G0/G1 точно нулевые.
2. **Вклад G2/G3?** Полная таблица выше; на L5 преобладает G2, на L6 G3 компенсирует G2 loss.
3. **Где больше predictive gain G3?** В bouncingballs на обоих уровнях, но это не гарантирует лучший actual net.
4. **Каналы?** Канал 0 даёт больше total gain во всех четырёх случаях; внутри K≥4 бывают отрицательные channel contributions.
5. **Рост с K?** Общая монотонная польза больших K не подтверждена; фиксированные K-таблицы описательные.
6. **Почему L5 окупается?** Значительно больший gross gain оплачивает более дорогие masses. L6 имеет слабый gross ещё до side cost.
7. **Проблема L6?** Сочетание слабого predictive gain, потери на G2 и стоимости переданных PMFs; overhead не единственная причина.
8. **Residual?** В основном сравнении от −2.308 до +0.359 B; полный вторичный диапазон также доступен в totals.csv. Residual не распределён по категориям.
9. **Что стоит дорого?** Sparse exceptions по 3 B, затем 48 B дополнительных row headers и +124 B суммарной metadata. Общие заголовки учтены отдельно.
10. **Rows избыточны?** У Mean8 две точные cross-channel пары G0/G1, присутствующие также у Geometry4; пустые rows почти бесплатны. Близость feature rows зависит от сцены.
11. **Минимальное улучшение L6?** Bouncingballs: 376 B для положительного net, 4471 B для +4096; hellwarrior: уже +197, нужно 3899 B до +4096.
12. **Что гипотетично?** Причинная роль смешивания G2/G3, выгода будущего выбора/объединения PMFs, переносимость на другие сцены/levels/quantizers и научная новизна. Они не проверены этой диагностикой.

## Проверки, ресурсы и воспроизводимость

16/16 bin-only fresh-process decodes: exact coarse/fine symbols и class IDs совпали с hash-проверенными прежними outputs. Аудит Python file-open разрешал только соответствующий .bin и код/зависимости; source checkpoint, quantized exports и contexts decoder не читал. Fitting/encoding entry points заблокированы. Это проверка доступа на уровне Python, не OS sandbox для произвольного native кода; проверенный native entropy engine получает только массивы. Новое canonical re-encoding специально отключено, прежние sealed corruption/strict-decoder проверки сохранены.

Проверены positive masses/sum65536/strict CDF, exact allocated-slot coverage, counts старой geometry, G0/G1 equality, оба канала, category partition sums tolerance1e−7 bit, физический размер всех секций. Независимый scalar math.log2 расчёт по counts×mass повторил идеальные длины, без summing сохранённых individual gains. Синтетические тесты: независимый scalar hash, sparse/packed/dense inspector и break-even arithmetic. FINAL_VALIDATION.json содержит итоговые статусы и SHA256. Source snapshots и dependency-versions.json обеспечивают продолжение.

Основной analysis: 36.873 s wall, 10.172 s CPU родителя; subprocess CPU суммарно 19.859 s. Peak RSS родителя 141.00 MiB, max decoder 135.24 MiB; процессы последовательные, это per-process peaks, не измерение общего system peak. Консервативная сумма peaks меньше 277 MiB. Cold decoder 1.123–2.446 s, внутренняя decode wall 0.713–2.023 s (не отдельный warm benchmark). CPU, GPU не использовался. Pilot прогнозировал 237.4 s, 512 MiB, ограничения не превышены. Хеширование архива, подготовка отчётов и графиков не включены в это время.

Точка продолжения: CONTINUATION_001_ANALYSIS_DONE.md и заключительная CONTINUATION_COMPLETE.md. Скрипты пишут exclusive; не запускать их повторно в каталог с результатами. Для повторения скопировать diagnostic .py scripts в новый `research/mean8_context_cost_analysis_<new_id>`; из корня проекта запустить initialize.py → test_analysis.py → analyze.py → describe.py → plots.py → refine_waterfall.py → reports.py → finalize.py. Перед plots.py установить MPLCONFIGDIR на writable локальный путь: первоначальный запуск выдал предупреждение о font cache, но все фигуры были созданы; revised waterfall использует local cache. Finalize после внешней визуальной проверки формирует seal. Старые форматы и inputs должны совпасть с manifests; при mismatch остановка. Базовая команда: `.tools/phase2-plotting-env/Scripts/python.exe -B research/<new_id>/<script>.py`.
## Материал для НИР

Выполнена декомпозиция информационной длины по фактически переданным scene-specific PMFs для двух обученных сцен Grid4D и переходов пространственной HashGrid L4→L5 и L5→L6. Установлено, что эффективный выигрыш Mean8 неоднороден по геометрическим категориям: на L5 положительные вклады дают singleton и colliding slots, тогда как на L6 положительный вклад colliding slots частично компенсируется отрицательным вкладом singleton slots. При росте доли colliding slots с 25.45% до 76.74% средний выигрыш в этой категории уменьшается. Поэтому multiplicity сама по себе не определяет эффективность межуровневого контекста.

На L6 фактическое сокращение fine payload составляет 832 и 1020 B, а дополнительные расходы на массы и metadata — 1207 и 823 B соответственно. Это приводит к standalone net −375 и +197 B. На L5 net относительно Geometry4 равен +11278 и +2873 B. Различие идеальной PMF оценки и физического payload имеет порядок единиц байтов и не объясняет малую итоговую экономию L6. Основной компонент стоимости sparse PMFs — exceptions, а не пустые контекстные строки. Результаты обосновывают проверку ограниченного cost-aware выбора geometry-only и mean-feature PMFs, но не доказывают полезность такого алгоритма или его научную новизну.

## Следующий шаг

Выбрана одна гипотеза: ограниченный cost-aware выбор Geometry4/Mean8 по G2/G3 × channel с полным учётом signalling и PMF bytes. Она пока не реализована и не считается научной новизной; основание и prior-art ссылки приведены в NEXT_ALGORITHM_HYPOTHESIS.md.

## Документы и данные

- [GEOMETRY_GAIN_REPORT.md](GEOMETRY_GAIN_REPORT.md): geometry, channels, K и Canonical8.
- [SPARSE_MODEL_COST_REPORT.md](SPARSE_MODEL_COST_REPORT.md): точный wire budget и сходство rows.
- BREAK_EVEN_ANALYSIS.md (внешний артефакт; см. каталог исключённых ссылок): integer thresholds и условные сценарии.
- CROSS_SCENE_LEVEL_COMPARISON.md (внешний артефакт; см. каталог исключённых ссылок): actual sizes отдельно от historical held-out CE.
- NEXT_ALGORITHM_HYPOTHESIS.md (внешний артефакт; см. каталог исключённых ссылок): пять направлений и ровно одна выбранная гипотеза.
- ANALYSIS_PROTOCOL.md (внешний артефакт; см. каталог исключённых ссылок), INPUT_MANIFEST.json (внешний артефакт; см. каталог исключённых ссылок), [FINAL_VALIDATION.json](FINAL_VALIDATION.json).
- `gain-contributions`, `physical-sections`, `probability-row-costs`, `probability-row-pairs`, `row-summary`, `category-statistics`, `break-even`, `hypothetical-costs`: CSV и JSON; четыре case directories содержат NPZ для individual symbols/PMFs/counts.

Все прежние результаты сохраняются. Новая диагностика не является повторной проверкой Count6 или Mean4×Std2 и не отменяет их прежних NO-GO. Изменения ограничены новым каталогом. Выбранный будущий алгоритм не реализован.
