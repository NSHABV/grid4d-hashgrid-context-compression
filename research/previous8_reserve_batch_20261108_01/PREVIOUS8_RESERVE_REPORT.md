> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# PREVIOUS8: закрывающий пакет четырёх резервных сцен

TECHNICAL_COMPLETE = true. OLD_AUDIT_GATE_STATUS = WEAK_SIGNAL, unchanged. NOVELTY = NOT_ESTABLISHED.

CONTEXT_TRANSFER_SUMMARY = **ALL_FOUR_POSITIVE**. Это результат фиксированного scene-specific codec на четырёх ранее подготовленных checkpoints. Численные PMF переносом со старых сцен не являлись: они один раз fitted на symbols каждой новой сцены и полностью переданы внутри файла. Это не held-out prediction и не оценка вероятности универсального успеха.

## Физические файлы и собственный вклад контекста

| scene | mode | X_unchanged_B | replaced_payload_B | model_B | metadata_framing_B | total_B |
| --- | --- | --- | --- | --- | --- | --- |
| hook | X | 251592 | 1008292 | 0 | 5536 | 1265420 |
| hook | I | 251592 | 938204 | 3838 | 5575 | 1199209 |
| hook | P | 251592 | 921652 | 13254 | 5580 | 1192078 |
| jumpingjacks | X | 441496 | 1192220 | 0 | 5538 | 1639254 |
| jumpingjacks | I | 441496 | 1112108 | 3829 | 5581 | 1563014 |
| jumpingjacks | P | 441496 | 1096616 | 13830 | 5586 | 1557528 |
| mutant | X | 220472 | 855512 | 0 | 5533 | 1081517 |
| mutant | I | 220472 | 773708 | 3682 | 5568 | 1003430 |
| mutant | P | 220472 | 764128 | 12846 | 5573 | 1003019 |
| standup | X | 292912 | 1202204 | 0 | 5534 | 1500650 |
| standup | I | 292912 | 1117484 | 3805 | 5577 | 1419778 |
| standup | P | 292912 | 1096864 | 14058 | 5582 | 1409416 |

| scene | X_to_I_B | I_to_P_B | X_to_P_B | context_gain_percent_of_I | total_gain_percent_of_X | ACTUAL_3PCT_REFERENCE |
| --- | --- | --- | --- | --- | --- | --- |
| hook | 66211 | 7131 | 73342 | 0.594642 | 5.795862 | True |
| jumpingjacks | 76240 | 5486 | 81726 | 0.350989 | 4.985561 | True |
| mutant | 78087 | 411 | 78498 | 0.040960 | 7.258138 | True |
| standup | 80872 | 10362 | 91234 | 0.729832 | 6.079632 | True |

Все величины размеров — ACTUAL physical bytes. X/I/P реализуют один прежний G4DPREV1 формат. P всегда кодирует все L6–L10 без исключений и fallback;11 прочих XZ payloads побитно одинаковы. Общий spatial-файл содержит только xyz, не полную сцену Grid4D. Идентичность G_XP=G_XI+G_IP проверена в целых байтах. Собственный эффект контекста — I→P; выигрыш X→P нельзя полностью приписывать conditioning.

## Цена декодирования и fitting

| scene | pure_X_seconds | pure_I_seconds | pure_P_seconds | P_minus_I_decode_seconds | P_over_X_decode |
| --- | --- | --- | --- | --- | --- |
| hook | 0.065807 | 1.734839 | 2.714932 | 0.980093 | 41.255659 |
| jumpingjacks | 0.081037 | 1.724450 | 2.754752 | 1.030303 | 33.993929 |
| mutant | 0.060718 | 1.528226 | 2.676530 | 1.148303 | 44.081102 |
| standup | 0.074497 | 1.679000 | 2.513702 | 0.834702 | 33.742506 |

