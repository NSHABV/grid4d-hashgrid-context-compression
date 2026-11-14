> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Grid4D H3: cost-aware Geometry4/Mean8 hybrid

Дата: 27.10.2026. Fixed-PMF, actual scene-specific coding; две уже изученные сцены. Это exploratory experiment, не независимое подтверждение обобщаемости. Все символы, quantizer, PMF и thresholds взяты из прежних файлов без refit. Экономия относится только к standalone xyz-паре, не ко всему Grid4D.


| Сцена/уровень | Маска | Лучший исходный baseline | Baseline B | H3 B | Экономия B | % пары | Выигрыш routing при общем формате B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 1111 | Mean8 | 229233 | 228642 | 591 | 0.2578 | 0 |
| hellwarrior_L5 | 1111 | Mean8 | 156027 | 155440 | 587 | 0.3762 | 0 |
| bouncingballs_L6 | 0100 | Geometry4 | 441425 | 440635 | 790 | 0.1790 | 130 |
| hellwarrior_L6 | 1100 | Mean8 | 325336 | 324655 | 681 | 0.2093 | 9 |

## Прогноз и actual

| Сцена/уровень | Маска | Predicted net B | Net с резервом64 B | Actual net B |
| --- | --- | --- | --- | --- |
| bouncingballs_L5 | 1111 | 610.504 | 546.504 | 591 |
| hellwarrior_L5 | 1111 | 609.214 | 545.214 | 587 |
| bouncingballs_L6 | 0100 | 811.419 | 747.419 | 790 |
| hellwarrior_L6 | 1100 | 701.520 | 637.520 | 681 |

Engineering gate256B после64B резерва пройден на обеих L6;4096B practical target не достигнут. Лучшие маски L6 различаются.

## Интерпретация механизма

На bouncingballs L6 маска0100 использует Mean8 только для G3 канала0. Она избегает потерь singleton G2 и сохраняет часть преимущества colliding G3. Но таблицы для второго Mean8-канала не окупаются при фиксированных PMF.

На hellwarrior L6 лучшая1100 использует Mean8 для G2 и G3 канала0, а Geometry4 для обоих типов канала1. Это **не** универсальное правило «Mean8 только для collisions»: индивидуальное качество и совместная стоимость строк/thresholds меняют решение. Условный выбор отдельных групп нельзя оптимизировать независимо, потому что они делят PMF bins. В частности, переход0100→1100 ухудшает fine payload на164B, но уменьшает PMF section на256B при неизменной metadata: net92B. Поэтому G2 канала0 выбран для Mean8 несмотря на отрицательный ideal gain −1313.904bits; выбор объясняется общей стоимостью модели, а не улучшением предсказания G2.

Результат относительно старых файлов положительный, но основная доля — общий формат/точное sharing. При едином формате новый routing даёт130B на bouncingballs L6 и всего9B на hellwarrior L6. Это точные размеры, но малый эффект;4096B практического запаса нет. На обеих L5 побеждает1111, то есть исходный Mean8, и hybrid routing добавляет0B. L5 регрессии нет при выборе лучшей маски для данного уровня; перенос L6-маски на L5 не рекомендуется.

Нельзя из этих опытов заключить, что счётчик collisions причинно объясняет выигрыш, что H3 переносится на новые сцены или что получена новая научная разработка. Нет нового held-out эксперимента. Masses были scene-specific fitted в прежних опытах, здесь они полностью оплачены и неизменны. Энкодер может выбрать маску по fine targets, поскольку1B решения передаётся; decoder использует только этот byte и coarse-derived routing.

## Честная декомпозиция

| Сцена/уровень | Контроль | Δpayload B | ΔPMF B | Δmetadata B | Net B |
| --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 0000 | 15452 | -4046 | -112 | 11294 |
| bouncingballs_L5 | 1111 | 0 | 0 | 0 | 0 |
| hellwarrior_L5 | 0000 | 6192 | -3195 | -112 | 2885 |
| hellwarrior_L5 | 1111 | 0 | 0 | 0 | 0 |
| bouncingballs_L6 | 0000 | 964 | -778 | -56 | 130 |
| bouncingballs_L6 | 1111 | 132 | 305 | 56 | 493 |
| hellwarrior_L6 | 0000 | 628 | -354 | -56 | 218 |
| hellwarrior_L6 | 1111 | -392 | 345 | 56 | 9 |

