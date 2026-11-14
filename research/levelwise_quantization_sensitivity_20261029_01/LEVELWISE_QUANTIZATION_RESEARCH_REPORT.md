> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Grid4D: Level-wise quantization sensitivity

Четыре исходных checkpoint, один training seed на сцену, 20 фиксированных test views. 56 абляций и 8 заново рассчитанных контролей. Общий frozen table-wise8 диапазон на весь xyz-тензор каждой сцены. Никакого нового quantization fitting, обучения, H4/H5 или mixed-precision container. В рендерере все embeddings имеют dtype FP32; различается только источник значений slices.

| scene | Q_ONLY_worst_level | Q_ONLY_loss_dB | RESTORE_best_level | RESTORE_gain_dB | RESTORE_SSIM_gain | RESTORE_LPIPS_improvement | estimated_extra_raw_bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 5 | 2.045002 | 5 | 1.048904 | 0.000459 | 0.001343 | 3145728 |
| hellwarrior | 8 | 0.089329 | 8 | 0.077988 | 0.000159 | 0.000241 | 3145728 |
| hook | 6 | 0.480793 | 6 | 0.233841 | 0.000535 | 0.000402 | 3145728 |
| jumpingjacks | 4 | 0.129879 | 4 | 0.089336 | 0.000095 | 0.000059 | 1232274 |


# Next research decision

Direction **A — Mixed-Precision Quantization — отдельное исследование, без внедрения codec**.

Уровни различаются по измеренному эффекту. Наиболее полезный RESTORE совпадает с наиболее чувствительным Q_ONLY по PSNR внутри каждой сцены: bouncingballs L5, hellwarrior L8, hook L6, jumpingjacks L4. Два первых уровня по PSNR также совпадают между A/B внутри каждой сцены, но общего списка между сценами нет. RESTORE gains: +1.048904, +0.077988, +0.233841, +0.089336 dB. Дополнительная несжатая стоимость FP32 вместо uint8: 3,145,728 B для L5/L8/L6 и 1,232,274 B для L4. Особенно bouncingballs даёт количественный повод исследовать повышенную точность; небольшой gain hellwarrior не объявляется экономически выгодным за 3 MiB. Это выбор направления A, а не утверждение об оптимальности FP32 или выигрыше mixed-precision bitstream. Новый порог приемлемости не вводился. B не выбран главным направлением из-за неоднородности чувствительности. Контекстная зависимость ограничивает перенос на комбинации, но не отменяет индивидуального эффекта, поэтому C не требуется как единственное возможное направление.

Один следующий отдельный, заранее зафиксированный эксперимент: проверить одну повышенную точность uint16 для единственного PSNR-leading RESTORE уровня каждой сцены (L5/L8/L6/L4 соответственно), оставив остальные xyz на прежнем uint8 и сохранив исходные общие min/max. Сравнить с уже имеющимися R2 и RESTORE_FP32 на том же протоколе; выбор уровней по текущим test результатам явно считать exploratory follow-up, а не независимым подтверждением. Не подбирать несколько битностей или комбинации и не создавать codec в текущей задаче. Такой опыт проверит, можно ли приблизиться к измеренному FP32 recovery при меньшей несжатой стоимости; реальный mixed-format transport потребует отдельной оценки позже.

This is a research direction, not a selected mixed-precision policy. No new numerical GO threshold was introduced; decision is supported by the measured deltas and raw storage costs shown above. Do not start H5 or mixed-precision codec automatically.


1. Наиболее чувствительные по Q_ONLY PSNR уровни: bouncingballs L5 (−2.045002 dB), hellwarrior L8 (−0.089329), hook L6 (−0.480793), jumpingjacks L4 (−0.129879). Это ранжирование по PSNR, не автоматический компромисс трёх метрик.

2. Наибольшее восстановление PSNR дают те же уровни: +1.048904, +0.077988, +0.233841 и +0.089336 dB. Для этих четырёх вариантов SSIM повышается, LPIPS уменьшается. Но у jumpingjacks максимальное улучшение LPIPS даёт L7 (+0.000084421), а не PSNR-лидер L4 (+0.000059051); выбор метрики влияет на решение.

3. Первые два уровня рейтинга PSNR совпадают между Q_ONLY и RESTORE внутри каждой сцены: L5/L4, L8/L7, L6/L5, L4/L5. Полные рейтинги различаются. Нельзя переносить величину изолированной потери в gain при fully-quantized background.

4. Между сценами универсальный чувствительный уровень не обнаружен. У bouncingballs L5 RESTORE улучшает PSNR во всех 20 views (от +0.554661 до +1.518192 dB); hook L6 — также в 20/20 (от +0.026207 до +1.024761). Hellwarrior L8 улучшает 18/20, jumpingjacks L4 — 16/20; некоторые кадры ухудшаются. Это описательные paired результаты, без заявления статистической значимости или независимости кадров.

