> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Заключительный аудит атрибуции выигрыша GLOBAL8 Grid4D

Статусы: **EXISTING_GATE_STATUS = WEAK_SIGNAL; ACTUAL_CONTEXTUAL_CODEC = NOT_IMPLEMENTED; PROTOTYPE_AUTHORIZED = false.** Выбранным семейством остаётся PREVIOUS8. Это закрывающий анализ готовых данных, без нового fitting, splits, shuffle, обучения, квантования или entropy payload.

## Данные и виды измерений

Только прежние development checkpoints bouncingballs и hellwarrior, frozen GLOBAL8. Полный spatial tensor каждой сцены: uint8[6098108,2]. Для CHANNEL8/PREVIOUS8 взяты все L6–L10: 5×524288×2=5242880 symbols. Для Mean8 и всех его контролей — все L7/L8: 2097152 symbols. Пустые/редкие allocated slots не исключены. Checkpoint не загружался; достаточно сохранённых full_scene counts, assigned_counts и integer masses. Пропусков данных нет, восстанавливать отсутствующие PMF не потребовалось.

ACTUAL_FILE — физические стандартные файлы. ACTUAL_DRY_MODEL — реально сериализованные модели, без entropy payload. FULL_FIT_IDEAL — информационная длина по полным PMF. HELDOUT_ESTIMATE — прежняя оценка fit-only PMF на check. FULL_GRID_PROJECTION — смесь actual незаменённых sections и estimated заменяемых sections. Эти типы не взаимозаменяемы.

## Что уже доказано физическими файлами

| scene | type | DEFLATE6_slot_B | XZ6_slot_B | compressor_saving_B | historical_NPZ_B | historical_minus_same_compressor_raw_wrapper_B |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | ACTUAL_FILE | 2077434.00 | 1750275.00 | 327159.00 | 2079708.00 | 2274.00 |
| hellwarrior | ACTUAL_FILE | 1764798.00 | 1504834.00 | 259964.00 | 1766604.00 | 1806.00 |

Смена DEFLATE6→XZ6 при том же slot-major layout дала 327159/259964 B. Это результат стандартного компрессора, не нового HashGrid-контекста и не научная новизна. Разности historical NPZ→diagnostic raw DEFLATE — 2274/1806 B — относятся к представлению/упаковке (включая NPY headers внутри compressed sections), а не к смене компрессора. Сами compressors не запускались повторно; размер/SHA файлов проверен по manifests, прежний exact decode остаётся основанием корректности.

## Оплаченные контрольные модели

Прежние masses сохранены без изменения. Проверен их точный пересчёт существующим frequencies(counts): alpha=1, положительные массы, сумма65536. Payload независимо пересчитан как sum(assigned_counts * -log2(mass/65536))/8. Для PREVIOUS8 использованы именно assigned_counts: start PMF обучена на полной marginal, но start symbols оплачиваются только128раз на канал/уровень. Оба канала CHANNEL8 включены; channel0 IID учитывается один раз.

Для IID и Geometry4 удалены только неиспользуемые threshold_rule и пустой именованный edges array; передан пустой словарь порогов (2B). Существующий serializer и формат не изменены. Это уменьшает side на98B на уровень; поэтому контроль L6–L10 дешевле прежнего на490B, L7/L8 на196B. Mapping, specification, checksum и framing полностью оплачены. Прежние и новые side lengths есть в CONTROL_MODEL_COSTS.csv; новые dry control bytes сохранены в control_models/. Выбран кратчайший из прежних трёх transports; все случаи — sparse_default_u16. Context bytes сохранены byte-identically. Старые held-out числа не менялись и используют прежний side accounting.

| scene | levels | payload_type | IID_payload_B | side_type | IID_side_B | S_IID_paid_B | projection_type | Bhat_IID_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | 6,7,8,9,10 | FULL_FIT_IDEAL | 1188116.25 | ACTUAL_DRY_MODEL | 4036.00 | 1192152.25 | FULL_GRID_PROJECTION | 1736423.25 |
| bouncingballs | 7,8 | FULL_FIT_IDEAL | 588533.86 | ACTUAL_DRY_MODEL | 1677.00 | 590210.86 | FULL_GRID_PROJECTION | 1730901.86 |
| hellwarrior | 6,7,8,9,10 | FULL_FIT_IDEAL | 1130478.12 | ACTUAL_DRY_MODEL | 3826.00 | 1134304.12 | FULL_GRID_PROJECTION | 1426170.12 |
| hellwarrior | 7,8 | FULL_FIT_IDEAL | 498590.98 | ACTUAL_DRY_MODEL | 1551.00 | 500141.98 | FULL_GRID_PROJECTION | 1469143.98 |

