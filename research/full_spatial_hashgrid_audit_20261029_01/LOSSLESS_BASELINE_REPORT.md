> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Standard lossless baseline
| scene | xyz_parameters | xyz_bytes | RAW8_B | ZLIB8_B | FP32_to_RAW8_x | FP32_to_ZLIB8_x | RAW8_to_ZLIB8_x |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 12196216 | 48784864 | 12202580 | 2079708 | 3.997914 | 23.457555 | 5.867449 |
| hellwarrior | 12196216 | 48784864 | 12202579 | 1766604 | 3.997914 | 27.615054 | 6.907365 |
| hook | 12196216 | 48784864 | 12202579 | 1488870 | 3.997914 | 32.766369 | 8.195866 |
| jumpingjacks | 12196216 | 48784864 | 12202579 | 1917692 | 3.997914 | 25.439364 | 6.363159 |

RAW8 uses standard NumPy NPZ ZIP_STORED, ZLIB8 NPZ ZIP_DEFLATED default. Each level is a .npy member; canonical JSON metadata is another uint8 .npy member. No new entropy model/coder.
| scene | RAW8_overhead_B | ZLIB_metadata_member_B | ZLIB_framing_B |
| --- | --- | --- | --- |
| bouncingballs | 6364 | 1009 | 2062 |
| hellwarrior | 6363 | 1011 | 2062 |
| hook | 6363 | 1009 | 2062 |
| jumpingjacks | 6363 | 1009 | 2062 |

Exact budget: sum(level compressed members)+metadata compressed member+ZIP framing=file size. Member compressed sizes include each NPY header; common metadata and ZIP framing are reported separately and not assigned arbitrarily to levels. Ratios are input/output factors, not percentages. Eight fresh-process decodes with input-only data-read audit PASS.
Largest compressed members:
bouncingballs: L7=358565 B, L8=340017 B, L6=291182 B, L9=226799 B
hellwarrior: L8=318526 B, L7=307918 B, L9=305361 B, L6=244626 B
hook: L8=286954 B, L7=284966 B, L9=247902 B, L6=232328 B
jumpingjacks: L8=312994 B, L7=306028 B, L9=289234 B, L6=249724 B


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

