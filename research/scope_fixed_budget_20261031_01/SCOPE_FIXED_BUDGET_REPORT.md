> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Проверенный итог fixed-budget эксперимента

Все 70 архивов измерены и независимо декодированы. В пределах заданного семейства LEVEL имеет более высокий test PSNR, чем validation-selected GLOBAL, в 0 из 5 сцен. Близки по фактическому размеру (NEAR_RATE) 1 из 5 пар. Это результат под общим потолком бюджета, а не сравнение при строго равном rate.

Во всех пяти сценах validation-selected GLOBAL совпал с GLOBAL8. Поэтому два требуемых сравнения численно совпадают; в SIGNED_COMPARISONS.csv сохранены обе роли baseline.

| Сцена | GLOBAL | LEVEL | Бюджет, B | LEVEL, B | Не использовано LEVEL, B | Rate gap | ΔPSNR | ΔSSIM | ΔLPIPS |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| mutant | GLOBAL8 | LEVEL4 | 1,290,969 | 983,199 | 307,770 | 23.84% | -11.271904 | -0.053204 | +0.036495 |
| bouncingballs | GLOBAL8 | LEVEL5 | 2,079,602 | 1,518,977 | 560,625 | 26.96% | -10.665367 | -0.013523 | +0.018238 |
| hellwarrior | GLOBAL8 | LEVEL4 | 1,766,497 | 903,035 | 863,462 | 48.88% | -6.978477 | -0.026555 | +0.029637 |
| hook | GLOBAL8 | LEVEL4 | 1,488,765 | 1,018,650 | 470,115 | 31.58% | -10.936857 | -0.057743 | +0.039985 |
| jumpingjacks | GLOBAL8 | LEVEL5 | 1,917,587 | 1,882,411 | 35,176 | 1.83% | -5.641445 | -0.011288 | +0.005976 |

Знаки в этой таблице: LEVEL минус выбранный GLOBAL; для LPIPS положительная разность означает ухудшение. В подробной таблице ниже LPIPS_improvement имеет противоположный знак. Значения не округлялись при выборе или Pareto-проверках.

Проведена отдельная проверка полноты validation/test, выбора максимума validation PSNR, строгого бюджета и суммы компонентов каждого файла, хронологии freeze/test, переноса метрик в CSV и числа ухудшившихся кадров. Результат: report_review/REPORT_REVIEW.json.

Контроли p8: изменение physical bytes v4 относительно v3 записано отдельно в report_review/FORMAT_DELTA.json. Проверено, что оно целиком относится к compressed metadata: level payload и framing не изменились. Эта разница не засчитывается как эффект нового квантования.

Измеренное quantization_seconds включает создание encoder reconstruction и scalar checks; это время CPU-этапа, а не изолированного quantizer kernel. Cold decode включает запуск Python и проверку доступа к файлам; internal decode указан отдельно. Рендеринговые проверки хешей и загрузка модели входят в wall subprocess, но не в per-frame forward time.

Скрипт review_results.py добавлен после ARCHIVES_FREEZE (фиксации научных исходников), до общего SELECTION_FREEZE, только для проверки и оформления результатов; quantizer, decoder, renderer, selector и их frozen source hashes не изменялись. Исходная версия отчёта сохранена побитно в report_review/SCOPE_FIXED_BUDGET_REPORT_before_review.md.

Пауза и возобновление: 55 готовых validation-оценок переиспользованы после проверки хешей; заново рассчитаны только jumpingjacks LEVEL4 и LEVEL5. Для завершённого jumpingjacks validation LEVEL3 родительский guard был остановлен до записи телеметрии. Его quality/decoder/PNG checks проверены, но полный subprocess wall time, sampled process-tree RSS, device peak и minimum RAM отсутствуют. RESOURCES.csv и guarded_seconds исключают ровно этот evaluation job; это неполная сумма наблюдавшегося времени, не полное время эксперимента. Доступные отдельные render/metric времена и RSS сохранены в RESUME_20261103_BOUNDARY_RECONCILIATION.json. Дни паузы не считаются compute time.

Окружение: Python 3.10.21, NumPy 1.26.4, PyTorch 2.7.0+cu128, CUDA 12.8, torchvision 0.22.0+cu128, Pillow 9.5.0, LPIPS 0.1.4, zlib 1.3.2; полные хеши в RUNTIME.json. Обучение Grid4D не выполнялось.

