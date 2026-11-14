"""Render an immutable stages 0–1 report from already verified artifacts."""
import argparse
import json
from pathlib import Path

from .core import ROOT

PAIRS = ('L4_to_L5', 'L5_to_L6')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    target = run / 'DIAGNOSTIC_REPORT.md'
    if target.exists():
        raise FileExistsError('Completed reports are immutable: choose a new run.')

    def read(name):
        return json.loads((run / name).read_text(encoding='utf-8'))

    def link(label, name):
        return f'[{label}]({(run / name).as_posix()})'

    manifest = read('run-manifest.json')
    pilot = read('pilot.json')
    validation = read('context-validation.json')
    synthetic = read('synthetic-tests.json')
    independent = read('example_verification/validation.json')
    integrity = read('integrity_checks/validation.json')
    summary = read('diagnostics/summary.json')
    examples = read('diagnostics/examples.json')
    metas = {p: read(f'{p}/decoder_bundle/decoder_metadata.json') for p in PAIRS}
    gpu = {p: read(f'gpu_checks/{p}/gpu-parity.json') for p in PAIRS}
    cross = read('gpu_checks/cross-cpu-parity.json')
    assert all(x['status'] == 'PASS' for x in (manifest, validation, synthetic, independent, integrity, cross))
    assert pilot['status'] == 'GO' and all(gpu[p]['status'] == 'PASS' for p in PAIRS)
    rows = {v['pair']: v for v in validation['pairs']}
    out = [
        '# Decoder-available контексты хешированных уровней G_xyz: L4→L5 и L5→L6',
        '',
        'Дата: 2026-10-13. Выполнены только этапы 0–1 исследовательского протокола. **Статус: PASS.**',
        '',
        'Для каждой из 524288 выделенных строк L5 и L6 сохранены геометрия, canonical context, '
        'двухканальные mean и population Std. Два независимых decoder process на каждую пару '
        'побитно восстановили все массивы из coarse symbols и metadata. Fine targets сохранены '
        'отдельно после расчёта и replay; при построении контекстов они не читались.',
        '',
        'Вероятностные модели, энтропийное кодирование, bitstream, новое квантование и обучение '
        'Grid4D не выполнялись. Предиктивная полезность Std и выигрыш сжатия пока не измерены.',
        '',
        '## 1. Входы и границы эксперимента',
        '',
        f'Исходный протокол: [RESEARCH_DIRECTION_DECISION.md]({(ROOT / "research/RESEARCH_DIRECTION_DECISION.md").as_posix()}), '
        'разделы 5, 6, 10. Результаты сравниваются с сохранённым '
        f'[geometry audit]({(ROOT / "research/direction_audit_20261011_01/geometry-diagnostic.json").as_posix()}). '
        'Предыдущие отчёты и upstream Grid4D не менялись.',
        '',
        'Использован официальный [Grid4D](https://github.com/JiaweiXu8/Grid4D), '
        'commit `3ab7b74482910d22fba7d51ac60c8cae1fe24bf1`. '
        'Checkpoint: `outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth`.',
        '',
        f'- SHA256 checkpoint: `{manifest["checkpoint_sha256"]}`.',
        f'- SHA256 готового `xyz_encoding.u8.bin`: `{manifest["table8_sha256"]}`.',
        f'- SHA256 официального `hashencoder.cu`: `{metas[PAIRS[0]]["implementation"]["cuda_sha256"]}`.',
        f'- {link("Manifest входов этапа 0", "run-manifest.json")} и '
        f'{link("хеши защищённых прежних файлов", "protected-input-hashes.json")}.',
        '',
        'Quantizer взят из существующего table-wise 8-bit экспорта, shape xyz `[6098108,2]`: '
        f'min={metas[PAIRS[0]]["coarse"]["quantization"]["min"]}, '
        f'max={metas[PAIRS[0]]["coarse"]["quantization"]["max"]}, '
        f'Δ={metas[PAIRS[0]]["coarse"]["quantization"]["step"]:.17g}. '
        'Исходные uint8 symbols копируются точными level slices. Никакого повторного quantize нет. '
        'Dequantization — существующий `research/grid4d/codec.py::dequantize`: тело функции '
        'загружается через AST без импорта несвязанных torch/checkpoint loaders.',
        '',
        'Coarse symbols являются decoder-equivalent сохранёнными кодами. Этот этап не извлекал '
        'их из entropy bitstream. Глобальные min/max — metadata существующего quantizer: они '
        'должны быть известны decoder. Они не являются fine-derived выбором correspondence.',
        '',
        '## 2. Проверенные факты о структуре коллизий',
        '',
        'Нумерация уровней zero-based. Slot index локален уровню; global row = offset_start + slot. '
        'Actual scale взят из ранее подтверждённого CUDA geometry и ещё раз проверен текущим probe.',
        '',
        '| Level | Роль | Actual scale по каждой оси | Resolution | Rows | Offsets [start,end) | Lookup |',
        '|---|---|---:|---|---:|---|---|',
    ]
    for role, pair in [('coarse', PAIRS[0]), ('fine', PAIRS[0]), ('fine', PAIRS[1])]:
        g = metas[pair][role]
        out.append(f'| L{g["level"]} | {"coarse" if g["level"] == 4 else "fine / coarse" if g["level"] == 5 else "fine"} '
                   f'| {g["scale"][0]:.17g} | {g["lookup_resolution"][0]}³ | {g["rows"]} '
                   f'| {g["offset_start"]}, {g["offset_end"]} | {"dense" if g["level"] == 4 else "hash"} |')
    out += ['', '| Fine level | Slots | Nominal vertices | Eligible point vertices | Nominal colliding slots | Point colliding G3 | Max nominal multiplicity |',
            '|---|---:|---:|---:|---:|---:|---:|']
    for p in PAIRS:
        v, s = rows[p], summary['pairs'][p]
        maxn = max(z['multiplicity'] for z in s['nominal_multiplicity_histogram'] if z['slots'])
        out.append(f'| L{metas[p]["fine"]["level"]} | {v["all_slots"]} | {v["nominal_vertices"]} '
                   f'| {v["point_vertices"]} | {v["nominal_collision_slots"]} '
                   f'| {v["point_collision_slots"]} | {maxn} |')
    out += ['', '| Fine level | G0: nominal empty | G1: nominal>0, E empty | G2: n=1 | G3: n>1 |',
            '|---|---:|---:|---:|---:|']
    for p in PAIRS:
        c = rows[p]['geometry_counts']
        out.append(f'| L{metas[p]["fine"]["level"]} | {c["G0"]} | {c["G1"]} | {c["G2"]} | {c["G3"]} |')
    out += ['', 'Все cardinalities, полные multiplicity histograms и категории **точно совпадают** '
            'с предыдущим geometry audit. Перебор выполнен по всему nominal lattice: 531441 и '
            '1404928 вершин. Результат содержит все 524288 slots каждого уровня ровно один раз, '
            'включая G0/G1.', '',
            'Nominal множество `S_j={v: 0≤v_a<R_a, h(v)=j}`; допустимое point-context множество '
            '`E_j={v∈S_j: v_a≤floor(scale_a)}`. Coordinates вычисляются как float32 `u=v/scale`, '
            'без clamp. Верхний corner `ceil(scale)` при нецелом scale имеет `u>1` по данной оси '
            'и не входит в E. **E-empty не означает rendering-unused**: такой corner всё ещё '
            'может участвовать в interpolation внутри куба. Occupancy и training frequency не измерялись.', '',
            f'![Multiplicity и geometry]({(run / "diagnostics/multiplicity_geometry.png").as_posix()})', '',
            '## 3. Математическое соответствие и decoder contract', '',
            'CUDA scale `s=exp2f(level·log2(per_level_scale))·base_resolution−1`; '
            '`R=ceil(s)+1`. Allocation и runtime resolution — разные сущности. '
            'Offsets и cap берутся из сохранённой specification, без пересчёта allocation float64.', '',
            'Официальный `get_grid_index` накапливает dense x-fast index с uint32 stride. '
            'Если stride превышает rows, используется XOR hash '
            '`((x·1) XOR (y·2654435761) XOR (z·805459861)) mod rows`; умножения и stride '
            'оборачиваются по модулю 2³². На L4 dense index, на L5/L6 hash. '
            'В L5→L6 coarse lookup сам обращается к хешированной L5; dense substitution не используется.', '',
            'Coarse lookup: `p=u·s_coarse`, `b=floor(p)`, `f=p−b`, smoothstep '
            '`a=f²(3−2f)`, сумма восьми corners с произведением a/1−a по осям. '
            'При выходе query за [0,1]³ возвращается zero. Boundary weights и zero-weight '
            'corner indices сохраняют CUDA modulo semantics. CPU использует отдельные float32 '
            'операции без FMA, corners 0…7 и axes 0…2.', '',
            'Для непустого E representative — `v*=argmin (v_x+R_x·v_y+R_xR_y·v_z)`, '
            'минимальный **x-fast ordinal в E**, не minimum hash. '
            '`f_v=Lookup_coarse(Dequant(Q_coarse),v/s_fine)`.', '',
            'Зафиксировано численно устойчивое накопление: anchor `a_j=f_v*`, '
            '`δ_v=float64(f_v)−float64(a_j)`; '
            '`μ_j=a_j+Σδ_v/n_j`, '
            '`σ_j=sqrt(max(0,Σδ_v²/n_j−(Σδ_v/n_j)²))`. '
            'Это population Std по каждому каналу, без поправки n−1. Обновления np.add.at '
            'идут в возрастающем x-fast порядке. Chunk меняет только буфер, порядок сложения '
            'остаётся тем же. Singleton Std принудительно равен точному нулю.', '',
            'При E-empty canonical ordinal −1, vertex (−1,−1,−1), coordinates (0,0,0), '
            'canonical features/mean/Std (0,0), representative_valid=false. '
            'Это sentinel, а не допустимая вершина. G0/G1 сохраняются раздельно.', '',
            f'Идентификатор арифметики: `{manifest["arithmetic"]}`. '
            'Decoder должен закрепить эту specification, coarse uint8 symbols, quantizer, '
            'scale/resolution/rows/offsets, hash constants, geometry convention и fallback. '
            'Зависимости от checkpoint, undecoded fine targets, изображений или occupancy нет.', '',
            'L4→L5 получает только q(L4); L5→L6 только уже доступный q(L5). '
            'То, что q(L5) также является target предыдущей пары, корректно для последовательного '
            'decoder. Fine symbols не участвуют в выборе вершины, mean/Std или примеров.', '',
            '## 4. Проверенные свойства coarse features', '',
            'Ниже статистика по **всем G3 slots**. Singleton G2 имеет Std=0 в обоих каналах, '
            'mean=canonical точно; G0/G1 используют явный fallback. Δ — существующий quantization step.', '',
            '| Fine level | G3 slots | Хотя бы один Std>0 | Median σ₀ | Median σ₁ | P90 σ₀ | P90 σ₁ |',
            '|---|---:|---:|---:|---:|---:|---:|']
    for p in PAIRS:
        s = summary['pairs'][p]
        n = rows[p]['point_collision_slots']
        positive = s['colliding_at_least_one_nonzero_std']
        quant = [s['channels'][str(c)]['point_colliding_G3']['std']['quantiles'] for c in (0, 1)]
        out.append(f'| L{metas[p]["fine"]["level"]} | {n} | {positive} ({100*positive/n:.6f}%) '
                   f'| {quant[0]["0.5"]:.9g} | {quant[1]["0.5"]:.9g} '
                   f'| {quant[0]["0.9"]:.9g} | {quant[1]["0.9"]:.9g} |')
    out += ['', '| Fine level | Both σ exactly zero in G3 | Median norm(σ) | P90 norm(σ) | norm(σ)>Δ |',
            '|---|---:|---:|---:|---:|']
    for p in PAIRS:
        s = summary['pairs'][p]
        q = s['vector_dispersion']['point_colliding_G3']['quantiles']
        n = rows[p]['point_collision_slots']
        gt = s['colliding_sigma_norm_gt_one_quantization_step']
        out.append(f'| L{metas[p]["fine"]["level"]} | {s["colliding_both_channels_exact_zero_std"]} '
                   f'| {q["0.5"]:.9g} | {q["0.9"]:.9g} | {gt} ({100*gt/n:.6f}%) |')
    out += ['', 'В данном checkpoint L6 имеет большую долю colliding slots и более высокую '
            'медиану разброса coarse responses. Это измеренная характеристика двух уровней одной '
            'сцены. Coarse tables также разные: L4 dense против L5 hash; причинный эффект только '
            'числа коллизий здесь не выделен.', '',
            'Строго положительный Std включает значения порядка 10⁻⁹: часть различий может '
            'быть округлением float32 interpolation. Даже constant nonzero table иногда даёт '
            'такую вариацию через сумму weights. Поэтому доля Std>0 сама по себе не доказывает '
            'существенную неоднородность. Сравнение ||σ|| с Δ — только диагностический масштаб, '
            'не тест predictive usefulness.', '',
            f'![Распределения Std по каналам и G2/G3]({(run / "diagnostics/std_distributions.png").as_posix()})', '',
            f'![Mean и Std coarse features]({(run / "diagnostics/mean_std_hexbin.png").as_posix()})', '',
            'Multiplicity и одномерные распределения используют полные strata. Mean/Std hexbin '
            'показывает 80000 равномерно выбранных G3 slots/level с fixed seed; точные численные '
            'summaries вычислены без sampling. `describe.population_std` в summary JSON описывает '
            'разброс статистики между slots и отличается от σ внутри одного collision set.', '',
            '### Реальные slots с похожими mean и различными Std', '',
            'Поиск использовал только coarse-only arrays: допуск ||μ_A−μ_B||₂≤Δ/4 '
            '=0.008381165242662617. Выбраны три непересекающиеся пары/level. '
            'Поиск ограничен candidate sampling, глобальная оптимальность не утверждается.', '',
            '| Fine | Slots A / B | n_A / n_B | distance(μ_A,μ_B) | norm(σ_A) / norm(σ_B) | Δσ norm / Δ |',
            '|---|---|---|---:|---|---:|']
    for e in examples:
        out.append(f'| {e["pair"]} | {e["low_slot"]} / {e["high_slot"]} '
                   f'| {e["low_point_count"]} / {e["high_point_count"]} '
                   f'| {e["mean_l2_distance"]:.9g} '
                   f'| {e["low_sigma_norm"]:.9g} / {e["high_sigma_norm"]:.9g} '
                   f'| {e["sigma_difference_in_quantization_steps"]:.6g} |')
    out += ['', 'Все 12 slots проверены повторно независимым scalar uint32 lookup и суммированием '
            'math.fsum: 34 nominal correspondences, canonical indices/features exact, mean error=0, '
            f'maximum Std error={independent["maximum_std_error"]:.17g} (tolerance 1e−14). '
            'Похожие mean могут скрывать различный разброс coarse responses. Связь этого различия '
            'с fine-symbol distribution остаётся непроверенной.', '',
            f'{link("Полные примеры с mean/Std каждого канала", "diagnostics/examples.json")}; '
            f'{link("scalar-проверка", "example_verification/validation.json")}; '
            f'{link("все correspondences выбранных slots", "example_verification/selected-correspondences.csv")}.', '',
            '## 5. Проверки воспроизводимости и причинности', '',
            '| Проверка | Результат | Область доказательства |',
            '|---|---|---|',
            '| Synthetic collisions / dense / uint32 wrap / boundary / empty / population Std | PASS: 16 tests | Independent scalar oracle, controlled small grids |',
            '| Все allocated slots | PASS | 524288/level, без gaps/duplicates; NPZ и CSV |',
            '| Geometry audit | PASS exact | Полные nominal/point counts, histograms, G0–G3 |',
            '| Fresh decoder replay | PASS bitwise | 2 processes/level, chunks 4096 и 65536, все arrays |',
            '| Запрещённые чтения | PASS | Checkpoint, full xyz bin, fine_symbols.npy, parent contexts.npz блокируются отдельно |',
            '| Independent real examples | PASS | 12 slots, scalar indexing exact; moment tolerance 1e−14 |',
            '| CUDA indexing / runtime geometry | PASS exact | 512 indices/coarse и fine на пару, включая uint32 overflow |',
            '| CPU/GPU features | PASS tolerance, не bitwise | 512 queries/pair; max abs 2.9802322387695312e−8 |',
            '| Windows/WSL CPU lookup sample | PASS bitwise | Те же sampled queries; не полный aggregate portability test |',
            '| Context classes CPU/GPU | NOT RUN | Classes/edges ещё не строились |',
            '| Предыдущие artifacts и исходники | PASS SHA256 | 2967 защищённых файлов неизменны |', '',
            'Каждый replay process читает только `decoder_bundle/decoder_metadata.json` и '
            '`decoder_bundle/coarse_symbols.npy` как данные. Импорты, stdlib и public source code '
            'допустимы. Normal replay имеет blocked_reads=[] и false checkpoint/fine-target flags. '
            'Четыре отдельные negative probes на пару дают четыре запрещённых чтения. '
            'Python audit hook проверяет этот decoder; это не OS security sandbox.', '',
            'CPU encoder и CPU decoder совпали побитно для geometry и floating context arrays. '
            'Приблизительный GPU feature parity **не доказывает точного совпадения будущих '
            'контекстных классов**. Будущие bin edges/CDF требуют отдельного точного контракта. '
            'Sampled CPU bitwise parity между NumPy 1.26.4 и 1.21.6 не заменяет проверку '
            'полного aggregation на другой платформе.', '',
            f'{link("Synthetic results", "synthetic-tests.json")}; '
            f'{link("все context checks", "context-validation.json")}; '
            f'{link("artifact integrity", "integrity_checks/validation.json")}; '
            f'{link("Windows/WSL CPU parity", "gpu_checks/cross-cpu-parity.json")}.', '',
            '## 6. Оценка compute и фактические затраты', '',
            f'Предварительный pilot по 65536 nominal vertices/pair: '
            f'{pilot["estimated_compute_seconds"]:.3f} s для трёх context passes '
            '(parent + два decoder replay на каждую пару), conservative projected peak '
            f'{pilot["estimated_conservative_peak_mib"]} MiB. GO относительно лимитов '
            '1800 s CPU и 1024 MiB. Это оценка context compute; CSV, hashing, plots и import startup '
            'не входили в экстраполяцию.', '',
            '| Пара | Parent context wall / CPU, s | CSV wall, s | Parent peak RSS, MiB |',
            '|---|---|---:|---:|']
    for p in PAIRS:
        v = rows[p]
        out.append(f'| {p} | {v["parent_wall_seconds"]:.3f} / {v["parent_cpu_seconds"]:.3f} '
                   f'| {v["csv_seconds"]:.3f} | {v["parent_peak_rss_mib"]:.2f} |')
    replay_cpu, replay_wall = 0., 0.
    for p in PAIRS:
        for c in (4096, 65536):
            r = read(f'{p}/decoder_replay_{c}/read-audit.json')
            replay_cpu += r['cpu_seconds']
            replay_wall += r['wall_seconds']
    out += ['', f'Четыре replay: суммарно {replay_wall:.3f} s wall / {replay_cpu:.3f} s CPU '
            'внутри расчёта; отдельный startup/NPZ IO не включён. '
            f'Графики и summaries: {summary["elapsed_seconds"]:.3f} s, '
            f'peak total RSS={summary["process_peak_rss_bytes"]/2**20:.2f} MiB. '
            f'Независимые реальные примеры: {independent["elapsed_seconds"]:.3f} s. '
            'Единого end-to-end таймера всей сессии нет: длительность обсуждения/реализации '
            'не равна вычислительным затратам.', '',
            'GPU использован только для небольшого parity probe в существующем WSL audit-env: '
            f'Python 3.10.21, NumPy 1.21.6, PyTorch 2.7.0+cu128, CUDA 12.8, RTX 5060 Laptop. '
            f'Max allocated GPU memory={max(gpu[p]["torch_peak_allocated_bytes"] for p in PAIRS)/2**20:.2f} MiB; '
            f'max total CPU RSS этого процесса={max(gpu[p]["process_peak_rss_bytes"] for p in PAIRS)/2**20:.2f} MiB '
            '(включая torch runtime). CUDA modules уже были собраны; rebuild не запускался. '
            'CPU replay и plots выполнялись отдельно. Измеренный total process RSS является '
            'консервативной верхней границей дополнительной памяти процесса; существующий '
            'WSL runtime/shared resident memory не измерялся отдельно.', '',
            'Данные geometry/context: по 55574528 B массивов/level. CSV потоковый; полный '
            'список correspondences или slot×256 probability arrays не хранится. Бюджет '
            '30 min CPU / 1 GiB не превышен.', '',
            '## 7. Точные данные и воспроизведение', '',
            'Для каждой пары NPZ содержит следующие массивы (N=524288):', '',
            '| Массивы | Shape | Dtype |',
            '|---|---|---|',
            '| slot_index, global_embedding_row, nominal_count, point_count, canonical_ordinal | [N] | int64 |',
            '| geometry | [N] | uint8 (0…3) |',
            '| canonical_vertex | [N,3] | int32 |',
            '| canonical_coordinates | [N,3] | float32 |',
            '| canonical_features | [N,2] | float32 |',
            '| mean, std | [N,2] | float64 |',
            '| representative_valid | [N] | bool |', '',
            'CSV разворачивает два канала и три координаты; Python round-trip float representations '
            'сохраняют precision. Отдельный `fine_symbols.npy` [N,2] uint8 — существующие labels '
            'для будущего этапа; contexts.npz/CSV их не содержат. Join выполняется по slot_index.', '']
    for p in PAIRS:
        out += [f'**{p}:** {link("NPZ", p+"/contexts.npz")}; '
                f'{link("CSV", p+"/contexts.csv")}; {link("fine labels", p+"/fine_symbols.npy")}; '
                f'{link("metadata", p+"/decoder_bundle/decoder_metadata.json")}; '
                f'{link("coarse symbols", p+"/decoder_bundle/coarse_symbols.npy")}; '
                f'{link("CUDA parity", "gpu_checks/"+p+"/gpu-parity.json")}.', '',
                f'Array SHA256 (sorted keys/dtype/shape/bytes): `{rows[p]["arrays_sha256"]}`. '
                f'Coarse NPY SHA256: `{metas[p]["coarse_symbols_sha256"]}`.', '']
    out += ['CPU environment: Windows Python 3.12.14, NumPy 1.26.4; существующий '
            '`.tools/phase2-plotting-env`, Matplotlib для plots. Новые зависимости не установлены.', '',
            'Команды выполняются из <PROJECT_ROOT>. Используйте **новый пустой каталог**; '
            'этот завершённый run не переиспользовать. Отчёт и результаты защищены от overwrite.', '',
            '```powershell',
            "$env:PYTHONDONTWRITEBYTECODE='1'",
            "$py='<PROJECT_ROOT>\\.tools\\phase2-plotting-env\\Scripts\\python.exe'",
            "$run='research/hashed_context_diagnostic_<NEW_UNIQUE_ID>'",
            'New-Item -ItemType Directory -Path $run',
            '& $py -m research.hashgrid_analysis.hashed_context.diagnostic prepare --output $run',
            '& $py -m research.hashgrid_analysis.hashed_context.diagnostic pilot --output $run',
            '# Proceed only when pilot.json status is GO.',
            '& $py -m research.hashgrid_analysis.hashed_context.diagnostic compute --output $run',
            '& $py -m research.hashgrid_analysis.hashed_context.visualize $run',
            '& $py -m research.hashgrid_analysis.hashed_context.verify_real_examples --run $run',
            '# Optional CUDA probes: commands below. Then integrity checks and final report:',
            '& $py -m research.hashgrid_analysis.hashed_context.integrity $run',
            '& $py -m research.hashgrid_analysis.hashed_context.report $run',
            '& $py -m research.hashgrid_analysis.hashed_context.finalize $run',
            '```', '',
            'Optional GPU commands внутри существующего WSL checkout `<PROJECT_ROOT>` '
            '(перед report, новые выходные каталоги):', '',
            '```bash',
            'run="research/hashed_context_diagnostic_<NEW_UNIQUE_ID>"',
            'bash research/hashgrid_analysis/hashed_context/run_gpu_parity.sh --bundle "$run/L4_to_L5/decoder_bundle" --output "$run/gpu_checks/L4_to_L5"',
            'bash research/hashgrid_analysis/hashed_context/run_gpu_parity.sh --bundle "$run/L5_to_L6/decoder_bundle" --output "$run/gpu_checks/L5_to_L6"',
            '```', '',
            'Cross-CPU sample check выполняется Windows Python: '
            '`-m research.hashgrid_analysis.hashed_context.cross_cpu_parity --results <run> '
            '--output <run>/gpu_checks/cross-cpu-parity.json`; '
            'report требует результаты этих проверок для данного verified run. '
            'Для CPU-only новой среды GPU section необходимо оформить отдельно как unavailable, '
            'не подменяя её вымышленным PASS.', '',
            'Исходники нового модуля и использованные public dependencies сохранены в '
            '`source_snapshot/`, их SHA — `source-hashes.json`; итоговые artifact hashes '
            'и ссылки проверяются `final-validation.json`. Эти файлы создаются отдельным finalize. '
            'Исходный driver этапа 0 сохранён как `source_stage0/diagnostic.py`; до pilot '
            'исправлен только вызов synthetic unittest suite. Hash manifest этапа 0 сохранён '
            'без изменений. Core алгоритм и все protected inputs остались прежними.', '',
            '## 8. Пока не проверенные гипотезы об эффективности сжатия', '',
            'Пока неизвестно, помогает ли Std предсказывать fine symbols сверх mean, canonical '
            'и geometry-only baseline; сохраняется ли эффект на held-out slots/других сценах; '
            'компенсирует ли выигрыш model/metadata bytes и decoder time. '
            'Ни scatter/hexbin, ни найденные mean-similar pairs не отвечают на эти вопросы. '
            'Compression ratio, conditional entropy, actual stream length и научная новизна '
            'этим этапом не установлены.', '',
            '## 9. Возможные препятствия и граница следующего этапа', '',
            'Технического препятствия для следующего CPU held-out исследования на этих данных '
            'не найдено. Следующие ограничения нужно учитывать:', '',
            '- Future context classes должны воспроизводиться точно; GPU allclose features '
            'не разрешают заменять canonical CPU арифметику без отдельной проверки classes.',
            '- C10/C6 model metadata и hashed envelope ещё не поддержаны прежним interlevel '
            'serializer; этот этап их не реализует. Для model/metadata costs потребуется '
            'отдельная разрешённая работа.',
            '- Split выполняется по slot: все correspondences данного target остаются вместе. '
            'Edges и probabilities fit только по train; geometry-only и fallback strata обязательны.',
            '- Boundary convention исключает верхние corner vertices из E; это явное '
            'ограничение point-context approximation, а не разрешение pruning.',
            '- Имеются только одна сцена, два соседних перехода и existing table8 quantizer. '
            'Переносимость на другие сцены/levels и устойчивость к precision пока не доказаны.', '',
            'Рекомендуемый следующий минимальный шаг — отдельный held-out тест H1: сравнить '
            'Canonical8, Mean8 и Mean4×Std2 при matched capacity, с IID/geometry-only controls, '
            'сохранёнными split seeds и train-only edges. Сейчас эта работа **не начата**.', '',
            '**Остановка после этапов 0–1.** Все старые результаты остаются доступны по прежним '
            'путям; новый diagnostic run имеет собственные data, graphs, validations и source snapshots.', '']
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write('\n'.join(out))
    print(json.dumps({'report': str(target), 'status': 'PASS'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