5. Различие bouncingballs и hellwarrior локализовано, в частности, на L5: Q_ONLY loss 2.045002 против 0.070648 dB; RESTORE gain 1.048904 против 0.064651 dB. У bouncingballs общий quantizer step меньше (0.033524661 против 0.043866530), поэтому объяснение только более крупным шагом квантования не подходит. Причина большей чувствительности не доказана: возможны различия в распределениях features, чувствительности deformation network, траекториях Gaussians и image-space error. Эти механизмы требуют отдельного контролируемого анализа.

6. Размер ZLIB-member не даёт универсального ранжирования distortion. У bouncingballs наиболее дорог L7 (358565 B), но наиболее чувствителен L5 (183235 B). У jumpingjacks наиболее дорог L8 (312994 B), но лидер PSNR sensitivity — L4 (58584 B). У hellwarrior L8 лидирует и по размеру, и по PSNR sensitivity. Это наблюдения о зависимости от сцены, без вывода о причинности или значимости корреляции.

7. L7/L8 нельзя объявить безопасными для снижения точности: Q_ONLY L7/L8 у bouncingballs даёт −0.543045/−0.203518 dB, у hook −0.231586/−0.199379. На hellwarrior это два самых чувствительных по PSNR исследованных уровня. Большой размер сам по себе не означает избыточность.

8. Есть основание исследовать повышенную точность избранных уровней, но нет готовой общей policy. Сохранение FP32 не всегда улучшает качество: у bouncingballs RESTORE L6 изменяет PSNR на −0.024044 dB при небольшом улучшении SSIM/LPIPS; у hook RESTORE L10 ухудшает все три метрики (PSNR −0.006989 dB). Это допустимый эффект замены одной ошибки на фоне остальных, а не нарушение exact mask checks.

9. Обоснован переход к отдельному эксперименту A по mixed precision, но не к автоматической реализации codec или оптимизации битности по этим test views. FP32 здесь — диагностическая верхняя точность одного уровня, а не доказанно оптимальный storage format. Комбинации уровней и промежуточные precision не исследовались.

10. Ограничения: четыре scene-specific checkpoint и один training seed, 20 коррелированных test views, один global table8 range, только L4–L10 в индивидуальных абляциях. R2 также квантован на L0–L3/L11–L15, чей индивидуальный вклад не измерен. PSNR логарифмичен; эффекты не складываются. Эксперимент не доказывает безопасность pruning, причинную независимость уровней, универсальность ранжирования или фактическую эффективность mixed-precision bitstream.

L5–L10 имеют одинаковые allocated/raw размеры, но различаются по ZLIB contribution и качеству. У bouncingballs сохранение L4 даёт +0.460045 dB за оценочные 1,232,274 дополнительных raw bytes, сохранение L5 — +1.048904 dB за 3,145,728 B. У hellwarrior L8 даёт только +0.077988 dB за те же оценочные 3,145,728 B. Поэтому экономическая целесообразность не следует из положительного gain. Эти разницы raw bytes не являются измеренным overhead mixed-precision файла. Сжатие сохранённых FP32, framing и общий транспорт не измерены; размеры прежних ZLIB members нельзя просто заменить FP32 bytes и назвать результат новым codec. Размеры и диаграмма служат для постановки следующего rate–distortion эксперимента.

## Baselines

| scene | variant | PSNR | SSIM | LPIPS | old_baseline_PNG_exact |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | R0 | 42.492241 | 0.995814 | 0.007435 | True |
| bouncingballs | R2 | 38.832985 | 0.994529 | 0.009730 | True |
| hellwarrior | R0 | 42.840996 | 0.990779 | 0.015664 | True |
| hellwarrior | R2 | 42.270187 | 0.989561 | 0.016923 | True |
| hook | R0 | 39.024078 | 0.990584 | 0.008997 | True |
| hook | R2 | 37.136925 | 0.987501 | 0.011111 | True |
| jumpingjacks | R0 | 39.245857 | 0.992449 | 0.007618 | True |
| jumpingjacks | R2 | 38.417347 | 0.991524 | 0.008221 | True |


Isolated loss (внешний артефакт; см. каталог исключённых ссылок)

Restoration gain (внешний артефакт; см. каталог исключённых ссылок)

