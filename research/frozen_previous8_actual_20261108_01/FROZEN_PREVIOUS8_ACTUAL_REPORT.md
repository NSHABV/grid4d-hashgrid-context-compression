> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Frozen PREVIOUS8: bounded actual spatial bitstreams

OLD_AUDIT_GATE_STATUS = WEAK_SIGNAL (unchanged). Новый эксперимент разрешён отдельно. TECHNICAL = PASS: шесть standalone spatial archives точно восстанавливают GLOBAL8 symbols и canonical dequantization. GENERALIZATION = NOT_TESTED: две development-сцены. NOVELTY = NOT_ESTABLISHED.

## Физические размеры и атрибуция

Все байты в следующих таблицах — ACTUAL filesystem sizes, без фиктивного резерва. X использует XZ6 на всех16 уровнях; I/P заменяют строго все L6–L10. Остальные11 compressed sections побитно одинаковы. Это xyz archive, не полная самостоятельная сцена Grid4D.

| scene | mode | unchanged_XZ_B | replaced_payload_B | model_side_B | metadata_framing_B | total_filesystem_B |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | X | 536904 | 1210180 | 0 | 5540 | 1752624 |
| bouncingballs | I | 536904 | 1188220 | 4036 | 5581 | 1734741 |
| bouncingballs | P | 536904 | 1142572 | 15396 | 5586 | 1700458 |
| hellwarrior | X | 284500 | 1217144 | 0 | 5533 | 1507177 |
| hellwarrior | I | 284500 | 1130580 | 3826 | 5575 | 1424481 |
| hellwarrior | P | 284500 | 1111608 | 16023 | 5579 | 1417710 |

| scene | X_to_I_B | I_to_P_B | X_to_P_B | I_to_P_percent_of_full_I | X_to_P_percent_of_full_X | ACTUAL_3PCT_REFERENCE |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 17883 | 34283 | 52166 | 1.9762604331136464 | 2.9764513095792364 | False |
| hellwarrior | 82696 | 6771 | 89467 | 0.47533101529609734 | 5.936064576356991 | True |

Сумма секций равна размеру каждого файла точно. X→P = X→I + I→P проверено целочисленно. Собственный эффект conditioning — только I→P. На hellwarrior IID объясняет основную часть экономии. На bouncingballs вклад PREVIOUS8 значительно больше относительно IID, чем на hellwarrior. Это не процент сжатия всего Grid4D и не выигрыш DEFLATE→XZ.

## Сравнение с прежним прогнозом

| scene | old_predicted_P_vs_XZ_B | actual_P_vs_X_B | difference_B | range_P_minus_ideal_B | old_predicted_P_vs_IID_B | actual_P_vs_I_B | X_new_vs_old_wrapper_B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 48138.12961699022 | 52166 | 4027.87038300978 | 102.12961699011794 | 34286.37512501143 | 34283 | 2349 |
| hellwarrior | 85438.86921254732 | 89467 | 4028.130787452683 | 101.86921254712797 | 6774.98928413121 | 6771 | 2343 |

Прогноз сохранён без исправлений. Отличие actual X→P от прежнего прогноза = 4416 − 240 + (framing_X−framing_P) − (payload_P−ideal_P). Здесь4416 — прежний резерв, который заменён реальными расходами,240 — пять старых48B descriptors в заменяемых sections. Разность actual I→P и прогнозируемого conditioning = (payload_I−ideal_I) − (payload_P−ideal_P) + (framing_I−framing_P). Обе формулы проверены с допуском1e−6B. Wrapper X отличается от старого XZ только metadata/framing; payload всех16 уровней идентичен.

PER_CHANNEL_PAYLOAD.csv содержит40 строк (2сцены×2range-режима×5уровней×2канала): прежнюю ideal length, physical payload, residual, pure encode и termination/export time. Payload кратен4B: engine возвращает32-bit words. Residual совместно включает конечную range arithmetic, termination и word alignment; отдельно приписывать его части без недоступного внутреннего bit-level счётчика было бы необоснованно. Model/CDF mismatch не включён в residual: все CDF точно проверены.

## Engine и причинность

Существующий constriction0.4.2 RangeEncoder/RangeDecoder поддерживает смену модели между symbols при сохранении состояния. Старый perfect=False немного меняет CDF: сохранён контрпример в ENGINE_PROBE.json. Использован существующий API Categorical(perfect=True), без изменений arithmetic core. Проверены все256 symbol intervals каждой из200 frozen PMF rows: внутренние границы равны uint16 CDF×256 при precision24, через публичный pos() начального состояния RangeEncoder. Это плановый causal adapter с иной настройкой существующей модели для точного сохранения вероятностей; прежние decoders не изменены.

На каждом уровне два непрерывных streams — channel0, затем channel1. PREVIOUS8 на первом slot каждого4096-блока использует сохранённую marginal start PMF (128 starts/канал/уровень); иначе previous symbol того же канала. LUT заранее строится исключительно из transmitted thresholds; model objects кешируются. Reset контекста не закрывает stream. Transport order зафиксирован контейнером; historical descriptive code_order в неизменном dry envelope не используется как транспортный порядок. Semantics PMF/context/reset сохранены. IID также использует два streams. Параллельное декодирование не реализовано.

## Входы и проверки

GLOBAL8 codes из прежних ZLIB8_decoded/symbols.npy; полный SHA и hashes всех16 уровней проверены. Checkpoints не загружались. PMF и thresholds full_scene не fitted заново. IID side4036/3826B считался по физическим trimmed envelopes; PREVIOUS8 bytes совпали с прежними. Независимый пересчёт assigned_counts совпал с архивами; первый канал/starts не оплачиваются дважды. Source/runtime и hashes сохранены.

