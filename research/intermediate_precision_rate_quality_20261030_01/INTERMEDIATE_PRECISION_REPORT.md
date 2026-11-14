> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Промежуточная точность выбранного уровня: M10/M12

Выполнены8 новых состояний,160 новых кадров и8 контрольных кадров. Созданы40 пространственных архивов RAW/DEFLATE:16 для M10/M12 и24 для перепакованных R2/M16/RESTORE. Все файлы используют одну schema v2. Это bounded exploratory experiment на прежних test views, не независимая политика выбора точности и не новый специализированный компрессор. Уровни zero-based и не менялись.

M10/M12/M16 хранятся в little-endian uint16 NPY:2 B/scalar, независимо от числа допустимых кодов. Кодовая точность10/12 не означает физическую упаковку в10/12 бит. Остальные15 уровней — прежние uint8. Все renderer embeddings остаются FP32. Архивы содержат только spatial xyz, без temporal grids, MLP и Gaussian PLY.

R2/M16 прошли exact ordinal0 controls, RESTORE подтверждён полным exact xyz и сохранностью прежнего pipeline/quality provenance. Контрольные20-view метрики переиспользованы. M10/M12 рендерились из нового DEFLATE decoder output на всех20 views, метрики измерены заново. Primary LPIPS — прежний проверенный STANDARD_VGG (normalize=True ровно один раз, eval/inference_mode), legacy заново не запускался. Mean PSNR — среднее покадровых PSNR. Источники и hashes приведены в RESULTS.csv, protocol и per-scene files.

## bouncingballs — xyz L5

| state | quantization_bits_selected | storage_dtype_selected | DEFLATE_B | selected_member_B | PSNR | SSIM | LPIPS_STANDARD_VGG |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R2 | 8 | \|u1 | 2079543 | 183235 | 38.83298492 | 0.9945289493 | 0.02060077153 |
| M10 | 10 | <u2 | 2271530 | 375181 | 39.79003143 | 0.9949472547 | 0.01908859611 |
| M12 | 12 | <u2 | 2415601 | 519253 | 39.86783218 | 0.9949831963 | 0.01900997013 |
| M16 | 16 | <u2 | 2772005 | 875654 | 39.88209152 | 0.9949885607 | 0.01901504211 |
| RESTORE | None | <f4 | 5859914 | 3963583 | 39.88188934 | 0.9949882627 | 0.01901414432 |

Size versus PSNR (внешний артефакт; см. каталог исключённых ссылок)

Size versus LPIPS (внешний артефакт; см. каталог исключённых ссылок)
## hellwarrior — xyz L8

| state | quantization_bits_selected | storage_dtype_selected | DEFLATE_B | selected_member_B | PSNR | SSIM | LPIPS_STANDARD_VGG |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R2 | 8 | \|u1 | 1766437 | 318526 | 42.27018738 | 0.989561379 | 0.02439784631 |
| M10 | 10 | <u2 | 2131655 | 683709 | 42.34648895 | 0.9897173643 | 0.02404854074 |
| M12 | 12 | <u2 | 2461528 | 1013580 | 42.3482666 | 0.9897195697 | 0.02404158935 |
| M16 | 16 | <u2 | 3022041 | 1574095 | 42.34815979 | 0.9897205234 | 0.02404378355 |
| RESTORE | None | <f4 | 5370365 | 3922437 | 42.34817505 | 0.9897204638 | 0.02404460683 |

Size versus PSNR (внешний артефакт; см. каталог исключённых ссылок)

Size versus LPIPS (внешний артефакт; см. каталог исключённых ссылок)
## hook — xyz L6

| state | quantization_bits_selected | storage_dtype_selected | DEFLATE_B | selected_member_B | PSNR | SSIM | LPIPS_STANDARD_VGG |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R2 | 8 | \|u1 | 1488708 | 232328 | 37.13692474 | 0.9875012636 | 0.01423047762 |
| M10 | 10 | <u2 | 1769941 | 513518 | 37.3614769 | 0.9880058169 | 0.01385677792 |
| M12 | 12 | <u2 | 2017030 | 760608 | 37.37060928 | 0.9880375862 | 0.0138451485 |
| M16 | 16 | <u2 | 2462936 | 1206514 | 37.37082672 | 0.9880364537 | 0.01383729838 |
| RESTORE | None | <f4 | 5229883 | 3973479 | 37.37076569 | 0.9880367517 | 0.01383819617 |

