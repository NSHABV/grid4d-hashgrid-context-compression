> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Выбранный уровень uint16: качество и несжатый объём

Выполнены четыре M16 ×20 views =80 новых кадров; восемь smoke controls ordinal0. R0/R2/RESTORE переиспользованы после проверки provenance и точного повторения smoke PNG/float RGB. Ни training, ни новый compressed format, ни H4/H5 не запускались. Уровни zero-based, выбраны до этого эксперимента по прежним test PSNR; это exploratory follow-up, не независимая политика точности.

## 1. Четыре состояния и качество

| scene | level | state | PSNR | SSIM | LPIPS_LEGACY | LPIPS_STANDARD_VGG |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 5 | R0 | 42.492240906 | 0.995813727 | 0.007435153 | 0.017818049 |
| bouncingballs | 5 | R2 | 38.832984924 | 0.994528949 | 0.009729510 | 0.020600772 |
| bouncingballs | 5 | RESTORE | 39.881889343 | 0.994988263 | 0.008386532 | 0.019014144 |
| bouncingballs | 5 | M16 | 39.882091522 | 0.994988561 | 0.008386469 | 0.019015042 |
| hellwarrior | 8 | R0 | 42.840995789 | 0.990779281 | 0.015664417 | 0.022806788 |
| hellwarrior | 8 | R2 | 42.270187378 | 0.989561379 | 0.016923258 | 0.024397846 |
| hellwarrior | 8 | RESTORE | 42.348175049 | 0.989720464 | 0.016682576 | 0.024044607 |
| hellwarrior | 8 | M16 | 42.348159790 | 0.989720523 | 0.016681340 | 0.024043784 |
| hook | 6 | R0 | 39.024078369 | 0.990584195 | 0.008997337 | 0.011900998 |
| hook | 6 | R2 | 37.136924744 | 0.987501264 | 0.011111248 | 0.014230478 |
| hook | 6 | RESTORE | 37.370765686 | 0.988036752 | 0.010709595 | 0.013838196 |
| hook | 6 | M16 | 37.370826721 | 0.988036454 | 0.010709430 | 0.013837298 |
| jumpingjacks | 4 | R0 | 39.245857239 | 0.992448986 | 0.007618422 | 0.010650467 |
| jumpingjacks | 4 | R2 | 38.417346954 | 0.991524100 | 0.008220712 | 0.011276050 |
| jumpingjacks | 4 | RESTORE | 38.506683350 | 0.991618812 | 0.008161660 | 0.011209117 |
| jumpingjacks | 4 | M16 | 38.506469727 | 0.991618752 | 0.008162817 | 0.011208611 |

R0: исходный FP32; R2: прежний uint8 на всех xyz; RESTORE: выбранный уровень исходный FP32, остальные uint8; M16: выбранный уровень canonical uint16→FP32, остальные frozen uint8→FP32. Renderer FP32 во всех состояниях. LPIPS_LEGACY и LPIPS_STANDARD_VGG имеют разные протоколы и не смешиваются.

### Подписанные разницы M16

| scene | PSNR_gain16 | PSNR_gap_to_restore | PSNR_difference_vs_R0 | SSIM_gain16 | SSIM_gap_to_restore | LPIPS_LEGACY_gain16 | LPIPS_LEGACY_gap_to_restore | LPIPS_STANDARD_VGG_gain16 | LPIPS_STANDARD_VGG_gap_to_restore |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 1.049106598 | -0.000202179 | -2.610149384 | 0.000459611 | -0.000000298 | 0.001343042 | -0.000000063 | 0.001585729 | 0.000000898 |
| hellwarrior | 0.077972412 | 0.000015259 | -0.492835999 | 0.000159144 | -0.000000060 | 0.000241918 | -0.000001237 | 0.000354063 | -0.000000823 |
| hook | 0.233901978 | -0.000061035 | -1.653251648 | 0.000535190 | 0.000000298 | 0.000401818 | -0.000000165 | 0.000393179 | -0.000000898 |
| jumpingjacks | 0.089122772 | 0.000213623 | -0.739387512 | 0.000094652 | 0.000000060 | 0.000057895 | 0.000001157 | 0.000067440 | -0.000000507 |