Диаграмма измеренных validation-точек: PNG (внешний артефакт; см. каталог исключённых ссылок), PDF (внешний артефакт; см. каталог исключённых ссылок). Линии интерполяции отсутствуют. Предыдущий завершённый опыт: QUANTIZER_SCOPE_REPORT.md (внешний артефакт; см. каталог исключённых ссылок).

---

# GLOBAL и LEVEL под одинаковым максимальным бюджетом spatial-архива

Итог технических проверок — FINAL_VALIDATION.json. PASS_COMPLETED означает завершение протокола, а не победу LEVEL. Это SAME_BUDGET_CAP exploratory experiment на пяти ранее наблюдавшихся сценах. Фактические размеры не обязаны совпадать.

## Протокол

70 кандидатов: 5 сцен × GLOBAL/LEVEL × p2…8. У каждого кандидата один p для всех16 уровней; все коды uint8 NPY без упаковки битов. Ranges вычислены из исходного FP32 по всем allocated rows и обоим каналам и фиксированы между p. Арифметика: FP64 step=(b−a)/(2^p−1), nearest-even((x−a)/step), clip перед cast; clip(a+q*step)→FP32. Constant: step0,codes0. Все файлы — scope-v4 ZIP/NPY DEFLATE6 с неизменным transport. GLOBAL8/LEVEL8 перепакованы в общий формат, их коды и FP32 побитно прежние; разница формата учитывается отдельно.

Бюджет каждой сцены — actual bytes нового GLOBAL8, без допуска. Проверены все p, монотонность не предполагается. На20 validation views оцениваются все feasible кандидаты. Выбор отдельно для каждого scope: максимум mean(per-view PSNR), точные ties — меньше bytes, затем меньше p. SSIM и STANDARD VGG LPIPS не участвуют в выборе. Все пять selections заморожены до нового test p<8.

Test —20 прежних views: выбранные GLOBAL/LEVEL, GLOBAL8; R0 и LEVEL8 только reference. Повторяющийся GLOBAL8 оценивается один раз. Старые scores переиспользуются после runtime/provenance/camera/time/GT и exact ordinal0 PNG/floatRGB smoke. Рендеринг из независимо decoded xyz; другие параметры проверены без изменений. 800×800,black,PNG roundtrip,FP32 mean PSNR,SSIM,LPIPS_STANDARD_VGG normalize=True ровно один раз.

## Выбранные варианты: val

| scene | scope | p | budget | bytes | unused_budget_B | budget_utilization | PSNR | SSIM | LPIPS_STANDARD_VGG |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mutant | GLOBAL | 8 | 1290969 | 1290969 | 0 | 1 | 38.9088020325 | 0.990441977978 | 0.00854807905853 |
| mutant | LEVEL | 4 | 1290969 | 983199 | 307770 | 0.7615976836 | 27.9529361725 | 0.939520716667 | 0.043746996671 |
| bouncingballs | GLOBAL | 8 | 2079602 | 2079602 | 0 | 1 | 38.9250564575 | 0.994454979897 | 0.0212652757764 |
| bouncingballs | LEVEL | 5 | 2079602 | 1518977 | 560625 | 0.730417166362 | 28.4149627686 | 0.980810821056 | 0.039637863636 |
| hellwarrior | GLOBAL | 8 | 1766497 | 1766497 | 0 | 1 | 42.1312217712 | 0.989674091339 | 0.02289560996 |
| hellwarrior | LEVEL | 4 | 1766497 | 903035 | 863462 | 0.511200981377 | 35.3663063049 | 0.964323163033 | 0.0517685897648 |
| hook | GLOBAL | 8 | 1488765 | 1488765 | 0 | 1 | 37.6979904175 | 0.989649116993 | 0.0121910953894 |
| hook | LEVEL | 4 | 1488765 | 1018650 | 470115 | 0.684224844082 | 26.4905204773 | 0.933699011803 | 0.0522895045578 |
| jumpingjacks | GLOBAL | 8 | 1917587 | 1917587 | 0 | 1 | 38.614692688 | 0.991584122181 | 0.0116753671318 |
| jumpingjacks | LEVEL | 5 | 1917587 | 1882411 | 35176 | 0.981656112604 | 32.9272537231 | 0.980314850807 | 0.0179712865502 |

