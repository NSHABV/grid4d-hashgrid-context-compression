> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Влияние области диапазона квантования: GLOBAL8 против LEVEL8

Статус завершения и сохранности — FINAL_VALIDATION.json. Корректное завершение не означает обязательного превосходства LEVEL8. Это exploratory baseline comparison на пяти ранее наблюдавшихся сценах, а не независимая валидация универсального метода. Нового обучения и загрузок нет.

## Постановка и происхождение

R0 — исходный FP32 xyz. GLOBAL8 — прежние frozen uint8 с единым диапазоном. LEVEL8 — uint8 с 16 диапазонами, каждый общий обоим каналам соответствующего уровня. Все 6 098 108 allocated rows,16 уровней × 2 канала, сохранены. Mutant M10/L4 — замороженный исторический контроль другого представления; selector не запускался. Temporal/MLP/Gaussian/buffers неизменны. Все 11 архивов и исходники заморожены до первого нового quality measurement.

Ранний level-8 из PHASE2 неэквивалентен:200 итераций, 400×400, все 4 сетки, legacy LPIPS, другой transport. Совместимые controls переиспользованы только после exact ordinal0 PNG/floatRGB smoke, provenance/runtime,decodedxyz иcamera/time/GT проверки. Новые validation controls четырёх старых сцен измерены отдельно. Метрики —800×800, чёрный фон, PNG round-trip, FP32 mean(per-view), SSIM, STANDARD_VGG normalize=True ровно один раз. Test уже наблюдался; кадры коррелированы. SPLIT_MANIFEST содержит все path/image/camera/time пересечения; никакие views не исключались.

## Реальные полные spatial-файлы

| scene | state | filesystem_bytes | level_member_bytes | metadata_member_bytes | framing_bytes | numerical_nbytes |
| --- | --- | --- | --- | --- | --- | --- |
| mutant | GLOBAL8 | 1290972 | 1287999 | 1249 | 1724 | 12196216 |
| mutant | LEVEL8 | 5109774 | 5106159 | 1891 | 1724 | 12196216 |
| mutant | M10 | 1359544 | 1356534 | 1286 | 1724 | 12606974 |
| bouncingballs | GLOBAL8 | 2079605 | 2076637 | 1244 | 1724 | 12196216 |
| bouncingballs | LEVEL8 | 4646272 | 4642660 | 1888 | 1724 | 12196216 |
| hellwarrior | GLOBAL8 | 1766500 | 1763531 | 1245 | 1724 | 12196216 |
| hellwarrior | LEVEL8 | 5594208 | 5590611 | 1873 | 1724 | 12196216 |
| hook | GLOBAL8 | 1488768 | 1485799 | 1245 | 1724 | 12196216 |
| hook | LEVEL8 | 4941703 | 4938097 | 1882 | 1724 | 12196216 |
| jumpingjacks | GLOBAL8 | 1917589 | 1914621 | 1244 | 1724 | 12196216 |
| jumpingjacks | LEVEL8 | 4902585 | 4898980 | 1881 | 1724 | 12196216 |

Это spatial xyz only, не самостоятельные сцены Grid4D. GLOBAL8/LEVEL8 имеют одинаковые12 196 216 B численных кодов, но разные compressed sizes. Compressed NPY member включает header+data. Все состояния перепакованы в единыйv3: DEFLATE6,фиксированныйZIP/NPY,точная metadata диапазонов оплачена. M10 не квантовался заново; старыеv2 размеры не подмешаны.

## Качество по сценам и splits

### mutant: val

| state | DEFLATE_B | PSNR | SSIM | LPIPS_STANDARD_VGG | PSNR_loss_to_R0 | extra_B_vs_GLOBAL8 | reused |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | None | 44.0684890747 | 0.996525585651 | 0.00582623155788 | 0 | None | True |
| GLOBAL8 | 1290972 | 38.9088020325 | 0.990441977978 | 0.00854807905853 | 5.15968704224 | 0 | True |
| LEVEL8 | 5109774 | 42.6132965088 | 0.995618700981 | 0.0062844408676 | 1.45519256592 | 3818802 | False |
| M10 | 1359544 | 39.229259491 | 0.99121427536 | 0.00826271437109 | 4.83922958374 | 68572 | True |

### mutant: test