Size versus PSNR (внешний артефакт; см. каталог исключённых ссылок)

Size versus LPIPS (внешний артефакт; см. каталог исключённых ссылок)
## jumpingjacks — xyz L4

| state | quantization_bits_selected | storage_dtype_selected | DEFLATE_B | selected_member_B | PSNR | SSIM | LPIPS_STANDARD_VGG |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R2 | 8 | \|u1 | 1917526 | 58584 | 38.41734695 | 0.9915241003 | 0.01127605047 |
| M10 | 10 | <u2 | 1992001 | 133020 | 38.51586533 | 0.9916187525 | 0.011214233 |
| M12 | 12 | <u2 | 2064313 | 205331 | 38.50536346 | 0.9916176796 | 0.01121404115 |
| M16 | 16 | <u2 | 2239009 | 380029 | 38.50646973 | 0.9916187525 | 0.01120861061 |
| RESTORE | None | <f4 | 3405108 | 1546145 | 38.50668335 | 0.9916188121 | 0.01120911725 |

Size versus PSNR (внешний артефакт; см. каталог исключённых ссылок)

Size versus LPIPS (внешний артефакт; см. каталог исключённых ссылок)

## Цена и сохранённое качество

| scene | state | saving_vs_M16_B | saving_vs_M16_pct | extra_vs_R2_B | PSNR_gain_vs_R2 | PSNR_gap_to_M16 | SSIM_gain_vs_R2 | SSIM_gap_to_M16 | LPIPS_STANDARD_VGG_gain_vs_R2 | LPIPS_STANDARD_VGG_gap_to_M16 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | M10 | 500475 | 18.05462111 | 191987 | 0.9570465088 | 0.09206008911 | 0.000418305397 | 4.130601883e-05 | 0.001512175426 | 7.35539943e-05 |
| bouncingballs | M12 | 356404 | 12.85726397 | 336058 | 1.03484726 | 0.01425933838 | 0.0004542469978 | 5.36441803e-06 | 0.001590801403 | -5.071982741e-06 |
| hellwarrior | M10 | 890386 | 29.46306817 | 365218 | 0.07630157471 | 0.001670837402 | 0.0001559853554 | 3.159046173e-06 | 0.0003493055701 | 4.757195711e-06 |
| hellwarrior | M12 | 560513 | 18.5474982 | 695091 | 0.07807922363 | -0.0001068115234 | 0.0001581907272 | 9.536743164e-07 | 0.0003562569618 | -2.194195986e-06 |
| hook | M10 | 692995 | 28.13694712 | 281233 | 0.2245521545 | 0.009349822998 | 0.000504553318 | 3.063678741e-05 | 0.0003736997023 | 1.947954297e-05 |
| hook | M12 | 445906 | 18.10465233 | 528322 | 0.2336845398 | 0.0002174377441 | 0.0005363225937 | -1.132488251e-06 | 0.0003853291273 | 7.850117981e-06 |
| jumpingjacks | M10 | 247008 | 11.03202354 | 74475 | 0.09851837158 | -0.009395599365 | 9.46521759e-05 | 0 | 6.181746721e-05 | 5.622394383e-06 |
| jumpingjacks | M12 | 174696 | 7.802380428 | 146787 | 0.08801651001 | 0.001106262207 | 9.35792923e-05 | 1.072883606e-06 | 6.200931966e-05 | 5.430541933e-06 |

Gain PSNR/SSIM = Mp−reference; improvement LPIPS = reference−Mp. Gap к M16/RESTORE = reference−Mp для PSNR/SSIM и Mp−reference для LPIPS. Знаки не обрезаются. Retained gain — отношение gain Mp над R2 к gain M16 над R2, описательное число без ограничения100%; это не доля восстановленных исходных весов.

| scene | state | PSNR_retained_M16_gain_pct | SSIM_retained_M16_gain_pct | LPIPS_STANDARD_VGG_retained_M16_gain_pct |
| --- | --- | --- | --- | --- |
| bouncingballs | M10 | 91.2249061 | 91.0128388 | 95.36150409 |
| bouncingballs | M12 | 98.6408113 | 98.83283621 | 100.3198517 |
| hellwarrior | M10 | 97.85714286 | 98.01498127 | 98.65639763 |
| hellwarrior | M12 | 100.1369863 | 99.40074906 | 100.6197195 |
| hook | M10 | 96.00267467 | 94.2755318 | 95.04563295 |
| hook | M12 | 99.90703895 | 100.2116049 | 98.00342514 |
| jumpingjacks | M10 | 110.5423105 | 100 | 91.66309917 |
| jumpingjacks | M12 | 98.75872105 | 98.86649874 | 91.94757847 |