Gain PSNR/SSIM = M16−R2; improvement LPIPS = R2−M16. Gap к RESTORE: RESTORE−M16 для PSNR/SSIM и M16−RESTORE для LPIPS. Отрицательные значения сохранены. Разница к R0 в RESULTS.csv — M16−R0 для каждой метрики; для LPIPS положительная разница означает ухудшение. RESTORE не считается доказанным верхним пределом image quality. Порог «почти FP32» не вводился.

## 2. Числовой payload выбранного уровня

| scene | level | selected_scalars | uint8_bytes | uint16_bytes | FP32_bytes | M16_extra_vs_R2 | M16_saving_vs_RESTORE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 5 | 1048576 | 1048576 | 2097152 | 4194304 | 1048576 | 2097152 |
| hellwarrior | 8 | 1048576 | 1048576 | 2097152 | 4194304 | 1048576 | 2097152 |
| hook | 6 | 1048576 | 1048576 | 2097152 | 4194304 | 1048576 | 2097152 |
| jumpingjacks | 4 | 410758 | 410758 | 821516 | 1643032 | 410758 | 821516 |

### Полный xyz numerical payload и физические research artifacts

| scene | full_xyz_R0_payload | full_xyz_R2_payload | full_xyz_RESTORE_payload | full_xyz_M16_payload | q16_npy_physical_bytes | quantizer_json_physical_bytes |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 48784864 | 12196216 | 15341944 | 13244792 | 2097280 | 690 |
| hellwarrior | 48784864 | 12196216 | 15341944 | 13244792 | 2097280 | 690 |
| hook | 48784864 | 12196216 | 15341944 | 13244792 | 2097280 | 689 |
| jumpingjacks | 48784864 | 12196216 | 13428490 | 12606974 | 821644 | 688 |

Все размеры в байтах. В full_xyz_M16 только один выбранный уровень имеет 2 bytes/scalar, остальные —1 byte/scalar. Это расчёт числового payload, не физический mixed-format файл. .npy/JSON overhead показан отдельно. Renderer VRAM не уменьшена: все embeddings на GPU FP32. Не вычитаются байты из ZLIB8, новый compression ratio не заявляется.

## Ошибка признаков

| scene | level | precision | MAE | RMSE | max_absolute_error | extreme_code_0_count | extreme_code_max_count | nbytes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 5 | uint8 | 0.013053486 | 0.013951914 | 0.016762331 | 0 | 0 | 1048576 |
| bouncingballs | 5 | uint16 | 0.000029490 | 0.000034785 | 0.000065223 | 0 | 0 | 2097152 |
| hellwarrior | 8 | uint8 | 0.010736992 | 0.012440608 | 0.021933272 | 0 | 0 | 1048576 |
| hellwarrior | 8 | uint16 | 0.000042796 | 0.000049390 | 0.000085346 | 0 | 0 | 2097152 |
| hook | 6 | uint8 | 0.013252290 | 0.014584903 | 0.024953587 | 0 | 0 | 1048576 |
| hook | 6 | uint16 | 0.000048823 | 0.000056322 | 0.000097096 | 0 | 0 | 2097152 |
| jumpingjacks | 4 | uint8 | 0.013901894 | 0.014860678 | 0.020500184 | 0 | 0 | 410758 |
| jumpingjacks | 4 | uint16 | 0.000037156 | 0.000043976 | 0.000079768 | 0 | 0 | 821516 |

Ошибка параметров не заменяет image-space метрики.

## Покадровые эффекты

### PSNR

| scene | PSNR_views_improved | PSNR_views_worsened | PSNR_views_equal | PSNR_paired_gain_min | PSNR_paired_gain_max | PSNR_paired_gap_min | PSNR_paired_gap_max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 20 | 0 | 0 | 0.554492950 | 1.519077301 | -0.002235413 | 0.001251221 |
| hellwarrior | 18 | 2 | 0 | -0.086597443 | 0.303287506 | -0.000480652 | 0.000606537 |
| hook | 20 | 0 | 0 | 0.026062012 | 1.024326324 | -0.001060486 | 0.000434875 |
| jumpingjacks | 16 | 4 | 0 | -0.057018280 | 0.298267365 | -0.000881195 | 0.001270294 |

