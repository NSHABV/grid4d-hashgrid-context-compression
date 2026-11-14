> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Первичные источники и границы сопоставления

Проверка выполнена 8 ноября 2026 года. Использованы только перечисленные первичные работы и официальный источник entropy engine; дополнительных научных источников не добавлено. Уверенность HIGH ниже относится к содержанию указанного источника и прочитанного локального кода, а не к превосходству методов. Сопоставимые вычислительные эксперименты с CNC и 4DGS-CC не выполнялись.

## L1. Grid4D

Jiawei Xu, Zexin Fan, Jian Yang, Jin Xie. **Grid4D: 4D Decomposed Hash Encoding for High-fidelity Dynamic Gaussian Splatting**. arXiv:2410.20815v1, 28 October 2024.

[Первичный текст, §§3.2–3.3](https://arxiv.org/html/2410.20815v1#S3.SS2). Источник описывает пространственную и пространственно-временные hash-таблицы и directional attention decoder деформаций. Наше соответствие — происхождение кодируемых параметров; отличие — исследование хранения после обучения. Entropy context не следует из attention. Уверенность: HIGH. Новое обучение, повтор rendering-метрик и whole-model compression в данном обобщении не выполнялись.

Официальная цепочка происхождения сохранена в локальном BASELINE_GRID4D.md и NVCC_SOURCE_AUDIT.md: [авторская страница](https://jiaweixu8.github.io/Grid4D-web/) → [JiaweiXu8/Grid4D](https://github.com/JiaweiXu8/Grid4D). Текущий HEAD репозитория здесь не используется как версия экспериментального кода.

## L2. CNC

Yihang Chen, Qianyi Wu, Mehrtash Harandi, Jianfei Cai. **How Far Can We Compress Instant-NGP-Based NeRF?** CVPR 2024; проверенный текст arXiv:2406.04101v1, 6 June 2024.

[Статья, §§3.2–3.4, Eq.(2)–(4)](https://arxiv.org/html/2406.04101v1#S3). Бинарные признаки, coarse-to-fine conditioning, occupancy-weighted probability fusion и совместная оптимизация представления. Mean8 проекта усредняет признаки, PREVIOUS8 использует символ предыдущего слота; ни один не воспроизводит Hash Fusion. Уверенность: HIGH для механизма, NOT_PERFORMED для численного сравнения.

Дополнительная проверяемая привязка сохранённого аудита: [официальный utils_bpp_acc.py, commit 137c36595b7bad427b279cccdbb761106a39198a](https://github.com/YihangChen-ee/CNC/blob/137c36595b7bad427b279cccdbb761106a39198a/examples/utils_bpp_acc.py), CNC_context_models. Это версия, проверенная прежним аудитом 11 октября 2026 года, не новый runtime или новое чтение всего репозитория. Детали и границы — CNC_SOURCE_AUDIT.md, §§2–3.

## L3. 4DGS-CC / NVCC

Zicong Chen, Zhenghao Chen, Wei Jiang, Wei Wang, Lei Liu, Dong Xu. **4DGS-CC: A Contextual Coding Framework for 4D Gaussian Splatting Data Compression**. arXiv:2504.18925v2, 30 April 2025.

[Первичный текст, §§3.2, 3.4–3.5; Appendix §6.1](https://arxiv.org/html/2504.18925v2#S3.SS4). NVCC использует coarse-plane и предшествующие временные признаки; §3.4 описывает обновление скрытого состояния и cross-attention. PREVIOUS8 имеет доступный decoder префикс, но не временную координату и не этот пространственный механизм. Уверенность: HIGH для различия. Сопоставимый rate-distortion benchmark и воспроизведение NVCC отсутствуют.

Исторический поиск официальной реализации документирован локально. Новая полная проверка её доступности не проводилась: **CURRENT_OFFICIAL_CODE_AVAILABILITY=NOT_CHECKED**. Историческое «не найдено» нельзя превращать в утверждение об отсутствии метода или кода сегодня. Название работы не смешивается с другой CC-4DGS.

## L4. Официальная документация constriction

Проект **constriction**, официальный Python API, модуль stream.model, класс Categorical, раздел Fixed Arguments/perfect; веб-версия проверена 8 ноября 2026 года. [Документация](https://bamler-lab.github.io/constriction/apidoc/python/stream/model.html).

Документированы fixed-point модели и необходимость совпадения perfect у encoder/decoder. perfect=True выбирает более тщательное приближение; это не универсальная гарантия тождества заданной integer CDF. Версия экспериментального runtime **0.4.2** закреплена локальным SOURCE_RUNTIME.json, а точное равенство CDF подтверждено ENGINE_PROBE.json и reserve fitting audit. Уверенность HIGH в этом ограниченном утверждении; другие версии не проверялись.

## Локальные привязки и отсутствующие сравнения

- research/BASELINE_GRID4D.md (внешний артефакт; см. каталог исключённых ссылок)
- research/direction_audit_20261011_01/CNC_SOURCE_AUDIT.md (внешний артефакт; см. каталог исключённых ссылок)
- research/direction_audit_20261011_01/NVCC_SOURCE_AUDIT.md (внешний артефакт; см. каталог исключённых ссылок)
- research/4DGS_CC_AVAILABILITY.md (внешний артефакт; см. каталог исключённых ссылок)
- research/frozen_previous8_actual_20261108_01/SOURCE_RUNTIME.json (внешний артефакт; см. каталог исключённых ссылок)
- research/frozen_previous8_actual_20261108_01/ENGINE_PROBE.json (внешний артефакт; см. каталог исключённых ссылок)
- research/previous8_reserve_batch_20261108_01/MODEL_FITTING_AUDIT.json (внешний артефакт; см. каталог исключённых ссылок)

Не измерены: единый размер полного Grid4D после нашего метода; общий файл H4+PREVIOUS8; actual CHANNEL8 в изученном full-spatial scope; actual Mean8 на fine L7/L8; сопоставимое превосходство над CNC/NVCC; production latency optimum. Это пробелы доказательств, а не отрицательные результаты неисполненных экспериментов. Никакая из первичных публикаций не используется для подстановки её benchmark-чисел вместо измерений проекта.
