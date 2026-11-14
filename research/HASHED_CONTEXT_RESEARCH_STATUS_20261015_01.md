> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Статус НИР: постобучающее контекстное кодирование HashGrid Grid4D

15 октября 2026 года. Эксперименты A/B завершены. Correctness gate B пройден, включая повторную проверку обработки повреждённых файлов. Измерения, вероятностные прогнозы и ограничения интерпретации разделены ниже.

## 1. Завершённые исследования и границы результата

Исследовательская основа — обученный Grid4D checkpoint `bouncingballs-reference-50000`, неизменные table-wise 8-bit symbols пространственной сетки G_xyz. Уровни нумеруются с нуля. Результаты относятся к одному checkpoint и существующему квантователю.

Проведены два разных эксперимента:

- **A — Count6 против Geometry4:** exploratory held-out исследование xyz L4→L5 и L5→L6. Train-only probability tables; прежние splits seeds0/1/2; размеры dry probability models измерены, payload/net savings прогнозируются. Итог: **NO-GO отдельному Count6 codec на обоих уровнях**.
- **B — Mean8 actual scene-specific coding:** настоящий standalone bitstream пары xyz L4+L5 с общим coarse prerequisite, четырьмя моделями IID/Geometry4/Canonical8/Mean8 и тремя вариантами передачи probability masses. Symbol decode и class replay совпадают точно. Численный критерий эффективности пройден: Mean8 меньше самого сильного baseline Canonical8 на **8152 B**, или **3,434% размера этой пары**. Итог B: **GO для измеренного Mean8 standalone codec** при exact reconstruction.

Предыдущий Mean4×Std2 NO-GO остаётся в силе. Эксперимент B проверяет отдельную модель Mean8 и не переинтерпретирует отрицательный результат dispersion-модели.

Основные документы:

- MULTIPLICITY_REPORT.md (внешний артефакт; см. каталог исключённых ссылок).
- BITSTREAM_REPORT.md (внешний артефакт; см. каталог исключённых ссылок).
- Предыдущий HELDOUT_REPORT.md (внешний артефакт; см. каталог исключённых ссылок).
- Контракт geometry/coarse context (внешний артефакт; см. каталог исключённых ссылок).

## 2. Что установлено фактическими bitstreams

Размеры — `filesystem size`, байты. Для каждого arm независимо выбран наиболее короткий реально сериализованный transport из dense_u32, packed_u16 и sparse_default_u16; здесь у всех выигрывает sparse_default_u16. В колонке Coarse учтены его payload и probability-model envelope. Model bytes — fine integer masses; thresholds, model specification, headers и integrity относятся к Metadata/framing. Сумма четырёх компонент точно равна Total.

| Модель | Coarse | Fine payload | Fine model | Metadata/framing | Total |
|---|---:|---:|---:|---:|---:|
| IID | 76130 | 186800 | 470 | 2304 | 265704 |
| Geometry4 | 76130 | 159600 | 2465 | 2316 | 240511 |
| Canonical8 | 76130 | 152752 | 6053 | 2450 | 237385 |
| Mean8 | 76130 | 144148 | 6515 | 2440 | 229233 |

Mean8 экономит **36471 B относительно IID**, **11278 B относительно Geometry4**, **8152 B относительно Canonical8**. Самый сильный корректный baseline — Canonical8. Общий coarse payload/model побитно одинаков у всех вариантов; поэтому incremental fine saving после оплаты всей дополнительной модели/metadata также равно standalone pair saving в байтах. Это не процент сжатия всего Grid4D и не результат для всех xyz levels.

Независимый decoder читает один `.bin`, восстанавливает q4, строит контекст только из q4 и переданной metadata, восстанавливает probability masses/CDF и декодирует q5. Внешняя проверка сравнила каждый символ обоих каналов: q4 имеет 205379 rows, q5 — 524288 rows; всего **1459334 точных uint8 symbols на контейнер**. Все allocated slots, включая nominal-empty и boundary cases, присутствуют один раз. Context class IDs совпадают с encoder.

Exact reconstruction означает **нулевое дополнительное искажение относительно замороженных uint8 symbols**. Оно не означает lossless восстановление исходной float-модели: старое квантование уже могло вносить искажения. Rendering/RD whole-scene comparison в A/B не запускался и не подменяется symbol equality.


