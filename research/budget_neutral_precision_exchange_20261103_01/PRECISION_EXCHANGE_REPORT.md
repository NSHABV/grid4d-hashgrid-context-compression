> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Ограниченный обмен точностью GLOBAL7 / GLOBAL10

Статус завершения и сохранности входов определяется FINAL_VALIDATION.json. PASS_COMPLETED означает корректное выполнение протокола, а не обязательную пользу обмена.

## Главный результат

| scene | G8_B | feasible_E_out_of_42 | feasible_D_out_of_7 | D_best | E_best | FINAL_choice |
| --- | --- | --- | --- | --- | --- | --- |
| mutant | 1290908 | 6 | 7 | D_10 | E_10_4 | E_10_4 |
| bouncingballs | 2079541 | 10 | 7 | D_9 | E_10_4 | E_10_4 |
| hellwarrior | 1766435 | 5 | 7 | G8 | G8 | G8 |
| hook | 1488707 | 4 | 7 | G8 | G8 | G8 |
| jumpingjacks | 1917524 | 3 | 7 | G8 | G8 | G8 |

Выбор зафиксирован по validation до любых новых test-комбинаций всех пяти сцен. D_best выбирается среди G8 и допустимых D_i; E_best — среди G8 и допустимых E_i_j. Оба проходят точные guards SSIM≥G8 и LPIPS≤G8. Затем максимум PSNR, точный tie: меньше bytes, меньше изменённых уровней, лексикографический порядок числовых индексов. FINAL_choice выбирается тем же правилом среди этих трёх решений. Ниже совпадающие состояния объединены в одну строку с несколькими ролями, FINAL_choice — отметка.

## Validation: зафиксированные роли

| scene | roles | state | FINAL_choice | donor | recipient | bytes | delta_B_vs_G8 | PSNR | SSIM | LPIPS_STANDARD_VGG | delta_PSNR | delta_SSIM | delta_LPIPS_STANDARD_VGG | unused_budget_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mutant | G8 | G8 | False | — | — | 1290908 | 0 | 38.9088020325 | 0.990441977978 | 0.00854807905853 | 0 | 0 | 0 | 0 |
| mutant | D_best | D_10 | False | 10 | — | 1203884 | -87024 | 39.2870674133 | 0.991023540497 | 0.00818607956171 | 0.378265380859 | 0.000581562519073 | -0.000361999496818 | 87024 |
| mutant | E_best | E_10_4 | True | 10 | 4 | 1272451 | -18457 | 39.6655158997 | 0.991842627525 | 0.00789151713252 | 0.756713867188 | 0.00140064954758 | -0.000656561926007 | 18457 |
| bouncingballs | G8 | G8 | False | — | — | 2079541 | 0 | 38.9250564575 | 0.994454979897 | 0.0212652757764 | 0 | 0 | 0 | 0 |
| bouncingballs | D_best | D_9 | False | 9 | — | 2008263 | -71278 | 38.9402046204 | 0.994466125965 | 0.0212495941669 | 0.0151481628418 | 1.1146068573e-05 | -1.56816095114e-05 | 71278 |
| bouncingballs | E_best | E_10_4 | True | 10 | 4 | 2034756 | -44785 | 39.2290420532 | 0.994590580463 | 0.0208131279796 | 0.303985595703 | 0.000135600566864 | -0.00045214779675 | 44785 |
| hellwarrior | G8+D_best+E_best | G8 | True | — | — | 1766435 | 0 | 42.1312217712 | 0.989674091339 | 0.02289560996 | 0 | 0 | 0 | 0 |
| hook | G8+D_best+E_best | G8 | True | — | — | 1488707 | 0 | 37.6979904175 | 0.989649116993 | 0.0121910953894 | 0 | 0 | 0 | 0 |
| jumpingjacks | G8+D_best+E_best | G8 | True | — | — | 1917524 | 0 | 38.614692688 | 0.991584122181 | 0.0116753671318 | 0 | 0 | 0 | 0 |

## Test: зафиксированные роли