## Выбранные варианты: test

| scene | scope | p | budget | bytes | unused_budget_B | budget_utilization | PSNR | SSIM | LPIPS_STANDARD_VGG |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mutant | GLOBAL | 8 | 1290969 | 1290969 | 0 | 1 | 38.6794548035 | 0.989810287952 | 0.0086723100394 |
| mutant | LEVEL | 4 | 1290969 | 983199 | 307770 | 0.7615976836 | 27.4075508118 | 0.936605811119 | 0.0451673269272 |
| bouncingballs | GLOBAL | 8 | 2079602 | 2079602 | 0 | 1 | 38.8329849243 | 0.994528949261 | 0.0206007715315 |
| bouncingballs | LEVEL | 5 | 2079602 | 1518977 | 560625 | 0.730417166362 | 28.1676177979 | 0.981005489826 | 0.0388390161097 |
| hellwarrior | GLOBAL | 8 | 1766497 | 1766497 | 0 | 1 | 42.2701873779 | 0.989561378956 | 0.0243978463113 |
| hellwarrior | LEVEL | 4 | 1766497 | 903035 | 863462 | 0.511200981377 | 35.2917098999 | 0.963006198406 | 0.0540351979434 |
| hook | GLOBAL | 8 | 1488765 | 1488765 | 0 | 1 | 37.1369247437 | 0.987501263618 | 0.0142304776236 |
| hook | LEVEL | 4 | 1488765 | 1018650 | 470115 | 0.684224844082 | 26.2000675201 | 0.929758429527 | 0.0542153120041 |
| jumpingjacks | GLOBAL | 8 | 1917587 | 1917587 | 0 | 1 | 38.4173469543 | 0.991524100304 | 0.0112760504708 |
| jumpingjacks | LEVEL | 5 | 1917587 | 1882411 | 35176 | 0.981656112604 | 32.7759017944 | 0.98023635149 | 0.017252035439 |

## Signed сравнения