Format vs routing (внешний артефакт; см. каталог исключённых ссылок)

All masks (внешний артефакт; см. каталог исключённых ссылок)

Дата: 27.10.2026. Fixed-PMF, actual scene-specific coding; две уже изученные сцены. Это exploratory experiment, не независимое подтверждение обобщаемости. Все символы, quantizer, PMF и thresholds взяты из прежних файлов без refit. Экономия относится только к standalone xyz-паре, не ко всему Grid4D.


| Сцена/уровень | Маска | Лучший исходный baseline | Baseline B | H3 B | Экономия B | % пары | Выигрыш routing при общем формате B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 1111 | Mean8 | 229233 | 228642 | 591 | 0.2578 | 0 |
| hellwarrior_L5 | 1111 | Mean8 | 156027 | 155440 | 587 | 0.3762 | 0 |
| bouncingballs_L6 | 0100 | Geometry4 | 441425 | 440635 | 790 | 0.1790 | 130 |
| hellwarrior_L6 | 1100 | Mean8 | 325336 | 324655 | 681 | 0.2093 | 9 |


| Общий выбор | Маска | Сумма B | Scene-specific сумма B | Цена общего выбора B |
| --- | --- | --- | --- | --- |
| L5 | 1111 | 384082 | 384082 | 0 |
| L6 | 0100 | 765382 | 765290 | 92 |
| all | 1111 | 1149874 | 1149372 | 502 |

## Проверки

64/64 fresh strict exact decode,64/64 byte-identical repeats,160/160 corruption rejected,16/16 legacy regression,36/36 selective parity. Ни одной корректирующей подгонки PMF или новых bins. Полная целостность прежних6209 файлов и seal текущего run записаны в FINAL_VALIDATION.json.

Дата: 27.10.2026. Fixed-PMF, actual scene-specific coding; две уже изученные сцены. Это exploratory experiment, не независимое подтверждение обобщаемости. Все символы, quantizer, PMF и thresholds взяты из прежних файлов без refit. Экономия относится только к standalone xyz-паре, не ко всему Grid4D.

Все расчёты CPU; GPU/VRAM не использовались. Python 3.12.14, NumPy 1.26.4, constriction0.4.2. Основной цикл64 streams+64 repeats+64 fresh strict decodes: **314.95s**. Peak RSS parent **143.82MiB**, children max **136.69MiB**. Это per-process peaks, не суммарный замер Windows memory; parent и один child могут существовать одновременно. Сумма максимумов<281MiB. Подготовка/финальный hash audit и дополнительные тесты не входят в314.95s. Pilot и actual pilot сохранены;30min/1GiB бюджет соблюдён.

| Case | Mask | Geometry s | Mean context s | Lookup внутри него s | Encode s | Repeat s | Strict decode s | Strict overhead s | Cold process s | Selective context s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 1111 | 0.0468 | 0.3127 | 0.1488 | 0.9027 | 0.8860 | 1.8282 | 0.6647 | 2.1860 | 0.3243 |
| hellwarrior_L5 | 1111 | 0.0457 | 0.3067 | 0.1477 | 0.8486 | 0.8992 | 1.7712 | 0.6147 | 2.1623 | 0.3242 |
| bouncingballs_L6 | 0100 | 0.1180 | 0.7303 | 0.4307 | 1.3741 | 1.3648 | 3.0904 | 0.9539 | 3.5043 | 0.7266 |
| hellwarrior_L6 | 1100 | 0.1144 | 0.7112 | 0.4184 | 1.3135 | 1.3114 | 2.9464 | 0.9448 | 3.3239 | 0.7444 |

