> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Hellwarrior Mean8 — карта завершённого эксперимента

Каталог: `<PROJECT_ROOT>\research\mean8_hellwarrior_validation_20261020_01`.

- [Основной отчёт и actual размеры](BITSTREAM_REPORT.md).
- Вторичный held-out отчёт (внешний артефакт; см. каталог исключённых ссылок).
- Actual independent audit (внешний артефакт; см. каталог исключённых ссылок).
- Held-out independent audit (внешний артефакт; см. каталог исключённых ссылок).
- [Решение](decision.json), размеры (внешний артефакт; см. каталог исключённых ссылок), [экономия](actual-gains.csv), [runtime](runtime-summary.csv), [prediction bridge](prediction-bridge.csv).
- Inputs manifest (внешний артефакт; см. каталог исключённых ссылок), runtime geometry (внешний артефакт; см. каталог исключённых ссылок), context checks (внешний артефакт; см. каталог исключённых ссылок), freeze (внешний артефакт; см. каталог исключённых ссылок).
- Exact decode checks (внешний артефакт; см. каталог исключённых ссылок), corruption checks (внешний артефакт; см. каталог исключённых ссылок).
- Environment (внешний артефакт; см. каталог исключённых ссылок), decoder dependencies (внешний артефакт; см. каталог исключённых ссылок), failure history (внешний артефакт; см. каталог исключённых ссылок).
- `source_snapshot/` и `source-snapshot.json`: точные исходники. `final-validation.json`: итоговый artifact manifest. `integrity-final.json`: сохранность4776 прежних файлов.
- `CONTINUATION_001`…`004`: точки продолжения. `004` обозначает завершение; данные не нужно заново quantize/fit.

## Выполненные команды

Из `<PROJECT_ROOT>`. Скрипты используют exclusive creates и откажутся перезаписывать завершённые outputs.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.tools/phase2-plotting-env/Scripts/python.exe research/mean8_hellwarrior_validation_20261020_01/run_actual.py
.tools/phase2-plotting-env/Scripts/python.exe research/mean8_hellwarrior_validation_20261020_01/run_heldout.py all --run research/mean8_hellwarrior_validation_20261020_01
.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.hashed_pair_v2.corruption --run research/mean8_hellwarrior_validation_20261020_01/actual --output research/mean8_hellwarrior_validation_20261020_01/actual-corruption-001
```

Предварительный WSL export/context запуск: `run_input_pipeline_np126.sh` с `research/env_common.sh` и audit-env Python3.10.21; offline isolated dependency установка — `install_numpy126_offline.sh`. Этот export уже выполнен ровно один раз; не повторять в архивном run. Actual runner допускает `--resume` с проверкой всех hashes только для незавершённого запуска.

## Самостоятельный decode уже готового файла

Для повторной проверки используйте новый пустой каталог вывода. Checkpoint, source symbols и contexts decoder не нужны. Python3.12.14 Windows, зависимости из requirements-decoder.txt, публичный код в текущем workspace или его snapshot.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$decodeOutput = 'research/mean8_hellwarrior_replay_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.hashed_pair_v2.replay --input research/mean8_hellwarrior_validation_20261020_01/actual/streams/Mean8__sparse_default_u16.bin --output $decodeOutput
```

Результат: q4.npy, q5.npy, classes.npy, read-audit.json. Exact внешнее сравнение всех массивов уже выполнено run_actual.py и независимо проверено audit_actual_001.py. Значения q4/q5 в файле являются quantized symbols, не исходными float32 параметрами.

Для независимого воспроизведения всего опыта создайте новый уникальный run, сохраните те же source/requirements и frozen inputs/metadata; перенесите runner scripts, protocol/freeze/review gates с прежними hashes. Полная повторная проверка symbols возможна из сохранённого checkpoint с quantizer specification, но не должна заменять архивные файлы. Новые результаты и manifest должны находиться отдельно.