| state | DEFLATE_B | PSNR | SSIM | LPIPS_STANDARD_VGG | PSNR_loss_to_R0 | extra_B_vs_GLOBAL8 | reused |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | None | 43.9813652039 | 0.996362566948 | 0.00577259948477 | 0 | None | True |
| GLOBAL8 | 1290972 | 38.6794548035 | 0.989810287952 | 0.0086723100394 | 5.30191040039 | 0 | True |
| LEVEL8 | 5109774 | 42.2892684937 | 0.995278000832 | 0.00628227507696 | 1.69209671021 | 3818802 | False |
| M10 | 1359544 | 38.9509506226 | 0.990351080894 | 0.00840528216213 | 5.0304145813 | 68572 | True |

### bouncingballs: val

| state | DEFLATE_B | PSNR | SSIM | LPIPS_STANDARD_VGG | PSNR_loss_to_R0 | extra_B_vs_GLOBAL8 | reused |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | None | 42.7797660828 | 0.995770096779 | 0.0183018241078 | 0 | None | False |
| GLOBAL8 | 2079605 | 38.9250564575 | 0.994454979897 | 0.0212652757764 | 3.85470962524 | 0 | False |
| LEVEL8 | 4646272 | 41.2792778015 | 0.995465874672 | 0.018911883235 | 1.50048828125 | 2566667 | False |

### bouncingballs: test

| state | DEFLATE_B | PSNR | SSIM | LPIPS_STANDARD_VGG | PSNR_loss_to_R0 | extra_B_vs_GLOBAL8 | reused |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | None | 42.4922409058 | 0.995813727379 | 0.0178180485964 | 0 | None | True |
| GLOBAL8 | 2079605 | 38.8329849243 | 0.994528949261 | 0.0206007715315 | 3.65925598145 | 0 | True |
| LEVEL8 | 4646272 | 41.0467948914 | 0.995457947254 | 0.0184065382928 | 1.4454460144 | 2566667 | False |

### hellwarrior: val

| state | DEFLATE_B | PSNR | SSIM | LPIPS_STANDARD_VGG | PSNR_loss_to_R0 | extra_B_vs_GLOBAL8 | reused |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | None | 42.5787315369 | 0.99071586132 | 0.0216594710946 | 0 | None | False |
| GLOBAL8 | 1766500 | 42.1312217712 | 0.989674091339 | 0.02289560996 | 0.447509765625 | 0 | False |
| LEVEL8 | 5594208 | 42.5027999878 | 0.990532398224 | 0.0218494310975 | 0.0759315490723 | 3827708 | False |

### hellwarrior: test

| state | DEFLATE_B | PSNR | SSIM | LPIPS_STANDARD_VGG | PSNR_loss_to_R0 | extra_B_vs_GLOBAL8 | reused |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | None | 42.8409957886 | 0.990779280663 | 0.0228067878634 | 0 | None | True |
| GLOBAL8 | 1766500 | 42.2701873779 | 0.989561378956 | 0.0243978463113 | 0.570808410645 | 0 | True |
| LEVEL8 | 5594208 | 42.7731208801 | 0.990614116192 | 0.0230098571628 | 0.0678749084473 | 3827708 | False |

### hook: val

| state | DEFLATE_B | PSNR | SSIM | LPIPS_STANDARD_VGG | PSNR_loss_to_R0 | extra_B_vs_GLOBAL8 | reused |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | None | 39.7743721008 | 0.992597281933 | 0.00996544584632 | 0 | None | False |
| GLOBAL8 | 1488768 | 37.6979904175 | 0.989649116993 | 0.0121910953894 | 2.07638168335 | 0 | False |
| LEVEL8 | 4941703 | 39.111782074 | 0.991567313671 | 0.0105008576065 | 0.662590026855 | 3452935 | False |

### hook: test

| state | DEFLATE_B | PSNR | SSIM | LPIPS_STANDARD_VGG | PSNR_loss_to_R0 | extra_B_vs_GLOBAL8 | reused |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | None | 39.0240783691 | 0.99058419466 | 0.0119009977207 | 0 | None | True |
| GLOBAL8 | 1488768 | 37.1369247437 | 0.987501263618 | 0.0142304776236 | 1.88715362549 | 0 | True |
| LEVEL8 | 4941703 | 38.3380088806 | 0.989556014538 | 0.0124622741714 | 0.686069488525 | 3452935 | False |