### SSIM

| scene | SSIM_views_improved | SSIM_views_worsened | SSIM_views_equal | SSIM_paired_gain_min | SSIM_paired_gain_max | SSIM_paired_gap_min | SSIM_paired_gap_max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 20 | 0 | 0 | 0.000272512 | 0.001002550 | -0.000001073 | 0.000000596 |
| hellwarrior | 19 | 1 | 0 | -0.000090480 | 0.000421941 | -0.000001311 | 0.000000834 |
| hook | 20 | 0 | 0 | 0.000052154 | 0.002623320 | -0.000000656 | 0.000004649 |
| jumpingjacks | 17 | 3 | 0 | -0.000041425 | 0.000230491 | -0.000000715 | 0.000000834 |

### LPIPS_LEGACY

| scene | LPIPS_LEGACY_views_improved | LPIPS_LEGACY_views_worsened | LPIPS_LEGACY_views_equal | LPIPS_LEGACY_paired_gain_min | LPIPS_LEGACY_paired_gain_max | LPIPS_LEGACY_paired_gap_min | LPIPS_LEGACY_paired_gap_max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 20 | 0 | 0 | 0.000854974 | 0.002420135 | -0.000002977 | 0.000004543 |
| hellwarrior | 20 | 0 | 0 | 0.000036225 | 0.000481270 | -0.000006827 | 0.000002296 |
| hook | 20 | 0 | 0 | 0.000012347 | 0.002042457 | -0.000010218 | 0.000006959 |
| jumpingjacks | 17 | 3 | 0 | -0.000058698 | 0.000154373 | -0.000004293 | 0.000007798 |

### LPIPS_STANDARD_VGG

| scene | LPIPS_STANDARD_VGG_views_improved | LPIPS_STANDARD_VGG_views_worsened | LPIPS_STANDARD_VGG_views_equal | LPIPS_STANDARD_VGG_paired_gain_min | LPIPS_STANDARD_VGG_paired_gain_max | LPIPS_STANDARD_VGG_paired_gap_min | LPIPS_STANDARD_VGG_paired_gap_max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 20 | 0 | 0 | 0.001104295 | 0.002341714 | -0.000006787 | 0.000011701 |
| hellwarrior | 19 | 1 | 0 | -0.000115307 | 0.000575013 | -0.000009116 | 0.000005830 |
| hook | 20 | 0 | 0 | 0.000027810 | 0.001862288 | -0.000015372 | 0.000013262 |
| jumpingjacks | 15 | 5 | 0 | -0.000122434 | 0.000258284 | -0.000006754 | 0.000009184 |

Кадры коррелированы; counts/ranges описательны. Независимость или статистическая значимость не утверждается.

## Научный вывод

**bouncingballs, L5.** Средние PSNR/SSIM и оба LPIPS улучшились относительно R2. PSNR gain +1.049106598 dB, gap RESTORE−M16 -0.000202179 dB. SSIM gain +0.000459611416, gap -2.98023224e-07. LPIPS_LEGACY improvement +0.00134304166, gap M16−RESTORE -6.33299351e-08; STANDARD improvement +0.00158572942, gap +8.97794962e-07. Относительно R2 ухудшились 0/20 кадров по PSNR, 0/20 по SSIM, 0/20 по LEGACY и 0/20 по STANDARD. Ошибка признаков уменьшилась: MAE в 442.65, RMSE в 401.09, max absolute error в 257.00 раза. Крайних кодов 0/max в выбранном slice нет при обеих битностях. Дополнительный числовой payload против R2 — 1,048,576 B; снижение против RESTORE — 2,097,152 B. M16 остаётся ниже R0 по среднему PSNR на 2.610149 dB. Есть основание отдельно измерить фактический размер смешанного хранения; экономическая эффективность пока не проверена.