## Разрывы до RESTORE и R0

| scene | state | PSNR_gap_to_RESTORE | SSIM_gap_to_RESTORE | LPIPS_STANDARD_VGG_gap_to_RESTORE | PSNR_gain_vs_R0 | SSIM_gain_vs_R0 | LPIPS_STANDARD_VGG_gain_vs_R0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | M10 | 0.09185791016 | 4.100799561e-05 | 7.445178926e-05 | -2.702209473 | -0.0008664727211 | -0.001270547509 |
| bouncingballs | M12 | 0.01405715942 | 5.066394806e-06 | -4.174187779e-06 | -2.624408722 | -0.0008305311203 | -0.001191921532 |
| hellwarrior | M10 | 0.001686096191 | 3.099441528e-06 | 3.933906555e-06 | -0.4945068359 | -0.001061916351 | -0.001241752878 |
| hellwarrior | M12 | -9.155273438e-05 | 8.940696716e-07 | -3.017485142e-06 | -0.492729187 | -0.001059710979 | -0.001234801486 |
| hook | M10 | 0.009288787842 | 3.093481064e-05 | 1.858174801e-05 | -1.662601471 | -0.002578377724 | -0.001955780201 |
| hook | M12 | 0.0001564025879 | -8.344650269e-07 | 6.95232302e-06 | -1.653469086 | -0.002546608448 | -0.001944150776 |
| jumpingjacks | M10 | -0.009181976318 | 5.960464478e-08 | 5.115754902e-06 | -0.7299919128 | -0.0008302330971 | -0.000563765876 |
| jumpingjacks | M12 | 0.001319885254 | 1.132488251e-06 | 4.923902452e-06 | -0.7404937744 | -0.0008313059807 | -0.0005635740235 |

### Покадрово: PSNR

| scene | state | PSNR_views_improved | PSNR_views_worsened | PSNR_views_equal | PSNR_paired_min | PSNR_paired_max |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | M10 | 20 | 0 | 0 | 0.5554618835 | 1.479427338 |
| bouncingballs | M12 | 20 | 0 | 0 | 0.5341186523 | 1.486064911 |
| hellwarrior | M10 | 17 | 3 | 0 | -0.1098136902 | 0.2986373901 |
| hellwarrior | M12 | 18 | 2 | 0 | -0.08452987671 | 0.3026351929 |
| hook | M10 | 20 | 0 | 0 | 0.01803970337 | 1.005626678 |
| hook | M12 | 20 | 0 | 0 | 0.02627182007 | 1.015556335 |
| jumpingjacks | M10 | 17 | 3 | 0 | -0.03929138184 | 0.3095016479 |
| jumpingjacks | M12 | 16 | 4 | 0 | -0.04777908325 | 0.2858314514 |

### Покадрово: SSIM

| scene | state | SSIM_views_improved | SSIM_views_worsened | SSIM_views_equal | SSIM_paired_min | SSIM_paired_max |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | M10 | 20 | 0 | 0 | 0.0002325773239 | 0.0008982419968 |
| bouncingballs | M12 | 20 | 0 | 0 | 0.0002544522285 | 0.00100260973 |
| hellwarrior | M10 | 19 | 1 | 0 | -0.000111579895 | 0.0004281401634 |
| hellwarrior | M12 | 19 | 1 | 0 | -8.487701416e-05 | 0.000420153141 |
| hook | M10 | 20 | 0 | 0 | 4.255771637e-05 | 0.002515077591 |
| hook | M12 | 20 | 0 | 0 | 5.078315735e-05 | 0.002615332603 |
| jumpingjacks | M10 | 18 | 2 | 0 | -3.361701965e-05 | 0.0002250671387 |
| jumpingjacks | M12 | 17 | 3 | 0 | -4.196166992e-05 | 0.0002224445343 |

### Покадрово: LPIPS_STANDARD_VGG