### jumpingjacks: val

| state | DEFLATE_B | PSNR | SSIM | LPIPS_STANDARD_VGG | PSNR_loss_to_R0 | extra_B_vs_GLOBAL8 | reused |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | None | 39.6697502136 | 0.992632746696 | 0.0109849916771 | 0 | None | False |
| GLOBAL8 | 1917589 | 38.614692688 | 0.991584122181 | 0.0116753671318 | 1.05505752563 | 0 | False |
| LEVEL8 | 4902585 | 39.3880004883 | 0.99234187603 | 0.0111263496801 | 0.281749725342 | 2984996 | False |

### jumpingjacks: test

| state | DEFLATE_B | PSNR | SSIM | LPIPS_STANDARD_VGG | PSNR_loss_to_R0 | extra_B_vs_GLOBAL8 | reused |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | None | 39.2458572388 | 0.992448985577 | 0.0106504671276 | 0 | None | True |
| GLOBAL8 | 1917589 | 38.4173469543 | 0.991524100304 | 0.0112760504708 | 0.828510284424 | 0 | True |
| LEVEL8 | 4902585 | 39.0337791443 | 0.992241978645 | 0.0107268560678 | 0.212078094482 | 2984996 | False |

## Signed эффект LEVEL8−GLOBAL8

| scene | split | size_delta_B | data_delta_B | metadata_delta_B | framing_delta_B | PSNR_gain | SSIM_gain | LPIPS_improvement | remaining_PSNR_gap_R0 | fraction_global_PSNR_gap_closed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mutant | val | 3818802 | 3818160 | 642 | 0 | 3.70449447632 | 0.00517672300339 | 0.00226363819093 | 1.45519256592 | 0.717968831442 |
| mutant | test | 3818802 | 3818160 | 642 | 0 | 3.60981369019 | 0.00546771287918 | 0.00239003496245 | 1.69209671021 | 0.680851507773 |
| bouncingballs | val | 2566667 | 2566023 | 644 | 0 | 2.35422134399 | 0.00101089477539 | 0.00235339254141 | 1.50048828125 | 0.610738959058 |
| bouncingballs | test | 2566667 | 2566023 | 644 | 0 | 2.21380996704 | 0.000928997993469 | 0.0021942332387 | 1.4454460144 | 0.60498909567 |
| hellwarrior | val | 3827708 | 3827080 | 628 | 0 | 0.371578216553 | 0.000858306884766 | 0.00104617886245 | 0.0759315490723 | 0.830324263502 |
| hellwarrior | test | 3827708 | 3827080 | 628 | 0 | 0.502933502197 | 0.00105273723602 | 0.0013879891485 | 0.0678749084473 | 0.881089859257 |
| hook | val | 3452935 | 3452298 | 637 | 0 | 1.41379165649 | 0.00191819667816 | 0.0016902377829 | 0.662590026855 | 0.680891990057 |
| hook | test | 3452935 | 3452298 | 637 | 0 | 1.20108413696 | 0.00205475091934 | 0.00176820345223 | 0.686069488525 | 0.636452761842 |
| jumpingjacks | val | 2984996 | 2984359 | 637 | 0 | 0.773307800293 | 0.00075775384903 | 0.000549017451704 | 0.281749725342 | 0.732953210137 |
| jumpingjacks | test | 2984996 | 2984359 | 637 | 0 | 0.616432189941 | 0.000717878341675 | 0.000549194402993 | 0.212078094482 | 0.744024789469 |

Положительное LPIPS_improvement означает уменьшение LPIPS. Доля закрытого PSNR gap — отношение разностейdB, а не доля восстановленных пикселей/качества. Все отрицательные и малые отличия сохранены без tolerance.

## Per-view ухудшения