| scene | split | baseline | LEVEL | byte_delta_LEVEL_minus_GLOBAL | relative_rate_gap | rate_label | PSNR_gain | SSIM_gain | LPIPS_improvement | LEVEL_dominates_all | GLOBAL_dominates_all |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mutant | val | GLOBAL8 | LEVEL4 | -307770 | 0.2384023164 | NOT_NEAR_RATE | -10.95586586 | -0.0509212613106 | -0.0351989176124 | False | False |
| mutant | val | GLOBAL8 | LEVEL4 | -307770 | 0.2384023164 | NOT_NEAR_RATE | -10.95586586 | -0.0509212613106 | -0.0351989176124 | False | False |
| mutant | test | GLOBAL8 | LEVEL4 | -307770 | 0.2384023164 | NOT_NEAR_RATE | -11.2719039917 | -0.0532044768333 | -0.0364950168878 | False | False |
| mutant | test | GLOBAL8 | LEVEL4 | -307770 | 0.2384023164 | NOT_NEAR_RATE | -11.2719039917 | -0.0532044768333 | -0.0364950168878 | False | False |
| bouncingballs | val | GLOBAL8 | LEVEL5 | -560625 | 0.269582833638 | NOT_NEAR_RATE | -10.510093689 | -0.0136441588402 | -0.0183725878596 | False | False |
| bouncingballs | val | GLOBAL8 | LEVEL5 | -560625 | 0.269582833638 | NOT_NEAR_RATE | -10.510093689 | -0.0136441588402 | -0.0183725878596 | False | False |
| bouncingballs | test | GLOBAL8 | LEVEL5 | -560625 | 0.269582833638 | NOT_NEAR_RATE | -10.6653671265 | -0.0135234594345 | -0.0182382445782 | False | False |
| bouncingballs | test | GLOBAL8 | LEVEL5 | -560625 | 0.269582833638 | NOT_NEAR_RATE | -10.6653671265 | -0.0135234594345 | -0.0182382445782 | False | False |
| hellwarrior | val | GLOBAL8 | LEVEL4 | -863462 | 0.488799018623 | NOT_NEAR_RATE | -6.76491546631 | -0.0253509283066 | -0.0288729798049 | False | False |
| hellwarrior | val | GLOBAL8 | LEVEL4 | -863462 | 0.488799018623 | NOT_NEAR_RATE | -6.76491546631 | -0.0253509283066 | -0.0288729798049 | False | False |
| hellwarrior | test | GLOBAL8 | LEVEL4 | -863462 | 0.488799018623 | NOT_NEAR_RATE | -6.97847747803 | -0.0265551805496 | -0.0296373516321 | False | False |
| hellwarrior | test | GLOBAL8 | LEVEL4 | -863462 | 0.488799018623 | NOT_NEAR_RATE | -6.97847747803 | -0.0265551805496 | -0.0296373516321 | False | False |
| hook | val | GLOBAL8 | LEVEL4 | -470115 | 0.315775155918 | NOT_NEAR_RATE | -11.2074699402 | -0.0559501051903 | -0.0400984091684 | False | False |
| hook | val | GLOBAL8 | LEVEL4 | -470115 | 0.315775155918 | NOT_NEAR_RATE | -11.2074699402 | -0.0559501051903 | -0.0400984091684 | False | False |
| hook | test | GLOBAL8 | LEVEL4 | -470115 | 0.315775155918 | NOT_NEAR_RATE | -10.9368572235 | -0.0577428340912 | -0.0399848343804 | False | False |
| hook | test | GLOBAL8 | LEVEL4 | -470115 | 0.315775155918 | NOT_NEAR_RATE | -10.9368572235 | -0.0577428340912 | -0.0399848343804 | False | False |
| jumpingjacks | val | GLOBAL8 | LEVEL5 | -35176 | 0.018343887396 | NEAR_RATE | -5.68743896484 | -0.0112692713737 | -0.00629591941833 | False | False |
| jumpingjacks | val | GLOBAL8 | LEVEL5 | -35176 | 0.018343887396 | NEAR_RATE | -5.68743896484 | -0.0112692713737 | -0.00629591941833 | False | False |
| jumpingjacks | test | GLOBAL8 | LEVEL5 | -35176 | 0.018343887396 | NEAR_RATE | -5.64144515991 | -0.0112877488136 | -0.00597598496825 | False | False |
| jumpingjacks | test | GLOBAL8 | LEVEL5 | -35176 | 0.018343887396 | NEAR_RATE | -5.64144515991 | -0.0112877488136 | -0.00597598496825 | False | False |

NEAR_RATE означает relative gap≤0.05, только заранее заданную описательную близость размеров. Это не равенство качества и не EXACT_SAME_RATE. Padding, интерполяции и BD-rate нет.

## Reference и остаточные потери на test

