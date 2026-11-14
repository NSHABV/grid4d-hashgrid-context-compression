> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Grid4D full spatial audit and quantization quality

Measured physical sizes:
| scene | xyz_parameters | xyz_bytes | RAW8_B | ZLIB8_B | FP32_to_RAW8_x | FP32_to_ZLIB8_x | RAW8_to_ZLIB8_x |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 12196216 | 48784864 | 12202580 | 2079708 | 3.997914 | 23.457555 | 5.867449 |
| hellwarrior | 12196216 | 48784864 | 12202579 | 1766604 | 3.997914 | 27.615054 | 6.907365 |
| hook | 12196216 | 48784864 | 12202579 | 1488870 | 3.997914 | 32.766369 | 8.195866 |
| jumpingjacks | 12196216 | 48784864 | 12202579 | 1917692 | 3.997914 | 25.439364 | 6.363159 |

Spatial share (% of learned parameter bytes):
| scene | xyz_share_deformation | xyz_share_full_scene | full_scene_parameters | other_parameter_bytes | model_only_checkpoint_bytes |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | 92.221278 | 50.390318 | 24203491 | 48029100 | 96836836 |
| hellwarrior | 92.221278 | 76.500202 | 15942724 | 14986032 | 63796580 |
| hook | 92.221278 | 47.857168 | 25484617 | 53153604 | 101960868 |
| jumpingjacks | 92.221278 | 57.602963 | 21172897 | 35906724 | 84715876 |

Quality under one fixed pipeline:
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

Historical H4 scale (not full-grid coding):
| scene | historical_H4_gain_B | C1_pair_B | gain_pct_C1_pair | gain_pct_RAW8 | gain_pct_ZLIB8 | gain_pct_FP32 | gain_pct_model_only |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 3011 | 228833 | 1.315807 | 0.024675 | 0.144780 | 0.006172 | 0.003109 |
| hellwarrior | 2940 | 155631 | 1.889084 | 0.024093 | 0.166421 | 0.006026 | 0.004608 |
| hook | 2922 | 151908 | 1.923533 | 0.023946 | 0.196256 | 0.005990 | 0.002866 |
| jumpingjacks | 3329 | 171990 | 1.935578 | 0.027281 | 0.173594 | 0.006824 | 0.003930 |

Most expensive ZLIB levels:
bouncingballs: L7=358565 B, L8=340017 B, L6=291182 B, L9=226799 B
hellwarrior: L8=318526 B, L7=307918 B, L9=305361 B, L6=244626 B
hook: L8=286954 B, L7=284966 B, L9=247902 B, L6=232328 B
jumpingjacks: L8=312994 B, L7=306028 B, L9=289234 B, L6=249724 B

Зафиксировать отдельный эксперимент по чувствительности качества к квантованию L6–L10: по одному уровню за раз, прежний общий table8 quantizer и те же test views, без обучения. Сначала локализовать вклад этих наиболее дорогих после ZLIB уровней в distortion; затем решать, имеет ли смысл новый полный codec. Не выбирать новые thresholds по текущим test metrics.

Checks: eight independent RAW8/ZLIB8 decodes; all allocated levels/symbols; exact canonical dequantization; same20 views/time/GT across variants; unchanged temporal/MLP/Gaussian parameters;12 complete metric sets; independent CPU PSNR. Final source/past artifact SHA audit is recorded in FINAL_VALIDATION.json.

Measured: NPZ filesystem sizes, rendering metrics and resources. Theoretical: nominal vertex load, parameter tensor bytes from shape×dtype, empirical Shannon summaries. Unmeasured: full-spatial H4 codec and compression ratio. No claim of novelty or whole-Grid4D lossless compression.

Reproduction commands: prepare.py (Windows; fresh unique directory), audit_cpu.py SCENE (WSL pinned NumPy1.26.4), decode_npz.py ARTIFACT OUTPUT, evaluate_variant.py SCENE R0/R1/R2, report.py, finalize.py. env: source research/env_common.sh with audit-env prefix. Source snapshots and manifests retained. path_fix_001 preserves initial protocol and documents Windows/WSL path-only correction; scientific settings unchanged.



## Интерпретация измерений

Table-wise8 здесь означает один диапазон для всего xyz-тензора. Размер ZLIB8 является результатом lossy quantization и затем lossless DEFLATE. Он не означает lossless-восстановление исходных FP32 весов или всей сцены.
Во всех четырёх сценах R2 хуже R0 и R1 по всем трём метрикам. Дополнительная потеря PSNR от R1 к R2 составляет соответственно 1.0071, 0.4783, 1.3738 и 0.5845 dB (bouncingballs, hellwarrior, hook, jumpingjacks). Порог допустимой потери качества заранее не задан, поэтому решение о приемлемости этих потерь не объявляется.
Затраты на RAW8 metadata/framing составляют 6363–6364 B. Общий quantizer хранится один раз. В каждом артефакте присутствуют все allocated slots; ни малое число symbols, ни низкая энтропия не доказывают, что веса можно удалить.

