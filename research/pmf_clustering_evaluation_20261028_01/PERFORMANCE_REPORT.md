> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Performance
| case | mode | step | process_wall_s | codec_s | histogram_s | optimizer_s | pooled_fit_s | peak_RSS_MiB | optimizer_extra_sampled_MiB | serialized_cumulative_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L6 | C0 | optimize | 3.173582 | 0 | 0.014906 | 0.043877 | 0 | 134.949219 | 0.144531 | 71713 |
| bouncingballs_L6 | C0 | encode | 5.662760 | 2.945141 | 0.010781 | 0 | 0 | 137.250000 | 0.000000 | 81370 |
| bouncingballs_L6 | C0 | decode | 4.089598 | 3.558582 | 0 | 0 | 0 | 135.980469 | 0.000000 | 12876 |
| bouncingballs_L6 | C1 | optimize | 2.617100 | 0 | 0.011162 | 0.020186 | 0 | 136.386719 | 0.140625 | 64123 |
| bouncingballs_L6 | C1 | encode | 5.840389 | 3.076835 | 0.014636 | 0 | 0 | 136.285156 | 0.000000 | 72334 |
| bouncingballs_L6 | C1 | decode | 3.790582 | 3.289829 | 0 | 0 | 0 | 135.230469 | 0.000000 | 10948 |
| bouncingballs_L6 | C2 | optimize | 3.463730 | 0 | 0.010695 | 0.905784 | 0.020558 | 136.589844 | 0.183594 | 1867415 |
| bouncingballs_L6 | C2 | encode | 5.674595 | 3.069597 | 0.010805 | 0 | 0 | 136.988281 | 0.000000 | 72334 |
| bouncingballs_L6 | C2 | decode | 3.839488 | 3.359490 | 0 | 0 | 0 | 135.878906 | 0.000000 | 10948 |
| hellwarrior_L6 | C0 | optimize | 2.362794 | 0 | 0.010529 | 0.020117 | 0 | 135.218750 | 0.218750 | 70246 |
| hellwarrior_L6 | C0 | encode | 5.014496 | 2.672041 | 0.010662 | 0 | 0 | 136.625000 | 0.000000 | 78436 |
| hellwarrior_L6 | C0 | decode | 3.550613 | 3.073231 | 0 | 0 | 0 | 134.886719 | 0.000000 | 10920 |
| hellwarrior_L6 | C1 | optimize | 2.424198 | 0 | 0.010598 | 0.019736 | 0 | 135.386719 | 0.128906 | 62656 |
| hellwarrior_L6 | C1 | encode | 5.128855 | 2.775975 | 0.010686 | 0 | 0 | 137.058594 | 0.000000 | 69400 |
| hellwarrior_L6 | C1 | decode | 3.515690 | 2.996350 | 0 | 0 | 0 | 136.507812 | 0.000000 | 8992 |
| hellwarrior_L6 | C2 | optimize | 3.166494 | 0 | 0.010586 | 0.792115 | 0.006174 | 134.296875 | 0.195312 | 1817270 |
| hellwarrior_L6 | C2 | encode | 4.954034 | 2.620346 | 0.010717 | 0 | 0 | 137.546875 | 0.000000 | 69400 |
| hellwarrior_L6 | C2 | decode | 3.566567 | 3.070629 | 0 | 0 | 0 | 133.937500 | 0.000000 | 8992 |
| bouncingballs_L5 | C0 | optimize | 1.309458 | 0 | 0.010950 | 0.027896 | 0 | 125.949219 | 0.367188 | 78979 |
| bouncingballs_L5 | C0 | encode | 2.616926 | 1.334651 | 0.010844 | 0 | 0 | 127.296875 | 0.000000 | 98974 |
| bouncingballs_L5 | C0 | decode | 2.446481 | 1.968262 | 0 | 0 | 0 | 124.250000 | 0.000000 | 26660 |
| bouncingballs_L5 | C1 | optimize | 1.289658 | 0 | 0.011241 | 0.026885 | 0 | 126.093750 | 0.386719 | 71578 |
| bouncingballs_L5 | C1 | encode | 2.703275 | 1.351825 | 0.011191 | 0 | 0 | 126.332031 | 0.000000 | 90316 |
| bouncingballs_L5 | C1 | decode | 2.441193 | 1.957928 | 0 | 0 | 0 | 124.378906 | 0.000000 | 24984 |
| bouncingballs_L5 | C2 | optimize | 5.868554 | 0 | 0.015209 | 4.573817 | 0.029816 | 125.636719 | 0.695312 | 7196577 |
| bouncingballs_L5 | C2 | encode | 2.604870 | 1.331149 | 0.010763 | 0 | 0 | 126.167969 | 0.000000 | 48250 |
| bouncingballs_L5 | C2 | decode | 2.410045 | 1.929927 | 0 | 0 | 0 | 124.519531 | 0.000000 | 13324 |
| hellwarrior_L5 | C0 | optimize | 1.257446 | 0 | 0.010884 | 0.026547 | 0 | 125.562500 | 0.285156 | 79273 |
| hellwarrior_L5 | C0 | encode | 2.512252 | 1.253637 | 0.010803 | 0 | 0 | 127.136719 | 0.000000 | 96490 |
| hellwarrior_L5 | C0 | decode | 2.293476 | 1.811965 | 0 | 0 | 0 | 124.222656 | 0.000000 | 22956 |
| hellwarrior_L5 | C1 | optimize | 1.246465 | 0 | 0.010749 | 0.024365 | 0 | 125.851562 | 0.347656 | 71872 |
| hellwarrior_L5 | C1 | encode | 2.531279 | 1.262683 | 0.010973 | 0 | 0 | 127.332031 | 0.000000 | 87832 |
| hellwarrior_L5 | C1 | decode | 2.291593 | 1.807415 | 0 | 0 | 0 | 124.558594 | 0.000000 | 21280 |
| hellwarrior_L5 | C2 | optimize | 6.598731 | 0 | 0.011286 | 5.307622 | 0.040253 | 125.863281 | 0.523438 | 7862110 |
| hellwarrior_L5 | C2 | encode | 2.705684 | 1.365208 | 0.011078 | 0 | 0 | 127.191406 | 0.000000 | 50464 |
| hellwarrior_L5 | C2 | decode | 2.591326 | 1.988254 | 0 | 0 | 0 | 124.988281 | 0.000000 | 8656 |