| scene | roles | state | FINAL_choice | donor | recipient | bytes | delta_B_vs_G8 | PSNR | SSIM | LPIPS_STANDARD_VGG | delta_PSNR | delta_SSIM | delta_LPIPS_STANDARD_VGG | unused_budget_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mutant | G8 | G8 | False | — | — | 1290908 | 0 | 38.6794548035 | 0.989810287952 | 0.0086723100394 | 0 | 0 | 0 | 0 |
| mutant | D_best | D_10 | False | 10 | — | 1203884 | -87024 | 39.0170860291 | 0.990381062031 | 0.00827500037849 | 0.337631225586 | 0.000570774078369 | -0.000397309660912 | 87024 |
| mutant | E_best | E_10_4 | True | 10 | 4 | 1272451 | -18457 | 39.3269996643 | 0.990968883038 | 0.00799405761063 | 0.64754486084 | 0.00115859508514 | -0.00067825242877 | 18457 |
| bouncingballs | G8 | G8 | False | — | — | 2079541 | 0 | 38.8329849243 | 0.994528949261 | 0.0206007715315 | 0 | 0 | 0 | 0 |
| bouncingballs | D_best | D_9 | False | 9 | — | 2008263 | -71278 | 38.8231010437 | 0.994530856609 | 0.0205882787704 | -0.00988388061523 | 1.90734863281e-06 | -1.24927610159e-05 | 71278 |
| bouncingballs | E_best | E_10_4 | True | 10 | 4 | 2034756 | -44785 | 39.1710586548 | 0.994690418243 | 0.0202679857612 | 0.338073730469 | 0.000161468982697 | -0.000332785770297 | 44785 |
| hellwarrior | G8+D_best+E_best | G8 | True | — | — | 1766435 | 0 | 42.2701873779 | 0.989561378956 | 0.0243978463113 | 0 | 0 | 0 | 0 |
| hook | G8+D_best+E_best | G8 | True | — | — | 1488707 | 0 | 37.1369247437 | 0.987501263618 | 0.0142304776236 | 0 | 0 | 0 | 0 |
| jumpingjacks | G8+D_best+E_best | G8 | True | — | — | 1917524 | 0 | 38.4173469543 | 0.991524100304 | 0.0112760504708 | 0 | 0 | 0 | 0 |

## Обмен против down-only

| scene | split | comparison | candidate | baseline | delta_B | delta_PSNR | delta_SSIM | delta_LPIPS_STANDARD_VGG | PSNR_worse_views | SSIM_worse_views | LPIPS_worse_views |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mutant | val | D_vs_G8 | D_10 | G8 | -87024 | 0.378265380859 | 0.000581562519073 | -0.000361999496818 | 1 | 3 | 0 |
| mutant | val | E_vs_G8 | E_10_4 | G8 | -18457 | 0.756713867188 | 0.00140064954758 | -0.000656561926007 | 1 | 1 | 0 |
| mutant | val | E_vs_D | E_10_4 | D_10 | 68567 | 0.378448486328 | 0.000819087028503 | -0.00029456242919 | 1 | 1 | 2 |
| mutant | test | D_vs_G8 | D_10 | G8 | -87024 | 0.337631225586 | 0.000570774078369 | -0.000397309660912 | 1 | 2 | 0 |
| mutant | test | E_vs_G8 | E_10_4 | G8 | -18457 | 0.64754486084 | 0.00115859508514 | -0.00067825242877 | 0 | 1 | 0 |
| mutant | test | E_vs_D | E_10_4 | D_10 | 68567 | 0.309913635254 | 0.000587821006775 | -0.000280942767859 | 2 | 2 | 0 |
| bouncingballs | val | D_vs_G8 | D_9 | G8 | -71278 | 0.0151481628418 | 1.1146068573e-05 | -1.56816095114e-05 | 8 | 7 | 10 |
| bouncingballs | val | E_vs_G8 | E_10_4 | G8 | -44785 | 0.303985595703 | 0.000135600566864 | -0.00045214779675 | 3 | 3 | 3 |
| bouncingballs | val | E_vs_D | E_10_4 | D_9 | 26493 | 0.288837432861 | 0.000124454498291 | -0.000436466187239 | 2 | 3 | 3 |
| bouncingballs | test | D_vs_G8 | D_9 | G8 | -71278 | -0.00988388061523 | 1.90734863281e-06 | -1.24927610159e-05 | 12 | 11 | 8 |
| bouncingballs | test | E_vs_G8 | E_10_4 | G8 | -44785 | 0.338073730469 | 0.000161468982697 | -0.000332785770297 | 1 | 1 | 2 |
| bouncingballs | test | E_vs_D | E_10_4 | D_9 | 26493 | 0.347957611084 | 0.000159561634064 | -0.000320293009281 | 1 | 1 | 3 |
| hellwarrior | val | D_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hellwarrior | val | E_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hellwarrior | val | E_vs_D | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hellwarrior | test | D_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hellwarrior | test | E_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hellwarrior | test | E_vs_D | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hook | val | D_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hook | val | E_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hook | val | E_vs_D | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hook | test | D_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hook | test | E_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hook | test | E_vs_D | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| jumpingjacks | val | D_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| jumpingjacks | val | E_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| jumpingjacks | val | E_vs_D | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| jumpingjacks | test | D_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| jumpingjacks | test | E_vs_G8 | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| jumpingjacks | test | E_vs_D | G8 | G8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Quantized slices рассчитываются один раз на сцену и используются во всех конфигурациях. Подтверждённые compressed level members сохранены в compressed_member_cache и переиспользуются для точной проверки идентичности во всех состояниях. Сборка/повторная сборка ZIP используют прежний стандартный pack без нового assembler и повторяют DEFLATE; ускорение encoder за счёт compressed-cache не заявляется. Это консервативный выбор реализации, измеренная стоимость повторного сжатия включена в CPU_TIMINGS.csv.

