> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Проверка официальной реализации 4DGS-CC

Проверено 2026-10-06. Статья: **4DGS-CC: A Contextual Coding Framework for 4D
Gaussian Splatting Data Compression**, Zicong Chen, Zhenghao Chen, Wei Jiang,
Wei Wang, Lei Liu, Dong Xu. https://arxiv.org/abs/2504.18925, latest v2 от 2025-04-30.

Повторная проверка 2026-10-07: результат не изменился. Заново получены abstract/HTML
с Appendix, author homepage/JS bundle и GitHub Search API; web search полного названия
с code/project/checkpoint и именами авторов также не дал подтверждённого implementation.
API по-прежнему total_count=1, KyungdaePark/CC-4DGS относится к другой работе.
Свежие snapshots/hash/timestamps: `research/audit/sources/manifest.json`.
Official Neural Voxel Contextual Coding code и checkpoints не найдены; отдельный
4DGS-CC baseline по этим источникам воспроизвести нельзя. Это не блокирует Grid4D-based
фазу 2; ограниченный отрицательный результат поиска не доказывает отсутствие private code.

**Подтверждённая официальная реализация, project page и pretrained checkpoints
не найдены в проверенных публичных источниках.** Это результат поиска, а не
доказательство того, что код никогда не существовал или не доступен privately.

Проверки:

1. arXiv abstract page, external links, полная HTML v2 статьи и раздел 6 Appendix
   (lossless decoding, hyperparameters, per-scene results, RD curves).
   Ссылки GitHub в HTML относятся к инструментам arXiv/LaTeXML, а не к коду авторов.
   Отдельный официальный supplementary code/checkpoint artifact не найден.
2. Поиск полного названия и `4DGS-CC github code project pretrained`,
   поиск имён Zicong Chen / Zhenghao Chen в контексте GitHub и этой работы.
3. GitHub Repository Search API `q=4DGS-CC`: total_count=1,
   `KyungdaePark/CC-4DGS`. Репозиторий относится к **CC-4DGS: Computational
   Deformation and Point-Cloud Compression for Storage-Efficient Dynamic Gaussian
   Splatting**, авторы Kyungdae Park и Chae Eun Rhee; это другая работа.
   Он не клонировался и не объявлялся реализацией 4DGS-CC.
4. Институциональная страница соавтора:
   https://profiles.newcastle.edu.au/Zhenghao-Chen.
   Personal homepage https://z-chen.net/ и её публичный JS bundle проверены;
   упоминания этой работы или связанного code link в полученном содержимом нет.
   Публичные GitHub accounts авторов, достоверно связанные именно с 4DGS-CC,
   идентифицировать не удалось. Неподтверждённые одноимённые аккаунты не использовались.

Первичные HTML/API snapshots и SHA256: `research/sources/manifest.json`.
GitHub API snapshot: `research/sources/4dgscc-github-search.json`.
Никаких сообщений авторам не отправлялось.

Практическое решение: Grid4D остаётся основным baseline. 4DGS-CC используется
как архитектурный reference. Статья строит NVCC вокруг multi-resolution HexPlane
features и spatial/temporal priors; перенос на HashGrid требует отдельного исследования
топологии и collisions. Собственный NVCC/VQCC и codec здесь не реализуются.

Для Grid4D отдельно проверены README, project page и GitHub Releases API:
публичных releases нет (`[]`), официальные pretrained Grid4D checkpoints
в этих источниках не опубликованы. Поэтому baseline обучается коротким smoke test.