CPU Windows Python3.12.14/NumPy1.26.4/constriction0.4.2; GPU и новые dependencies не использовались. Внешний sitecustomize профилирует без изменения source functions. Время включает instrumentation overhead. process_wall начинается при sitecustomize и включает module imports/CLI/input validation, но не раннюю инициализацию интерпретатора; это приближение process startup wall, не полностью измеренный cold launch. codec_s — внутренний encode/strict decode; не отдельный warm benchmark.

histogram_s — построение counts, pooled_fit_s — сумма frequencies для candidate PMFs (вложена в optimizer_s, не складывать повторно). C0/C1 не refit исходные PMF. Encode CLI повторно загружает/проверяет frozen inputs; optimize и encode поэтому имеют отдельный histogram time.

Windows PeakWorkingSetSize — фактический lifetime peak RSS процесса. Optimizer extra — максимум sampled RSS каждые10ms и конечного RSS минус RSS на входе; это наблюдавшееся приращение, не точная верхняя граница allocations. Совокупный system RAM peak не измерялся. serialized_cumulative_B — суммарные bytes всех полных временных H4PM сериализаций соответствующего процесса, включая повторные проверки; не physical output и не только mass section. Физические pmf B приведены отдельно в physical.csv.

Greedy C2 занимает0.906/0.792s на L6 и4.574/5.308s на L5. Peak RSS всех measured subprocesses≤137.55MiB; sampled extra optimizer≤0.70MiB. Decoder не выполняет search. Repeated encode без profiling создал byte-identical streams, что проверяет отсутствие влияния instrumentation на результаты.