S_IID — стоимость заменяемых уровней, не всего spatial-файла. Bhat_IID включает остальные actual XZ sections и общий резерв. Empirical H0 не подставлялась вместо конечных PMF и не трактуется как универсальная нижняя граница.

## Декомпозиция полного прогноза

Для каждого семейства отдельно: A=полный XZ, R=actual заменяемые sections, S=ideal payload+measured side. Bhat=A−R+S+F. F=4416B для L6–L10, F=4224B для L7/L8. Резерв — объявленный инженерный бюджет, не измеренный overhead и не доказанная верхняя граница. Он одинаков вдоль каждой цепочки. Shared quantizer/geometry metadata и coarse prerequisite не добавляются повторно; контекстные specification/thresholds/mapping оплачены в S. Семейства не складываются в hybrid.

Все следующие gains — **FULL_GRID_PROJECTION**, основанная на FULL_FIT_IDEAL и ACTUAL_DRY_MODEL. Положительный знак означает экономию.

| scene | family | Gain_XZ_to_IID_B | Gain_IID_to_Geometry_B | Gain_control_to_context_B | Gain_XZ_to_context_B |
| --- | --- | --- | --- | --- | --- |
| bouncingballs | CHANNEL8 | 13851.75 | 0.00 | 28632.07 | 42483.82 |
| bouncingballs | PREVIOUS8 | 13851.75 | 0.00 | 34286.38 | 48138.13 |
| bouncingballs | MEAN8 | 19373.14 | -1722.62 | -3714.75 | 13935.78 |
| hellwarrior | CHANNEL8 | 78663.88 | 0.00 | 20554.74 | 99218.62 |
| hellwarrior | PREVIOUS8 | 78663.88 | 0.00 | 6774.99 | 85438.87 |
| hellwarrior | MEAN8 | 35690.02 | -1830.62 | -2605.56 | 31253.84 |

Для CHANNEL8/PREVIOUS8: общий выигрыш = XZ→IID + IID→context. Для Mean8: XZ→IID + IID→Geometry4 + Geometry4→Mean8. Равенства проверены с заранее заданным абсолютным допуском1e−6B. Колонка Geometry равна0 для не-spatial семейств. Суммы после округления до сотых могут отличаться на0.01B.

У PREVIOUS8 вклад conditioning составляет34286.38B на bouncingballs и6774.99B на hellwarrior: около71.23% и7.93% соответствующего полного прогноза. Простая IID-модель объясняет около28.77% и92.07%. Поэтому общий выигрыш относительно XZ нельзя целиком приписывать контексту.

На L7/L8 Geometry4 сама дороже IID после side, а Mean8 ещё дороже Geometry4. Положительный итог Mean8 относительно XZ объясняется исходным IID-прогнозом, не пользой coarse features.

## Payload против цены conditioning

Все payload differences ниже — FULL_FIT_IDEAL; дополнительные side sections — ACTUAL_DRY_MODEL. Контроль IID для CHANNEL8/PREVIOUS8, Geometry4 для Mean8.

| scene | family | conditional_payload_reduction_B | additional_pmf_bytes | additional_threshold_bytes | additional_mapping_bytes | additional_specification_bytes | additional_framing_bytes | additional_side_B | Gain_control_to_context_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | CHANNEL8 | 33579.07 | 4007.00 | 340.00 | 35.00 | 565.00 | 0.00 | 4947.00 | 28632.07 |
| bouncingballs | PREVIOUS8 | 45646.38 | 9440.00 | 640.00 | 80.00 | 1200.00 | 0.00 | 11360.00 | 34286.38 |
| bouncingballs | MEAN8 | -396.75 | 2508.00 | 256.00 | 24.00 | 530.00 | 0.00 | 3318.00 | -3714.75 |
| hellwarrior | CHANNEL8 | 25858.74 | 4364.00 | 340.00 | 35.00 | 565.00 | 0.00 | 5304.00 | 20554.74 |
| hellwarrior | PREVIOUS8 | 18971.99 | 10277.00 | 640.00 | 80.00 | 1200.00 | 0.00 | 12197.00 | 6774.99 |
| hellwarrior | MEAN8 | -193.56 | 1602.00 | 256.00 | 24.00 | 530.00 | 0.00 | 2412.00 | -2605.56 |