| scene | split | views_PSNR_worse | views_SSIM_worse | views_LPIPS_worse | min_per_view_PSNR_gain | max_per_view_PSNR_gain |
| --- | --- | --- | --- | --- | --- | --- |
| mutant | val | 0 | 0 | 0 | 0.57848739624 | 6.29872512817 |
| mutant | test | 0 | 0 | 0 | 0.709892272949 | 5.68274688721 |
| bouncingballs | val | 0 | 0 | 0 | 0.717575073242 | 4.67864990234 |
| bouncingballs | test | 0 | 0 | 0 | 0.967292785645 | 3.99666213989 |
| hellwarrior | val | 1 | 0 | 0 | -0.0508422851562 | 1.04264831543 |
| hellwarrior | test | 1 | 1 | 0 | -0.204174041748 | 1.321849823 |
| hook | val | 2 | 2 | 0 | -0.40442276001 | 4.05375289917 |
| hook | test | 1 | 1 | 0 | -0.737609863281 | 4.27542495728 |
| jumpingjacks | val | 3 | 2 | 2 | -0.559684753418 | 2.15530014038 |
| jumpingjacks | test | 1 | 1 | 0 | -0.0600357055664 | 1.58655166626 |

## Pareto

| scene | split | axes | state | nondominated | dominators |
| --- | --- | --- | --- | --- | --- |
| mutant | val | bytes+PSNR | GLOBAL8 | True |  |
| mutant | val | bytes+PSNR | LEVEL8 | True |  |
| mutant | val | bytes+PSNR | M10 | True |  |
| mutant | val | bytes+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| mutant | val | bytes+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| mutant | val | bytes+LPIPS_STANDARD_VGG | M10 | True |  |
| mutant | val | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| mutant | val | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| mutant | val | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | M10 | True |  |
| mutant | test | bytes+PSNR | GLOBAL8 | True |  |
| mutant | test | bytes+PSNR | LEVEL8 | True |  |
| mutant | test | bytes+PSNR | M10 | True |  |
| mutant | test | bytes+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| mutant | test | bytes+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| mutant | test | bytes+LPIPS_STANDARD_VGG | M10 | True |  |
| mutant | test | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| mutant | test | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| mutant | test | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | M10 | True |  |
| bouncingballs | val | bytes+PSNR | GLOBAL8 | True |  |
| bouncingballs | val | bytes+PSNR | LEVEL8 | True |  |
| bouncingballs | val | bytes+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| bouncingballs | val | bytes+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| bouncingballs | val | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| bouncingballs | val | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| bouncingballs | test | bytes+PSNR | GLOBAL8 | True |  |
| bouncingballs | test | bytes+PSNR | LEVEL8 | True |  |
| bouncingballs | test | bytes+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| bouncingballs | test | bytes+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| bouncingballs | test | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| bouncingballs | test | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| hellwarrior | val | bytes+PSNR | GLOBAL8 | True |  |
| hellwarrior | val | bytes+PSNR | LEVEL8 | True |  |
| hellwarrior | val | bytes+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| hellwarrior | val | bytes+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| hellwarrior | val | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| hellwarrior | val | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| hellwarrior | test | bytes+PSNR | GLOBAL8 | True |  |
| hellwarrior | test | bytes+PSNR | LEVEL8 | True |  |
| hellwarrior | test | bytes+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| hellwarrior | test | bytes+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| hellwarrior | test | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| hellwarrior | test | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| hook | val | bytes+PSNR | GLOBAL8 | True |  |
| hook | val | bytes+PSNR | LEVEL8 | True |  |
| hook | val | bytes+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| hook | val | bytes+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| hook | val | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| hook | val | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| hook | test | bytes+PSNR | GLOBAL8 | True |  |
| hook | test | bytes+PSNR | LEVEL8 | True |  |
| hook | test | bytes+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| hook | test | bytes+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| hook | test | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| hook | test | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| jumpingjacks | val | bytes+PSNR | GLOBAL8 | True |  |
| jumpingjacks | val | bytes+PSNR | LEVEL8 | True |  |
| jumpingjacks | val | bytes+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| jumpingjacks | val | bytes+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| jumpingjacks | val | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| jumpingjacks | val | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| jumpingjacks | test | bytes+PSNR | GLOBAL8 | True |  |
| jumpingjacks | test | bytes+PSNR | LEVEL8 | True |  |
| jumpingjacks | test | bytes+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| jumpingjacks | test | bytes+LPIPS_STANDARD_VGG | LEVEL8 | True |  |
| jumpingjacks | test | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | GLOBAL8 | True |  |
| jumpingjacks | test | bytes+PSNR+SSIM+LPIPS_STANDARD_VGG | LEVEL8 | True |  |