| scene | state | LPIPS_STANDARD_VGG_views_improved | LPIPS_STANDARD_VGG_views_worsened | LPIPS_STANDARD_VGG_views_equal | LPIPS_STANDARD_VGG_paired_min | LPIPS_STANDARD_VGG_paired_max |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | M10 | 20 | 0 | 0 | 0.0008992291987 | 0.002255439758 |
| bouncingballs | M12 | 20 | 0 | 0 | 0.001111023594 | 0.002303140238 |
| hellwarrior | M10 | 19 | 1 | 0 | -9.370408952e-05 | 0.0005484372377 |
| hellwarrior | M12 | 19 | 1 | 0 | -0.0001560878009 | 0.0005672667176 |
| hook | M10 | 20 | 0 | 0 | 4.427228123e-05 | 0.001742219552 |
| hook | M12 | 20 | 0 | 0 | 2.513499931e-05 | 0.001793283969 |
| jumpingjacks | M10 | 16 | 4 | 0 | -0.0001381617039 | 0.0002459548414 |
| jumpingjacks | M12 | 16 | 4 | 0 | -0.0001250151545 | 0.0002556499094 |

Кадры коррелированы; диапазоны и counts описательны. Никакой независимости кадров или статистической значимости не утверждается. Все160 новых per-view записей и signed deltas к четырём reference states — PER_VIEW_METRICS.csv. Фиксированная галерея ordinal0/10/19 — FIXED_VIEW_COMPARISON.html (внешний артефакт; см. каталог исключённых ссылок).

## Точные Pareto-проверки

| scene | state | PSNR_front | LPIPS_front | all3_front |
| --- | --- | --- | --- | --- |
| bouncingballs | R2 | True | True | True |
| bouncingballs | M10 | True | True | True |
| bouncingballs | M12 | True | True | True |
| bouncingballs | M16 | True | False | True |
| bouncingballs | RESTORE | False | False | True |
| hellwarrior | R2 | True | True | True |
| hellwarrior | M10 | True | True | True |
| hellwarrior | M12 | True | True | True |
| hellwarrior | M16 | False | False | True |
| hellwarrior | RESTORE | False | False | True |
| hook | R2 | True | True | True |
| hook | M10 | True | True | True |
| hook | M12 | True | True | True |
| hook | M16 | True | True | True |
| hook | RESTORE | False | False | True |
| jumpingjacks | R2 | True | True | True |
| jumpingjacks | M10 | True | True | True |
| jumpingjacks | M12 | False | True | True |
| jumpingjacks | M16 | False | True | True |
| jumpingjacks | RESTORE | False | False | True |

Недоминирование проверено отдельно на каждой сцене по bytes/PSNR, bytes/LPIPS и bytes/PSNR/SSIM/LPIPS. Доминирующая точка должна быть не хуже по всем выбранным координатам и строго лучше хотя бы по одной. Нет tolerance или округления для получения нужного победителя. R0 имеет только reference качества, без rate-точки. Графики содержат отдельные точки, без интерполяции, BD-rate или непрерывной RD curve.

## Структура файлов и format delta

| scene | variant | numerical_bytes | selected_member_bytes | other15_member_bytes | metadata_member_bytes | framing_bytes | filesystem_bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | R2 | 12196216 | 183235 | 1893402 | 1182 | 1724 | 2079543 |
| bouncingballs | M16 | 13244792 | 875654 | 1893402 | 1225 | 1724 | 2772005 |
| bouncingballs | RESTORE | 15341944 | 3963583 | 1893402 | 1205 | 1724 | 5859914 |
| bouncingballs | M10 | 13244792 | 375181 | 1893402 | 1223 | 1724 | 2271530 |
| bouncingballs | M12 | 13244792 | 519253 | 1893402 | 1222 | 1724 | 2415601 |
| hellwarrior | R2 | 12196216 | 318526 | 1445005 | 1182 | 1724 | 1766437 |
| hellwarrior | M16 | 13244792 | 1574095 | 1445005 | 1217 | 1724 | 3022041 |
| hellwarrior | RESTORE | 15341944 | 3922437 | 1445005 | 1199 | 1724 | 5370365 |
| hellwarrior | M10 | 13244792 | 683709 | 1445005 | 1217 | 1724 | 2131655 |
| hellwarrior | M12 | 13244792 | 1013580 | 1445005 | 1219 | 1724 | 2461528 |
| hook | R2 | 12196216 | 232328 | 1253471 | 1185 | 1724 | 1488708 |
| hook | M16 | 13244792 | 1206514 | 1253471 | 1227 | 1724 | 2462936 |
| hook | RESTORE | 15341944 | 3973479 | 1253471 | 1209 | 1724 | 5229883 |
| hook | M10 | 13244792 | 513518 | 1253471 | 1228 | 1724 | 1769941 |
| hook | M12 | 13244792 | 760608 | 1253471 | 1227 | 1724 | 2017030 |
| jumpingjacks | R2 | 12196216 | 58584 | 1856037 | 1181 | 1724 | 1917526 |
| jumpingjacks | M16 | 12606974 | 380029 | 1856037 | 1219 | 1724 | 2239009 |
| jumpingjacks | RESTORE | 13428490 | 1546145 | 1856037 | 1202 | 1724 | 3405108 |
| jumpingjacks | M10 | 12606974 | 133020 | 1856037 | 1220 | 1724 | 1992001 |
| jumpingjacks | M12 | 12606974 | 205331 | 1856037 | 1221 | 1724 | 2064313 |