| scene | mode | read_codes_seconds | threshold_and_classes_seconds | histogram_seconds | PMF_normalization_seconds | serialization_seconds | XZ_compress_seconds | range_encode_seconds | end_to_end_seconds | pure_min_seconds | pure_max_seconds | cold_strict_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hook | X | 0.018129 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 3.235944 | 0.000000 | 3.267851 | 0.061543 | 0.067335 | 0.639485 |
| hook | I | 0.003201 | 0.010338 | 0.079158 | 0.002115 | 0.005358 | 0.805568 | 1.486310 | 2.620268 | 1.726150 | 1.736876 | 3.088613 |
| hook | P | 0.003270 | 0.162182 | 0.106719 | 0.007260 | 0.011064 | 0.836153 | 2.367290 | 3.750807 | 2.667764 | 2.849013 | 4.882526 |
| jumpingjacks | X | 0.019734 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 3.963439 | 0.000000 | 4.009095 | 0.076516 | 0.082829 | 0.629620 |
| jumpingjacks | I | 0.003744 | 0.009667 | 0.077824 | 0.001624 | 0.005444 | 1.565881 | 1.414728 | 3.329206 | 1.680754 | 1.771466 | 3.009768 |
| jumpingjacks | P | 0.004290 | 0.181633 | 0.107188 | 0.007476 | 0.012204 | 1.532911 | 2.285067 | 4.388688 | 2.600265 | 2.830935 | 4.586336 |
| mutant | X | 0.020063 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 3.152690 | 0.000000 | 3.186246 | 0.060324 | 0.064349 | 0.645031 |
| mutant | I | 0.003287 | 0.008499 | 0.078963 | 0.001794 | 0.004785 | 0.863180 | 1.386149 | 2.574250 | 1.404254 | 1.868890 | 2.846633 |
| mutant | P | 0.017335 | 0.217330 | 0.168838 | 0.012012 | 0.014303 | 0.858236 | 3.107993 | 4.814402 | 2.633965 | 2.690403 | 5.016907 |
| standup | X | 0.017098 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 3.052537 | 0.000000 | 3.083011 | 0.074401 | 0.074523 | 0.661247 |
| standup | I | 0.003395 | 0.010471 | 0.078365 | 0.002062 | 0.005801 | 0.784057 | 1.336752 | 2.439599 | 1.585454 | 1.704785 | 3.005305 |
| standup | P | 0.003659 | 0.172123 | 0.099274 | 0.007154 | 0.013585 | 0.725529 | 2.097292 | 3.368660 | 2.498186 | 2.779465 | 4.585211 |

Pure decode — один прогрев и три измеренных повторения, median и range, после каждого проверены полные symbols/hash. Models/CDF подготовлены до timed loop; timed loop включает causal lookup, range/XZ decode и запись output arrays. Strict re-encode/integrity исключены из pure, но включены в cold fresh-process decode. Файл PERFORMANCE.csv отдельно показывает strict verification, подготовку CDF, assembly, disk write и process lifetime peak RSS.

Encoder end-to-end каждого режима начинается с полного np.load одного и того же frozen uint8 файла (не mmap open), включает необходимый fitting, actual XZ compression и range encode, assembly и disk write. X действительно сжимает16уровней; I/P —11уровней, без cached compression в этом таймере. Только повтор для byte identity не refit модели. Source archive audit/decode выполнен отдельно один раз; FP32 checkpoint никогда не загружался. Внутренние таймеры вложены в E2E, не прибавлять их повторно. PMF normalization замерена профилированием неизменного frequencies; histogram time — время fit_masses минус normalization. Инструментирование имеет небольшой overhead. Дополнительный assigned_counts/CDF audit учтён в encoder_validation_seconds и E2E; это консервативное время проверочного encoder.

Размер выигрыша следует рассматривать вместе с latency. Отношение P/X не обещает практическую выгоду при любых требованиях хранения и задержки; backend не оптимизировался, parallelism не заявляется.

## Все уровневые вклады

