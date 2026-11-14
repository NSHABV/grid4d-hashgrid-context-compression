> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Held-out L6: фиксированные модели и два checkpoint

Train/validation/test =335545/83886/104857 slots, seeds0/1/2. Все соответствия и оба channels одного slot принадлежат одному split. Thresholds и masses fit только train; validation/test не используются для изменения алгоритма. Bouncingballs — репликация, hellwarrior — впервые проверенный L6 второй сцены при заранее frozen protocol. Это не полностью новая сцена для НИР: L5 hellwarrior изучался ранее.

| Scene | Model | CE all | CE channel0 | CE channel1 | CE G3 |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | IID | 1.976133579 | 1.962024949 | 1.990242208 | 2.148152082 |
| bouncingballs | Geometry4 | 1.904874333 | 1.889404938 | 1.920343728 | 2.135199007 |
| bouncingballs | Canonical8 | 1.923797745 | 1.908419179 | 1.939176311 | 2.141573426 |
| bouncingballs | Mean8 | 1.901428970 | 1.885707073 | 1.917150867 | 2.120040994 |
| hellwarrior | IID | 1.536267112 | 1.549171746 | 1.523362477 | 1.678232855 |
| hellwarrior | Geometry4 | 1.494505014 | 1.506939087 | 1.482070942 | 1.671574570 |
| hellwarrior | Canonical8 | 1.506328827 | 1.519068345 | 1.493589309 | 1.678673640 |
| hellwarrior | Mean8 | 1.489007134 | 1.499686348 | 1.478327920 | 1.660499425 |

bouncingballs: Geometry4−Mean8 = +0.003445363 bits/symbol; положительный знак 3/3 seeds. Canonical8−Mean8 = +0.022368775. Полные seeds/channels/G0–G3 и K subsets: HELDOUT_REPORT.md (внешний артефакт; см. каталог исключённых ссылок), test-scores.csv (внешний артефакт; см. каталог исключённых ссылок), paired-differences.csv (внешний артефакт; см. каталог исключённых ссылок).

hellwarrior: Geometry4−Mean8 = +0.005497880 bits/symbol; положительный знак 3/3 seeds. Canonical8−Mean8 = +0.017321693. Полные seeds/channels/G0–G3 и K subsets: HELDOUT_REPORT.md (внешний артефакт; см. каталог исключённых ссылок), test-scores.csv (внешний артефакт; см. каталог исключённых ссылок), paired-differences.csv (внешний артефакт; см. каталог исключённых ссылок).

Независимый аудит проверил24 модели,72 dry transports и576 строк CE через отдельную формулу16−log2(mass); independently reconstructed train counts, positive16 masses и class thresholds. Independent coarse-only decoder воспроизвёл12 arrays на сцену. Bouncingballs288 shared scores и все split IDs совпали точно с прежним L6; это повторная проверка, а не добавление независимых наблюдений.

Mean8 выигрывает по среднему CE и внутри G3 на обеих сценах, однако положительная CE не гарантирует оплаченного выигрыша. Три seeds одного checkpoint не являются независимыми training runs; spatial/hash dependence не устранена. Разбиение по slots предотвращает повторное попадание одного fine target в разные splits, но не устраняет shared coarse dependencies. Доверительные интервалы descriptive/conditional-on-fit, без поправки за множественные сравнения. K strata exploratory, не меняют модели. Старые NO-GO Count6 и Mean4×Std2 не пересматриваются.

Независимая проверка: audit.json (внешний артефакт; см. каталог исключённых ссылок). Полные predictions с измеренным dry overhead — prediction-bridge.csv; actual размеры — BITSTREAM_REPORT.md.

Heldout (внешний артефакт; см. каталог исключённых ссылок)