Итоговые проверки B: **15 unit tests PASS**, **594 corruption/malformed checks PASS**, независимый аудит всех12 физических контейнеров PASS. После минимального исправления error contract повторены12 fresh-process decodes и12 byte-identical re-encodes; q4/q5/classes совпали точно. Первоначальные24 неуспешных exception-contract checks означали, что повреждённые payload отклонялись backend через AssertionError вместо ValueError. Ни одного malformed container принято не было. Новый adapter нормализует исключение; entropy engine и ранее созданные bytes не менялись. Первоначальные проверки и failure history (внешний артефакт; см. каталог исключённых ссылок) сохранены.

Подтверждения: corruption checks (внешний артефакт; см. каталог исключённых ссылок), post-repair validation (внешний артефакт; см. каталог исключённых ссылок), independent review (внешний артефакт; см. каталог исключённых ссылок). Контроль сохранности исходных checkpoint, frozen symbols и предыдущих artifacts фиксируется в final-validation.json (внешний артефакт; см. каталог исключённых ссылок); прежние результаты не заменяются текущими документами.

## 3. Что установлено только held-out CE

Эксперимент A использует train335545 / validation83886 / test104857 fine slots, прежние seeds0/1/2. Оба канала одного slot сохраняются в одном split. Integer probability masses fit только на train: Laplace α=1, минимальная mass1, сумма65536. Ни число классов, ни границы multiplicity buckets после test не менялись.

| Fine level | Geometry4 CE | Count6 CE | ΔCE all | ΔCE G3 | PREDICTED net, B |
|---|---:|---:|---:|---:|---:|
| L5 | 1,220546973 | 1,221418298 | −0,000871325 | −0,003408852 | −1618,21 |
| L6 | 1,904874333 | 1,899353830 | +0,005520503 | +0,007195714 | −20,42 |

Положительное ΔCE = CE Geometry4 − CE Count6. На L5 знак отрицателен в обоих каналах и всех seeds для all/G3. На L6 знак положителен в обоих каналах и всех seeds для all/G3, но переносится на подгруппы неодинаково: K2 и K≥4 выигрывают, K3 проигрывает. Это измеренные результаты фиксированной модели, а не разрешение подбирать новые bucket configurations на том же test.

**A — follow-up exploratory study на уже анализировавшихся данных.** Новый preregistration не устраняет предшествующий выбор направления по этой сцене и K-подгруппам. Три split seeds не являются тремя независимыми сценами или training runs. Результат не доказывает обобщение на новый checkpoint.

Ранее Mean8 на L5 давал held-out ΔCE≈+0,114710 bits/symbol относительно Geometry4, включая положительный выигрыш внутри G3. B теперь дополняет этот прогноз физическим файлом для той же пары. Однако B fit probability tables и quantile thresholds по всем symbol rows и полностью оплачивает их передачу: это **actual scene-specific coding**, а не новый held-out результат.

## 4. Что остаётся прогнозом

В A gross/net оцениваются как N_full·ΔCE/8 минус измеренная разность dry-model side bytes; actual Count6 payload не создавался. Средние net −1618,21 B и −20,42 B не являются физическими размерами файлов. Прежний Mean4×Std2 и результаты Mean8 для L6 также остаются в области held-out/model-cost forecast.

Ни улучшение целого Grid4D checkpoint, ни общая RD curve, ни перенос на temporal tables, другие levels, quantizers или сцены не измерены. Экономия старой dense пары L3→L4 не включена в новый L4→L5 standalone file.

## 5. Помогает ли multiplicity самостоятельно

Count6 использует **число допустимых point-context correspondences**, а не nominal multiplicity или occupancy. Классы G0/G1/K1/K2/K3/K≥4 восстанавливаются из geometry/hash specification без coarse features или undecoded fine targets. Exact geometry-only fresh-process replay прошёл для обоих уровней.

На L5 Count6 не даёт дополнительного выигрыша сверх Geometry4 даже в CE. На L6 он обнаруживает небольшую устойчивую предиктивную связь с symbol distribution сверх объединённого G3; это основание считать multiplicity потенциально информативным в данном режиме, но не экономически успешным самостоятельным кодером. Дополнительные модели поглощают выигрыш. Значение L6 net близко к нулю и сильно ниже заранее заданного запаса4096 B; один положительный seed (+22,98 B) не меняет решения NO-GO.