Mean context содержит повторный geometry pass в исходном core, lookup является вложенным измерением; их нельзя суммировать как непересекающиеся расходы. Encoder time включает новый fine payload и container, **coarse payload reused**, а не якобы бесплатный новый coarse encode. Дополнительная фактическая регенерация общего coarse payload:

| Case | Coarse encode s | Byte-identical |
| --- | --- | --- |
| bouncingballs_L5 | 0.1857 | True |
| hellwarrior_L5 | 0.1694 | True |
| bouncingballs_L6 | 0.4858 | True |
| hellwarrior_L6 | 0.4354 | True |

Fresh process cold wall включает startup и output I/O. Internal decoder time не является отдельным cold-start benchmark. Дополнительно выполнены два последовательных non-strict warm decode каждого лучшего файла и endpoints, с exact equality:

| Case | Mask | Repeat | Warm decode без strict s |
| --- | --- | --- | --- |
| bouncingballs_L5 | 0000 | 0 | 0.8262 |
| bouncingballs_L5 | 0000 | 1 | 0.8139 |
| bouncingballs_L5 | 1111 | 0 | 1.1677 |
| bouncingballs_L5 | 1111 | 1 | 1.1695 |
| hellwarrior_L5 | 0000 | 0 | 0.7476 |
| hellwarrior_L5 | 0000 | 1 | 0.7519 |
| hellwarrior_L5 | 1111 | 0 | 1.0895 |
| hellwarrior_L5 | 1111 | 1 | 1.0708 |
| bouncingballs_L6 | 0000 | 0 | 1.2122 |
| bouncingballs_L6 | 0000 | 1 | 1.2285 |
| bouncingballs_L6 | 0100 | 0 | 1.9527 |
| bouncingballs_L6 | 0100 | 1 | 1.9553 |
| bouncingballs_L6 | 1111 | 0 | 1.9908 |
| bouncingballs_L6 | 1111 | 1 | 2.0239 |
| hellwarrior_L6 | 0000 | 0 | 1.1743 |
| hellwarrior_L6 | 0000 | 1 | 1.1751 |
| hellwarrior_L6 | 1100 | 0 | 1.9284 |
| hellwarrior_L6 | 1100 | 1 | 1.8594 |
| hellwarrior_L6 | 1111 | 0 | 1.8630 |
| hellwarrior_L6 | 1111 | 1 | 1.8638 |

Для mask0000 основной decoder уже не делает feature lookup. Optional `selective_context.py` пропускает все точки слотов, которым Mean8 не нужен, сохраняя исходный порядок оставшихся x-fast обновлений и отдельные float32 операции. Он также не вычисляет неиспользуемый Std, поэтому его timing — комбинированная оптимизация, не чистая оценка одного skipping. Оба feature channels lookup пока считаются вместе; побитовое сохранение routed classes проверено, значения неиспользуемых классов не обязаны совпадать. Оптимизация не подменяла исходный benchmark. `selective-context-checks.csv` содержит36 замеров.
## Следующий шаг и ограничения

**Решение:** StageA GO; StageB correctness PASS и положительный actual net относительно исходных контейнеров. Практическая значимость H3 не подтверждена: routing-only130B/9B на L6,0B на L5, существенно ниже4096B. Новизна не доказана. Предыдущий NO-GO Mean4×Std2 не отменяется.

**Один следующий эксперимент:** preregistered независимая проверка фиксированной общей L6-маски0100 на третьем, заранее выбранном checkpoint без просмотра его H3 результатов. Использовать тот же table8 quantizer scope, arithmetic contract, модельный транспорт и frozen правило получения исходных Geometry4/Mean8 PMF; оплачивать все scene-specific таблицы. Главный контроль —0000/1111 в том же H3 формате, а не старые overhead-heavy файлы. Основная метрика — actual standalone bytes при exact decode, плюс runtime. Не выбирать новую маску по третьей сцене, не менять bins/PMFs после просмотра. Это проверит переносимость ограниченного routing, а не независимость старых сцен. В этой сессии третий checkpoint не запускался.