Все signed дельты означают candidate−baseline; положительная ΔLPIPS означает ухудшение. Число ухудшений вычислено без округления или допусков на20 связанных кадрах; независимость кадров и статистическая значимость не утверждаются. Полные signed per-view данные всех validation-кандидатов и test-вариантов — PER_VIEW_METRICS.csv.

## Физический бюджет

| scene | state | donor | recipient | bytes | donor_saving_B | recipient_cost_B | metadata_delta_B | framing_delta_B | total_delta_B | unused_budget_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mutant | G8 | — | — | 1290908 | 0 | 0 | 0 | 0 | 0 | 0 |
| mutant | D_10 | 10 | — | 1203884 | 87050 | 0 | 26 | 0 | -87024 | 87024 |
| mutant | E_10_4 | 10 | 4 | 1272451 | 87050 | 68535 | 58 | 0 | -18457 | 18457 |
| bouncingballs | G8 | — | — | 2079541 | 0 | 0 | 0 | 0 | 0 | 0 |
| bouncingballs | D_9 | 9 | — | 2008263 | 71307 | 0 | 29 | 0 | -71278 | 71278 |
| bouncingballs | E_10_4 | 10 | 4 | 2034756 | 125929 | 81079 | 65 | 0 | -44785 | 44785 |
| hellwarrior | G8 | — | — | 1766435 | 0 | 0 | 0 | 0 | 0 | 0 |
| hook | G8 | — | — | 1488707 | 0 | 0 | 0 | 0 | 0 | 0 |
| jumpingjacks | G8 | — | — | 1917524 | 0 | 0 | 0 | 0 | 0 | 0 |

Donor saving = минус изменение compressed NPY member; recipient cost = изменение recipient member. Знаки сохраняются. Полный net — сумма двух member deltas и изменений metadata/framing, подтверждённая filesystem size единого полного spatial-архива. Отдельные standalone файлы не складывались. Для G8 все дельты нулевые. Эти байты относятся только к xyz, не ко всему Grid4D. RATE_AUDIT.csv содержит все250 состояний, включая overbudget.

## Отдельное изменение формата G8

| scene | old_G8_bytes | new_G8_bytes | filesystem_bytes | level_member_bytes | metadata_member_bytes | framing_bytes |
| --- | --- | --- | --- | --- | --- | --- |
| mutant | 1290969 | 1290908 | -61 | 0 | -61 | 0 |
| bouncingballs | 2079602 | 2079541 | -61 | 0 | -61 | 0 |
| hellwarrior | 1766497 | 1766435 | -62 | 0 | -62 | 0 |
| hook | 1488765 | 1488707 | -58 | 0 | -58 | 0 |
| jumpingjacks | 1917587 | 1917524 | -63 | 0 | -63 | 0 |

Переход scope-v4 → exchange-v5 меняет только compressed metadata G8; все16 compressed level members и framing прежние. Эта разница не является выигрышем quantization или precision exchange. Все250 кандидатов сравниваются только в общем новом формате; budget — физический размер нового G8. Полные дельты — FORMAT_DELTA.csv.