Доминирование: не хуже по всем выбранным координатам и строго лучше хотя бы по одной, без допуска. R0 — только quality reference, без выдуманного rate. BD-rate по двум точкам не вычислялся.

## Проверки и ресурсы

{
  "status": "Измерения завершены; итог сохранности см. FINAL_VALIDATION.json",
  "resources": {
    "guarded_seconds": 937.9659504629999,
    "peak_sampled_process_tree_RSS_bytes": 4857167872,
    "peak_total_device_MiB": 3110
  },
  "new_frames": 374,
  "metric_views": 640,
  "independent_decodes": 11,
  "exact_level_arrays": 176
}

11 независимых декодирований: 176 массивов, metadata и полная FP32-реконструкция совпали точно; повторная сборка побитно идентична. GLOBAL8 побитно совпал с прежним представлением, LEVEL8 проверен независимой формулой и scalar spots. Synthetic tests: rounding,constant,соседние ranges,missing/extra ranges,scope/precision,metadata/shape/offset,corrupt/truncatedmembers. Python read audit — проверка доступов реализации, не OS sandbox. Перед каждым deformation forward хешxyz; другие веса побитно совпадают. Runtime/source hashes и frozenviews сохранены.

RESOURCES.csv содержит cold subprocess, sampled process-tree RSS, minimum available RAM и полную занятую VRAM устройства (включает desktop). GPU использовался только для render/metrics, не quantization/compression/decode. FILE_SIZES.csv раздельно содержит compression,colddecode иinternaldecode; последняя колонка исключает запуск процесса, но не является повторным прогретым benchmark. CPU_COMPLETE.json включает quantization+diagnostics; RENDER.json иMETRICS.json — rendering иmetrics отдельно. RSS sum может повторно учитывать shared pages. Hashing/report отдельно в preservation/REPORT_COMPLETE.

## Научные границы

Меньший quantizer step не гарантирует меньшую ошибку каждого параметра или улучшение каждого кадра: положения сеток квантования различаются. Поуровневая feature-error диагностика — LEVEL_RANGES_AND_ERRORS.csv, а не замена image metrics. Нельзя приписывать весь исходный gap общему range, если remaininggap ненулевой. Scope quantization не заявляется новой научной разработкой; прошлый TRANSFER_PASS остаётся корректным в прежней постановке. Никаких H4 gains,wholeGrid4D ratio,универсальности или нового quality gate.

## Воспроизведение

Pinned WSL audit-env, Python3.10.21,Torch2.7.0+cu128,NumPy1.26.4,zlib1.3.2. QUANTIZER_SCOPE_SPEC.md содержит команды и точную арифметику. INPUT_MANIFEST/PREREGISTERED_PROTOCOL/ARCHIVES_FREEZE фиксируют источники и предписанные правила. Старые runs не изменялись; окончательный контроль — FINAL_VALIDATION.json.

## Ответы на исследовательские вопросы

**mutant test:** Δbytes=+3818802; ΔPSNR=+3.60981369019dB; ΔSSIM=+0.00546771287918; improvement LPIPS=+0.00239003496245. LEVEL8 не хуже по rate и всем трём метрикам качества: **False**. Не хуже по всем метрикам качества: **True**. Остаточный разрыв до R0=1.69209671021dB; отношение закрытого gap=0.680851507773. При положительном Δbytes и положительных quality deltas наблюдается обмен большего файла на меньшее искажение, а не бесплатный выигрыш.

**bouncingballs test:** Δbytes=+2566667; ΔPSNR=+2.21380996704dB; ΔSSIM=+0.000928997993469; improvement LPIPS=+0.0021942332387. LEVEL8 не хуже по rate и всем трём метрикам качества: **False**. Не хуже по всем метрикам качества: **True**. Остаточный разрыв до R0=1.4454460144dB; отношение закрытого gap=0.60498909567. При положительном Δbytes и положительных quality deltas наблюдается обмен большего файла на меньшее искажение, а не бесплатный выигрыш.