Для самостоятельного научного вклада ещё требуется обоснование экономического/decoder-causal критерия, независимая валидация и строгая атрибуция выигрыша после выравнивания транспорта моделей. Сам механизм выбора между известными контекстами и передача mode bit не являются автоматически новыми.
## Ограниченная проверка аналогов

Первичные источники проверены27.10.2026. [CNC, CVPR2024](https://arxiv.org/abs/2406.04101) уже использует level-wise/dimension-wise context и hash-collision/occupancy priors для NeRF. Здесь исследуется post-training frozen uint8 Grid4D и четыре оплаченных geometry/channel решения с фиксированными PMF; это иной ограниченный эксперимент, но не доказательство отсутствия аналогов.

В [официальном libjxl enc_cluster.cc](https://raw.githubusercontent.com/libjxl/libjxl/main/lib/jxl/enc_cluster.cc) присутствуют histogram clustering и учёт кодировочной стоимости; [enc_ans_params.h](https://github.com/libjxl/libjxl/blob/main/lib/jxl/enc_ans_params.h) описывает оценку header+data cost. Следовательно, общий принцип cost-aware выбора/разделения вероятностных моделей и context maps нельзя объявлять новым. Это ограниченная сверка, не исчерпывающий literature/patent review; реализация JPEG XL не переносилась в эксперимент.
## Воспроизведение и точки продолжения

Рабочий каталог `<PROJECT_ROOT>`. Python `.tools/phase2-plotting-env/Scripts/python.exe`, всегда `-B`. Завершённый run неизменяемый: для повторного исследования сначала создать новый уникальный каталог и скопировать run scripts; старые результаты не удалять. common.py выводит RUN из собственного пути. Входные SHA зафиксированы в INPUT_MANIFEST/protected-input-hashes. Для полной новой копии: initialize.py → stage_a.py → validate_stage_a.py → (только GO) stage_b.py → validate_legacy.py → validate_corruption.py → validate_selective.py → benchmark_warm.py → report.py → finalize.py. Перед этим использовать сохранённый source_snapshot/версии зависимостей. stage_b.py поддерживает только проверенное продолжение завершённых mask checkpoints; неполный файл не перезаписывает.

Одиночный standalone decode (выход должен быть новым):

```powershell
.tools/phase2-plotting-env/Scripts/python.exe -B -m research.experiment_bench.hybrid_pair.replay --input research/hybrid_context_selection_20261027_01/bouncingballs_L6/actual/0100.bin --output research/hybrid_decode_new_unique
```

Выход coarse.npy/fine.npy/routes.npy/audit.json; ни checkpoint, ни сохранённые contexts не нужны. Эталонные source snapshots,64 bin и per-mask JSON сохранены; CONTINUATION_004_READY_TO_SEAL.md описывает финальную контрольную точку. После FINAL_VALIDATION PASS работа остановлена.

## Документы

- [MASK_ENUMERATION_REPORT.md](MASK_ENUMERATION_REPORT.md)
- [HYBRID_MODEL_COST_REPORT.md](HYBRID_MODEL_COST_REPORT.md)
- DRY_SIZE_PREDICTIONS.md (внешний артефакт; см. каталог исключённых ссылок)
- GO_NO_GO_STAGE_A.md (внешний артефакт; см. каталог исключённых ссылок)
- [HYBRID_BITSTREAM_REPORT.md](HYBRID_BITSTREAM_REPORT.md)
- INDEPENDENT_DECODER_VALIDATION.md (внешний артефакт; см. каталог исключённых ссылок)
- CROSS_SCENE_COMPARISON.md (внешний артефакт; см. каталог исключённых ссылок)
- [PERFORMANCE_REPORT.md](PERFORMANCE_REPORT.md)
- NEXT_RESEARCH_DECISION.md (внешний артефакт; см. каталог исключённых ссылок)
- [FINAL_VALIDATION.json](FINAL_VALIDATION.json)