## Остаточный разрыв до R0 на test

| scene | roles | state | PSNR_gap_R0 | SSIM_gap_R0 | LPIPS_excess_R0 |
| --- | --- | --- | --- | --- | --- |
| mutant | G8 | G8 | 5.30191040039 | 0.00655227899551 | 0.00289971055463 |
| mutant | D_best | D_10 | 4.9642791748 | 0.00598150491714 | 0.00250240089372 |
| mutant | E_best | E_10_4 | 4.65436553955 | 0.00539368391037 | 0.00222145812586 |
| bouncingballs | G8 | G8 | 3.65925598145 | 0.00128477811813 | 0.00278272293508 |
| bouncingballs | D_best | D_9 | 3.66913986206 | 0.0012828707695 | 0.00277023017406 |
| bouncingballs | E_best | E_10_4 | 3.32118225098 | 0.00112330913544 | 0.00244993716478 |
| hellwarrior | G8+D_best+E_best | G8 | 0.570808410645 | 0.0012179017067 | 0.00159105844796 |
| hook | G8+D_best+E_best | G8 | 1.88715362549 | 0.00308293104172 | 0.00232947990298 |
| jumpingjacks | G8+D_best+E_best | G8 | 0.828510284424 | 0.00092488527298 | 0.000625583343208 |

## Раздельные научные выводы

| scene | FEASIBILITY | CALIBRATION_GAIN | TEST_TRANSFER | ADDED_VALUE_VS_DOWN_ONLY | E_validation_preferred_to_D | FINAL_choice |
| --- | --- | --- | --- | --- | --- | --- |
| mutant | True | True | PASS | TEST_PSNR_GAIN_NO_WORSE_SSIM_LPIPS | True | E_10_4 |
| bouncingballs | True | True | PASS | TEST_PSNR_GAIN_NO_WORSE_SSIM_LPIPS | True | E_10_4 |
| hellwarrior | True | False | NOT_APPLIED_G8 | NOT_APPLIED_G8 | False | G8 |
| hook | True | False | NOT_APPLIED_G8 | NOT_APPLIED_G8 | False | G8 |
| jumpingjacks | True | False | NOT_APPLIED_G8 | NOT_APPLIED_G8 | False | G8 |

FEASIBILITY означает наличие хотя бы одной из42 пар в бюджете. CALIBRATION_GAIN требует выбранную пару с положительным PSNR gain и обоими validation guards; меньший файл при точно том же PSNR может быть выбран tie-breaking, но не называется PSNR gain. TEST_TRANSFER требует положительный test PSNR gain и неухудшение SSIM/LPIPS относительно G8. ADDED_VALUE_VS_DOWN_ONLY отдельно проверяет положительный test PSNR gain E_best над D_best при неухудшении двух других метрик. Все исходные дельты выше сохраняют возможные trade-offs; эти ярлыки не заменяют метрик. Если FINAL_choice=D_best, пользу нельзя приписывать повышению точности. G8 fallback — корректный отказ от модификации.

## Протокол, точность и проверки

GLOBAL scope неизменен: один min/max исходного FP32 xyz по всем allocated rows и обоим каналам, общий для всех16 уровней и p7/p8/p10. Коды получены из исходных FP32; FP64 step=(b−a)/(2^p−1), nearest-even round((x−a)/step), clipping перед cast; dequantization в прежнем порядке с FP32 output. P7/p8 — uint8 NPY, p10 — little-endian uint16 NPY, без bitpacking. Quantizer map внутри файла; Qmax не выводится из dtype. Исходные helper semantics и Grid4D forward не менялись.

5 сцен × (G8 +7 donors +42 пары) =250 полных ZIP/NPY файлов, единый versioned transport, DEFLATE6, постоянные timestamps/attributes/member order/JSON conventions. Каждый файл независимо декодируется в новом процессе до quality: exact codes/metadata/canonical FP32, изменённые и незатронутые level masks, все allocated slots, byte-identical rebuild, регрессии G7/G8/M10. Read audit проверяет обращения Python к данным и не является OS sandbox. У новых evaluation jobs сохраняется guard telemetry.