Numerical payload не является compressed rate. Compressed NPY member содержит header и данные; после сжатия они не разделяются произвольно. FILE_SIZES.csv и MEMBER_BUDGETS.csv содержат RAW, DEFLATE, несжатые размеры NPY, local/central ZIP headers и end records. Сумма непересекающихся физических секций точно равна filesystem bytes для всех40 файлов.

| scene | variant | old_file_bytes | new_file_bytes | metadata_delta | framing_delta |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | R2 | 2079533 | 2079543 | 10 | 0 |
| bouncingballs | M16 | 2771990 | 2772005 | 15 | 0 |
| bouncingballs | RESTORE | 5859896 | 5859914 | 18 | 0 |
| hellwarrior | R2 | 1766427 | 1766437 | 10 | 0 |
| hellwarrior | M16 | 3022026 | 3022041 | 15 | 0 |
| hellwarrior | RESTORE | 5370348 | 5370365 | 17 | 0 |
| hook | R2 | 1488696 | 1488708 | 12 | 0 |
| hook | M16 | 2462919 | 2462936 | 17 | 0 |
| hook | RESTORE | 5229863 | 5229883 | 20 | 0 |
| jumpingjacks | R2 | 1917515 | 1917526 | 11 | 0 |
| jumpingjacks | M16 | 2238995 | 2239009 | 14 | 0 |
| jumpingjacks | RESTORE | 3405090 | 3405108 | 18 | 0 |

Переход v1→v2 изменяет только metadata; все16 NPY/compressed level bytes контролей совпадают. Это изменение формата не является эффектом precision. Контроли не перезаписаны. Варианты сравниваются только в новом общем v2; неизменные15 members совпадают побитно.

| scene | variant | selected_member_delta_vs_M16 | metadata_delta_vs_M16 | framing_delta_vs_M16 | file_delta_vs_M16 |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | M10 | -500473 | -2 | 0 | -500475 |
| bouncingballs | M12 | -356401 | -3 | 0 | -356404 |
| hellwarrior | M10 | -890386 | 0 | 0 | -890386 |
| hellwarrior | M12 | -560515 | 2 | 0 | -560513 |
| hook | M10 | -692996 | 1 | 0 | -692995 |
| hook | M12 | -445906 | 0 | 0 | -445906 |
| jumpingjacks | M10 | -247009 | 1 | 0 | -247008 |
| jumpingjacks | M12 | -174698 | 2 | 0 | -174696 |

## Ошибка признаков

