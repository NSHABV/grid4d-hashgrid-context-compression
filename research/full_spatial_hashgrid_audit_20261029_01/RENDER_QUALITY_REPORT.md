> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Quantization quality
| scene | variant | PSNR | SSIM | LPIPS | delta_PSNR_vs_R0 | delta_SSIM_vs_R0 | delta_LPIPS_vs_R0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | R0 | 42.492241 | 0.995814 | 0.007435 | 0.000000 | 0.000000 | 0.000000 |
| bouncingballs | R1 | 39.840111 | 0.995079 | 0.009008 | -2.652130 | -0.000734 | 0.001573 |
| bouncingballs | R2 | 38.832985 | 0.994529 | 0.009730 | -3.659256 | -0.001285 | 0.002294 |
| hellwarrior | R0 | 42.840996 | 0.990779 | 0.015664 | 0.000000 | 0.000000 | 0.000000 |
| hellwarrior | R1 | 42.748444 | 0.990565 | 0.015835 | -0.092552 | -0.000214 | 0.000171 |
| hellwarrior | R2 | 42.270187 | 0.989561 | 0.016923 | -0.570808 | -0.001218 | 0.001259 |
| hook | R0 | 39.024078 | 0.990584 | 0.008997 | 0.000000 | 0.000000 | 0.000000 |
| hook | R1 | 38.510738 | 0.989849 | 0.009523 | -0.513340 | -0.000736 | 0.000525 |
| hook | R2 | 37.136925 | 0.987501 | 0.011111 | -1.887154 | -0.003083 | 0.002114 |
| jumpingjacks | R0 | 39.245857 | 0.992449 | 0.007618 | 0.000000 | 0.000000 | 0.000000 |
| jumpingjacks | R1 | 39.001808 | 0.992253 | 0.007720 | -0.244049 | -0.000196 | 0.000101 |
| jumpingjacks | R2 | 38.417347 | 0.991524 | 0.008221 | -0.828510 | -0.000925 | 0.000602 |

| scene | R2_minus_R1_PSNR | R2_minus_R1_SSIM | R2_minus_R1_LPIPS |
| --- | --- | --- | --- |
| bouncingballs | -1.007126 | -0.000550 | 0.000722 |
| hellwarrior | -0.478256 | -0.001004 | 0.001088 |
| hook | -1.373814 | -0.002347 | 0.001588 |
| jumpingjacks | -0.584461 | -0.000729 | 0.000501 |

PSNR/SSIM: higher is better; LPIPS: lower is better. Same20 JSON-order test views, timestamps,800×800,black background,seed0. All12 variants recomputed; old metrics not used as R0. Exact camera/time and GT hashes match within each scene. Metrics use unchanged upstream PNG8 RGB[0,1] pipeline and LPIPS VGG with original invocation (not a new normalization convention). Results are protocol-specific.
| scene | variant | mean_render_ms | first_frame_ms | peak_allocated_MiB | peak_reserved_MiB |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | R0 | 49.667918 | 508.326319 | 962.877930 | 1244.000000 |
| bouncingballs | R1 | 51.332287 | 537.431067 | 962.877930 | 1244.000000 |
| bouncingballs | R2 | 35.097468 | 207.470113 | 962.877930 | 1244.000000 |
| hellwarrior | R0 | 14.152663 | 152.645521 | 402.650391 | 448.000000 |
| hellwarrior | R1 | 19.043788 | 254.549221 | 402.650391 | 448.000000 |
| hellwarrior | R2 | 21.331773 | 297.187829 | 402.650391 | 448.000000 |
| hook | R0 | 40.704384 | 318.650000 | 1049.227539 | 1406.000000 |
| hook | R1 | 40.122788 | 322.274724 | 1049.227539 | 1406.000000 |
| hook | R2 | 39.311444 | 315.251065 | 1049.227539 | 1406.000000 |
| jumpingjacks | R0 | 25.854282 | 198.265016 | 757.378906 | 938.000000 |
| jumpingjacks | R1 | 26.695047 | 214.939239 | 757.378906 | 938.000000 |
| jumpingjacks | R2 | 27.654949 | 222.793857 | 757.378906 | 938.000000 |

Timing synchronized across deform.step+render, excludes I/O and loading; cold first view included in mean and separately shown. Peak VRAM is PyTorch allocated/reserved for renderer process, not total desktop GPU usage. Each model loaded separately. No fine-tuning. State checks confirm exact intended xyz substitution and no other learned tensor changes. CPU PNG PSNR independently agrees within1e-4dB.



## Ресурсы и ограничения

| CPU audit | Wall seconds | Peak RSS MiB |
|---|---:|---:|
| bouncingballs | 14.038 | 753.090 |
| hellwarrior | 11.419 | 710.305 |
| hook | 13.216 | 765.973 |
| jumpingjacks | 12.833 | 729.414 |

Сумма CPU audit wall: 51.505 s. Сумма wall для 12 fresh-process render+metrics: 352.395 s. Время подготовки, хеширования и написания отчётов в эти суммы не включено. CPU audit RSS относится к родительскому процессу; отдельный RSS decoder сохранён в его validation.json, одновременный суммарный RSS не измерялся. GPU peak относится к PyTorch renderer allocated/reserved, не к полной VRAM устройства или отдельному metrics process. Скорости одиночных запусков зависят от первого кадра и прогрева; различие времени R0/R1/R2 не интерпретируется как ускорение квантованием: рендерер во всех случаях получает FP32.


Ни одна сцена не улучшилась по PSNR, SSIM или LPIPS в R2 относительно R0/R1. Приемлемость потерь требует внешнего требования к качеству; критерий GO по качеству не изобретается после измерений.

PSNR deltas (внешний артефакт; см. каталог исключённых ссылок)