| scene | state | bytes | PSNR | SSIM | LPIPS_STANDARD_VGG | PSNR_gap_R0 | SSIM_gap_R0 | LPIPS_excess_R0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mutant | GLOBAL8 | 1290969 | 38.6794548035 | 0.989810287952 | 0.0086723100394 | 5.30191040039 | 0.00655227899551 | 0.00289971055463 |
| mutant | LEVEL4 | 983199 | 27.4075508118 | 0.936605811119 | 0.0451673269272 | 16.5738143921 | 0.0597567558289 | 0.0393947274424 |
| mutant | LEVEL8 | 5109772 | 42.2892684937 | 0.995278000832 | 0.00628227507696 | 1.69209671021 | 0.00108456611633 | 0.000509675592184 |
| mutant | R0 | None | 43.9813652039 | 0.996362566948 | 0.00577259948477 | 0 | 0 | 0 |
| bouncingballs | GLOBAL8 | 2079602 | 38.8329849243 | 0.994528949261 | 0.0206007715315 | 3.65925598145 | 0.00128477811813 | 0.00278272293508 |
| bouncingballs | LEVEL5 | 1518977 | 28.1676177979 | 0.981005489826 | 0.0388390161097 | 14.3246231079 | 0.0148082375526 | 0.0210209675133 |
| bouncingballs | LEVEL8 | 4646269 | 41.0467948914 | 0.995457947254 | 0.0184065382928 | 1.4454460144 | 0.000355780124664 | 0.000588489696383 |
| bouncingballs | R0 | None | 42.4922409058 | 0.995813727379 | 0.0178180485964 | 0 | 0 | 0 |
| hellwarrior | GLOBAL8 | 1766497 | 42.2701873779 | 0.989561378956 | 0.0243978463113 | 0.570808410645 | 0.0012179017067 | 0.00159105844796 |
| hellwarrior | LEVEL4 | 903035 | 35.2917098999 | 0.963006198406 | 0.0540351979434 | 7.54928588867 | 0.0277730822563 | 0.0312284100801 |
| hellwarrior | LEVEL8 | 5594205 | 42.7731208801 | 0.990614116192 | 0.0230098571628 | 0.0678749084473 | 0.000165164470673 | 0.000203069299459 |
| hellwarrior | R0 | None | 42.8409957886 | 0.990779280663 | 0.0228067878634 | 0 | 0 | 0 |
| hook | GLOBAL8 | 1488765 | 37.1369247437 | 0.987501263618 | 0.0142304776236 | 1.88715362549 | 0.00308293104172 | 0.00232947990298 |
| hook | LEVEL4 | 1018650 | 26.2000675201 | 0.929758429527 | 0.0542153120041 | 12.824010849 | 0.0608257651329 | 0.0423143142834 |
| hook | LEVEL8 | 4941700 | 38.3380088806 | 0.989556014538 | 0.0124622741714 | 0.686069488525 | 0.00102818012238 | 0.000561276450753 |
| hook | R0 | None | 39.0240783691 | 0.99058419466 | 0.0119009977207 | 0 | 0 | 0 |
| jumpingjacks | GLOBAL8 | 1917587 | 38.4173469543 | 0.991524100304 | 0.0112760504708 | 0.828510284424 | 0.00092488527298 | 0.000625583343208 |
| jumpingjacks | LEVEL5 | 1882411 | 32.7759017944 | 0.98023635149 | 0.017252035439 | 6.46995544434 | 0.0122126340866 | 0.00660156831145 |
| jumpingjacks | LEVEL8 | 4902583 | 39.0337791443 | 0.992241978645 | 0.0107268560678 | 0.212078094482 | 0.000207006931305 | 7.63889402151e-05 |
| jumpingjacks | R0 | None | 39.2458572388 | 0.992448985577 | 0.0106504671276 | 0 | 0 | 0 |

## Ухудшения отдельных кадров

| scene | split | baseline | PSNR_worse_views | SSIM_worse_views | LPIPS_worse_views |
| --- | --- | --- | --- | --- | --- |
| mutant | val | GLOBAL8 | 20 | 20 | 20 |
| mutant | val | GLOBAL8 | 20 | 20 | 20 |
| mutant | test | GLOBAL8 | 20 | 20 | 20 |
| mutant | test | GLOBAL8 | 20 | 20 | 20 |
| bouncingballs | val | GLOBAL8 | 20 | 20 | 20 |
| bouncingballs | val | GLOBAL8 | 20 | 20 | 20 |
| bouncingballs | test | GLOBAL8 | 20 | 20 | 20 |
| bouncingballs | test | GLOBAL8 | 20 | 20 | 20 |
| hellwarrior | val | GLOBAL8 | 20 | 20 | 20 |
| hellwarrior | val | GLOBAL8 | 20 | 20 | 20 |
| hellwarrior | test | GLOBAL8 | 20 | 20 | 20 |
| hellwarrior | test | GLOBAL8 | 20 | 20 | 20 |
| hook | val | GLOBAL8 | 20 | 20 | 20 |
| hook | val | GLOBAL8 | 20 | 20 | 20 |
| hook | test | GLOBAL8 | 20 | 20 | 20 |
| hook | test | GLOBAL8 | 20 | 20 | 20 |
| jumpingjacks | val | GLOBAL8 | 20 | 20 | 20 |
| jumpingjacks | val | GLOBAL8 | 20 | 20 | 20 |
| jumpingjacks | test | GLOBAL8 | 20 | 20 | 20 |
| jumpingjacks | test | GLOBAL8 | 20 | 20 | 20 |

**mutant:** GLOBAL p8, LEVEL p4. Test ΔPSNR=-11.2719039917, ΔSSIM=-0.0532044768333, LPIPS improvement=-0.0364950168878. Δbytes=-307770; NOT_NEAR_RATE. LEVEL dominates по bytes и всем3 metrics: False; GLOBAL dominates: False. Меньший недозаполненный файл с худшим качеством не доказывает проигрыш при одинаковом фактическом rate.

