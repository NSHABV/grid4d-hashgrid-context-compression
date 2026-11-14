> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Время, память и проверка пропуска контекста

Дата: 27.10.2026. Fixed-PMF, actual scene-specific coding; две уже изученные сцены. Это exploratory experiment, не независимое подтверждение обобщаемости. Все символы, quantizer, PMF и thresholds взяты из прежних файлов без refit. Экономия относится только к standalone xyz-паре, не ко всему Grid4D.

Все расчёты CPU; GPU/VRAM не использовались. Python 3.12.14, NumPy 1.26.4, constriction0.4.2. Основной цикл64 streams+64 repeats+64 fresh strict decodes: **314.95s**. Peak RSS parent **143.82MiB**, children max **136.69MiB**. Это per-process peaks, не суммарный замер Windows memory; parent и один child могут существовать одновременно. Сумма максимумов<281MiB. Подготовка/финальный hash audit и дополнительные тесты не входят в314.95s. Pilot и actual pilot сохранены;30min/1GiB бюджет соблюдён.

| Case | Mask | Geometry s | Mean context s | Lookup внутри него s | Encode s | Repeat s | Strict decode s | Strict overhead s | Cold process s | Selective context s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 1111 | 0.0468 | 0.3127 | 0.1488 | 0.9027 | 0.8860 | 1.8282 | 0.6647 | 2.1860 | 0.3243 |
| hellwarrior_L5 | 1111 | 0.0457 | 0.3067 | 0.1477 | 0.8486 | 0.8992 | 1.7712 | 0.6147 | 2.1623 | 0.3242 |
| bouncingballs_L6 | 0100 | 0.1180 | 0.7303 | 0.4307 | 1.3741 | 1.3648 | 3.0904 | 0.9539 | 3.5043 | 0.7266 |
| hellwarrior_L6 | 1100 | 0.1144 | 0.7112 | 0.4184 | 1.3135 | 1.3114 | 2.9464 | 0.9448 | 3.3239 | 0.7444 |

Mean context содержит повторный geometry pass в исходном core, lookup является вложенным измерением; их нельзя суммировать как непересекающиеся расходы. Encoder time включает новый fine payload и container, **coarse payload reused**, а не якобы бесплатный новый coarse encode. Дополнительная фактическая регенерация общего coarse payload:

| Case | Coarse encode s | Byte-identical |
| --- | --- | --- |
| bouncingballs_L5 | 0.1857 | True |
| hellwarrior_L5 | 0.1694 | True |
| bouncingballs_L6 | 0.4858 | True |
| hellwarrior_L6 | 0.4354 | True |

Fresh process cold wall включает startup и output I/O. Internal decoder time не является отдельным cold-start benchmark. Дополнительно выполнены два последовательных non-strict warm decode каждого лучшего файла и endpoints, с exact equality:

| Case | Mask | Repeat | Warm decode без strict s |
| --- | --- | --- | --- |
| bouncingballs_L5 | 0000 | 0 | 0.8262 |
| bouncingballs_L5 | 0000 | 1 | 0.8139 |
| bouncingballs_L5 | 1111 | 0 | 1.1677 |
| bouncingballs_L5 | 1111 | 1 | 1.1695 |
| hellwarrior_L5 | 0000 | 0 | 0.7476 |
| hellwarrior_L5 | 0000 | 1 | 0.7519 |
| hellwarrior_L5 | 1111 | 0 | 1.0895 |
| hellwarrior_L5 | 1111 | 1 | 1.0708 |
| bouncingballs_L6 | 0000 | 0 | 1.2122 |
| bouncingballs_L6 | 0000 | 1 | 1.2285 |
| bouncingballs_L6 | 0100 | 0 | 1.9527 |
| bouncingballs_L6 | 0100 | 1 | 1.9553 |
| bouncingballs_L6 | 1111 | 0 | 1.9908 |
| bouncingballs_L6 | 1111 | 1 | 2.0239 |
| hellwarrior_L6 | 0000 | 0 | 1.1743 |
| hellwarrior_L6 | 0000 | 1 | 1.1751 |
| hellwarrior_L6 | 1100 | 0 | 1.9284 |
| hellwarrior_L6 | 1100 | 1 | 1.8594 |
| hellwarrior_L6 | 1111 | 0 | 1.8630 |
| hellwarrior_L6 | 1111 | 1 | 1.8638 |

Для mask0000 основной decoder уже не делает feature lookup. Optional `selective_context.py` пропускает все точки слотов, которым Mean8 не нужен, сохраняя исходный порядок оставшихся x-fast обновлений и отдельные float32 операции. Он также не вычисляет неиспользуемый Std, поэтому его timing — комбинированная оптимизация, не чистая оценка одного skipping. Оба feature channels lookup пока считаются вместе; побитовое сохранение routed classes проверено, значения неиспользуемых классов не обязаны совпадать. Оптимизация не подменяла исходный benchmark. `selective-context-checks.csv` содержит36 замеров.