| scene | bits | MAE | RMSE | max_absolute_error | code0 | codeQmax |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 8 | 0.01305348555 | 0.01395191435 | 0.01676233113 | 0 | 0 |
| bouncingballs | 10 | 0.0009042770962 | 0.001546444524 | 0.004178276286 | 0 | 0 |
| bouncingballs | 12 | 0.0002465296382 | 0.0003894485664 | 0.00104381144 | 0 | 0 |
| bouncingballs | 16 | 2.94895155e-05 | 3.478488032e-05 | 6.522274222e-05 | 0 | 0 |
| hellwarrior | 8 | 0.01073699245 | 0.01244060799 | 0.02193327248 | 0 | 0 |
| hellwarrior | 10 | 0.00281571351 | 0.003242877855 | 0.005467235111 | 0 | 0 |
| hellwarrior | 12 | 0.0006633331348 | 0.0007760230165 | 0.001365803648 | 0 | 0 |
| hellwarrior | 16 | 4.279575174e-05 | 4.938981925e-05 | 8.534640074e-05 | 0 | 0 |
| hook | 8 | 0.01325229017 | 0.01458490275 | 0.02495358698 | 0 | 0 |
| hook | 10 | 0.003586771513 | 0.00395471726 | 0.006220079958 | 0 | 0 |
| hook | 12 | 0.0006043735516 | 0.0007564761824 | 0.001553889364 | 0 | 0 |
| hook | 16 | 4.882281642e-05 | 5.632232343e-05 | 9.709596634e-05 | 0 | 0 |
| jumpingjacks | 8 | 0.01390189352 | 0.01486067845 | 0.0205001838 | 0 | 0 |
| jumpingjacks | 10 | 0.001954668378 | 0.002322716294 | 0.005110011669 | 0 | 0 |
| jumpingjacks | 12 | 0.0004020871846 | 0.0005483844342 | 0.001276565716 | 0 | 0 |
| jumpingjacks | 16 | 3.71563637e-05 | 4.397615737e-05 | 7.976777852e-05 | 0 | 0 |

Это диагностика параметров, а не замена image metrics.

## Научная интерпретация

**bouncingballs:** frontier PSNR: R2, M10, M12, M16; frontier STANDARD LPIPS: R2, M10, M12; по всем трём mean metrics: R2, M10, M12, M16, RESTORE.

M10: экономия против M16 +500,475 B; цена относительно R2 +191,987 B; PSNR gain +0.957046509 dB, gap к M16 +0.092060089 dB. PSNR ухудшился на 0/20 views, STANDARD LPIPS — на 0/20; среднее не скрывает эти случаи.

M12: экономия против M16 +356,404 B; цена относительно R2 +336,058 B; PSNR gain +1.034847260 dB, gap к M16 +0.014259338 dB. PSNR ухудшился на 0/20 views, STANDARD LPIPS — на 0/20; среднее не скрывает эти случаи.

**hellwarrior:** frontier PSNR: R2, M10, M12; frontier STANDARD LPIPS: R2, M10, M12; по всем трём mean metrics: R2, M10, M12, M16, RESTORE.

M10: экономия против M16 +890,386 B; цена относительно R2 +365,218 B; PSNR gain +0.076301575 dB, gap к M16 +0.001670837 dB. PSNR ухудшился на 3/20 views, STANDARD LPIPS — на 1/20; среднее не скрывает эти случаи.

M12: экономия против M16 +560,513 B; цена относительно R2 +695,091 B; PSNR gain +0.078079224 dB, gap к M16 -0.000106812 dB. PSNR ухудшился на 2/20 views, STANDARD LPIPS — на 1/20; среднее не скрывает эти случаи.

**hook:** frontier PSNR: R2, M10, M12, M16; frontier STANDARD LPIPS: R2, M10, M12, M16; по всем трём mean metrics: R2, M10, M12, M16, RESTORE.

M10: экономия против M16 +692,995 B; цена относительно R2 +281,233 B; PSNR gain +0.224552155 dB, gap к M16 +0.009349823 dB. PSNR ухудшился на 0/20 views, STANDARD LPIPS — на 0/20; среднее не скрывает эти случаи.

M12: экономия против M16 +445,906 B; цена относительно R2 +528,322 B; PSNR gain +0.233684540 dB, gap к M16 +0.000217438 dB. PSNR ухудшился на 0/20 views, STANDARD LPIPS — на 0/20; среднее не скрывает эти случаи.

**jumpingjacks:** frontier PSNR: R2, M10; frontier STANDARD LPIPS: R2, M10, M12, M16; по всем трём mean metrics: R2, M10, M12, M16, RESTORE.

M10: экономия против M16 +247,008 B; цена относительно R2 +74,475 B; PSNR gain +0.098518372 dB, gap к M16 -0.009395599 dB. PSNR ухудшился на 3/20 views, STANDARD LPIPS — на 4/20; среднее не скрывает эти случаи.

M12: экономия против M16 +174,696 B; цена относительно R2 +146,787 B; PSNR gain +0.088016510 dB, gap к M16 +0.001106262 dB. PSNR ухудшился на 4/20 views, STANDARD LPIPS — на 4/20; среднее не скрывает эти случаи.