**bouncingballs:** GLOBAL p8, LEVEL p5. Test ΔPSNR=-10.6653671265, ΔSSIM=-0.0135234594345, LPIPS improvement=-0.0182382445782. Δbytes=-560625; NOT_NEAR_RATE. LEVEL dominates по bytes и всем3 metrics: False; GLOBAL dominates: False. Меньший недозаполненный файл с худшим качеством не доказывает проигрыш при одинаковом фактическом rate.

**hellwarrior:** GLOBAL p8, LEVEL p4. Test ΔPSNR=-6.97847747803, ΔSSIM=-0.0265551805496, LPIPS improvement=-0.0296373516321. Δbytes=-863462; NOT_NEAR_RATE. LEVEL dominates по bytes и всем3 metrics: False; GLOBAL dominates: False. Меньший недозаполненный файл с худшим качеством не доказывает проигрыш при одинаковом фактическом rate.

**hook:** GLOBAL p8, LEVEL p4. Test ΔPSNR=-10.9368572235, ΔSSIM=-0.0577428340912, LPIPS improvement=-0.0399848343804. Δbytes=-470115; NOT_NEAR_RATE. LEVEL dominates по bytes и всем3 metrics: False; GLOBAL dominates: False. Меньший недозаполненный файл с худшим качеством не доказывает проигрыш при одинаковом фактическом rate.

**jumpingjacks:** GLOBAL p8, LEVEL p5. Test ΔPSNR=-5.64144515991, ΔSSIM=-0.0112877488136, LPIPS improvement=-0.00597598496825. Δbytes=-35176; NEAR_RATE. LEVEL dominates по bytes и всем3 metrics: False; GLOBAL dominates: False. Меньший недозаполненный файл с худшим качеством не доказывает проигрыш при одинаковом фактическом rate.

## Проверки, хранение и ресурсы

70 физических архивов,70 fresh-process decodes,1120 exact level arrays,точная metadata и canonical FP32,byte-identical rebuild. P8 регрессия обеих scopes, synthetic p2..8/constant/bounds/metadata/selection/ties/no-feasible/freeze/truncation checks. Decoder Python read audit — проверка реализации, не OS sandbox. Полные временные FP32/model копии удаляются только после PASS; архивы, manifest, reference hashes и decoder checks сохранены.

{
  "guarded_seconds": 2724.7157082330004,
  "peak_RSS_bytes": 4856143872,
  "peak_total_device_MiB": 3968
}

GPU использовался для render/metrics; quantization/compression/decode — CPU. Пик VRAM относится ко всему устройству, включая desktop. RSS — sampled process-tree sum и может повторно учитывать shared pages. ENCODE_DECODE_TIMING разделяет квантизацию, compression, cold process decode и internal decode. RESOURCES — wall subprocess; RENDER/METRICS содержат отдельные времена. Hashing/preparation и reporting — отдельно в PRESERVATION_BEFORE/FINAL и REPORT_COMPLETE.

## Допустимые выводы

Результат относится к конкретным пяти сценам, budget caps, DEFLATE и семействам p2…8. Это не независимая валидация, не глобальная оптимальность, не mixed precision и не новизна scalar quantization. Отдельные кадры коррелированы; статистическая значимость не утверждается. Улучшение против GLOBAL8 и против выбранного GLOBAL — разные сравнения даже если в этом запуске их выбор совпал. Знак каждой метрики сохранён без постфактум допусков.

Один следующий шаг: репликация неизменённого ограниченного протокола на заранее выбранном независимом checkpoint, чтобы проверить переносимость выявленного scope-specific эффекта и underfill. Здесь новая сцена не запускается.

## Воспроизведение

Windows: prepare.py в новом каталоге с исходниками. WSL pinned audit-env: launch.sh setup,rate,rate_seal,pilot,validation,freeze,test. Затем report.py и finalize.py. Пути нового run вlaunch.sh изменить до запуска; завершённые артефакты не перезаписывать. Состояние определяется STAGE_*.json, scene checkpoints и logs/*.json. Каждый test запуск проверяет общий freeze. Новых данных, обучения, p вне2…8, range fitting по картинкам или новых compressors нет.
