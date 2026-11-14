> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Resource measurements
Training wall 7527.716s; sampled GPU total peak 4835.0MiB. GPU used only training and limited indexing/scale probe; entropy pipeline CPU.
Export 1.663661s; quantization nested 0.242638s; export RSS 879.270MiB.
| mode | phase | wall_s | peak_RSS_MiB | histogram_s | optimizer_s | codec_s |
| --- | --- | --- | --- | --- | --- | --- |
| C0 | optimizer | 1.1863200000007055 | 125.0078125 | 0.010240299998258706 | 0.025361400003021117 | 0 |
| C0 | encoder | 2.396193900000071 | 126.12109375 | 0.01020260000223061 | 0 | 1.2332844000047771 |
| C0 | decoder | 2.2135960000014165 | 123.9609375 | 0 | 0 | 1.7946569999985513 |
| C1 | optimizer | 1.1667721000048914 | 125.53125 | 0.010568600002443418 | 0.023462599994672928 | 0 |
| C1 | encoder | 2.510913199999777 | 127.33203125 | 0.010775800001283642 | 0 | 1.2790078000034555 |
| C1 | decoder | 2.261240200001339 | 124.02734375 | 0 | 0 | 1.8013900999940233 |
| C2 | optimizer | 5.829815199998848 | 126.3359375 | 0.010117999998328742 | 4.686241499999596 | 0 |
| C2 | encoder | 2.4055743999997503 | 126.2734375 | 0.010249500002828427 | 0 | 1.2431116000007023 |
| C2 | decoder | 2.270907800004352 | 123.55859375 | 0 | 0 | 1.875526700001501 |

Profiling includes instrumentation overhead. process wall starts at sitecustomize, excludes earliest interpreter startup; codec counters nested. Do not add nested counters. RSS is Windows lifetime PeakWorkingSetSize; exported Linux ru_maxrss separate. No claim of GPU speedup for CPU codec. Raw records include pooled fitting and sampled10ms optimizer extra RSS.