PREVIOUS8 уменьшает ideal payload на45646.38/18971.99B, но дополнительные модели и metadata стоят11360/12197B. Для Mean8 даже ideal payload выше Geometry4 на396.75/193.56B; отрицательный net не объясняется одним overhead.

## Full-fit и прежний held-out — разные оценки

| scene | family | seed | heldout_type | check_CE | check_paid_extrapolated_gain_B | full_fit_type | fullfit_incremental_gain_B | projection_type | fullgrid_gain_vs_XZ_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | CHANNEL8 | 0.00 | HELDOUT_ESTIMATE | 1.76 | 28986.24 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 28632.07 | FULL_GRID_PROJECTION | 42483.82 |
| bouncingballs | CHANNEL8 | 1.00 | HELDOUT_ESTIMATE | 1.75 | 29257.45 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 28632.07 | FULL_GRID_PROJECTION | 42483.82 |
| bouncingballs | CHANNEL8 | 2.00 | HELDOUT_ESTIMATE | 1.75 | 28678.11 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 28632.07 | FULL_GRID_PROJECTION | 42483.82 |
| bouncingballs | PREVIOUS8 | 0.00 | HELDOUT_ESTIMATE | 1.74 | 33619.67 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 34286.38 | FULL_GRID_PROJECTION | 48138.13 |
| bouncingballs | PREVIOUS8 | 1.00 | HELDOUT_ESTIMATE | 1.74 | 33533.22 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 34286.38 | FULL_GRID_PROJECTION | 48138.13 |
| bouncingballs | PREVIOUS8 | 2.00 | HELDOUT_ESTIMATE | 1.74 | 32654.72 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 34286.38 | FULL_GRID_PROJECTION | 48138.13 |
| bouncingballs | MEAN8 | 0.00 | HELDOUT_ESTIMATE | 2.24 | -14249.70 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | -3714.75 | FULL_GRID_PROJECTION | 13935.78 |
| bouncingballs | MEAN8 | 1.00 | HELDOUT_ESTIMATE | 2.25 | -14586.09 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | -3714.75 | FULL_GRID_PROJECTION | 13935.78 |
| bouncingballs | MEAN8 | 2.00 | HELDOUT_ESTIMATE | 2.25 | -14395.00 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | -3714.75 | FULL_GRID_PROJECTION | 13935.78 |
| hellwarrior | CHANNEL8 | 0.00 | HELDOUT_ESTIMATE | 1.68 | 22314.80 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 20554.74 | FULL_GRID_PROJECTION | 99218.62 |
| hellwarrior | CHANNEL8 | 1.00 | HELDOUT_ESTIMATE | 1.68 | 22736.30 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 20554.74 | FULL_GRID_PROJECTION | 99218.62 |
| hellwarrior | CHANNEL8 | 2.00 | HELDOUT_ESTIMATE | 1.69 | 22299.70 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 20554.74 | FULL_GRID_PROJECTION | 99218.62 |
| hellwarrior | PREVIOUS8 | 0.00 | HELDOUT_ESTIMATE | 1.69 | 9468.46 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 6774.99 | FULL_GRID_PROJECTION | 85438.87 |
| hellwarrior | PREVIOUS8 | 1.00 | HELDOUT_ESTIMATE | 1.69 | 9502.23 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 6774.99 | FULL_GRID_PROJECTION | 85438.87 |
| hellwarrior | PREVIOUS8 | 2.00 | HELDOUT_ESTIMATE | 1.70 | 8970.72 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | 6774.99 | FULL_GRID_PROJECTION | 85438.87 |
| hellwarrior | MEAN8 | 0.00 | HELDOUT_ESTIMATE | 1.91 | -13549.43 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | -2605.56 | FULL_GRID_PROJECTION | 31253.84 |
| hellwarrior | MEAN8 | 1.00 | HELDOUT_ESTIMATE | 1.91 | -13764.74 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | -2605.56 | FULL_GRID_PROJECTION | 31253.84 |
| hellwarrior | MEAN8 | 2.00 | HELDOUT_ESTIMATE | 1.91 | -13783.86 | FULL_FIT_IDEAL_PLUS_ACTUAL_DRY_MODEL | -2605.56 | FULL_GRID_PROJECTION | 31253.84 |

