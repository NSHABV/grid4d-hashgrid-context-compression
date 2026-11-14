> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Resources
Training observed wall 4762.212s; last segment sampled total GPU peak 3690.0MiB. Full per-segment telemetry retained; total GPU includes other applications.
Export 1.873050s, nested quantization 0.169829s, export RSS878.215MiB.
| mode | phase | process_wall_s | peak_RSS_MiB | kernel_or_optimizer_s |
| --- | --- | --- | --- | --- |
| C0 | optimizer | 1.514668799994979 | 125.75 | 0.03879620000225259 |
| C0 | encoder | 2.480192500006524 | 126.91015625 | 1.257242399995448 |
| C0 | decoder | 2.2680113000023994 | 124.53125 | 1.8330080000014277 |
| C1 | optimizer | 1.2144305999972858 | 125.86328125 | 0.025285399999120273 |
| C1 | encoder | 2.5639310000042315 | 126.703125 | 1.3100564000051236 |
| C1 | decoder | 2.396549799996137 | 125.22265625 | 1.972750699998869 |
| C2 | optimizer | 5.07325149999815 | 125.69921875 | 3.75720690000162 |
| C2 | encoder | 2.753840499994112 | 126.6171875 | 1.4565714999989723 |
| C2 | decoder | 2.498855400001048 | 124.140625 | 2.052417200000491 |

Process wall starts at sitecustomize, excluding earliest interpreter startup; nested counters are not summed. CPU entropy coding; GPU only training/indexing probe. Profiling overhead included. Durability pilot/resume checkpoint timings are separate from compression.