| Scene | L6–L10 / physical ZLIB8 | Largest JS divergence vs L5 | Largest JS divergence vs L6 |
|---|---:|---|---|
| bouncingballs | 68.164% | L12: 0.682059 bits | L12: 0.553515 bits |
| hellwarrior | 80.303% | L0: 0.125337 bits | L13: 0.185677 bits |
| hook | 80.018% | L0: 0.269372 bits | L0: 0.194828 bits |
| jumpingjacks | 72.225% | L0: 0.241370 bits | L13: 0.221662 bits |

JS использует объединённую marginal histogram обоих каналов одного уровня. Это описательная мера различия, не прогноз экономии условного кодера. Распределения L5/L6 не следует переносить на остальные уровни без измерений.
Номинальная нагрузка растёт от 1.01364 вершины/slot на L5 до 16384 на L15. Это отношение размера номинальной решётки к allocated capacity; оно не измеряет посещаемость, число реально занятых slots или допустимых point correspondences. Нового collision enumeration на высоких уровнях не выполнялось.
Наиболее крупные сжатые members — L7/L8, с существенным вкладом L6/L9/L10. Поэтому следующий отдельный эксперимент: одноуровневая абляция квантования L6–L10 при прежнем общем table8 quantizer и тех же views. Она должна локализовать distortion до разработки H5. Новые min/max, обучение и codec в этом запуске не выполняются.

Measured level sizes (внешний артефакт; см. каталог исключённых ссылок)

PSNR differences (внешний артефакт; см. каталог исключённых ссылок)

## Ресурсы и ограничения

| CPU audit | Wall seconds | Peak RSS MiB |
|---|---:|---:|
| bouncingballs | 14.038 | 753.090 |
| hellwarrior | 11.419 | 710.305 |
| hook | 13.216 | 765.973 |
| jumpingjacks | 12.833 | 729.414 |

Сумма CPU audit wall: 51.505 s. Сумма wall для 12 fresh-process render+metrics: 352.395 s. Время подготовки, хеширования и написания отчётов в эти суммы не включено. CPU audit RSS относится к родительскому процессу; отдельный RSS decoder сохранён в его validation.json, одновременный суммарный RSS не измерялся. GPU peak относится к PyTorch renderer allocated/reserved, не к полной VRAM устройства или отдельному metrics process. Скорости одиночных запусков зависят от первого кадра и прогрева; различие времени R0/R1/R2 не интерпретируется как ускорение квантованием: рендерер во всех случаях получает FP32.


## Воспроизведение

Окружение измерений: WSL Python 3.10.21, PyTorch 2.7.0+cu128, CUDA build 12.8, NumPy 1.26.4, zlib 1.3.2; по сценам записано runtime.json. Существующее окружение audit-env и upstream Grid4D не изменялись. Windows Python 3.12.14 использован для preparation, aggregation и hashing. Версия GPU driver не зафиксирована этим запуском.

Завершённый run неизменяем. Для повторения скопировать только *.py данного run в новый уникальный каталог под research (не копировать результаты), а команды выполнять с путём нового каталога. Скрипты отказываются перезаписывать результаты. prepare.py привязан к четырём существующим source models и проверяет их SHA256.

PowerShell, рабочая директория <PROJECT_ROOT>:

```powershell
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/prepare.py
```

WSL Bash:

```bash
export GRID4D_PREFIX=<USER_HOME>/.local/share/grid4d-baseline/audit-env
source <PROJECT_ROOT>/research/env_common.sh
run=<PROJECT_ROOT>/research/<NEW_RUN>
for scene in bouncingballs hellwarrior hook jumpingjacks; do
  CUDA_VISIBLE_DEVICES="" python -B "$run/audit_cpu.py" "$scene"
  for variant in R0 R1 R2; do
    python -B "$run/evaluate_variant.py" "$scene" "$variant"
  done
done
# Independent decode alone; NEW_OUTPUT must not exist:
CUDA_VISIBLE_DEVICES="" python -B "$run/decode_npz.py" "$run/hook/ZLIB8.npz" "$run/NEW_OUTPUT"
```

PowerShell aggregation, after all variants succeed:

```powershell
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/report.py
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/finish_reports.py
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/finalize.py
```

Исторические launch scripts remaining_*.sh сохраняют фактическую последовательность этого запуска с pilot R0; для нового полного запуска использовать цикл выше. Единственная экспортная ошибка была в Windows/WSL path jumpingjacks; traceback, начальный protocol и path-only correction сохранены. Алгоритмы quantizer, renderer и H4 не исправлялись. Источники/прежние артефакты проверяются по INPUT_MANIFEST → integrity-final.json; итоговый seal — FINAL_VALIDATION.json.