Validation: непосредственный рендер всех feasible комбинаций на прежних20 views; сумма отдельных эффектов не используется. Test: только G8,D_best,E_best после общего freeze, одинаковые состояния один раз. R0 — reference разрыва. Reuse контролей требует provenance/runtime/camera/time/GT и exact ordinal0 smoke. Renderer embeddings FP32,800×800 black, PNG roundtrip, mean(per-view PSNR), прежний SSIM, LPIPS_STANDARD_VGG normalize=True ровно один раз. Temporal/MLP/Gaussian parameters не менялись; xyz hashes проверены перед forward.

## Ресурсы

{
  "CPU_jobs_wall_seconds": 1224.2658037380002,
  "validation_jobs_wall_seconds": 2337.0308219789995,
  "test_jobs_wall_seconds": 354.6334049529992,
  "peak_process_tree_RSS_bytes": 4855218176,
  "peak_total_device_MiB": 3309,
  "minimum_available_RAM_bytes": 2349015040,
  "peak_process_tree_RSS_GiB": 4.5217742919921875,
  "minimum_available_RAM_GiB": 2.1876907348632812,
  "validation_jobs_wall_minutes": 38.95051369964999,
  "test_jobs_wall_minutes": 5.910556749216653
}

GPU использовался для render/metrics последовательно; quantization/compression/decode — CPU. Peak_total_device в MiB включает desktop; process-tree RSS в GiB может повторно учитывать shared pages. CPU_TIMINGS.csv содержит один shared quantization_seconds на сцену из PREPARATION.json, а не повторяет эту стоимость для50 файлов. Это время создания quantized slices; загрузка исходных весов и отдельные проверки не включены в этот таймер. Для каждого файла отдельно сохранены compression_seconds, rebuild_seconds, cold_decode_seconds и internal_decode_seconds из *_checks.json. Cold decode включает запуск процесса; internal decode вложен в него и не должен прибавляться повторно. RESOURCES.csv содержит wall jobs, RENDER/METRICS — отдельные времена. Hashing и отчётность не включаются в encode/renderer timings; итоговый контроль сохранности отражён в FINAL_VALIDATION.json.

## Ограничения и следующий шаг

Это exploratory follow-up на пяти уже наблюдавшихся checkpoints и прежних test views. Freeze не делает их независимыми данными. Результат uniform LEVEL предыдущего опыта остаётся неизменным. Проверен только один donor7 и один recipient10 на S={4,…,10}, GLOBAL range и данном DEFLATE budget. Отрицательный или смешанный результат не опровергает произвольный mixed-precision метод; положительный не является новизной общего принципа и не доказывает практическую значимость малого gain. Нет BD-rate, новых quality tolerances, ретюнинга по test или расширения поиска.

Один следующий исследовательский шаг: репликация неизменённого протокола и selection rules на заранее выбранном независимом checkpoint, с отдельным down-only контролем. Новые данные или обучение в этом запуске не создавались.

## Воспроизведение и сохранность

SOURCE_REQUEST.txt, PREREGISTERED_PROTOCOL.json, INPUT_MANIFEST.json, RUNTIME.json и frozen source snapshot задают точные inputs/runtime/protocol. Новое воспроизведение выполняется в новом уникальном каталоге: скопировать исходники и требуемые runtime/split fixtures, исправить путь run в launch.sh/python.sh до создания нового протокола. Завершённые artifacts не перезаписывать. Ниже точные команды текущего запуска, а не разрешение повторно писать готовые outputs.

```powershell
# Из <PROJECT_ROOT>, после подготовки нового уникального каталога:
.tools/phase2-plotting-env/Scripts/python.exe -B research/budget_neutral_precision_exchange_20261103_01/prepare.py
foreach ($stage in @("setup","rate","seal","pilot","validation","freeze","test","runtime_after")) {
  wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/budget_neutral_precision_exchange_20261103_01/launch.sh $stage
  if ($LASTEXITCODE -ne 0) { throw "Stage failed: $stage" }
}
wsl -d Ubuntu -- bash <PROJECT_ROOT>/research/budget_neutral_precision_exchange_20261103_01/python.sh report.py
.tools/phase2-plotting-env/Scripts/python.exe -B research/budget_neutral_precision_exchange_20261103_01/finalize.py
```

Перед финальным seal проверить отчёт; финализатор использует native Windows filesystem для единого SHA-аудита и не запускает GPU. Старые runs read-only; точное покрытие итоговой SHA256-проверки указано в FINAL_VALIDATION.json. После завершения — STOP.