**hellwarrior test:** Δbytes=+3827708; ΔPSNR=+0.502933502197dB; ΔSSIM=+0.00105273723602; improvement LPIPS=+0.0013879891485. LEVEL8 не хуже по rate и всем трём метрикам качества: **False**. Не хуже по всем метрикам качества: **True**. Остаточный разрыв до R0=0.0678749084473dB; отношение закрытого gap=0.881089859257. При положительном Δbytes и положительных quality deltas наблюдается обмен большего файла на меньшее искажение, а не бесплатный выигрыш.

**hook test:** Δbytes=+3452935; ΔPSNR=+1.20108413696dB; ΔSSIM=+0.00205475091934; improvement LPIPS=+0.00176820345223. LEVEL8 не хуже по rate и всем трём метрикам качества: **False**. Не хуже по всем метрикам качества: **True**. Остаточный разрыв до R0=0.686069488525dB; отношение закрытого gap=0.636452761842. При положительном Δbytes и положительных quality deltas наблюдается обмен большего файла на меньшее искажение, а не бесплатный выигрыш.

**jumpingjacks test:** Δbytes=+2984996; ΔPSNR=+0.616432189941dB; ΔSSIM=+0.000717878341675; improvement LPIPS=+0.000549194402993. LEVEL8 не хуже по rate и всем трём метрикам качества: **False**. Не хуже по всем метрикам качества: **True**. Остаточный разрыв до R0=0.212078094482dB; отношение закрытого gap=0.744024789469. При положительном Δbytes и положительных quality deltas наблюдается обмен большего файла на меньшее искажение, а не бесплатный выигрыш.

**Mutant val, LEVEL8 против frozen M10/L4:** Δbytes=+3750230; ΔPSNR=+3.38403701782dB; ΔSSIM=+0.00440442562103; LPIPS improvement=+0.00197827350348. Это сравнение двух схем целиком, не изолированный эффект только scope.

**Mutant test, LEVEL8 против frozen M10/L4:** Δbytes=+3750230; ΔPSNR=+3.33831787109dB; ΔSSIM=+0.00492691993713; LPIPS improvement=+0.00212300708517. Это сравнение двух схем целиком, не изолированный эффект только scope.

**mutant, feature-space:** диапазон global step / level step=1…408.485847991; RMSE уменьшилась на 15/16 уровнях. Это измеренная диагностика всего slice, не гарантия каждой координаты или image quality.

**bouncingballs, feature-space:** диапазон global step / level step=1.00658388208…182.635286923; RMSE уменьшилась на 16/16 уровнях. Это измеренная диагностика всего slice, не гарантия каждой координаты или image quality.

**hellwarrior, feature-space:** диапазон global step / level step=1.11540119575…185.607209501; RMSE уменьшилась на 16/16 уровнях. Это измеренная диагностика всего slice, не гарантия каждой координаты или image quality.

**hook, feature-space:** диапазон global step / level step=1.13593940777…97.6720587359; RMSE уменьшилась на 16/16 уровнях. Это измеренная диагностика всего slice, не гарантия каждой координаты или image quality.

**jumpingjacks, feature-space:** диапазон global step / level step=1.21834217643…78.5289158163; RMSE уменьшилась на 16/16 уровнях. Это измеренная диагностика всего slice, не гарантия каждой координаты или image quality.

Смена только scope улучшила mean PSNR в 10/10 scene-split сравнениях; положительный remaining gap до R0 остался в 10/10. Это локальное свидетельство вклада global range в distortion в проверенных конфигурациях; доля закрытого gap приведена для каждой, поэтому весь gap общему диапазону не приписывается. Размер и всеметрикам качества рассматриваются вместе. Одного факта улучшения качества недостаточно, чтобы объявить LEVEL8 экономически лучшим baseline.

Mixed precision поверх другого baseline может оставаться исследовательским вопросом, но её необходимость и преимущество этот опыт не доказывает. Следующий один шаг: заранее ограниченное сравнение GLOBAL8 и LEVEL8 при сопоставимом фактическом byte budget с отдельным calibration rule и замороженным test; сначала установить, сохраняется ли выигрыш scope при равном rate, прежде чем усложнять mixed-precision policy. Здесь этот шаг не выполнялся.

## Техническая история

Первый CPU mutant child завершился FileNotFoundError до загрузки checkpoint:  Windows backslashes в относительном manifestpath. Исходный manifest, traceback и команда сохранены в path_fix_001; исправлены только разделители, повтор имеет отдельныйлог. Математические helpers, protocol, quantization и forward не менялись. Ошибка классифицирована как обычная оркестрация, без ложного BLOCKED_NEEDS_ULTRA.


