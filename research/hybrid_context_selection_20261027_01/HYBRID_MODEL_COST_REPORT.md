> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Стоимость моделей и сигнализации

Дата: 27.10.2026. Fixed-PMF, actual scene-specific coding; две уже изученные сцены. Это exploratory experiment, не независимое подтверждение обобщаемости. Все символы, quantizer, PMF и thresholds взяты из прежних файлов без refit. Экономия относится только к standalone xyz-паре, не ко всему Grid4D.

H3PM v1:22B заголовка,24B отображения [2,12],0/56/112B thresholds, PMF pool. В22B уже включены1B mask и1B mode; они не оплачиваются второй раз. Ключи0…3=Geometry4,4…11=Mean8 classes2…9. Только реально используемые ключи, определяемые по coarse-only routing. Полные256-symbol PMF остаются неизменными. Совпадающие uint32 строки разделяют один pool ID. G2/G3 могут ссылаться на общие Mean8 bins.

Проверены dense_u32, packed_u16, sparse_default_u16 для всех64 масок (192 exact dry roundtrips). Выбирается минимальный сериализованный размер; во всех основных файлах победил sparse_default_u16. CDF не дублируется. Модель не подгоняется заново.


| Case | Best mask | Used keys | Unique PMFs | Без exact sharing B | После sharing B | Экономия sharing B | Threshold B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | 1111 | 19 | 17 | 6511 | 6092 | 419 | 112 |
| hellwarrior_L5 | 1111 | 20 | 18 | 5585 | 5166 | 419 | 112 |
| bouncingballs_L6 | 0100 | 15 | 13 | 2760 | 2278 | 482 | 56 |
| hellwarrior_L6 | 1100 | 14 | 12 | 2231 | 1749 | 482 | 56 |

Сравнение до/после exact sharing относится к одним и тем же необходимым sparse PMF; это стоимость mass sections, не самостоятельных альтернативных файлов. Полные оплаченные бюджеты:

| Сцена/уровень | Модель | Coarse B | Fine payload B | PMF B | Metadata B | Total B |
| --- | --- | --- | --- | --- | --- | --- |
| bouncingballs_L5 | IID | 76130 | 186800 | 470 | 2304 | 265704 |
| bouncingballs_L5 | Geometry4 | 76130 | 159600 | 2465 | 2316 | 240511 |
| bouncingballs_L5 | Canonical8 | 76130 | 152752 | 6053 | 2450 | 237385 |
| bouncingballs_L5 | Mean8 | 76130 | 144148 | 6515 | 2440 | 229233 |
| bouncingballs_L5 | H3 0000 | 76130 | 159600 | 2046 | 2160 | 239936 |
| bouncingballs_L5 | H3 1111 | 76130 | 144148 | 6092 | 2272 | 228642 |
| bouncingballs_L5 | H3 best 1111 | 76130 | 144148 | 6092 | 2272 | 228642 |
| hellwarrior_L5 | IID | 44579 | 125180 | 428 | 2303 | 172490 |
| hellwarrior_L5 | Geometry4 | 44579 | 109616 | 2390 | 2315 | 158900 |
| hellwarrior_L5 | Canonical8 | 44579 | 106424 | 6431 | 2449 | 159883 |
| hellwarrior_L5 | Mean8 | 44579 | 103424 | 5585 | 2439 | 156027 |
| hellwarrior_L5 | H3 0000 | 44579 | 109616 | 1971 | 2159 | 158325 |
| hellwarrior_L5 | H3 1111 | 44579 | 103424 | 5166 | 2271 | 155440 |
| hellwarrior_L5 | H3 best 1111 | 44579 | 103424 | 5166 | 2271 | 155440 |
| bouncingballs_L6 | IID | 187483 | 259148 | 443 | 2336 | 449410 |
| bouncingballs_L6 | Geometry4 | 187483 | 249612 | 1982 | 2348 | 441425 |
| bouncingballs_L6 | Canonical8 | 187483 | 251748 | 3701 | 2482 | 445414 |
| bouncingballs_L6 | Mean8 | 187483 | 248780 | 3065 | 2472 | 441800 |
| bouncingballs_L6 | H3 0000 | 187483 | 249612 | 1500 | 2170 | 440765 |
| bouncingballs_L6 | H3 1111 | 187483 | 248780 | 2583 | 2282 | 441128 |
| bouncingballs_L6 | H3 best 0100 | 187483 | 248648 | 2278 | 2226 | 440635 |
| hellwarrior_L6 | IID | 125821 | 201116 | 347 | 2335 | 329619 |
| hellwarrior_L6 | Geometry4 | 125821 | 195488 | 1877 | 2347 | 325533 |
| hellwarrior_L6 | Canonical8 | 125821 | 196696 | 3494 | 2481 | 328492 |
| hellwarrior_L6 | Mean8 | 125821 | 194468 | 2576 | 2471 | 325336 |
| hellwarrior_L6 | H3 0000 | 125821 | 195488 | 1395 | 2169 | 324873 |
| hellwarrior_L6 | H3 1111 | 125821 | 194468 | 2094 | 2281 | 324664 |
| hellwarrior_L6 | H3 best 1100 | 125821 | 194860 | 1749 | 2225 | 324655 |

Геометрия/hash/actual scale/offsets/domain/quantizer/arithmetic записаны в outer JSON; prefix50B и SHA256 trailer32B. Slot→vertices таблица отсутствует, decoder воспроизводит её геометрически.