| scene | level | X_payload_B | I_payload_B | I_model_B | P_payload_B | P_model_B | I_to_P_before_common_framing_B | X_to_P_before_common_framing_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hook | 6 | 196512 | 189580 | 834 | 185700 | 2965 | 1749 | 7847 |
| hook | 7 | 242692 | 223776 | 795 | 221168 | 3034 | 369 | 18490 |
| hook | 8 | 244056 | 222784 | 762 | 220484 | 3037 | 25 | 20535 |
| hook | 9 | 209172 | 189344 | 732 | 186268 | 2680 | 1128 | 20224 |
| hook | 10 | 115860 | 112720 | 715 | 108032 | 1538 | 3865 | 6290 |
| jumpingjacks | 6 | 214416 | 208224 | 816 | 204524 | 2803 | 1713 | 7089 |
| jumpingjacks | 7 | 264824 | 243164 | 786 | 241736 | 3121 | -907 | 19967 |
| jumpingjacks | 8 | 271708 | 247836 | 750 | 246084 | 2974 | -472 | 22650 |
| jumpingjacks | 9 | 249300 | 228764 | 744 | 226220 | 2554 | 734 | 20526 |
| jumpingjacks | 10 | 191972 | 184120 | 733 | 178052 | 2378 | 4423 | 11542 |
| mutant | 6 | 163476 | 151924 | 771 | 149976 | 2716 | 3 | 10784 |
| mutant | 7 | 200536 | 180768 | 759 | 179108 | 3121 | -702 | 18307 |
| mutant | 8 | 194996 | 172800 | 732 | 172096 | 2518 | -1082 | 20382 |
| mutant | 9 | 172432 | 154784 | 720 | 152960 | 2335 | 209 | 17137 |
| mutant | 10 | 124072 | 113432 | 700 | 109988 | 2156 | 1988 | 11928 |
| standup | 6 | 224980 | 216980 | 807 | 212060 | 2782 | 2945 | 10138 |
| standup | 7 | 275864 | 251252 | 777 | 249632 | 2899 | -502 | 23333 |
| standup | 8 | 279844 | 252884 | 759 | 251420 | 2788 | -565 | 25636 |
| standup | 9 | 249164 | 228700 | 729 | 224864 | 2968 | 1597 | 21332 |
| standup | 10 | 172352 | 167668 | 733 | 158888 | 2621 | 6892 | 10843 |

Уровневые разности выше не распределяют общий JSON/framing искусственно по уровням. Полный бюджет учитывает его отдельно. Все отрицательные строки оставлены в P, никакой новый selected-level hybrid не построен. MODEL_SIDE_COSTS.csv разбивает PMF/thresholds/mapping/specification/framing реальных envelopes; PER_CHANNEL_PAYLOAD.csv даёт ideal lengths, actual payload и residual для каждого range channel. Residual включает finite range arithmetic, termination/word alignment, не новую зависимость и не ошибку PMF.

## Шесть сцен: development отдельно от reserve

| scene | group | X_B | I_B | P_B | X_to_I_B | I_to_P_B | X_to_P_B | context_gain_percent_of_I | total_gain_percent_of_X | pure_X_seconds | pure_I_seconds | pure_P_seconds | timing_kind |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hellwarrior | DEVELOPMENT | 1507177 | 1424481 | 1417710 | 82696 | 6771 | 89467 | 0.475331 | 5.936065 | 0.060159 | 1.195225 | 2.207923 | historical_single_measurement |
| bouncingballs | DEVELOPMENT | 1752624 | 1734741 | 1700458 | 17883 | 34283 | 52166 | 1.976260 | 2.976451 | 0.065105 | 1.312507 | 2.206981 | historical_single_measurement |
| hook | RESERVE_FOR_PREVIOUS8 | 1265420 | 1199209 | 1192078 | 66211 | 7131 | 73342 | 0.594642 | 5.795862 | 0.065807 | 1.734839 | 2.714932 | median3_after1warmup |
| jumpingjacks | RESERVE_FOR_PREVIOUS8 | 1639254 | 1563014 | 1557528 | 76240 | 5486 | 81726 | 0.350989 | 4.985561 | 0.081037 | 1.724450 | 2.754752 | median3_after1warmup |
| mutant | RESERVE_FOR_PREVIOUS8 | 1081517 | 1003430 | 1003019 | 78087 | 411 | 78498 | 0.040960 | 7.258138 | 0.060718 | 1.528226 | 2.676530 | median3_after1warmup |
| standup | RESERVE_FOR_PREVIOUS8 | 1500650 | 1419778 | 1409416 | 80872 | 10362 | 91234 | 0.729832 | 6.079632 | 0.074497 | 1.679000 | 2.513702 | median3_after1warmup |

Development размеры взяты из завершённых физических файлов без нового поиска. Их timing — прежнее одиночное измерение; reserve timing — median3 после прогрева. Эти времена не объединяются в одну статистику. Pooled reserve rates ниже суммируют байты, не сцены или независимые наблюдения; отрицательная сцена, если она есть, остаётся явной в основной таблице.

| gain | positive | zero | negative | minimum_bytes | median_bytes | maximum_bytes | minimum_percent | median_percent | maximum_percent | pooled_percent |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I_to_P_B | 4 | 0 | 0 | 411 | 6308.500000 | 10362 | 0.040960 | 0.472815 | 0.729832 | 0.451071 |
| X_to_P_B | 4 | 0 | 0 | 73342 | 80112.000000 | 91234 | 4.985561 | 5.937747 | 7.258138 | 5.919617 |

