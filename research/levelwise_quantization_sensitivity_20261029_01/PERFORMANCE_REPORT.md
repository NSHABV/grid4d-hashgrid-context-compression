> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Performance

| scene | configurations | process_wall_sum_s | render_wall_sum_s | metric_wall_sum_s | max_allocated_VRAM_MiB | max_reserved_VRAM_MiB | max_sampled_process_tree_RSS_MiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 16 | 618.932478 | 316.176218 | 178.801943 | 962.877930 | 1244.000000 | 3850.089844 |
| hellwarrior | 16 | 513.359105 | 240.089808 | 169.566253 | 402.650391 | 448.000000 | 3064.218750 |
| hook | 16 | 554.519796 | 264.095891 | 173.530571 | 1049.227539 | 1406.000000 | 3122.808594 |
| jumpingjacks | 16 | 612.992354 | 312.888967 | 185.365028 | 757.378906 | 938.000000 | 4465.644531 |

Sum of all 64 measured process wall times including pilot: 2299.804 s (38.330 min). Pauses between user turns, preparation, report generation and integrity hashing are excluded.

| scene | variant | mean_render_ms | first_render_ms | mean_after_first_ms | allocated_VRAM_MiB | reserved_VRAM_MiB |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | R0 | 77.102640 | 835.942935 | 37.163678 | 962.877930 | 1244.000000 |
| bouncingballs | R2 | 46.526482 | 291.173459 | 33.650326 | 962.877930 | 1244.000000 |
| bouncingballs | Q_ONLY_L4 | 52.093063 | 566.455949 | 25.021332 | 962.877930 | 1244.000000 |
| bouncingballs | Q_ONLY_L5 | 46.415533 | 231.000831 | 36.700517 | 962.877930 | 1244.000000 |
| bouncingballs | Q_ONLY_L6 | 43.429026 | 231.243929 | 33.544031 | 962.877930 | 1244.000000 |
| bouncingballs | Q_ONLY_L7 | 42.906865 | 184.879981 | 35.434595 | 962.877930 | 1244.000000 |
| bouncingballs | Q_ONLY_L8 | 41.925000 | 166.481419 | 35.369399 | 962.877930 | 1244.000000 |
| bouncingballs | Q_ONLY_L9 | 47.306683 | 282.333390 | 34.936857 | 962.877930 | 1244.000000 |
| bouncingballs | Q_ONLY_L10 | 46.555497 | 235.442075 | 36.614098 | 962.877930 | 1244.000000 |
| bouncingballs | RESTORE_FP32_L4 | 43.035945 | 190.892977 | 35.253996 | 962.877930 | 1244.000000 |
| bouncingballs | RESTORE_FP32_L5 | 41.786228 | 174.331334 | 34.810170 | 962.877930 | 1244.000000 |
| bouncingballs | RESTORE_FP32_L6 | 44.402424 | 222.735364 | 35.016479 | 962.877930 | 1244.000000 |
| bouncingballs | RESTORE_FP32_L7 | 41.110225 | 162.659298 | 34.712905 | 962.877930 | 1244.000000 |
| bouncingballs | RESTORE_FP32_L8 | 45.289904 | 222.747829 | 35.950013 | 962.877930 | 1244.000000 |
| bouncingballs | RESTORE_FP32_L9 | 44.774557 | 226.623846 | 35.203542 | 962.877930 | 1244.000000 |
| bouncingballs | RESTORE_FP32_L10 | 45.777736 | 252.060163 | 34.920766 | 962.877930 | 1244.000000 |
| hellwarrior | R0 | 21.406816 | 256.491494 | 9.033938 | 402.650391 | 448.000000 |
| hellwarrior | R2 | 23.557706 | 298.874722 | 9.067337 | 402.650391 | 448.000000 |
| hellwarrior | Q_ONLY_L4 | 23.407510 | 298.626537 | 8.922298 | 402.650391 | 448.000000 |
| hellwarrior | Q_ONLY_L5 | 22.016335 | 268.595694 | 9.038474 | 402.650391 | 448.000000 |
| hellwarrior | Q_ONLY_L6 | 24.118242 | 298.534616 | 9.675275 | 402.650391 | 448.000000 |
| hellwarrior | Q_ONLY_L7 | 22.029329 | 273.316580 | 8.803684 | 402.650391 | 448.000000 |
| hellwarrior | Q_ONLY_L8 | 22.025534 | 272.225033 | 8.857139 | 402.650391 | 448.000000 |
| hellwarrior | Q_ONLY_L9 | 21.256266 | 257.067571 | 8.845144 | 402.650391 | 448.000000 |
| hellwarrior | Q_ONLY_L10 | 22.622960 | 280.108534 | 9.071088 | 402.650391 | 448.000000 |
| hellwarrior | RESTORE_FP32_L4 | 21.123088 | 249.104235 | 9.124080 | 402.650391 | 448.000000 |
| hellwarrior | RESTORE_FP32_L5 | 21.460039 | 259.698085 | 8.921195 | 402.650391 | 448.000000 |
| hellwarrior | RESTORE_FP32_L6 | 22.630414 | 283.904345 | 8.879154 | 402.650391 | 448.000000 |
| hellwarrior | RESTORE_FP32_L7 | 21.984982 | 271.603482 | 8.847166 | 402.650391 | 448.000000 |
| hellwarrior | RESTORE_FP32_L8 | 21.333826 | 253.424175 | 9.118544 | 402.650391 | 448.000000 |
| hellwarrior | RESTORE_FP32_L9 | 21.863340 | 268.947252 | 8.858923 | 402.650391 | 448.000000 |
| hellwarrior | RESTORE_FP32_L10 | 22.311862 | 269.075830 | 9.324285 | 402.650391 | 448.000000 |
| hook | R0 | 48.506446 | 320.198100 | 34.206886 | 1049.227539 | 1406.000000 |
| hook | R2 | 47.119092 | 291.762454 | 34.243125 | 1049.227539 | 1406.000000 |
| hook | Q_ONLY_L4 | 45.595023 | 239.710601 | 35.378414 | 1049.227539 | 1406.000000 |
| hook | Q_ONLY_L5 | 48.179444 | 304.848474 | 34.670548 | 1049.227539 | 1406.000000 |
| hook | Q_ONLY_L6 | 47.494889 | 299.902729 | 34.210266 | 1049.227539 | 1406.000000 |
| hook | Q_ONLY_L7 | 52.133075 | 282.541742 | 40.006303 | 1049.227539 | 1406.000000 |
| hook | Q_ONLY_L8 | 49.922011 | 315.964664 | 35.919766 | 1049.227539 | 1406.000000 |
| hook | Q_ONLY_L9 | 51.236213 | 299.710587 | 38.158614 | 1049.227539 | 1406.000000 |
| hook | Q_ONLY_L10 | 50.311600 | 316.281296 | 36.313195 | 1049.227539 | 1406.000000 |
| hook | RESTORE_FP32_L4 | 51.438529 | 319.767619 | 37.315945 | 1049.227539 | 1406.000000 |
| hook | RESTORE_FP32_L5 | 48.572438 | 314.864840 | 34.557049 | 1049.227539 | 1406.000000 |
| hook | RESTORE_FP32_L6 | 49.152785 | 281.190312 | 36.940284 | 1049.227539 | 1406.000000 |
| hook | RESTORE_FP32_L7 | 45.647099 | 252.654529 | 34.751971 | 1049.227539 | 1406.000000 |
| hook | RESTORE_FP32_L8 | 51.218398 | 352.018680 | 35.386804 | 1049.227539 | 1406.000000 |
| hook | RESTORE_FP32_L9 | 48.469027 | 299.786168 | 35.241809 | 1049.227539 | 1406.000000 |
| hook | RESTORE_FP32_L10 | 47.184227 | 288.755215 | 34.469965 | 1049.227539 | 1406.000000 |
| jumpingjacks | R0 | 31.048465 | 180.721540 | 23.170935 | 757.378906 | 938.000000 |
| jumpingjacks | R2 | 30.796551 | 160.167955 | 23.987529 | 757.378906 | 938.000000 |
| jumpingjacks | Q_ONLY_L4 | 35.999611 | 238.777538 | 25.327088 | 757.378906 | 938.000000 |
| jumpingjacks | Q_ONLY_L5 | 31.728278 | 213.516429 | 22.160481 | 757.378906 | 938.000000 |
| jumpingjacks | Q_ONLY_L6 | 35.319925 | 269.432392 | 22.998216 | 757.378906 | 938.000000 |
| jumpingjacks | Q_ONLY_L7 | 34.512275 | 195.776638 | 26.024676 | 757.378906 | 938.000000 |
| jumpingjacks | Q_ONLY_L8 | 34.028922 | 221.795144 | 24.146490 | 757.378906 | 938.000000 |
| jumpingjacks | Q_ONLY_L9 | 33.098853 | 178.307568 | 25.456289 | 757.378906 | 938.000000 |
| jumpingjacks | Q_ONLY_L10 | 32.487609 | 175.028846 | 24.985438 | 757.378906 | 938.000000 |
| jumpingjacks | RESTORE_FP32_L4 | 33.459411 | 200.923418 | 24.645515 | 757.378906 | 938.000000 |
| jumpingjacks | RESTORE_FP32_L5 | 32.017887 | 146.229941 | 26.006727 | 757.378906 | 938.000000 |
| jumpingjacks | RESTORE_FP32_L6 | 31.416229 | 204.486396 | 22.307273 | 757.378906 | 938.000000 |
| jumpingjacks | RESTORE_FP32_L7 | 32.300974 | 221.219592 | 22.357889 | 757.378906 | 938.000000 |
| jumpingjacks | RESTORE_FP32_L8 | 35.214308 | 220.099881 | 25.483489 | 757.378906 | 938.000000 |
| jumpingjacks | RESTORE_FP32_L9 | 33.076169 | 221.400897 | 23.164342 | 757.378906 | 938.000000 |
| jumpingjacks | RESTORE_FP32_L10 | 35.042330 | 260.505075 | 23.175869 | 757.378906 | 938.000000 |

GPU peaks are PyTorch renderer allocated/reserved, not complete device VRAM or metric-process peaks. Mean kernel-path time covers synchronized deformation+render, excludes I/O and loading; first frame included and separately listed. RSS is sampled every 0.5 s by /proc for job process plus live descendants; shared pages may be counted multiple times and short peaks may be missed. Fresh-process overhead is included in process wall times. No performance/acceleration conclusion is drawn from differences between variants. The initial psutil launch issue was fixed before pilot by /proc sampling without dependency changes. The existing SciPy/NumPy compatibility warning is retained in logs; no environment update was attempted and baseline metrics must pass the fixed tolerance.