**hellwarrior, L8.** Средние PSNR/SSIM и оба LPIPS улучшились относительно R2. PSNR gain +0.077972412 dB, gap RESTORE−M16 +0.000015259 dB. SSIM gain +0.000159144402, gap -5.96046448e-08. LPIPS_LEGACY improvement +0.000241918489, gap M16−RESTORE -1.23679638e-06; STANDARD improvement +0.000354062766, gap -8.23289156e-07. Относительно R2 ухудшились 2/20 кадров по PSNR, 1/20 по SSIM, 0/20 по LEGACY и 1/20 по STANDARD. Ошибка признаков уменьшилась: MAE в 250.89, RMSE в 251.89, max absolute error в 256.99 раза. Крайних кодов 0/max в выбранном slice нет при обеих битностях. Дополнительный числовой payload против R2 — 1,048,576 B; снижение против RESTORE — 2,097,152 B. M16 остаётся ниже R0 по среднему PSNR на 0.492836 dB. Есть основание отдельно измерить фактический размер смешанного хранения; экономическая эффективность пока не проверена.

**hook, L6.** Средние PSNR/SSIM и оба LPIPS улучшились относительно R2. PSNR gain +0.233901978 dB, gap RESTORE−M16 -0.000061035 dB. SSIM gain +0.000535190105, gap +2.98023224e-07. LPIPS_LEGACY improvement +0.000401818193, gap M16−RESTORE -1.64844096e-07; STANDARD improvement +0.000393179245, gap -8.97794962e-07. Относительно R2 ухудшились 0/20 кадров по PSNR, 0/20 по SSIM, 0/20 по LEGACY и 0/20 по STANDARD. Ошибка признаков уменьшилась: MAE в 271.44, RMSE в 258.95, max absolute error в 257.00 раза. Крайних кодов 0/max в выбранном slice нет при обеих битностях. Дополнительный числовой payload против R2 — 1,048,576 B; снижение против RESTORE — 2,097,152 B. M16 остаётся ниже R0 по среднему PSNR на 1.653252 dB. Есть основание отдельно измерить фактический размер смешанного хранения; экономическая эффективность пока не проверена.

**jumpingjacks, L4.** Средние PSNR/SSIM и оба LPIPS улучшились относительно R2. PSNR gain +0.089122772 dB, gap RESTORE−M16 +0.000213623 dB. SSIM gain +9.46521759e-05, gap +5.96046448e-08. LPIPS_LEGACY improvement +5.78947365e-05, gap M16−RESTORE +1.15670264e-06; STANDARD improvement +6.74398616e-05, gap -5.06639481e-07. Относительно R2 ухудшились 4/20 кадров по PSNR, 3/20 по SSIM, 3/20 по LEGACY и 5/20 по STANDARD. Ошибка признаков уменьшилась: MAE в 374.15, RMSE в 337.93, max absolute error в 257.00 раза. Крайних кодов 0/max в выбранном slice нет при обеих битностях. Дополнительный числовой payload против R2 — 410,758 B; снижение против RESTORE — 821,516 B. M16 остаётся ниже R0 по среднему PSNR на 0.739388 dB. Есть основание отдельно измерить фактический размер смешанного хранения; экономическая эффективность пока не проверена.

Измеренные подписанные разрывы до RESTORE малы по сравнению с gain относительно R2, но порог «почти FP32» не вводится. Знак некоторых разрывов отрицателен: RESTORE не является доказанным верхним пределом image quality. Восстановление одного уровня не возвращает исходное качество всей сцены; остаточные разницы по всем метрикам приведены в RESULTS.csv. Уровни выбраны на прежних test PSNR, поэтому это exploratory follow-up, а не независимое подтверждение политики precision selection. Не проверены compressed rate, mixed-format framing/metadata, entropy coding uint16, перенос выбора уровней на другие checkpoints/views, выгодность rate–distortion и взаимодействия нескольких повышенных уровней. Простое повышение разрядности не заявляется как научная новизна.

## Следующий отдельный эксперимент

Отдельным заранее фиксированным экспериментом измерить реальный физический размер смешанного хранения для этих же четырёх состояний M16 и сравнимых R2/RESTORE, включая metadata/framing, с независимым точным восстановлением codes. Не менять уровни/quantizer после просмотра размеров и не переиспользовать uint8 coder как 65536-символьный без отдельной проверки. Нынешние результаты обосновывают такое измерение качества и размера, но не обещают выигрыш компрессора. В этой сессии mixed-format файл не создаётся.

