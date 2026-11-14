> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Вычислительная стоимость L5→L6

Actual coding/replay выполнены последовательно на canonical CPU Python3.12.14, NumPy1.26.4, constriction0.4.2. По одному отброшенному warmup и3 measured repetitions каждого лучшего arm. Медианы encoder/decoder включают только соответствующий вызов, не полную подготовку/аудит. Cold process измерен отдельно. Отсутствие конкурирующих экспериментальных запусков обеспечено; сторонние процессы ОС полностью не контролируются.

| Scene | Model | Encode s | Strict decode s | Context enc/dec s | Mass fitting s | Entropy encode s | Entropy decode s | Strict canonical overhead s | Cold process s | Fresh RSS MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | IID | 1.9056 | 4.0296 | 0.0012/0.0003 | 0.0349 | 1.8625 | 2.1523 | 1.8525 | 3.3290 | 56.83 |
| bouncingballs | Geometry4 | 2.1223 | 4.2235 | 0.2449/0.2312 | 0.0351 | 1.8282 | 2.1223 | 1.8408 | 2.9090 | 57.05 |
| bouncingballs | Canonical8 | 3.4444 | 5.5933 | 1.5034/1.4857 | 0.0345 | 1.9084 | 2.1722 | 1.9202 | 5.2261 | 133.75 |
| bouncingballs | Mean8 | 3.5571 | 5.4919 | 1.6306/1.4416 | 0.0471 | 1.9030 | 2.1731 | 1.8736 | 3.9159 | 135.12 |
| hellwarrior | IID | 1.6317 | 3.5524 | 0.0014/0.0004 | 0.0355 | 1.6044 | 1.8599 | 1.6489 | 2.5540 | 57.13 |
| hellwarrior | Geometry4 | 2.1539 | 4.5564 | 0.2754/0.2572 | 0.0382 | 1.8013 | 2.1038 | 2.1071 | 2.6450 | 56.98 |
| hellwarrior | Canonical8 | 3.1456 | 5.0985 | 1.5145/1.4756 | 0.0347 | 1.6066 | 1.9047 | 1.6406 | 3.8311 | 135.12 |
| hellwarrior | Mean8 | 3.2078 | 5.0237 | 1.5257/1.4970 | 0.0372 | 1.6253 | 1.9084 | 1.6167 | 4.7867 | 134.71 |

Strict canonical overhead — повторный entropy encode для отклонения неканонических payload и trailing words. Разность decode_total−canonical_validation описывает основной decode с остальными проверками; это не отдельный unchecked decoder benchmark. Cold−body включает запуск Python, imports, планирование и завершение процесса, а не только startup. Полные component timing/CPU seconds, warm samples, parent high-water RSS находятся в runtime-summary.csv и <scene>/actual/runtime_samples/. Peak RSS родителя — накопленный максимум одного последовательного процесса, не дополнительная память одного arm.

| Scene | Mean8 warm encode s | Mean8 strict decode s | Without canonical s | Cold overhead s | Parent peak RSS MiB |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | 3.5571 | 5.4919 | 3.6183 | 0.5027 | 153.36 |
| hellwarrior | 3.2078 | 5.0237 | 3.4070 | 0.5645 | 151.73 |

GPU использовался только для cached official CUDA scale/index probe,128 queries на уровень/сцену. PyTorch peak allocated4096 B, reserved2097152 B относятся к тензорам этой проверки, не к полной памяти CUDA context. Эти проверки не ускоряли entropy coding; actual codec VRAM=0. Приблизительный GPU feature lookup не используется для выбора CPU classes.

Pilot65536 vertices:0.1084/0.1619 s, peak88.75/88.87 MiB для bouncingballs/hellwarrior. Проекция двух полных context replays с3× запасом13.94/20.82 s. Плановая оценка всего actual+malformed stage900 s/512 MiB была записана до coding; она не является измерением. Фактическое время каждого main actual запуска и corruption suite указано ниже. После завершения обеих серий performance samples независимые corruption suites выполнялись с перекрытием; первая также перекрывалась с5.46 s post-hoc held-out audit. Поэтому их wall times описывают проверку корректности, а не изолированный performance benchmark (verification-schedule.json).

| Scene | Actual pipeline wall s | Corruption suite wall s |
| --- | --- | --- |
| bouncingballs | 212.632 | 347.422 |
| hellwarrior | 187.570 | 323.201 |

Сравнение с L4→L5: прежний hellwarrior Mean8 encode1.0079 s / strict decode1.7019 s, context encoder0.3472 s / decoder0.3310 s, freshRSS123.17 MiB. Это сохранённые измерения другого запуска, не paired microbenchmark. L6 требует1.367631 млн eligible vertices против512000 на L5, coarse L5 содержит524288 rows вместо205379 L4 и тоже хешируется. Изменяются enumeration, рабочие таблицы и symbol distribution; нельзя приписать весь прирост времени только hash lookup. Canonical8 в текущем исследовательском коде использует общий full aggregation routine, включая mean/std: его время не является оптимальным нижним пределом representative-only реализации. GPU acceleration и оптимизация не разрабатывались.

Environment: environment.json (внешний артефакт; см. каталог исключённых ссылок); raw timings: runtime-summary.csv (внешний артефакт; см. каталог исключённых ссылок).