Причинное объяснение исключительно «числом коллизий» не доказано: fine и coarse tables, geometry и распределения символов L5/L6 различаются. Не проверены иные geometry priors, оптимальная bucketization или совместная условная информация multiplicity и mean.

## 6. Полезен ли Mean8 для реального сжатия L5

Да, для измеренного standalone L4+L5 файла, заданного quantizer и четырёх корректных arms. Экономия относительно Canonical8 составляет 8152 B после полной оплаты модели, metadata и coarse prerequisite. Это локальный положительный engineering/experimental результат постобучающего кодирования.

По совокупности A/B фактический исход ближе к варианту **«Count6 не окупается, Mean8 полезен»**, с существенной оговоркой: Count6 на L6 полезен для CE, хотя codec gate не прошёл. Нельзя утверждать, что count вообще не содержит информации, или что mean и count являются независимыми механизмами. На L5 агрегированный coarse-feature context работает там, где данный count-only prior не заменяет его в выбранном модельном семействе.

## 7. Роль probability-model overhead и расхождение прогноза с actual

Относительно Canonical8 Mean8 уменьшает fine payload на **8604 B**, увеличивает fine masses на **462 B** и уменьшает прочую metadata на **10 B**. Чистый выигрыш: 8604−462+10=**8152 B**. Относительно Geometry4 gross payload gain15452 B оплачивает4050 B дополнительных masses и124 B metadata, оставляя11278 B. Сравнение одних payload завысило бы эффект.

Для Count6 на L5 дополнительные masses стоят1333–1684 B/seed, одновременно CE ухудшается. На L6 дополнительные masses721–763 B сопоставимы с PREDICTED gross669–777 B; поэтому стабильный положительный CE не становится устойчивым net gain.

Прежний Mean8 forecast относительно Geometry4 был≈11150 B; actual здесь11278 B. Близость чисел не доказывает точности любой оценки CE→file: прогноз использовал train-only fit и test CE, B — full-scene fit с переданными таблицами; отличаются quantile thresholds, probability tables, framing и конечное округление range coder. В B finite masses имеют16-bit precision; entropy engine constriction использует собственное24-bit categorical representation, поэтому конечный payload не тождествен Shannon estimate. Вывод об эффективности основан на физических файлах.

## 8. Различия L5 и L6

L5 содержит133424 допустимых colliding slots G3 из524288; L6 —402329. Count6 K≥4 представлен7184 slots на L5 и132432 на L6. Coarse table L4 для L5 dense, coarse table L5 для L6 hashed. Это разные collision regimes и разные coarse distributions.

На L5 прежний Std-median threshold был0, Mean4×Std2 вырождался в Mean4; Mean8 сохранил выигрыш и теперь прошёл actual coding. На L6 dispersion и multiplicity по отдельности улучшали некоторые held-out показатели, но их фиксированные model-cost gates не прошли. Actual Mean8 L6 и actual Count6 не выполнялись. Перенос положительного результата L5 на L6 не разрешён имеющимися данными.

## 9. Отклонённые гипотезы и границы отрицательных результатов

- Фиксированный Mean4×Std2 не обеспечивает требуемый оплачиваемый выигрыш над сильными baseline в прежнем протоколе; его NO-GO не отменён.
- Count6 не обеспечивает устойчивый оплачиваемый выигрыш с заданным safety margin сверх Geometry4 на исследованных L5/L6. Отдельный Count6 codec не строился.
- Улучшение CE само по себе недостаточно для выбора кодера; L6 демонстрирует это непосредственно через model bytes.

Не отвергнуты все dispersion-based модели, все multiplicity priors или любые bounded collision-aware модели. Отрицательные выводы относятся к конкретным зафиксированным arms, а не к отсутствию всех возможных зависимостей.

## 10. Допустимые научные выводы

На одной хешированной пространственной паре Grid4D можно построить decoder-available агрегированный coarse-feature context с явными boundary/empty conventions, точно воспроизвести classes и уменьшить standalone entropy file при неизменных quantized symbols. Анализ показывает практическую необходимость оплачивать model/metadata и сохранять сильные geometry/canonical baselines.