Из8 промежуточных точек недоминируемы 7 по PSNR, 8 по STANDARD LPIPS и 8 при совместной оценке трёх mean metrics. Наличие измеренных промежуточных недоминируемых точек даёт основание отдельно исследовать bounded precision selection, но не доказывает пригодность конкретной policy. Различия между сценами и между PSNR/LPIPS/frontier по всем метрикам показывают, почему универсальный победитель не назначается. Без допустимой потери качества и storage budget экономическая оптимальность не определена. Малые signed differences сохранены; одинаковое качество не объявляется постфактум.

Следующий единственный рекомендуемый опыт: заранее зафиксировать budget/допуск качества и отдельный calibration/validation split, затем проверить выбор только среди уже заданных R2/M10/M12/M16 на независимом checkpoint. Текущие test metrics не использовать для fitting policy. Никакая policy в этой сессии не реализована. Не исследованы другие уровни/битности/квантизаторы/компрессоры, перенос на другие checkpoints и сочетания повышенных уровней. Результаты ограничены стандартным NPY/DEFLATE6 transport.

## Проверки, ресурсы и воспроизведение

Synthetic scalar reference, p8/p16 frozen regressions и p12 прежняя ветка,23 container tests,40 fresh-process decodes,40 byte-identical rebuilds, exact canonical metadata/codes/full xyz,8 exact smoke PNG/float RGB,160 новых кадров и immutable weights/cameras/time/GT — PASS. Read audit является Python access check этой реализации, не OS security sandbox. Final source/old-artifact SHA256 count/status — FINAL_VALIDATION.json.

| scene | state | quantization_seconds | render_process_seconds | render_kernel_seconds | metric_seconds | render_allocated_MiB | render_reserved_MiB | metric_allocated_MiB | metric_reserved_MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | M10 | 0.002572055 | 16.55115794 | 1.043365992 | 5.215693969 | 962.8779297 | 1244 | 1600.256836 | 1644 |
| bouncingballs | M12 | 0.003804788 | 16.96056186 | 1.52386252 | 4.692891585 | 962.8779297 | 1244 | 1600.256836 | 1644 |
| hellwarrior | M10 | 0.002615966 | 13.21804914 | 1.283085644 | 5.440393819 | 402.6503906 | 448 | 1600.256836 | 1644 |
| hellwarrior | M12 | 0.003656 | 12.96767501 | 0.546716189 | 4.715402906 | 402.6503906 | 448 | 1600.256836 | 1644 |
| hook | M10 | 0.002846836 | 13.83269993 | 1.25071657 | 4.933165193 | 1049.227539 | 1406 | 1600.256836 | 1644 |
| hook | M12 | 0.004018216 | 13.89740283 | 1.149620458 | 4.729620347 | 1049.227539 | 1406 | 1600.256836 | 1644 |
| jumpingjacks | M10 | 0.000877883 | 15.55398846 | 0.82928751 | 4.878449854 | 757.3789062 | 938 | 1600.256836 | 1644 |
| jumpingjacks | M12 | 0.001205212 | 16.12325421 | 0.945479637 | 4.737084328 | 757.3789062 | 938 | 1600.256836 | 1644 |

Guarded CPU/render/metric wall total 565.701 s; maximum sampled process-tree RSS 3.770 GiB. Guard не сработал. RSS sum может повторно учитывать shared pages; sampling0.5s. GPU использован только rendering/metrics. Hash audit, setup и отчёты учитываются отдельно. Serialization/rebuild/decode timing по каждому файлу — FILE_SIZES.csv; cold process включает import/output, internal decode исключает startup.

Запуск в новом уникальном каталоге (скопировать только top-level scripts, не результаты): Windows Python `.tools/phase2-plotting-env/Scripts/python.exe prepare.py`, затем `amend_protocol_count.py` (архивирует наследованную описку24→40 до setup); WSL `bash launch.sh setup`, `pilot`, `remaining`; WSL `bash final_runtime.sh`; Windows Python `report.py`, после проверки отчёта/графиков — `finalize.py`. Абсолютные пути задаются через каталог нового run. WSL использует прежний audit-env и pinned NumPy1.26.4/Python3.10.21/Torch2.7.0+cu128; версии/source hashes в RUNTIME.json и snapshot. Старые файлы не меняются; exclusive writes и CONTINUATION_SCENES фиксируют точки продолжения. При scientific exactness failure — BLOCKED_NEEDS_ULTRA, без изменения definitions. Новые эксперименты автоматически не запускаются.
