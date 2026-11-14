> Публичная копия исторического документа. Локальные пути и ссылки адаптированы; численные результаты не пересчитывались. Хеши и PASS внутри текста относятся к исходному запуску, а не к этой копии.

# Multiplicity Count6: exploratory held-out исследование

14 октября 2026. Отдельный эксперимент A; `bouncingballs-reference-50000`, xyz L4→L5 и L5→L6, existing table-wise uint8. CPU Python 3.12.14 / NumPy 1.26.4. GPU не использовался.

**Это follow-up exploratory study на той же сцене, checkpoint и ранее анализировавшихся test/K-подгруппах.** Предварительная фиксация нового протокола предотвращает настройку Count6 после результата, но не превращает повторное использование данных в независимое подтверждение. Новые случайные seeds также не сделали бы данные независимыми.

## Итог отдельно от эксперимента B

- L4_to_L5: **NO-GO**; средний ΔCE=-0.000871325 bits/symbol; PREDICTED net=-1618.21 B; safety margin PASS 0/3 seeds.
- L5_to_L6: **NO-GO**; средний ΔCE=+0.005520503 bits/symbol; PREDICTED net=-20.42 B; safety margin PASS 0/3 seeds.

Решение относится к фиксированному Count6, а не ко всем геометрическим контекстам. Здесь не создан entropy bitstream. Реальный Mean8 codec — отдельный эксперимент B, который продолжается независимо от знака Count6 при PASS correctness.

## Геометрия и decoder-only контракт

Count6: class0=G0 (nominal_count=0); class1=G1 (nominal>0, point_count=0); class2=K1; class3=K2; class4=K3; class5=K≥4. Geometry4 объединяет классы 3–5 в G3. K означает **point_count**, не nominal multiplicity. Классы одинаковы для двух каналов, PMF обучаются отдельно по каналам.

Decoder получает только geometry-metadata.json: fine actual float32 scale, resolution, rows, offsets, domain convention, uint32 hash specification. Он перебирает nominal lattice в x-fast order; E допускает вершины v≤floor(scale). Hash — официальный stride/dense switch, unsigned 32-bit wrap, XOR primes (1,2654435761,805459861), modulo rows. Counts целочисленные и не зависят от порядка chunk accumulation. Ни coarse feature values, ни coarse symbols, ни occupancy, ни fine targets не нужны.

| Fine | G0 | G1 | K1 | K2 | K3 | K≥4 | allocated |
|---|---:|---:|---:|---:|---:|---:|---:|
| L4_to_L5 | 183592 | 7144 | 200128 | 96960 | 29280 | 7184 | 524288 |
| L5_to_L6 | 27888 | 3057 | 91014 | 137401 | 132496 | 132432 | 524288 |

## Протокол и статистика

Оригинальные splits скопированы byte-for-byte: seeds 0/1/2, train 335545 / validation 83886 / test 104857 slots (64/16/20% с прежним округлением). Оба канала slot принадлежат одному split. Laplace α=1, минимальная integer mass=1, stable largest remainder, сумма65536. Все probability distributions fit только на train; пустой train class получает uniform256. Validation только описательна; число классов, smoothing и bucket boundaries не настраивались. MODEL_FREEZE создан до exact decoder replay и единственного test evaluation.

GO объявлен заранее отдельно для каждого уровня: положительные gains all/G3 в каждом seed/channel и PREDICTED net каждого seed выше max(4096 B, 0.2·max(Δside,0)). Это консервативный gate для последующего кодирования, а не статистическая значимость. Парные SE в CSV описательны; пространственная зависимость и overlap seeds не дают независимых реплик.

| Fine | Geometry4 all | Count6 all | ΔCE all | Geometry4 G3 | Count6 G3 | ΔCE G3 |
|---|---:|---:|---:|---:|---:|---:|
| L4_to_L5 | 1.220546973 | 1.221418298 | -0.000871325 | 2.257348487 | 2.260757338 | -0.003408852 |
| L5_to_L6 | 1.904874333 | 1.899353830 | +0.005520503 | 2.135199007 | 2.128003293 | +0.007195714 |

Средние трёх повторных holdout seeds; положительное ΔCE означает выигрыш Count6. По каналам и подгруппам:

| Fine | Group | Test slots min…max | Geometry4 ch0/ch1 | Count6 ch0/ch1 | ΔCE ch0/ch1 | Gain min…max seed/channel |
|---|---|---:|---|---|---|---|
| L4_to_L5 | all | 104857…104857 | 1.242087 / 1.199007 | 1.242885 / 1.199952 | -0.000798 / -0.000944 | -0.000992…-0.000651 |
| L4_to_L5 | G3 | 26594…27002 | 2.300121 / 2.214576 | 2.303244 / 2.218271 | -0.003123 / -0.003695 | -0.003851…-0.002567 |
| L4_to_L5 | G3_K2 | 19420…19682 | 2.241904 / 2.162654 | 2.241128 / 2.162409 | +0.000776 / +0.000244 | -0.000069…+0.001067 |
| L4_to_L5 | G3_K3 | 5790…5872 | 2.413994 / 2.321558 | 2.422790 / 2.328339 | -0.008796 / -0.006781 | -0.009807…-0.006035 |
| L4_to_L5 | G3_K4plus | 1384…1454 | 2.630732 / 2.487875 | 2.663968 / 2.532793 | -0.033236 / -0.044918 | -0.046399…-0.031295 |
| L5_to_L6 | all | 104857…104857 | 1.889405 / 1.920344 | 1.883540 / 1.915168 | +0.005865 / +0.005176 | +0.004866…+0.006306 |
| L5_to_L6 | G3 | 80287…80553 | 2.115024 / 2.155374 | 2.107378 / 2.148628 | +0.007645 / +0.006746 | +0.006339…+0.008208 |
| L5_to_L6 | G3_K2 | 27393…27595 | 1.979185 / 1.988904 | 1.964628 / 1.974849 | +0.014557 / +0.014055 | +0.013334…+0.015278 |
| L5_to_L6 | G3_K3 | 26457…26687 | 2.135118 / 2.189153 | 2.137636 / 2.191570 | -0.002518 / -0.002416 | -0.003079…-0.001878 |
| L5_to_L6 | G3_K4plus | 26402…26437 | 2.236149 / 2.294634 | 2.225476 / 2.286282 | +0.010673 / +0.008352 | +0.007660…+0.012264 |

Paired gain (внешний артефакт; см. каталог исключённых ссылок)

Все K-подгруппы удовлетворяют заранее заданному минимуму 100 test slots. Группы не использовались для выбора новых bucket configurations. G0/G1/K1 PMF полностью совпадают с Geometry4, потому что train observations этих классов не изменились; дополнительная модель разделяет только G3.

## Реальная стоимость модели и прогноз payload

Проверены существующие dry transports dense_u32, packed_u16 и sparse_default_u16 (36 файлов, exact roundtrip). Для каждого arm/seed независимо выбран самый короткий actual serialized model file. CDF не дублируется. Common metadata сохранена идентичной предыдущему held-out experiment, включая coarse prerequisite/quantizer/provenance; это консервативный общий envelope, хотя Count6 decoder для классов использует лишь geometry. Model rule names имеют разную длину; эта разность оплачена. C6 уже поддерживается serializer, исходный код не изменён.

| Fine | seed | Model | Storage | Mass bytes | Threshold bytes | Spec bytes | Metadata | Header | Total side |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| L4_to_L5 | 0 | Geometry4 | sparse_default_u16 | 2735 | 34 | 206 | 1890 | 26 | 4891 |
| L4_to_L5 | 0 | Count6 | sparse_default_u16 | 4068 | 34 | 203 | 1890 | 26 | 6221 |
| L4_to_L5 | 1 | Geometry4 | sparse_default_u16 | 2696 | 34 | 206 | 1890 | 26 | 4852 |
| L4_to_L5 | 1 | Count6 | sparse_default_u16 | 4380 | 34 | 203 | 1890 | 26 | 6533 |
| L4_to_L5 | 2 | Geometry4 | sparse_default_u16 | 2678 | 34 | 206 | 1890 | 26 | 4834 |
| L4_to_L5 | 2 | Count6 | sparse_default_u16 | 4182 | 34 | 203 | 1890 | 26 | 6335 |
| L5_to_L6 | 0 | Geometry4 | sparse_default_u16 | 1772 | 34 | 206 | 1907 | 26 | 3945 |
| L5_to_L6 | 0 | Count6 | sparse_default_u16 | 2535 | 34 | 203 | 1907 | 26 | 4705 |
| L5_to_L6 | 1 | Geometry4 | sparse_default_u16 | 1541 | 34 | 206 | 1907 | 26 | 3714 |
| L5_to_L6 | 1 | Count6 | sparse_default_u16 | 2298 | 34 | 203 | 1907 | 26 | 4468 |
| L5_to_L6 | 2 | Geometry4 | sparse_default_u16 | 2009 | 34 | 206 | 1907 | 26 | 4182 |
| L5_to_L6 | 2 | Count6 | sparse_default_u16 | 2730 | 34 | 203 | 1907 | 26 | 4900 |

N_full=524288×2=1048576 symbols; gross=N_full·ΔCE/8; net=gross−Δside. Все следующие значения **PREDICTED**, перенос test CE на весь уровень; реальный payload и coder framing не измерялись.

| Fine | Seed | ΔCE | Gross B | Δmodel B | Δmetadata/framing B | Net B | margin PASS |
|---|---:|---:|---:|---:|---:|---:|---|
| L4_to_L5 | 0 | -0.000754588 | -98.91 | +1333 | -3 | -1428.91 | False |
| L4_to_L5 | 1 | -0.000949870 | -124.50 | +1684 | -3 | -1805.50 | False |
| L4_to_L5 | 2 | -0.000909515 | -119.21 | +1504 | -3 | -1620.21 | False |
| L5_to_L6 | 0 | +0.005526447 | +724.36 | +763 | -3 | -35.64 | False |
| L5_to_L6 | 1 | +0.005927910 | +776.98 | +757 | -3 | +22.98 | False |
| L5_to_L6 | 2 | +0.005107151 | +669.40 | +721 | -3 | -48.60 | False |