## Происхождение и ограничение независимости

hook/jumpingjacks — прежние sealed ZLIB8.npz полного spatial audit; mutant — GLOBAL8.zip из quantizer_scope_comparison; standup — G8.zip с pmap=[8]*16 и declared_changed_levels=[], не precision-exchange состояние. SHA archives, level arrays, full symbols, canonical reconstruction и checkpoint provenance сверены с прежними protected manifests и проверками. Все имеют16уровней,2канала,6098108rows. Полные значения и пути — INPUT_MANIFEST.json. Для mutant/standup metadata перенесена в прежнюю полную структуру без сокращения headers: архитектура проверена по saved cfg/actual offsets, заменены scene hashes/checkpoint/global range. Canonical dequantizer неизменен и результат совпал с прежним хешем.

По доступным отчётам/протоколам/freeze с PREVIOUS8 найден только development-аудит, его attribution и двухсценный actual prototype. Четыре текущие сцены ранее перечислены как резерв для PREVIOUS8; их результатов для выбора bins/reset/levels не найдено. Это ограничение доступной provenance, не доказательство отсутствия любого незафиксированного анализа. Сцены уже использовались для quantization/H4/других исследований проекта; поэтому это reserve-for-PREVIOUS8, а не совершенно новый независимый benchmark. Параметры файла fitted по всей новой сцене и оплачены; вывод не является переносом неизменных численных вероятностей или held-out generalization.

## Заморозка и проверки

До нового fitting сохранены PREREGISTERED_PROTOCOL.json, INPUT_MANIFEST.json и FROZEN_METHOD.json. Frozen codec.py, helpers и public dependencies не менялись. Regression на2development-сценах:20model envelopes, точные counts/assigned_counts/masses/thresholds/bytes — PASS. quantile eligible subset взят из прежнего fit_edges; start PMF использует full marginal,128start positions на канал/уровень, без двойной оплаты. Alpha1, stable ties, positive masses sum65536, shortest прежний transport и IID без неиспользуемых порогов сохранены.

Каждая новая PMF проверена через все256 initial encoder intervals: CDF24=CDF16×256, Categorical(perfect=True). Causal decoder выбирает модель только по decoded prefix; LUT из transmitted thresholds. Stream/reset/format неизменны. Один маленький pilot прошёл; прежние synthetic/causality/corruption evidence сохранены с hashes. Добавлены только2malformed-model tests на сцену.

Все12архивов прошли fresh-process decode оригинальным frozen codec.py. Python read audit после загрузки public code разрешал только один переданный bin; это не OS sandbox. Внешний validator проверил все symbols, canonical reconstruction, shape/offsets и decoder context IDs; повторное кодирование byte-identical. Никаких рендеров/PSNR, новых quantizers, обучения или GPU. Превышений1800s/2GiB не было.

Сохранность проверяет один итоговый audit с точным списком PROTECTED_FILES.json: прежний protected ledger плюс seals headroom/attribution/actual prototype и использованные inputs/dependencies. Это заявленное покрытие, не обещание проверки каждого произвольного файла диска. FINAL_VALIDATION.json фиксирует результат после завершения audit.

## Закрытие

Результат текущей фиксированной конфигурации ограничен перечисленными checkpoints и GLOBAL8. Нельзя объявлять научную новизну PREVIOUS8, пространственное соседство hash-slot indices, универсальное преимущество или число symbols числом независимых опытов. Actual3% — информационная колонка, не новая оптимизация и не пересмотр WEAK_SIGNAL. Дальнейший поиск, обучение новых сцен, замена контекста и оптимизация не запускаются.

Воспроизведение: native pinned Python3.12.14, NumPy1.26.4, constriction0.4.2. В новом уникальном каталоге: `batch.py prepare`, `batch.py regression`, `verify.py pilot`; `batch.py scene hook`, затем jumpingjacks, mutant, standup; `verify.py tests`; `report.py generate`; `verify.py preserve`; `report.py finalize`. Decoder оригинальный `research/frozen_previous8_actual_20261108_01/codec.py archive.bin fresh_output`. У каждого scene/mode сохранены command/stdout/stderr и COMPLETE точки. Source/runtime hashes и public source copies — FROZEN_METHOD.json/RUNNER_FREEZE.json/source_snapshot. Старые reports и containers read-only.

**FROZEN_PREVIOUS8_VALIDATION_BATCH_CLOSED**