Synthetic lengths1,4095,4096,4097,8193, неодинаковые каналы, extreme/rare/constant values, repeated thresholds, boundary resets, causal target/future mutation, oracle class IDs, repeat bytes — PASS. Pilot разрешил полный запуск в пределах1800s/2GiB. Малые fixtures используют те же сохранённые массы; изменённые synthetic thresholds не применялись к сценам.

Каждый из6 файлов декодирован в fresh native Python process. После импорта публичного кода аудит файловых чтений разрешал только переданный bin; PMF, reference arrays, oldbins и checkpoint decoder не читал. Это Python-level audit, не OS sandbox для произвольного native кода. Внешний validator сравнил все symbols обоих каналов, все16уровней, canonical dequantization hashes, decoder-derived IDs с независимым векторным oracle. Повторный encode byte-identical. Strict decode делает canonical re-encode range payload для отклонения лишних/truncated streams.

12 malformed tests охватывают counts/lengths, missing PMF, invalid masses/mapping/threshold, unknown contract, truncated/extra range payload и integrity. XZ11 sections между X/I/P и X16 sections против прежнего baseline совпали побитно. Рендеров нет: exact GLOBAL8 reconstruction не является lossless восстановлением исходного FP32 checkpoint.

## Производительность

| scene | mode | frozen_model_load_seconds | model_prepare_seconds | pure_encode_seconds | pure_decode_seconds | decode_strict_checks_seconds | fresh_decode_cold_seconds | encoder_peak_RSS | decoder_peak_RSS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | X | 0 | 0 | 0 | 0.06510490004438907 | 0.12752890001866035 | 0.6462210000026971 | 80146432 | 69332992 |
| bouncingballs | I | 0.0020320999901741743 | 0.0035244000027887523 | 2.1820190999860642 | 1.3125071999966167 | 1.1448551999928895 | 2.9306140999979107 | 81289216 | 72171520 |
| bouncingballs | P | 0.0025243000127375126 | 0.01458870001079049 | 3.6812733000406297 | 2.2069809999666177 | 2.0318108999927063 | 4.708448599994881 | 82776064 | 71589888 |
| hellwarrior | X | 0 | 0 | 0 | 0.060158899970701896 | 0.12345829998957925 | 0.6093965000036405 | 82776064 | 69156864 |
| hellwarrior | I | 0.0020949999889126047 | 0.003986600000644103 | 2.7190463000151794 | 1.19522539996251 | 1.067012600004091 | 2.7314581999962684 | 82776064 | 70561792 |
| hellwarrior | P | 0.0022089000267442316 | 0.01356110000051558 | 3.724641100037843 | 2.2079231000388972 | 2.0301104000245687 | 4.706614199996693 | 82776064 | 71151616 |

PERFORMANCE.csv дополнительно разделяет file IO, parse, assembly/integrity и startup+uninstrumented residual. Pure encode включает финальный export слов; его отдельно измеренная малая часть есть в PER_CHANNEL_PAYLOAD.csv. X pure encode=0: разрешённое копирование готовых XZ sections, не benchmark нового XZ compression. Frozen PMF fitting time не входит в encode. Cold decode включает model preparation, pure decode, strict re-encode, IO и startup; компоненты не складывать с cold повторно. Strict checks показывают стоимость измерительного валидатора отдельно от pure decoder. Peak RSS — per-process lifetime high-water, не дополнительная stage memory. CPU-only pinned Python3.12.14/NumPy1.26.4/constriction0.4.2. Ускорение GPU и parallelism не заявляются.

## Решения и воспроизведение

Actual gain и actual3% — отдельные наблюдения, не пересмотр прежнего WEAK_SIGNAL. PREVIOUS8 выбран заранее, на CHANNEL8 не переключались. Выигрыш conditioning положителен на обеих development-сценах, но неодинаков; generalization и научная новизна не установлены. Проверка резервных сцен, улучшение модели и дополнительный аудит не назначаются. Измерительный этап закрыт, далее STOP.

Команды pinned Python: `run.py prepare`, `run.py synthetic`, `run.py scenes`, `finish.py tests`, `finish.py summarize`, `finish.py preserve`, `finish.py report`, `finish.py finalize`. Decoder: `codec.py archive.bin fresh_output_dir`. Для повторения — новый уникальный каталог; scripts фиксируют ROOT относительно research/run. Decoder public dependencies: этот codec.py, headroom model_side.py/baselines.py/input_sources.py и импортируемые public helpers, NumPy и constriction. Data sources нужны только encoder/validator. Все записи exclusive, старые runs read-only. Source snapshots и manifests позволяют проверить точные версии; FINAL_VALIDATION.json фиксирует завершённый preservation audit.

### Точность разбиения времени

`source_array_load_seconds` измеряет открытие frozen mmap, а не полное чтение всех pages. Чтение исходного XZ-архива и входной полный hash не имели отдельного таймера в scene runner; их время не выдано за pure encode. Поэтому таблица не является полной профилировкой всех действий production encoder. Model-file IO и file write измерены отдельно; decoder IO измерено полностью в его fresh process. Отдельный startup не изолирован от небольшого Python orchestration: колонка явно названа startup_and_uninstrumented_seconds. Эти ограничения не влияют на физические размеры и exact decode. Предыдущий вариант текста сохранён и проверен побитно в REPORT_DRAFT_BEFORE_TIMING_CLARIFICATION.md.