Новые held-out вычисления не выполнялись: сводка копирует прежние check rows, агрегируя все заранее заданные levels. PMF/thresholds там fitted только на83 fit blocks, check содержит25 блоков; оба канала вместе. Full-fit использует все symbols и другие PMF/thresholds. Расхождения ожидаемы из-за fitting на subset против всей сцены, finite masses, разного sparse side и указанного удаления98B лишних контрольных полей. Held-out paid gain не вычитался из full-fit projection. Полные модели не доказывают обобщение.

Сохранённый shuffled control PREVIOUS8: правильное соответствие лучше shuffle в6/6 scene×seed, после shuffle положительный gain над IID остаётся в0/6. Новых перестановок не делалось. Это поддерживает полезность соответствия для фиксированного предиктора, но не доказывает меньший actual bitstream и не является тестом статистической значимости.

## Gate остаётся прежним

| scene | type | saving_B | saving_percent | required_3percent_B | surplus_vs_gate_B | measured_model_side_B | declared_reserve_B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs | FULL_GRID_PROJECTION | 48138.13 | 2.75 | 52508.25 | -4370.12 | 15396.00 | 4416.00 |
| hellwarrior | FULL_GRID_PROJECTION | 85438.87 | 5.68 | 45145.02 | 40293.85 | 16023.00 | 4416.00 |

bouncingballs недостаёт4370.120383B до3%; hellwarrior превышает этот уровень на40293.849213B. Порог требуется на обеих сценах. Резерв4416B не удалялся. WEAK_SIGNAL и выбор PREVIOUS8 не пересматриваются; более высокий результат CHANNEL8 на hellwarrior не основание переключить победителя после check.

## Научный вывод для НИР

Допустимая формулировка: «На двух development-сценах с фиксированными GLOBAL8 symbols простые внутритабличные зависимости дают дополнительное уменьшение оценённой длины относительно оплаченной IID-модели. Для заранее выбранного PREVIOUS8 full-fit вклад conditioning составил34.29KB и6.77KB. На второй сцене основная часть прогноза относительно XZ объясняется IID-кодированием. Mean8 на L7/L8 не даёт добавочного выигрыша сверх Geometry4. Физический контекстный bitstream не реализован, а общий engineering gate не пройден».

PREVIOUS8 использует порядок хранения hash slots и доступный decoded prefix. Соседний индекс таблицы не доказывает пространственное соседство. Mean8 использует официальный пространственный prior через eligible vertices и coarse lookup; это иной механизм. CHANNEL8 использует значение первого канала того же slot, уже включённого в кодируемые данные.

Нельзя заявлять: новизну общего принципа PREVIOUS8; экономию всего Grid4D; фактические contextual bytes; независимую межсценовую generalization; независимость hash slots или статистическую значимость трёх seeds; бесполезность любого contextual compression. Две сцены уже использовались при разработке, а модели и точность фиксированы.

Заключительное решение: закрыть текущий аудит с WEAK_SIGNAL. Ветку Mean8 в данном scope не спасать подбором bins. Вклад внутритабличного conditioning измеримо положителен как прогноз, однако actual proof отсутствует. Возможный bounded prototype требует отдельного решения пользователя; в этом задании он не разрешён и не запускается.

## Проверки и воспроизведение

Проверены source SHA256, scene/level/phase, masses>0 и sum65536, точный frequencies replay, одинаковые marginal symbol counts всех моделей, весь allocated scope обоих каналов,128 start symbols каждого канала PREVIOUS8, канальная IID-часть CHANNEL8, serializer roundtrip и shortest transport, точные суммы side sections, исходные context projections и algebra identities. CONTINUATION и результаты не затрагивают прежние runs. Статус единственного итогового preservation audit и хеш отчёта находятся в FINAL_VALIDATION.json.

Одна исправленная ошибка сводного скрипта: колонка channel в старом CSV использует `total`, а не `both`. Основные расчёты уже были сохранены и не повторялись; продолжен только экспорт held-out summary. Кодек, PMF и научный протокол не менялись. CSV_SCHEMA_NOTE.txt и исходный вариант audit_before_csv_label_fix.py сохраняют диагностику.

Команды native pinned Python: `audit.py prepare` → `audit.py compute` (в выполненном запуске затем `audit.py finish` после исправления CSV label) → `audit.py preserve`; `report.py report` → `report.py finalize`. Для повторения нужен новый уникальный каталог и перенесённые audit helpers; все записи exclusive. Python/NumPy и SHA источников зафиксированы в ANALYSIS_SPEC.json. CPU-only, без GPU, новых entropy streams или загрузки checkpoint.