PREDICTED net (внешний артефакт; см. каталог исключённых ссылок)

## Сопоставление с уже известными Mean8 и Mean4×Std2

Следующие числа старых моделей взяты из сохранённого предыдущего эксперимента; это **не новый независимый эксперимент или refit**. Geometry4 losses дополнительно побитно сверены с прежними для каждого seed. Все относятся к тому же checkpoint, quantizer и splits.

| Fine | Geometry4 CE | Count6 CE | old Mean8 CE | old Mean4×Std2 CE |
|---|---:|---:|---:|---:|
| L4_to_L5 | 1.220546973 | 1.221418298 | 1.105837307 | 1.155097541 |
| L5_to_L6 | 1.904874333 | 1.899353830 | 1.901428970 | 1.891378317 |

Прежний HELDOUT_REPORT.md (внешний артефакт; см. каталог исключённых ссылок). NO-GO прежнего Mean4×Std2 не пересматривается.

## Correctness, ресурсы и воспроизводимость

PASS: 5 новых synthetic tests (scalar uint32 hash/wrap, colliding tiny grids/boundaries, chunk1/7/65536, шесть классов, недопустимые counts, train-only fitting). Full geometry counts и 524288 class rows ×2 channels обеих пар точно совпадают с сохранённой диагностикой; нет gaps/duplicates. Два fresh decoder process читают только geometry JSON; ни coarse symbols, ни checkpoint, ни fine symbols. Шесть forbidden-read probes на пару отклонены. Python audit hook — инструмент контроля чтения этого decoder, не OS sandbox.

PASS: train histograms независимо проверены per-class bincount; masses положительны, сумма65536; 36 serialization roundtrips; 288 CE записей перепроверены по сохранённым losses и независимой формуле; forecast арифметика проверена отдельно. Полные splits/схемы/модели/точные classes/losses/CSV находятся в текущем каталоге.

| Stage | Wall s | CPU s | Peak total RSS MiB |
|---|---:|---:|---:|
| Input preservation hashes + prepare | 35.533 | 9.234 | 44.70 |
| Fit + validation + model serialization | 0.860 | 0.547 | 63.53 |
| Test + forecasts | 0.813 | 0.766 | 52.37 |
| Independent checks | 2.061 | 1.844 | 61.21 |
| Geometry decoder L4_to_L5 warm body | 0.669 | 0.656 | 54.53 |
| Decoder L4_to_L5 cold process, import+I/O | 0.902 | — | — |
| Geometry decoder L5_to_L6 warm body | 1.258 | 1.234 | 54.61 |
| Decoder L5_to_L6 cold process, import+I/O | 1.529 | — | — |

Pilot geometry projection: 2.659 s, conservative whole-study180 s CPU/256 MiB. Runtime stages measured separately; development time not included. RSS is measured total process working set; GPU/VRAM not used.

Репликация из <PROJECT_ROOT>, всегда новый run path:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$py='.tools/phase2-plotting-env/Scripts/python.exe'
$run='research/hashed_multiplicity_study_<NEW_UNIQUE_ID>'
& $py -m research.experiment_bench.multiplicity.study prepare --run $run
& $py -m research.experiment_bench.multiplicity.study fit --run $run
& $py -m research.experiment_bench.multiplicity.study replay --run $run
& $py -m research.experiment_bench.multiplicity.study test --run $run
& $py -m research.experiment_bench.multiplicity.report --run $run
```

## Допустимый научный вывод и следующий шаг

Положительная held-out ΔCE означает дополнительную предиктивную связь multiplicity с fine symbols сверх G3, но не причинность и не независимое подтверждение. Оплата двух дополнительных классов оценивается отдельно. Отрицательный net не означает отсутствия любой геометрической зависимости. Count6 сам по себе является простой предзаданной категоризацией; научная новизна не заявляется.

Для GO уровня минимальный следующий validation — тот же frozen Count6 protocol на независимом checkpoint, без подбора bucket configurations. При NO-GO отдельный Count6 codec не обоснован этим gate; Mean8 actual experiment B выполняется независимо. Смешанный geometry+feature context в этой работе не реализуется.

Ни entropy coding, ни quantization, ни обучение Grid4D не выполнялись. Preserved source hashes и source snapshot, final-validation.json и все предыдущие отчёты сохраняются; завершённые файлы не перезаписываются.

PREREGISTERED_PROTOCOL.json (внешний артефакт; см. каталог исключённых ссылок)
decision.json (внешний артефакт; см. каталог исключённых ссылок)
test-scores.csv (внешний артефакт; см. каталог исключённых ссылок)
paired-differences.csv (внешний артефакт; см. каталог исключённых ссылок)
model-sizes.csv (внешний артефакт; см. каталог исключённых ссылок)
predicted-net.csv (внешний артефакт; см. каталог исключённых ссылок)
replay-validation.json (внешний артефакт; см. каталог исключённых ссылок)
independent-audit.json (внешний артефакт; см. каталог исключённых ссылок)
final-validation.json (внешний артефакт; см. каталог исключённых ссылок)