## Ресурсы

| scene | scene_wall_seconds | process_tree_RSS_MiB | RAM_min_available_GiB | GPU_free_before_MiB | GPU_free_after_MiB | M16_render_mean_ms | M16_render_allocated_MiB | M16_render_reserved_MiB | metric_allocated_MiB | metric_reserved_MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 114.054734273 | 3234.183593750 | 3.890174866 | 6597 | 6583 | 67.704913900 | 962.877929688 | 1244.000000000 | 1600.256835938 | 1644.000000000 |
| hellwarrior | 96.466109023 | 2363.828125000 | 4.696411133 | 6627 | 6627 | 23.641544200 | 402.650390625 | 448.000000000 | 1600.256835938 | 1644.000000000 |
| hook | 97.955903613 | 2364.410156250 | 4.726783752 | 6627 | 6627 | 53.478260150 | 1049.227539062 | 1406.000000000 | 1600.256835938 | 1644.000000000 |
| jumpingjacks | 108.518676037 | 3873.718750000 | 3.238761902 | 6627 | 6732 | 47.397833150 | 757.378906250 | 938.000000000 | 1600.256835938 | 1644.000000000 |

Сумма четырёх scene process wall: 416.995 s (6.950 min); включает preparation, controls, M16 и metrics, исключает setup/audit/protocol hashing, отчёты и паузы. RSS измерен по process tree каждые0.5s (shared pages могут учитываться повторно). VRAM peaks — PyTorch allocated/reserved отдельно для renderer и metric process; свободная VRAM также измерялась. Guard не сработал.

## Correctness и воспроизведение

Synthetic tests, четыре independent decoders, четыре полных uint8 regression, exact slices/untouched parameters, восемь smoke PNG и float RGB, camera/time/GT, legacy numeric parity и standard explicit-transform parity прошли. Source preservation и полная опись новых файлов — FINAL_VALIDATION.json. Технический PASS не зависит от положительного gain.

Окружение: существующий WSL audit-env, Python3.10.21/PyTorch2.7.0+cu128/CUDA12.8/NumPy1.26.4, lpips0.1.4; точные версии и source/weight hashes — METRIC_PROTOCOL_AUDIT.json. Старое SciPy/NumPy предупреждение сохранено в логах, окружение не обновлялось.

Для повторения скопировать только top-level *.py и *.sh в новый уникальный каталог под research. Не запускать prepare/runner поверх завершённого run. PowerShell из <PROJECT_ROOT>:

```powershell
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/prepare.py
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/<NEW_RUN>/launch.sh setup
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/<NEW_RUN>/launch.sh pilot
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/<NEW_RUN>/launch.sh remaining
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/aggregate.py
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/<NEW_RUN>/final_runtime.sh
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/interpret_and_gallery.py
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/write_reports.py
```

INTERPRETATION.json формируется из измерений этого запуска. При независимом повторении проверить, что текст соответствует новым числам, затем проверить отчёты и запустить finalize.py тем же Windows Python. prepare.py фиксирует скопированные исходники; после этого их не менять. Независимый decoder: под тем же WSL окружением python -B decode16.py q16.npy quantizer.json NEW_OUTPUT_DIR. Все writes exclusive; частичный scene directory требует диагностики. CONTINUATION_SCENES_*.json фиксируют успешные сцены.

M16 renders: <scene>/M16/model/test/ours_50000/renders/00000.png,00010.png,00019.png — заранее выбранные ordinal для просмотра. Все80 renders и все per-view результаты сохранены. Baseline пути перечислены в PREREGISTERED_PROTOCOL.json. Никаких новых datasets, битностей или комбинаций не исследовалось.

Наглядное сравнение GT/R0/R2/RESTORE/M16 для всех четырёх сцен и фиксированных ordinal 0,10,19: FIXED_VIEW_COMPARISON.html (внешний артефакт; см. каталог исключённых ссылок). Галерея использует исходные полные PNG без нового рендеринга, кропа или усиления различий. Ссылки указывают на сохранённые локальные артефакты проекта.