## Проверка отчёта и дополнительные точные сведения

Проверено:11 budget rows,32 scene/split/state metric rows,640 per-view rows,160 level/state diagnostics. Во всех файлах сумма непересекающихся компонентов совпала с filesystem size; все10 size deltas разложены точно. Все GLOBAL8/LEVEL8 имеют одинаковые12 196 216 B numerical payload.

| Scene | Checkpoint | SHA256 |
|---|---|---|
|mutant|<PROJECT_ROOT>/research/calibrated_precision_validation_20261030_01/full/model/deform/iteration_50000/deform.pth|376d0d19d1c01241c3f4972244c043d675e37ce1abbfe09ab2cd953d1b0f3480|
|bouncingballs|<PROJECT_ROOT>/outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth|3306dabf8057728abfa7cda87d78c723b27a357f968fd7d721ea727ebd043090|
|hellwarrior|<PROJECT_ROOT>/research/mean8_cross_scene_20261018_02/full/model/deform/iteration_50000/deform.pth|4526ff7fe18a8570e97139dfa8d98882ab394ce49433113a4e29c36839ca6dc6|
|hook|<PROJECT_ROOT>/research/h4_independent_validation_20261029_02/full/model/deform/iteration_50000/deform.pth|320fbc4432a2ef4aece8678ea5803e0659cf60a7bb2aa69008a353ad0616a2fd|
|jumpingjacks|<PROJECT_ROOT>/research/h4_fourth_scene_validation_20261029_01/full/model/deform/iteration_50000/deform.pth|a6ddef70bad80b2015b9f8e2fe2b7eb8d2f9128d54f890326a0898b2a96dc0df|

### Раздельные времена

| Scene | Range fitting s | Quantization s |
|---|---:|---:|
|mutant|0.003610616|0.066259155|
|bouncingballs|0.003250477|0.048561072|
|hellwarrior|0.003507926|0.054853471|
|hook|0.003170329|0.045247900|
|jumpingjacks|0.003210162|0.045907788|
Это отдельный timing replay прежней фиксированной операции наCPU; все16 codes повторно сверены побитно. Измерение изолирует quantization от diagnostics/torchload/diskIO и не создаёт новый метод/вариант.

| Category | Summed seconds |
|---|---:|
|Compression,11 files|7.968895|
|Cold independent decode,11 processes|34.615410|
|Internal decode,without process startup|1.993824|
|Rendering internal,includes loading/instrumentation|374.581146|
|New metrics,excludes LPIPS construction|79.909427|
|Initial hash audit + preparation|198.026671|

Times overlap by nesting: do not sum internal times with full process walls. Cold decode includes output writes; internal decode does not. Final hashing time is inPRESERVATION_FINAL.json. Report writing time is inREPORT_COMPLETE.json.

Повторно проверены 17 runtime/source hashes. Для5 GLOBAL8 иmutant M10 все16 compressed level members побитно совпадают с прежними физическими архивами. Их v2→v3 size delta полностью объясняется metadata/framing; подробностиPOST_MEASUREMENT_AUDIT.json.

### Графики

Пунктир на графике rate/quality — R0, только ориентир качества. Показаны измеренные точки; непрерывная RD-кривая не строилась.

Measured test rate and quality (внешний артефакт; см. каталог исключённых ссылок)

Level range and feature error diagnostics (внешний артефакт; см. каталог исключённых ссылок)

### Команды для нового воспроизведения

В новом уникальном каталоге копировать только исходники, не результаты. Для подготовки в Windows использовать `prepare_portable.py` вместо исторического `prepare.py`: обёртка нормализует только относительные пути перед записью нового manifest. В launch.sh изменить путь нового run, оставив runtime. Затем `launch.sh setup`, `cpu`, `profile`, `freeze`, `pilot`, `evaluate`; `post_measurement_audit.py` в WSL; `report.py`, `plots.py`, `review_report.py` в Windows plotting-env; `finalize.py` в WSL. Исторический prepare.py и traceback сохранены; переносимая обёртка добавлена после измерений и не использовалась для изменения результатов. Полная повторная репликация в этой сессии не выполнялась.
