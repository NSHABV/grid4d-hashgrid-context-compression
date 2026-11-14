"""Immutable presentation of completed, prespecified stages 2–3 (no refitting)."""
import argparse
import json
import os
from pathlib import Path
import time
import numpy as np
from research.hashgrid_analysis.hashed_context.core import ROOT, sha
from research.hashgrid_analysis.hashed_context.runtime import write_json, peak_rss_mib
from .core import ARMS

PAIRS = ('L4_to_L5', 'L5_to_L6')
OLD = ROOT / 'research/hashed_context_diagnostic_20261013_01'
LABEL = {'L4_to_L5': 'L5 (L4→L5)', 'L5_to_L6': 'L6 (L5→L6)'}
DISPLAY = {'Mean4Std2': 'Mean4×Std2'}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def select(records, **filters):
    return [r for r in records if all(r[k] == v for k, v in filters.items())]


def average(records, key):
    return float(np.mean([r[key] for r in records]))


def interval(records, key, digits=6):
    x = [r[key] for r in records]
    return f'{min(x):.{digits}f}…{max(x):.{digits}f}'


def link(path, label=None):
    p = Path(path).resolve()
    return f'[{label or p.name}]({p.as_posix()})'


def make_plots(run, scores, paired, sizes, forecasts, validations):
    directory = run / 'plots'
    directory.mkdir(exist_ok=False)
    os.environ.setdefault('MPLCONFIGDIR', str(directory / 'matplotlib_config'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    paths = []

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.8), constrained_layout=True)
    colors = ['#2274a5', '#cc5803', '#6a994e']
    baselines = ('Geometry4', 'Canonical8', 'Mean8', 'Mean4')
    for row, pair in enumerate(PAIRS):
        for col, group in enumerate(('all', 'G3')):
            ax = axes[row, col]
            for seed in (0, 1, 2):
                records = [select(paired, pair=pair, seed=seed, candidate='Mean4Std2',
                                  baseline=b, stratum=group, channel='both')[0] for b in baselines]
                x = np.arange(4) + (seed-1)*.18
                y = np.array([r['gain_bits_per_symbol'] for r in records])
                error = np.array([1.96*r['paired_SE_descriptive'] for r in records])
                ax.errorbar(x, y, yerr=error, fmt='o', capsize=3, label=f'seed {seed}', color=colors[seed])
            ax.axhline(0, color='#555555', linewidth=1)
            ax.set_xticks(range(4), baselines)
            ax.set_ylabel('CE baseline − CE Mean4×Std2 [bits/symbol]')
            ax.set_title(f'{LABEL[pair]} | {group}')
            ax.grid(axis='y', alpha=.2)
    axes[0, 0].legend()
    fig.suptitle('Paired test gains; positive favours dispersion model\nBars: descriptive ±1.96 SE of paired slot losses, conditional on fitted models', fontsize=12)
    for ext in ('png', 'svg'):
        p = directory / f'paired_gains.{ext}'
        fig.savefig(p, dpi=155)
        paths.append(p)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), constrained_layout=True)
    names = list(ARMS)
    for row, pair in enumerate(PAIRS):
        for col, ch in enumerate((0, 1)):
            ax = axes[row, col]
            x = np.arange(len(names))
            ax.bar(x, list(ARMS.values()), color='#dddddd', width=.75, label='Maximum C')
            for seed in (0, 1, 2):
                n = [select(validations, pair=pair, seed=seed, model=name)[0]['occupied_classes_train'][ch] for name in names]
                ax.scatter(x+(seed-1)*.12, n, s=30, color=colors[seed], label=f'Occupied train, seed {seed}', zorder=3)
            ax.set_xticks(x, [DISPLAY.get(n, n) for n in names], rotation=25, ha='right')
            ax.set_ylim(0, 11)
            ax.set_yticks(range(0, 11, 2))
            ax.set_ylabel('Classes (including G0/G1 where applicable)')
            ax.set_title(f'{LABEL[pair]} | channel {ch}')
            ax.grid(axis='y', alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('Nominal capacity and effective training classes; duplicate quantiles retained', fontsize=12)
    for ext in ('png', 'svg'):
        p = directory / f'class_capacity.{ext}'
        fig.savefig(p, dpi=155)
        paths.append(p)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), constrained_layout=True)
    for ax, pair in zip(axes, PAIRS):
        for seed in (0, 1, 2):
            records = [select(forecasts, pair=pair, seed=seed, candidate='Mean4Std2', baseline=b)[0]
                       for b in baselines]
            x = np.arange(4)+(seed-1)*.2
            ax.bar(x, [r['net_saving_bytes']/1024 for r in records], width=.18,
                   label=f'seed {seed}', color=colors[seed])
        ax.axhline(0, color='#555555', linewidth=1)
        ax.axhline(4, color='#a02020', linestyle='--', linewidth=1, label='4 KiB minimum safety margin')
        ax.set_xticks(range(4), baselines, rotation=15)
        ax.set_ylabel('PREDICTED net saving [KiB]')
        ax.set_title(LABEL[pair])
        ax.grid(axis='y', alpha=.2)
    axes[0].legend(fontsize=9)
    fig.suptitle('Mean4×Std2: full-level forecast from held-out CE minus measured model cost\nNot an entropy bitstream or measured file saving', fontsize=12)
    for ext in ('png', 'svg'):
        p = directory / f'predicted_net.{ext}'
        fig.savefig(p, dpi=155)
        paths.append(p)
    plt.close(fig)
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    report = run / 'HELDOUT_REPORT.md'
    if report.exists() or (run/'plots').exists() or (run/'report-summary.json').exists():
        raise FileExistsError('Completed presentation artifacts are immutable; choose a new run')
    started = time.perf_counter()
    protocol = load(run/'PREREGISTERED_PROTOCOL.json')
    inputs = load(run/'input-validation.json')
    freeze = load(run/'MODEL_FREEZE.json')
    replay = load(run/'replay-validation.json')
    unit = load(run/'unit-tests.json')
    decision = load(run/'decision.json')
    assert inputs['status'] == freeze['status'] == replay['status'] == 'PASS'
    assert decision['test_evaluations'] == 1
    scores = load(run/'test-scores.json')
    paired = load(run/'paired-differences.json')
    sizes = load(run/'model-sizes.json')
    forecasts = load(run/'predicted-net.json')
    validations = load(run/'validation-scores.json')
    summary = {'scope': 'MEASURED/SINGLE-SCENE; model costs measured; payload/net PREDICTED',
               'decision': decision['decision'], 'pairs': {}}
    for pair in PAIRS:
        row = {'CE': {}, 'Mean4Std2_vs_Mean8': {}, 'std_thresholds': [], 'effective_classes': {}}
        for model in ARMS:
            row['CE'][model] = {}
            for group in ('all', 'G0', 'G1', 'G2', 'G3', 'G3_K2', 'G3_K3', 'G3_K4plus'):
                row['CE'][model][group] = {}
                for ch in ('both', '0', '1'):
                    entries = select(scores, pair=pair, model=model, stratum=group, channel=ch)
                    row['CE'][model][group][ch] = {'mean_over_seeds': average(entries, 'CE'),
                        'min': min(r['CE'] for r in entries), 'max': max(r['CE'] for r in entries)}
            row['effective_classes'][model] = [r['occupied_classes_train'] for r in select(validations, pair=pair, model=model)]
        row['std_thresholds'] = [load(run/pair/f'seed{seed}_Mean4Std2/spec.json')['edges']['std'] for seed in (0, 1, 2)]
        row['Mean4Std2_vs_Mean8']['gain_all'] = average(select(paired, pair=pair, candidate='Mean4Std2', baseline='Mean8', stratum='all', channel='both'), 'gain_bits_per_symbol')
        row['Mean4Std2_vs_Mean8']['gain_G3'] = average(select(paired, pair=pair, candidate='Mean4Std2', baseline='Mean8', stratum='G3', channel='both'), 'gain_bits_per_symbol')
        row['Mean4Std2_vs_Mean8']['predicted_net_bytes'] = average(select(forecasts, pair=pair, candidate='Mean4Std2', baseline='Mean8'), 'net_saving_bytes')
        summary['pairs'][pair] = row
    plots = make_plots(run, scores, paired, sizes, forecasts, validations)
    lines = [
        '# Held-out исследование dispersion-контекстов HashGrid: этапы 2–3', '',
        'Начало run: 13 октября 2026 года; завершение отчёта: 14 октября 2026 года. Checkpoint `bouncingballs-reference-50000`; xyz L4→L5 и L5→L6, уровни zero-based. '
        'Существующие table-wise uint8 targets. CPU Python 3.12.14 / NumPy 1.26.4. Все результаты относятся к одной сцене и одному checkpoint.', '',
        f'**Итог: {decision["decision"]} для перехода H1 к отдельной реализации bitstream.** '
        'Измерены held-out CE и реальные размеры сериализованных вероятностных моделей. Экономия payload и net — исключительно **PREDICTED**. '
        'Actual entropy stream отсутствует; quantization, Grid4D training и neural probability models не выполнялись.', '',
        '## 1. Неизменность входов и предварительная фиксация', '',
        f'Проверены SHA256 и PASS-статусы предшествующей диагностики: **{inputs["protected_files"]} защищённых файлов**. '
        f'Источник: {link(OLD/"DIAGNOSTIC_REPORT.md", "предыдущий диагностический отчёт")}. '
        f'Исследовательский протокол: {link(ROOT/"research/RESEARCH_DIRECTION_DECISION.md")}.', '',
        'Parent использует готовые `contexts.npz` и `fine_symbols.npy`; geometry/coarse features повторно вычисляются только в отдельном decoder replay, '
        'что необходимо для независимого восстановления class IDs. Targets одинаковы для всех arms; каждый fine slot и оба его канала принадлежат одному split.', '',
        f'Frozen protocol SHA256: `{sha(run/"PREREGISTERED_PROTOCOL.json")}`. '
        f'Фиксация моделей: `{sha(run/"MODEL_FREEZE.json")}`. '
        f'{link(run/"PREREGISTERED_PROTOCOL.json")} создан до fitting/test; {link(run/"MODEL_FREEZE.json")} — до test. '
        'Test вычислен один раз после exact class replay.', '',
        '## 2. Заранее определённые модели, splits и оценка', '',
        f'PCG64 permutation по fine slots, seeds 0/1/2: train **{protocol["train_slots"]}**, validation **{protocol["validation_slots"]}**, '
        f'test **{protocol["test_slots"]}** slots на seed. Train — остаток после floor(20% test), floor(16% validation). '
        'Splits и hashes сохранены отдельно. Seeds — повторные разбиения одной таблицы, не независимые сцены или training runs.', '',
        '| Модель | Максимум C на канал | Правило |', '|---|---:|---|',
        '| IID | 1 | Один histogram на канал |',
        '| Geometry4 | 4 | G0 nominal-empty; G1 nominal-positive/point-empty; G2 singleton; G3 colliding |',
        '| Canonical8 | 10 | 8 quantile bins canonical feature + отдельные G0/G1 |',
        '| Mean8 | 10 | 8 quantile bins mean + G0/G1 |',
        '| Mean4 | 6 | 4 quantile bins mean + G0/G1 |',
        '| Mean4×Std2 | 10 | 4 bins mean × 2 bins Std + G0/G1 |', '',
        'Edges fit только по train G2+G3 отдельно для каждого канала: `np.quantile(method="linear")`, float64. '
        'Повторяющиеся thresholds сохраняются; `searchsorted(side="right")`: значения на threshold принадлежат правому интервалу. '
        'Mean4 и Mean4×Std2 используют одинаковые mean edges. Std разделён одним общим median threshold по train G2+G3 на канал, без настройки по mean-bin. '
        'Никакие thresholds, число классов или smoothing не менялись после test.', '',
        'Train histograms преобразованы существующей `models.frequencies`: Laplace α=1, минимальная integer mass 1, stable largest remainder, '
        'сумма 65536. Пустой train class получает uniform masses 256. Все C distributions передаются, включая пустые; omission по train-empty не применяется. '
        'CE = среднее `−log2(mass/65536)`, без аналитической подмены finite PMF. CDF строго возрастает; cumulative endpoint=65536.', '',
        'Validation выбирает описательного победителя из шести фиксированных arms по общей CE. Hyperparameters/refit не используются; '
        'все шесть сравнений на test заданы заранее. Paired gain = CE baseline − CE candidate; положительный знак означает лучший candidate. '
        'Для обоих каналов сначала усредняются две разности одного slot. Интервалы ±1.96 SE — описательные, conditional-on-fit; '
        'они не учитывают пространственную зависимость/coarse sharing и не доказывают generalization.', '',
        '| Fine level | seed 0 validation winner | seed 1 | seed 2 |', '|---|---|---|---|']
    for pair in PAIRS:
        vals = [select(freeze['validation_selections'], pair=pair, seed=s)[0]['selected_by_validation'] for s in (0, 1, 2)]
        lines.append('| '+LABEL[pair]+' | '+' | '.join(vals)+' |')
    lines += ['', '## 3. Test cross-entropy: все заранее заданные arms', '',
        'Среднее трёх split seeds, bits/symbol; в скобках min…max по seeds. Это среднее результатов повторных holdout, не объединённый независимый test.', '',
        '| Модель | L5 all | L6 all | L5 G3 | L6 G3 |', '|---|---:|---:|---:|---:|']
    for model in ARMS:
        cells = []
        for group, pair in [('all', PAIRS[0]), ('all', PAIRS[1]), ('G3', PAIRS[0]), ('G3', PAIRS[1])]:
            rr = select(scores, pair=pair, model=model, stratum=group, channel='both')
            cells.append(f'{average(rr,"CE"):.6f} ({interval(rr,"CE")})')
        lines.append('| '+DISPLAY.get(model, model)+' | '+' | '.join(cells)+' |')
    lines += ['', 'По каналам: среднее CE трёх seeds.', '',
              '| Fine | Model | all ch0 | all ch1 | G3 ch0 | G3 ch1 |', '|---|---|---:|---:|---:|---:|']
    for pair in PAIRS:
        for model in ARMS:
            cells = [f'{average(select(scores,pair=pair,model=model,stratum=g,channel=ch),"CE"):.6f}' for g, ch in [('all','0'),('all','1'),('G3','0'),('G3','1')]]
            lines.append('| '+LABEL[pair]+' | '+DISPLAY.get(model,model)+' | '+' | '.join(cells)+' |')
    lines += ['', '## 4. Парные сравнения и роль geometry', '',
        '| Fine | Candidate / baseline | ΔCE all | ΔCE G3 | G3 min…max seed/channel |', '|---|---|---:|---:|---:|']
    comparisons = [('Canonical8','Geometry4'),('Mean8','Canonical8'),('Mean8','Geometry4'),
                   ('Mean4Std2','Geometry4'),('Mean4Std2','Canonical8'),('Mean4Std2','Mean8'),('Mean4Std2','Mean4')]
    for pair in PAIRS:
        for candidate, base in comparisons:
            allr = select(paired,pair=pair,candidate=candidate,baseline=base,stratum='all',channel='both')
            g3 = select(paired,pair=pair,candidate=candidate,baseline=base,stratum='G3',channel='both')
            detailed = [r for r in select(paired,pair=pair,candidate=candidate,baseline=base,stratum='G3') if r['channel']!='both']
            lines.append(f'| {LABEL[pair]} | {DISPLAY.get(candidate,candidate)} / {base} | {average(allr,"gain_bits_per_symbol"):+.6f} | '
                         f'{average(g3,"gain_bits_per_symbol"):+.6f} | {interval(detailed,"gain_bits_per_symbol")} |')
    lines += ['', '![Парные gains и conditional интервалы]('+ (run/'plots/paired_gains.png').as_posix()+')', '',
        'Интервалы нарисованы отдельно для каждого seed. Они не служат новым post-hoc критерием GO. '
        'Не следует интерпретировать перекрытие/неперекрытие этих интервалов как независимые сравнения сцен.', '',
        'Mean4×Std2 против Mean8, раздельно по G0/G1/G2/G3; знак и величина не смешиваются с долями strata.', '',
        '| Fine | Stratum | test slots min…max | Mean8 CE | Mean4×Std2 CE | ΔCE |', '|---|---|---:|---:|---:|---:|']
    for pair in PAIRS:
        for group in ('G0','G1','G2','G3'):
            a=select(scores,pair=pair,model='Mean8',stratum=group,channel='both')
            b=select(scores,pair=pair,model='Mean4Std2',stratum=group,channel='both')
            lines.append(f'| {LABEL[pair]} | {group} | {min(r["slots"] for r in a)}…{max(r["slots"] for r in a)} | {average(a,"CE"):.6f} | '
                         f'{average(b,"CE"):.6f} | {average(a,"CE")-average(b,"CE"):+.6f} |')
    lines += ['', '## 5. Multiplicity внутри G3: описательный анализ', '',
        'Группы K=2, K=3, K≥4 определены заранее, минимально 100 test slots. Новые классы по этим группам не fit. '
        'Это exploratory описание regime, не отдельное подтверждение H2 и не настройка победителя.', '',
        '| Fine | K | test slots min…max | ΔCE vs Mean8 | ΔCE vs Mean4 | ch0/ch1 ΔCE vs Mean8 |', '|---|---|---:|---:|---:|---|']
    for pair in PAIRS:
        for group in ('G3_K2','G3_K3','G3_K4plus'):
            a=select(paired,pair=pair,candidate='Mean4Std2',baseline='Mean8',stratum=group,channel='both')
            b=select(paired,pair=pair,candidate='Mean4Std2',baseline='Mean4',stratum=group,channel='both')
            cc=[average(select(paired,pair=pair,candidate='Mean4Std2',baseline='Mean8',stratum=group,channel=ch),'gain_bits_per_symbol') for ch in ('0','1')]
            lines.append(f'| {LABEL[pair]} | {group} | {min(r["slots"] for r in a)}…{max(r["slots"] for r in a)} | '
                         f'{average(a,"gain_bits_per_symbol"):+.6f} | {average(b,"gain_bits_per_symbol"):+.6f} | {cc[0]:+.6f} / {cc[1]:+.6f} |')
    lines += ['', 'Полные CE и paired tables включают каждый seed, канал, stratum и subgroup: '
        f'{link(run/"test-scores.csv")}; {link(run/"paired-differences.csv")}.', '',
        '## 6. Effective capacity и degenerate thresholds', '',
        '| Fine | Model | C max | train occupied ch0 min…max | ch1 min…max |', '|---|---|---:|---|---|']
    for pair in PAIRS:
        for model,C in ARMS.items():
            rr=select(validations,pair=pair,model=model)
            vals=[f'{min(r["occupied_classes_train"][ch] for r in rr)}…{max(r["occupied_classes_train"][ch] for r in rr)}' for ch in (0,1)]
            lines.append(f'| {LABEL[pair]} | {DISPLAY.get(model,model)} | {C} | {vals[0]} | {vals[1]} |')
    lines += ['', 'Std thresholds (ch0/ch1), seeds 0/1/2:', '']
    for pair in PAIRS:
        thresholds=summary['pairs'][pair]['std_thresholds']
        lines.append('')
        lines.append('- '+LABEL[pair]+': '+ '; '.join(f'{e[0][0]:.17g} / {e[1][0]:.17g}' for e in thresholds)+'.')
        if all(e[0][0]==0 and e[1][0]==0 for e in thresholds):
            exact=[]
            for seed in (0,1,2):
                with np.load(run/pair/f'test_losses_seed{seed}.npz',allow_pickle=False) as z:
                    exact.append(np.array_equal(z['Mean4Std2'],z['Mean4']))
            assert all(exact)
            summary['pairs'][pair]['meanstd_mean4_losses_bitwise_equal_all_seeds']=True
            lines += ['', f'**{LABEL[pair]}: вырождение Std-bin подтверждено.** Median=0 и все Std≥0; '
                      '`searchsorted(right)` относит и нулевые, и положительные Std в bin1. Поэтому Mean4×Std2 совпадает с Mean4 по test losses побитно во всех seeds; '
                      'четыре active classes на канал недостижимы. Здесь Std не проверяется содержательно в качестве разделяющего признака. '
                      'Это отрицательный результат данного заранее фиксированного binning, не доказательство отсутствия информации в Std. '
                      'Перенастройка zero-edge после test не проводилась; она потребовала бы отдельного нового протокола.']
    lines += ['', '![Максимальная и эффективная capacity]('+(run/'plots/class_capacity.png').as_posix()+')', '',
        '## 7. Измеренная стоимость модели и PREDICTED net', '',
        'Новый versioned dry serializer поддерживает C=1/4/6/10. Хранит exact integer masses и float64 thresholds, model specification, '
        'обязательную geometry/quantizer/runtime metadata и собственный header. Проверены dense_u32, packed_u16 и sparse_default_u16. '
        'Для sparse modal default выбирается детерминированно, исключения хранят symbol u8 / mass u16. CDF восстанавливается из masses, повторно не оплачивается.', '',
        'Для каждой модели независимо выбирается самый короткий measured dry envelope; равенство размеров разрешается фиксированным порядком storage. '
        'Coarse payload — общий prerequisite и сокращается в разности; это не новый pair/full-grid file. Metadata включает консервативные provenance поля; '
        'все одинаковые поля учитываются симметрично. Переданные train-fit models не refit на полной таблице.', '',
        '| Fine | Model | Best storage (seeds) | Probability bytes min…max | Threshold bytes | Spec bytes | Metadata bytes | Header bytes | Total bytes min…max |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for pair in PAIRS:
        for model in ARMS:
            best=[min(select(sizes,pair=pair,seed=seed,model=model),key=lambda r:r['total']) for seed in (0,1,2)]
            keys=[k for k in best[0] if k not in ('pair','seed','model','storage','roundtrip','total')]
            summary.setdefault('section_size_keys',keys)
            def rng(key):
                x=[r[key] for r in best]
                return str(x[0]) if min(x)==max(x) else f'{min(x)}…{max(x)}'
            # The dry serializer fixes names; fail instead of silently omitting a section.
            masskey=next(k for k in keys if 'mass' in k or 'prob' in k)
            threshkey=next(k for k in keys if 'threshold' in k)
            speckey=next(k for k in keys if 'spec' in k)
            metakey=next(k for k in keys if 'meta' in k)
            storage='/'.join(dict.fromkeys(r['storage'] for r in best))
            lines.append(f'| {LABEL[pair]} | {DISPLAY.get(model,model)} | {storage} | {rng(masskey)} | {rng(threshkey)} | {rng(speckey)} | {rng(metakey)} | {rng("header")} | {rng("total")} |')
    lines += ['', f'Все 108 dry roundtrips и варианты хранения: {link(run/"model-sizes.csv")}. '
        'Файлы `.model` содержат только probability model и metadata, без закодированных target symbols.', '',
        '`N_full = 524288 slots × 2 channels = 1048576 symbols`. '
        '`gross = N_full × (CE_baseline − CE_candidate) / 8`; `net = gross − (side_candidate − side_baseline)`. '
        'Все следующие числа **PREDICTED**; test→full-level перенос и конечный coder overhead не измерены. '
        'Условие запаса: gross > Δside + max(4096 B, 0.2·Δside), отдельно для каждого pair/seed/comparator.', '',
        '| Fine | Mean4×Std2 vs | ΔCE test mean | gross B mean | Δside B mean | net B mean | net B min…max | Margin PASS seeds |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for pair in PAIRS:
        for base in ('Geometry4','Canonical8','Mean8','Mean4'):
            rr=select(forecasts,pair=pair,candidate='Mean4Std2',baseline=base)
            lines.append(f'| {LABEL[pair]} | {base} | {average(rr,"delta_CE_test"):+.6f} | {average(rr,"gross_payload_saving_bytes"):+.1f} | '
                f'{average(rr,"delta_side_bytes"):+.1f} | {average(rr,"net_saving_bytes"):+.1f} | {interval(rr,"net_saving_bytes",1)} | {sum(r["margin_pass"] for r in rr)}/3 |')
    lines += ['', '![PREDICTED net]('+(run/'plots/predicted_net.png').as_posix()+')', '',
        f'Все paired forecasts: {link(run/"predicted-net.csv")}. Real entropy file size = null; '
        'положительная CE разность сама по себе не является экономией файла.', '',
        '## 8. Decoder reproducibility и проверки', '',
        'Два новых decoder process, по одному на пару, читают только coarse symbols, decoder metadata и переданные thresholds/specs. '
        'Каждый один раз воспроизводит geometry/coarse contexts в закреплённой CPU arithmetic, затем все 18 class arrays '
        '(6 arms × 3 seeds), по 524288 slots × 2 channels. **Все 36 arrays совпали побитно**. '
        'Fine targets, parent contexts.npz, полный xyz bin, checkpoint и probability masses decoder для классов не читает.', '',
        'Нормальные read audits имеют пустой список blocked reads; отдельные negative probes блокируют четыре запрещённых пути на пару. '
        'Audit hook контролирует этот Python decoder, не является OS sandbox. Code/stdlib imports разрешены. GPU не использовался; '
        'приблизительный CPU/GPU feature parity прошлого этапа не подменяет текущую exact class equality.', '',
        '| Проверка | Статус |', '|---|---|',
        f'| Synthetic class/fit/serializer tests: {unit["tests"]} | {unit["status"]} |',
        f'| Predecessor manifests, hashes, PASS records | {inputs["status"]} |',
        '| Slots split disjoint/complete; channels kept together | PASS |',
        '| Train-only edges/counts, unchanged targets, model freeze before test | PASS |',
        f'| Exact fresh decoder classes, all slots × both channels × all arms/seeds | {replay["status"]} |',
        '| Four forbidden-read probes per pair | PASS |',
        '| Positive masses/sum65536; dry threshold+mass+metadata roundtrip | PASS |', '',
        f'{link(run/"replay-validation.json")}; {link(run/"input-validation.json")}; '
        f'{link(run/"splits.json")}. Итоговая проверка сохранности артефактов и критический review записываются отдельно после этого отчёта.', '',
        '## 9. Вычислительная стоимость', '',
        f'Предварительная оценка: {protocol["cost_forecast"]["cpu_seconds_conservative"]} s CPU и '
        f'{protocol["cost_forecast"]["peak_additional_mib_conservative"]} MiB; без N×C×256 tensor.', '',
        f'Fit/validation/dry serializations: {freeze["wall_seconds"]:.3f} s wall, {freeze["cpu_seconds"]:.3f} s CPU, '
        f'peak total process RSS {freeze["peak_rss_mib"]:.2f} MiB. Test/paired/forecasts: {decision["wall_seconds"]:.3f} s wall, '
        f'{decision["cpu_seconds"]:.3f} s CPU, peak RSS {decision["peak_rss_mib"]:.2f} MiB.', '',
        '| Decoder pair | wall s | CPU s | peak RSS MiB |', '|---|---:|---:|---:|']
    for pair in PAIRS:
        r=load(run/pair/'decoder_replay/read-audit.json')
        lines.append(f'| {LABEL[pair]} | {r["wall_seconds"]:.3f} | {r["cpu_seconds"]:.3f} | {r["peak_rss_mib"]:.2f} |')
    lines += ['', 'Этапы выполнялись последовательно. RSS — total process, не сумма одновременно живущих копий. '
        'Startup, разработка/обсуждение и визуальный review не входят в вычислительные интервалы fit/test.', '',
        '## 10. Ответы на исследовательские вопросы и GO / NO-GO', '']
    def statement(candidate,baseline,group='all'):
        pieces=[]
        for pair in PAIRS:
            rr=select(paired,pair=pair,candidate=candidate,baseline=baseline,stratum=group,channel='both')
            pieces.append(f'{LABEL[pair]} {average(rr,"gain_bits_per_symbol"):+.6f} bits/symbol')
        return '; '.join(pieces)
    lines += [
        '1. **Canonical8 против Geometry4:** '+statement('Canonical8','Geometry4')+'. Знак оценивается на одинаковых test slots.',
        '2. **Mean8 против Canonical8:** '+statement('Mean8','Canonical8')+'. Это проверка среднего относительно representative, отдельно от Std.',
        '3. **Mean4×Std2 против Mean8 при C≤10:** '+statement('Mean4Std2','Mean8')+'. Равенство max C не гарантирует равенства effective capacity.',
        '4. **Дополнительная польза Std внутри G3:** против Mean8 '+statement('Mean4Std2','Mean8','G3')+'; против Mean4 '+statement('Mean4Std2','Mean4','G3')+'. Вырождение binning и эти разности ограничивают вывод H1.',
        '5. **L5 против L6:** collision regimes, coarse tables и effective Std classes различаются. Различие уровней измерено, причинный эффект только числа коллизий не выделен.',
        f'6. **Устойчивость seeds/channels:** строгие положительные gain checks не пройдены в {decision["nonpositive_gain_checks"]} из '
        f'{decision["gain_checks"]+decision["withinG3_vsMean4_checks"]} проверок. Полная детализация есть в paired CSV; нулевой gain не считается положительным.',
        f'7. **Оплата модели:** safety margin не пройден в {decision["cost_failures"]} из {decision["cost_checks"]} основных pair/seed/comparator checks. '
        'Оценка оплачивает самый короткий measured transport каждого baseline и candidate.',
        f'8. **Переход к bitstream: {decision["decision"]}.** Решение относится к этой H1 и заданным шести arms; actual entropy coding автоматически не запускается.',
        '9. **Не подтверждено:** actual file reduction, full-grid/scene gain, generalization на другие checkpoints/scenes/quantizers, spatially independent prediction, '
        'переносимость exact classes на произвольный CPU/GPU runtime, самостоятельная научная новизна Mean+Std. Prior art заново не исследовался.',
        '10. **Граница отрицательного вывода:** этот fixed Mean4×Std2 protocol не даёт достаточного основания для следующего compressor stage. '
        'Он не доказывает отсутствия всех dispersion-based зависимостей. Если продолжать отдельной задачей, протокол уже предлагает H2: '
        'integer Count6 = G0/G1/K1/K2/K3/K≥4 против Geometry4 на тех же frozen targets, с новым preregistration, train-only PMF и оплатой metadata. '
        'Текущие K-subgroups — только описание; Count6 не fit, не оценивался и не объявлен полезным.', '',
        'Отдельный результат для Mean8: относительно Geometry4 PREDICTED net составляет '
        + '; '.join(f'{LABEL[p]} {average(select(forecasts,pair=p,candidate="Mean8",baseline="Geometry4"),"net_saving_bytes"):+.2f} B' for p in PAIRS)
        + '. На L5 среднее полезно при неработающем Std-bin; на L6 снижение CE Mean8 не оплачивает рост модели. Это не разрешение запускать bitstream.', '',
        'На L6 знак Mean4×Std2 против Mean8 положителен внутри G3 во всех seeds/channels, но по K неоднороден: '
        'K=2 и K=3 в среднем проигрывают, K≥4 выигрывает. Относительно Mean4 gain положителен во всех трёх K-группах. '
        'Это поддерживает локальную предиктивную пользу данного Std-разбиения L6; независимый причинный эффект dispersion '
        'сверх любых более подробных geometry/multiplicity priors не установлен.', '',
        f'Машиночитаемое решение: {link(run/"decision.json")}. Критерий GO требует всех correctness PASS, '
        'положительных gains на обоих уровнях по каждому seed/channel в all и G3 против Geometry4/Canonical8/Mean8, '
        'плюс G3 advantage против Mean4 и safety margin каждого forecast. Никакая удачная subgroup не отменяет провал общего gate.', '',
        '## 11. Воспроизведение и артефакты', '',
        'Из <PROJECT_ROOT>, существующее CPU environment. Каждый новый run должен отсутствовать перед prepare. '
        'Команды fit/replay/test используют frozen artifacts, test нельзя повторить в том же run.', '',
        '```powershell',
        "$env:PYTHONDONTWRITEBYTECODE='1'",
        "$py='<PROJECT_ROOT>\\.tools\\phase2-plotting-env\\Scripts\\python.exe'",
        "$run='research/hashed_dispersion_heldout_<NEW_UNIQUE_ID>'",
        '& $py -m research.experiment_bench.hashed_interlevel.study prepare --run $run',
        '& $py -m research.experiment_bench.hashed_interlevel.unit_checks --run $run',
        '& $py -m research.experiment_bench.hashed_interlevel.study fit --run $run',
        '& $py -m research.experiment_bench.hashed_interlevel.study replay --run $run',
        '& $py -m research.experiment_bench.hashed_interlevel.study test --run $run',
        '& $py -m research.experiment_bench.hashed_interlevel.report --run $run',
        '& $py -m research.experiment_bench.hashed_interlevel.audit --run $run',
        '& $py -m research.experiment_bench.hashed_interlevel.finalize --run $run',
        '```', '',
        f'Протокол/splits: {link(run/"PREREGISTERED_PROTOCOL.json")}, {link(run/"splits.json")}. '
        f'Validation: {link(run/"validation-scores.json")}. Test: {link(run/"test-scores.csv")}. '
        f'Paired: {link(run/"paired-differences.csv")}. Costs: {link(run/"model-sizes.csv")}. '
        f'Прогнозы: {link(run/"predicted-net.csv")}.', '',
        'В каждой pair directory сохранены splits_seed*.npz, decoder-specs.json, decoder replay class IDs/read-audit, '
        'model specs, train counts/masses, exact class arrays и три `.model` transport варианта. Test loss arrays содержат slot_index '
        'и loss[N_test,2] каждого arm для повторного анализа уже оценённого test; новые настройки на них запрещены без отдельного exploratory обозначения.', '',
        '**Остановка после этапов 2–3.** Предыдущие отчёты и данные остаются по прежним путям. Новый run имеет собственные отчёт, '
        'данные, графики и проверки; стадии bitstream/training не запускались.', '']
    with report.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write('\n'.join(lines))
    summary['presentation_wall_seconds']=time.perf_counter()-started
    summary['presentation_peak_rss_mib']=peak_rss_mib()
    summary['plot_sha256']={p.relative_to(run).as_posix():sha(p) for p in plots}
    summary['report_sha256']=sha(report)
    write_json(run/'report-summary.json',summary)
    print(json.dumps({'report':str(report),'decision':decision['decision'],
                      'seconds':summary['presentation_wall_seconds'],'peak_rss_mib':summary['presentation_peak_rss_mib']}))


if __name__=='__main__':
    main()