Те же test split, camera matrices, timestamps, 800×800, чёрный background, seed 0, PNG8 round-trip и upstream PSNR/SSIM/LPIPS VGG. LPIPS вызван с прежней нормализацией RGB [0,1]. Это сопоставимые внутри протокола метрики, не новая оценка статьи. Заранее заданные абсолютные допуски R0/R2: PSNR 1e-4 dB, SSIM/LPIPS 1e-6, на aggregate и каждом кадре. Контроли сверены с прежним sealed аудитом. Поле evaluation.order скопировано из описания предыдущего аудита (R0/R1/R2); порядок нового эксперимента однозначно задан отдельным верхнеуровневым order и variants_quantized_levels и соблюдён runner. R1 в новом эксперименте не запускался. Это уточнение provenance, без изменения протокола после измерений.

All 56 ablations, 8 controls, 1,280 per-view records and 1,024 exact slice checks are saved. Protected-input SHA256 and final artifact hashes are in FINAL_VALIDATION.json. See QUALITY_SENSITIVITY_REPORT.md for all PSNR/SSIM/LPIPS and deltas, CROSS_SCENE_COMPARISON.md for each level across scenes, SPATIAL_LEVEL_SIZE_ANALYSIS.md for byte budgets, and PERFORMANCE_REPORT.md for timing.

| scene | configurations | process_wall_sum_s | render_wall_sum_s | metric_wall_sum_s | max_allocated_VRAM_MiB | max_reserved_VRAM_MiB | max_sampled_process_tree_RSS_MiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 16 | 618.932478 | 316.176218 | 178.801943 | 962.877930 | 1244.000000 | 3850.089844 |
| hellwarrior | 16 | 513.359105 | 240.089808 | 169.566253 | 402.650391 | 448.000000 | 3064.218750 |
| hook | 16 | 554.519796 | 264.095891 | 173.530571 | 1049.227539 | 1406.000000 | 3122.808594 |
| jumpingjacks | 16 | 612.992354 | 312.888967 | 185.365028 | 757.378906 | 938.000000 | 4465.644531 |


## Reproduction

This completed run is immutable. Copy only the runnable scripts to a new unique research directory; do not copy outputs. prepare.py freezes scene/view/variant definitions and source hashes. All writes are exclusive; runner skips only jobs with successful evaluation.json. A partial job must be inspected, never overwritten. Launch sequentially in the existing WSL audit-env:

```powershell
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/prepare.py
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/<NEW_RUN>/launch.sh pilot
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/<NEW_RUN>/launch.sh full
.tools/phase2-plotting-env/Scripts/python.exe research/<NEW_RUN>/aggregate.py
```

After inspecting measured results, write a new RESEARCH_DECISION.json with direction/rationale/scientific_analysis/size_interpretation/next_step/title; it must not alter the preregistered protocol. Then run write_reports.py, verify figures, and finalize.py. Final runtime hashes are verified in WSL by verify_runtime.py. Environment, pip-freeze, original source snapshots and all commands are saved. launch.sh full also resumes unstarted configurations after successful pilot. No reboot auto-resume is installed by this experiment.

Results layout: scene/variant/model/test/ours_50000/renders and gt; per_view.json and evaluation.json; mask_validation.json, render_validation.json, process_resources.json. progress/*.json are immutable continuation points. Error logs are retained. No protected earlier report or input is overwritten.

## Предварительно выбранные изображения

Ordinal 0, 10, 19 и варианты ниже зафиксированы до новых рендеров, без выбора по качеству. Ссылки ведут к исходным PNG без нового resize/cropping. Остальные test views также сохранены.

| Scene | Variant | View 0 | View 10 | View 19 |
|---|---|---|---|---|
| bouncingballs | R0 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| bouncingballs | R2 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| bouncingballs | Q_ONLY_L4 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| bouncingballs | Q_ONLY_L7 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| bouncingballs | RESTORE_FP32_L4 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| bouncingballs | RESTORE_FP32_L7 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hellwarrior | R0 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hellwarrior | R2 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hellwarrior | Q_ONLY_L4 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hellwarrior | Q_ONLY_L7 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hellwarrior | RESTORE_FP32_L4 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hellwarrior | RESTORE_FP32_L7 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hook | R0 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hook | R2 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hook | Q_ONLY_L4 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hook | Q_ONLY_L7 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hook | RESTORE_FP32_L4 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| hook | RESTORE_FP32_L7 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| jumpingjacks | R0 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| jumpingjacks | R2 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| jumpingjacks | Q_ONLY_L4 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| jumpingjacks | Q_ONLY_L7 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| jumpingjacks | RESTORE_FP32_L4 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |
| jumpingjacks | RESTORE_FP32_L7 | 00000.png (внешний артефакт; см. каталог исключённых ссылок) | 00010.png (внешний артефакт; см. каталог исключённых ссылок) | 00019.png (внешний артефакт; см. каталог исключённых ссылок) |