Стенд уже позволяет отделять geometry-only и feature-conditioned hypotheses, прогнозы и реальные sizes, exact decoding и approximate GPU parity. Это воспроизводимый экспериментальный вклад НИР. Его общность, конкурентоспособность с внешними codecs и новый алгоритмический механизм пока не установлены.

## 11. Отличие от CNC Hash Fusion

Согласно ранее проверенному [CNC paper, §§3.3–3.4, Eq.(3)](https://arxiv.org/html/2406.04101v1#S3.SS3) и локальному аудиту официального исходного кода (внешний артефакт; см. каталог исключённых ссылок), CNC использует binary features, coarse-to-fine context, обучаемый Context Fuser и aggregation предсказаний по spatial correspondences с occupancy/AOE weights; representation и entropy model оптимизируются совместно.

Наш Mean8 сначала равновесно усредняет признаки декодированной coarse grid по допустимым correspondences, затем выбирает bin по переданным quantile thresholds и256-symbol histogram. В общем случае predictor(mean(features)) и weighted mixture of per-vertex predictions не совпадают. Count6 задаётся целочисленной point multiplicity; он не является occupancy/AOE весом. Здесь фиксированы многозначные post-training uint8 targets, нет occupancy discard, все allocated symbols передаются точно.

Различие протоколов не является доказательством превосходства над CNC. CNC runtime не сравнивался на одинаковых targets/quality/side-information budgets. Общие идеи inter-level conditioning, collision correspondences и aggregation уже известны. В этой сессии использованы сохранённый source audit и ранее проверенная primary source; новый CNC runtime experiment не проводился.

## 12. Новизна и перспективность collision-aware моделей

Mean8, Count6, среднее, число correspondences и versioned container сами по себе не являются установленной научной новизной. Уменьшение compression ratio на одном checkpoint не доказывает новый механизм, универсальность, state of the art или публикационный приоритет.

Направление дешёвых collision-aware contexts остаётся перспективным как **проверяемая исследовательская гипотеза**: положительный actual Mean8 показывает существующий бюджет полезного context на L5, а L6 показывает, как overhead его уничтожает. Следует сохранить ограничение стоимости и независимые проверки, а не расширять число классов без evidence. Новые neural models, temporal/cross-grid features и unconstrained bucket search текущими результатами не обоснованы.

Поскольку A не прошёл экономический gate, совместный geometry+feature codec сейчас не рекомендуется как следующий автоматический этап. Если в будущем на независимых данных multiplicity покажет дополнительный оплачиваемый gain, минимальный заранее фиксируемый опыт мог бы сравнить Mean8 с G0/G1 + Mean4×1[K≥3] (не более10 classes/channel), при одинаковой оценке всего model budget. Это только условное направление; оно не реализовано и не заменяет ближайшую рекомендацию.

## 13. Один следующий научный эксперимент

**Независимо проверить frozen Mean8 L4→L5 на другом уже доступном обученном checkpoint**, сохранив те же IID/Geometry4/Canonical8 baselines, table-wise8 quantizer protocol, классы/арифметику/entropy engine, оплату всех models и самостоятельный decode. Не выбирать bucket configurations по текущему test. Для нового checkpoint его quantizer parameters и geometry должны передаваться и проверяться; текущий adapter намеренно ограничен reference geometry/quantizer, поэтому необходимое обобщение должно быть отдельной проверяемой инженерной частью будущей задачи.

Primary outcome — actual standalone bytes относительно лучшего baseline при exact reconstruction; вторичные — runtime/RSS и сопоставимый held-out CE. Предпочтителен другой scene/checkpoint, поскольку другой snapshot той же training trajectory слабее проверяет переносимость. Если подходящего готового checkpoint нет, сначала определить доступный источник и ресурсы отдельной задачей; в текущей сессии новые данные, обучение и quantization не запускать.

**Остановка после A/B и итоговой проверки.** Следующая collision-aware модель, новые datasets, уровни L7–L15 и temporal tables в этой сессии не разрабатываются. Предыдущие отчёты и связанные точные данные сохраняются по прежним путям.
