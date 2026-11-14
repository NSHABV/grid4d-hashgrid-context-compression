import argparse
import os
from pathlib import Path
import numpy as np
from research.hashgrid_analysis.common import ROOT,read,write,digest
from research.hashgrid_analysis.plots import Writer
from .core import MODELS

def generate(out):
    result=read(out/'results.json');hist=np.load(out/'fitted_histograms.npz',allow_pickle=False)
    os.environ['MPLCONFIGDIR']=str(out/'matplotlib-cache')
    import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    plt.rcParams.update({'font.size':9,'svg.fonttype':'none','svg.hashsalt':'xyz34-feasibility-v1'})
    writer=Writer(out);rows=result['per_split'];summary=result['summary'];representative_seed=result['seeds'][0]
    # An a-priori representative split, never the model's most favorable test split.
    distributions=[]
    for name,method,k in MODELS:
        mid=name if method is None else method+'-'+name
        for channel in (0,1):
            prefix=f'random-seed{representative_seed}__ch{channel}__{mid}'
            counts=hist[prefix+'_train_counts'];masses=hist[prefix+'_masses'];edges=hist[prefix+'_edges'];n=counts.sum(axis=1)
            distributions.append({'model':name,'method':method or 'none','model_id':mid,'channel':channel,'train_counts':counts.tolist(),
                'probability':(masses.astype(np.float64)/65536).tolist(),'class_n':n.tolist(),'edges':edges.tolist()})
    write(out/'representative-distributions.json',{'split':'random','seed':representative_seed,'source':'fitted_histograms.npz',
        'source_sha256':digest(out/'fitted_histograms.npz'),'distributions':distributions})
    for d in distributions:
        C=len(d['class_n']);cols=min(4,C);nr=(C+cols-1)//cols;counts=np.array(d['train_counts']);prob=np.array(d['probability'])
        iid=next(r for r in distributions if r['model_id']=='IID' and r['channel']==d['channel'])['probability'][0]
        fig,axes=plt.subplots(nr,cols,figsize=(max(8,cols*3.5),max(3,nr*2.45)),squeeze=False)
        for cls,ax in enumerate(axes.flat):
            if cls>=C:ax.axis('off');continue
            count=d['class_n'][cls];empirical=counts[cls]/count if count else np.zeros(256)
            ax.stairs(empirical,np.arange(257),color='#195e8a',label='empirical train frequency / n')
            ax.plot(np.arange(256),iid,'--',color='#bd6038',lw=.8,label='smoothed IID')
            is_boundary=(d['model']=='Boundary' and cls==1) or (d['method']!='none' and cls==C-1)
            ax.set(title=f'class {cls}, n={count}'+(' boundary' if is_boundary else '')+(' EMPTY' if count==0 else ''),
                xlabel='Fine symbol q4 [0..255]',ylabel='Probability / relative frequency',xlim=(0,255),ylim=(1e-6,1),yscale='log')
        axes.flat[0].legend(fontsize=6)
        title=f'{d["model_id"]}, channel{d["channel"]}: training conditional histograms'
        writer.save(fig,f'figures/distributions/{d["model_id"]}-ch{d["channel"]}',title,'representative-distributions.json',kind='training empirical distributions',
            limitations='Seed0 random split, fixed before scoring. Empirical zeros are clipped by the log display; empty classes have no empirical observations and finite uniform smoothing. All256 counts are saved.',measurements=int(counts.sum()))
        fig,ax=plt.subplots(figsize=(11,max(3.5,.32*C+2)))
        im=ax.imshow(prob,origin='lower',aspect='auto',interpolation='nearest',norm=LogNorm(vmin=1/65536,vmax=1),extent=(-.5,255.5,-.5,C-.5))
        ax.set(xlabel='Fine symbol q4 [0..255]',ylabel='Context class',title=f'train n={counts.sum()}; classes={C}')
        ax.set_yticks(np.arange(C));fig.colorbar(im,ax=ax,label='Finite conditional probability, log scale')
        writer.save(fig,f'figures/probabilities/{d["model_id"]}-ch{d["channel"]}',f'{d["model_id"]}, channel{d["channel"]}: p(q4|class)','representative-distributions.json',
            kind='training fitted finite probability model',limitations='Uniform color limits1/65536..1 for every model/channel. No test observations fitted.',measurements=int(counts.sum()))
    names=['IID','Boundary','Spatial-4','Spatial-8','Spatial-16'];kinds=result['split_regimes']
    def group(kind,channel,method):
        return [next(r for r in summary if r['split']==kind and r['channel']==channel and r['model']==name and r['method']==('none' if name in ('IID','Boundary') else method)) for name in names]
    for method in ('uniform','quantile'):
        fig,axes=plt.subplots(len(kinds),3,figsize=(15,len(kinds)*3.3),squeeze=False)
        for i,kind in enumerate(kinds):
            for j,ch in enumerate((0,1,'total')):
                data=group(kind,ch,method);ax=axes[i,j]
                ax.bar(names,[r['heldout_bits_per_symbol'] for r in data],yerr=[r['heldout_bits_per_symbol_std'] for r in data],capsize=3)
                ax.set(title=f'{kind}, channel {ch}',ylabel='Test bits / scalar symbol',xlabel='Probability model');ax.tick_params(axis='x',rotation=25)
        writer.save(fig,f'figures/crossentropy-{method}',f'{method}: held-out cross entropy, mean over3 seeds','results.json',kind='held-out measured predictive cost',
            limitations='Error bars are split standard deviation, not confidence intervals. Total divides both-channel bits by2*N. Spatial split test sizes vary; each seed has equal weight.')
        fig,axes=plt.subplots(2,1,figsize=(11,9))
        data=group('random','total',method);x=np.arange(5)
        for ax,baseline in zip(axes,('iid','boundary')):
            ax.bar(x-.15,[r['projected_payload_saving_vs_'+baseline+'_bytes'] for r in data],width=.3,label='Projected payload saving')
            ax.bar(x+.15,[r['primary_extra_overhead_vs_'+baseline+'_bytes'] for r in data],width=.3,label='Extra model bytes: existing dense uint32')
            ax.plot(x,[r['primary_estimated_net_vs_'+baseline+'_bytes'] for r in data],'ko',label='Net estimated saving')
            ax.axhline(0,color='gray',lw=.8);ax.set(xticks=x,xticklabels=names,xlabel=f'Model; baseline={baseline}',ylabel='Estimated full-L4 bytes');ax.legend()
        writer.save(fig,f'figures/net-saving-{method}',f'{method}: estimated payload benefit vs primary model cost','results.json',kind='estimated full-L4 extrapolation',
            limitations='No bitstream exists. Payload is held-out rate extrapolated to410758 symbols. Model cost uses dense uint32 masses plus boundaries and hypothetical JSON; common framing omitted.')
        fig,axes=plt.subplots(3,2,figsize=(13,11))
        for i,k in enumerate((4,8,16)):
            for ch in (0,1):
                d=next(r for r in distributions if r['model_id']==f'{method}-Spatial-{k}' and r['channel']==ch);ax=axes[i,ch];C=len(d['class_n'])
                prefix=f'random-seed{representative_seed}__ch{ch}__{method}-Spatial-{k}'
                # Occupancy is read from the saved CPU analysis CSV, not recomputed from test-fitting.
                import csv
                with (out/'class-occupancy.csv').open(encoding='utf-8') as f:
                    selected=[r for r in csv.DictReader(f) if r['split']=='random' and int(r['seed'])==representative_seed and int(r['channel'])==ch and r['model_id']==f'{method}-Spatial-{k}']
                xx=np.arange(C)
                for offset,field,label in ((-.25,'train_n','training'),(0,'validation_n','validation'),(.25,'test_n','test')):
                    ax.bar(xx+offset,[int(r[field]) for r in selected],width=.25,label=label)
                empty=[int(r['class']) for r in selected if r['empty_train']=='True']
                ax.set(title=f'{method}, K={k}, channel{ch}; empty train classes={empty}',xlabel=f'Context class (last={C-1}: boundary)',ylabel='Rows (symlog includes zero)',yscale='symlog')
                ax.legend(fontsize=7)
        writer.save(fig,f'figures/occupancy-{method}',f'{method}: context occupancy, separate train/validation/test','class-occupancy.csv',kind='measured class counts',
            limitations='Random seed0 representative only; every split is in CSV. Duplicate quantile boundaries retain empty classes and their model cost.')
        fig,axes=plt.subplots(3,1,figsize=(12,11))
        for ax,ch in zip(axes,(0,1,'total')):
            for offset,k in zip((-.16,0,.16),(4,8,16)):
                data=[next(r for r in rows if r['split']==kind and r['seed']==seed and r['channel']==ch and r['model_id']==f'{method}-Spatial-{k}') for kind in kinds for seed in result['seeds']]
                y=np.array([r['gain_vs_boundary_bits_per_symbol'] for r in data]);low=np.array([r['gain_vs_boundary_ci95_low'] for r in data]);high=np.array([r['gain_vs_boundary_ci95_high'] for r in data])
                ax.errorbar(np.arange(len(data))+offset,y,yerr=np.maximum(np.stack((y-low,high-y)),0),fmt='o',capsize=3,label=f'K={k}')
            labels=[kind+f' s{seed}' for kind in kinds for seed in result['seeds']]
            ax.axhline(0,color='gray',lw=.8);ax.set(xticks=np.arange(len(labels)),xticklabels=labels,ylabel='Gain vs boundary (bits/symbol)',title=f'Channel {ch}')
            ax.tick_params(axis='x',rotation=20);ax.legend()
        writer.save(fig,f'figures/stability-{method}',f'{method}: incremental predictive gain across fixed splits','results.json',kind='held-out gains with clustered bootstrap CI',
            limitations='95% percentile spatial-cluster bootstrap conditional on fit: width8 random/block8, width16 block16. Block16 has only12 test clusters. No retraining or multiple-comparison correction; seeds reuse one scene.')
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for ax,baseline in zip(axes,('iid','boundary')):
        x=np.arange(3)
        for offset,scenario in zip((-.27,-.09,.09,.27),('dense_u32','packed_u16','sparse_default_u16','no_overhead')):
            data=[next(r for r in summary if r['split']=='random' and r['channel']=='total' and r['model_id']==f'quantile-Spatial-{k}') for k in (4,8,16)]
            field='primary_estimated_net_vs_'+baseline+'_bytes' if scenario=='dense_u32' else scenario+'_net_vs_'+baseline+'_bytes'
            ax.bar(x+offset,[r[field] for r in data],width=.18,label=scenario)
        ax.axhline(0,color='gray',lw=.8);ax.set(xticks=x,xticklabels=['K4','K8','K16'],xlabel=f'Quantile model; baseline={baseline}',ylabel='Estimated full-L4 net saving (bytes)');ax.legend(fontsize=7)
    writer.save(fig,'figures/overhead-sensitivity','Predicted profitability depends on how probability masses are stored','results.json',kind='estimated storage sensitivity',
        limitations='Dense uint32 is the current bench format. Packed/sparse uint16 are lossless feasible storage estimates, not implemented stream formats. No_overhead is only an optimistic bound.')
    write(out/'figure-index.json',writer.records)
    return writer.records

def report(out,figures):
    r=read(out/'results.json');s=r['summary'];v=read(out/'validation.json');manifest=read(out/'manifest.json')
    def selected(kind,channel,method,name):return next(a for a in s if a['split']==kind and a['channel']==channel and a['method']==method and a['model']==name)
    q8=selected('random','total','quantile','Spatial-8');b=selected('random','total','none','Boundary');iid=selected('random','total','none','IID')
    lines=['# Feasibility: decoder-available G_xyz L3 → L4','',f'**{r["verdict"]}**, при компактном хранении вероятностных таблиц. Текущий dense uint32 формат не окупается.','',
        '## Краткий результат','',
        f'Quantile-8 даёт {q8["gain_vs_boundary_bits_per_symbol"]:.6f} bits/symbol сверх boundary-only на random test (среднее 3 seeds).',
        f'На block8 и block16 holdout средний дополнительный выигрыш: {selected("block-8","total","quantile","Spatial-8")["gain_vs_boundary_bits_per_symbol"]:.6f} и {selected("block-16","total","quantile","Spatial-8")["gain_vs_boundary_bits_per_symbol"]:.6f} bits/symbol.',
        f'Прогноз для всех L4 symbols относительно boundary: payload экономит {q8["projected_payload_saving_vs_boundary_bytes"]:.1f} B; dense-u32 net={q8["primary_estimated_net_vs_boundary_bytes"]:.1f} B, packed-u16 net={q8["packed_u16_net_vs_boundary_bytes"]:.1f} B, sparse-default-u16 net={q8["sparse_default_u16_net_vs_boundary_bytes"]:.1f} B.',
        '**Это оценки, а не измеренные compressed bytes. Ни новый coder, ни production encoder/decoder, ни neural model не реализованы.**','',
        '## Данные и гипотезы','',f'Checkpoint SHA256: `{r["checkpoint_sha256"]}`. Только bouncingballs / xyz / L3→L4 / table-wise8 /2 channels.',
        'Все 205379 fine rows учтены: 195112 in-bounds и 10267 OOB. Используются исходные pairs и сохранённый decoder-available GPU float32 context; checkpoint/raw L3 embeddings не читаются.',
        'H0: известное coarse feature не даёт практически существенного улучшения предсказания. H1: условная модель уменьшает held-out codelength и потенциально покрывает стоимость модели.',
        'IID оценивается отдельно по каждому feature channel. Boundary использует только геометрически воспроизводимый in_bounds. Spatial добавляет класс того же coarse channel; OOB всегда отдельный класс.','',
        '## Протокол','',
        'Seeds 0,1,2; slot split 64% training /16% validation /20% final test. Spatial regimes назначают целые кубические блоки ширины 8 и 16 в одну часть; размеры выборок могут отличаться от номинальных процентов.',
        'Uniform-width и quantile bins (4/8/16 внутренних классов) строятся только на training in-bounds features. Равные quantile edges сохраняются; searchsorted(side=right), вне обученного range — крайний класс. Пустые классы не удаляются задним числом.',
        'Сглаживание alpha=1. Используется существующий `experiment_bench.models.frequencies`:256 strictly-positive integer masses, сумма65536. Основные cross-entropies по finite probabilities; аналитический Laplace вариант сохранён отдельно.',
        'Training empirical MI считается отдельно от held-out gain; incremental MI условно по in_bounds не включает выигрыш только от границы.',
        'Для test T стоимость R = −Σ(i∈T) log2 p(q_i|class_i); bits/symbol = R/|T|. Для total суммируются стоимости двух каналов и делятся на 2|T|.',
        'Для каждого заранее заданного storage scenario модель выбирается только по validation прогнозу payload+overhead для L4. Test оценивается после выбора. Все заранее заданные модели также показаны как диагностические сравнения; победитель по final test не выбирался.',
        '95% CI — cluster bootstrap1000 repetitions, с фиксированной fitted model: spatial cluster width8 для random/block8 и width16 для block16. Последний режим имеет12 test blocks; CI не учитывает повторное обучение или вариацию сцен.',
        'Среднее в таблицах: равный вес 3 seeds, а не объединённая эмпирическая выборка. Seeds используют одну сцену и пересекающиеся данные; это не независимые репликации сцены.','',
        '## Итоговая таблица: random splits, среднее3 seeds','',
        '| Bins / Model | Channel | Held-out bits/symbol | Gain vs IID | Gain vs boundary | Model overhead B (u32) | Estimated net B vs IID |','|---|---|---:|---:|---:|---:|---:|']
    for a in s:
        if a['split']!='random':continue
        lines.append(f'| {a["method"]} / {a["model"]} | {a["channel"]} | {a["heldout_bits_per_symbol"]:.6f} | {a["gain_vs_iid_bits_per_symbol"]:.6f} | {a["gain_vs_boundary_bits_per_symbol"]:.6f} | {a["primary_model_overhead_bytes"]:.1f} | {a["primary_estimated_net_vs_iid_bytes"]:.1f} |')
    lines+=['','Model overhead — абсолютная стоимость candidate; net вычитает **дополнительную** стоимость относительно baseline, не абсолютную. Total bits/symbol = оба канала /2N. [Полная summary](summary.csv), [все splits/CI/границы](per-split-results.csv).','',
        '## Overhead и break-even','',
        'Primary dense_u32: C×256×4 B на channel, как существующие `.to_bytes()` probability masses. Нужны ещё(K−1)×8 B bin edges и измеренная длина гипотетического компактного JSON metadata. Bin edges передаются заранее; они не бесплатны.',
        'CDF257×4 B на class производен из масс: учитывается как decoder memory, без двойного начисления в размер файла. Training counts не передаются дополнительно к probability masses.',
        'Packed_u16: C×256×2 B. Все массы≤65281 (sum65536, остальные255 masses≥1), поэтому упаковка вuint16 без потери возможна и проверена на synthetic arrays. Bench stream сейчас хранитuint32; формат потребовал бы отдельной адаптации.',
        'Sparse-default-u16: на class default mass u16 + exception count u16 +3 B на исключение(symbol u8,mass u16). Это размер предварительного представления exact finite masses, а не разработанный bitstream. Model/header/framing новой схемы не проверялись actual coding.',
        'No-overhead — только верхняя граница возможной экономии. Common geometry/quantization metadata, уже известные baseline/decoder, отменяются при сравнении. Неизвестные дополнительные framing/termination bytes будущей схемы не выдаются за ноль фактического файла.',
        'Проекция rate×N использует только 410758 L4 scalar symbols. Прогноз полного размера сцены или сжатия Gaussian/MLP не строится.',
        'Estimated net bytes = gain_bits_per_symbol × N_symbols/8 − (model_candidate_bytes − model_baseline_bytes). Break-even = 8 × extra_model_bytes/N_symbols.','',
        '| Quantile model | Gain vs boundary | u32 break-even bits/symbol | payload saving B | u32 net B | packed-u16 net B | sparse-u16 net B |','|---|---:|---:|---:|---:|---:|---:|']
    for k in (4,8,16):
        a=selected('random','total','quantile',f'Spatial-{k}')
        lines.append(f'| K{k} | {a["gain_vs_boundary_bits_per_symbol"]:.6f} | {a["break_even_vs_boundary_bits_per_symbol"]:.6f} | {a["projected_payload_saving_vs_boundary_bytes"]:.1f} | {a["primary_estimated_net_vs_boundary_bytes"]:.1f} | {a["packed_u16_net_vs_boundary_bytes"]:.1f} | {a["sparse_default_u16_net_vs_boundary_bytes"]:.1f} |')
    lines+=['', 'Для quantile-8 пороги окупаемости относительно boundary-only (среднее 3 random seeds):', '',
        '| Storage | Extra model B | Break-even bits/symbol |', '|---|---:|---:|']
    for scenario,field in [('dense_u32','primary_estimated_net_vs_boundary_bytes'),('packed_u16','packed_u16_net_vs_boundary_bytes'),('sparse_default_u16','sparse_default_u16_net_vs_boundary_bytes')]:
        extra=q8['projected_payload_saving_vs_boundary_bytes']-q8[field]
        lines.append(f'| {scenario} | {extra:.1f} | {8*extra/(r["rows"]*r["channels"]):.6f} |')
    lines+=['','## Occupancy и отличие каналов','',
        'Все class train/validation/test counts, empty/tiny classes(<100 training rows), total variation и JS divergence относительно training IID: [class-occupancy.csv](class-occupancy.csv).','',
        '| Quantile-8, random seed0 | train rows по классам0..8 (последний OOB) |','|---|---|']
    import csv
    with (out/'class-occupancy.csv').open(encoding='utf-8') as f:occupancy=list(csv.DictReader(f))
    for ch in (0,1):
        counts=[int(a['train_n']) for a in occupancy if a['split']=='random' and int(a['seed'])==0 and int(a['channel'])==ch and a['model_id']=='quantile-Spatial-8']
        lines.append(f'| ch{ch} | {counts} |')
    lines+=['','Класс 5 пуст в обоих каналах этого представительного split из-за tied quantile boundaries; он всё равно оплачен dense model. Во всех splits пустые/малые классы маркированы явно.',
        'Для spatial и boundary OOB distribution одинакова, поэтому пространственный дополнительный gain на OOB равен 0.', '',
        '### In-bounds и OOB отдельно', '',
        'Random holdout, среднее 3 seeds; bits/symbol внутри каждой указанной части, без смешивания её размера с полным test.', '',
        '| Model | Channel | In-bounds bits/symbol | OOB bits/symbol | Interior gain vs boundary | OOB gain vs boundary |',
        '|---|---|---:|---:|---:|---:|']
    for channel in (0,1,'total'):
        for model_id in ('IID','Boundary','quantile-Spatial-8'):
            group=[a for a in r['per_split'] if a['split']=='random' and a['channel']==channel and a['model_id']==model_id]
            values=[np.mean([a[field] for a in group]) for field in ('in_bounds_bits_per_symbol','out_of_bounds_bits_per_symbol','in_bounds_gain_vs_boundary_bps','out_of_bounds_gain_vs_boundary_bps')]
            lines.append(f'| {model_id} | {channel} | '+' | '.join(f'{value:.6f}' for value in values)+' |')
    lines+=['', '### Training empirical MI', '',
        'MI ниже оценена на training частотах без сглаживания; это in-sample диагностическая величина, не held-out выигрыш и не размер bitstream.', '',
        '| Quantile-8 | I(class;q4), bits/symbol | I(coarse_class;q4|in_bounds), weighted bits/symbol |', '|---|---:|---:|']
    for channel in (0,1,'total'):
        a=selected('random',channel,'quantile','Spatial-8')
        lines.append(f'| {channel} | {a["training_empirical_MI_bits"]:.6f} | {a["training_incremental_MI_given_bounds_bits"]:.6f} |')
    lines+=['',
        '## Устойчивость: Quantile-8','', '| Split | Channel | Gain vs boundary mean | Min..max по seeds | Std | u32 net vs boundary B |','|---|---|---:|---|---:|---:|']
    for kind in r['split_regimes']:
        for ch in (0,1,'total'):
            a=selected(kind,ch,'quantile','Spatial-8')
            lines.append(f'| {kind} | {ch} | {a["gain_vs_boundary_bits_per_symbol"]:.6f} | {a["gain_vs_boundary_bits_per_symbol_min"]:.6f}..{a["gain_vs_boundary_bits_per_symbol_max"]:.6f} | {a["gain_vs_boundary_bits_per_symbol_std"]:.6f} | {a["primary_estimated_net_vs_boundary_bytes"]:.1f} |')
    lines+=['','## Выбор по validation','',
        'Dense-u32 выбирает IID для всех18 channel/split combinations. Packed-u16 выбирает quantile-8 либоquantile-4. Sparse-u16 выбирает quantile-8 либоquantile-16. Подробные validation objectives и независимые final test metrics: [model-selection.json](model-selection.json).',
        f'Прескриптивный критерий PROMISING: positive incremental CI lower bound и положительная mean-rate net projection vs обе baselines во всех9 splits хотя бы при одном явно указанном feasible storage scenario. Получены кандидаты: `{r["overhead_scenario_promising_candidates"]}`.',
        'Это feasibility screening, не multiple-testing-corrected подтверждение выбранного нового метода. Net projection CI не гарантирован положительным для каждого scenario; confidence intervals не покрывают неизвестный actual stream overhead.','',
        '## Ответы на исследовательские вопросы','',
        f'1. Измеримая зависимость есть: для quantile-8 training MI={q8["training_empirical_MI_bits"]:.6f}, incremental MI given bounds={q8["training_incremental_MI_given_bounds_bits"]:.6f} bits/symbol (random, среднее 3 seeds). Только по этим in-sample величинам вывод не делался.',
        '2. Она улучшает held-out prediction: quantile контексты дают положительный incremental gain сверх boundary во всех random/spatial splits; у quantile-8 все clustered CI lower bounds>0.',
        '3. Дополнительный gain quantile-8 около0.19 bits/symbol, с явным разбросом по seeds и spatial regimes в таблице выше.',
        '4. Current dense-u32 стоимость не окупается. Компактные mass representations дают положительную прогнозную net экономию; actual profitability ещё не измерена.',
        '5. Каналы различаются: обычно gain ch0 больше, но оба канала дают воспроизводимый положительный gain; occupancy и CDF различаются.',
        '6. Quantile bins существенно лучше uniform-width. Результат сохраняется при spatial holdout, но absolute rates и величина gain зависят от удержанных областей. Больше классов не означает больше net saving.',
        '7. Имеет смысл отдельный небольшой actual coding эксперимент с существующим range engine и компактным хранением модели, если исследователь задаст такой следующий этап. Новый coder engine разрабатывать на основании этих данных не требуется.',
        '8. Вывод нельзя переносить на L5+: collisions нарушают биекцию slot↔vertex, меняют соответствия и target weights; decoder causality и coverage потребуется проверить заново.',
        '9. Альтернативы: spatial active/inactive regions, общий уровень амплитуды, квантование/outliers, shared initialization, tied float32 context values/ULP effects и локальная корреляция. Это не доказательство causal influence L3 на L4.','',
        '## Проверки и ограничения','',f'Unit tests: {v["unit_tests"]}; все integrity/leakage/probability/unit checks: [validation.json](validation.json), [tests.log](tests.log), [validation.log](validation.log).',
        *(['Исправлена ошибка имени поля при построении sensitivity plot и ширина одноклассового графика; численные расчёты не менялись. Журнал: [failure-history.json](failure-history.json).'] if (out/'failure-history.json').exists() else []),
        'GPU indexing NOT RUN здесь: предыдущая exhaustive parity подтверждена и использована, повторных GPU операций не было. Декодированный контекст сравнен с сохранённым audited fresh-process replay.',
        'Одна синтетическая сцена, один trained seed, одна пара уровней и table8 quantization; нет доказательства обобщения NVCC-style priors. Sparse MI biased и training-only; CI conditional-on-fit;12 spatial blocks в наиболее крупном holdout.',
        'Canonical context — сохранённый GPU float32. Пороги quantile могут быть близки к tied values/ULP; предыдущая CPU/GPU tolerance не доказывает идентичность class assignments на других платформах. Для actual decoder потребуется фиксированная воспроизводимая context arithmetic.',
        'Все savings estimated, actual_bitstream_bytes=null. Не выполнены actual entropy coding, новая модель Grid4D или обучение; это не незавершённые проверки данного диагностического этапа.',
        f'Полная повторяемость: {v.get("reproducibility","NOT RUN")}. [Reproducibility evidence](reproducibility.json).','',
        '## Воспроизведение','', '```powershell',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.xyz34_feasibility.run --output research/interlevel_xyz34_feasibility_new',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.xyz34_feasibility.finish --output research/interlevel_xyz34_feasibility_new',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.xyz34_feasibility.compare research/interlevel_xyz34_feasibility research/interlevel_xyz34_feasibility_new',
        '.tools/phase2-plotting-env/Scripts/python.exe -m unittest research.hashgrid_analysis.xyz34_feasibility.tests -v', '```',
        f'CPU compute: {manifest["seconds"]:.2f} s, environment `{manifest["environment"]}`. Existing matplotlib environment reused.','',
        '## Графики','',
        'Начать: crossentropy-quantile, overhead-sensitivity, stability-quantile; затем probability heatmaps и occupancy. Все PNG/SVG имеют exact source data/settings/SHA.',
        '| Figure | Type | Source |','|---|---|---|']
    for f in figures:lines.append(f'| [{f["title"]}]({f["png"]}) | {f["data_type"]} | [{f["source"]}]({f["source"]}) |')
    (out/'FEASIBILITY_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def finish(out,replot=True):
    figures=generate(out) if replot else read(out/'figure-index.json')
    from PIL import Image
    import xml.etree.ElementTree as ET
    checks=[];result=read(out/'results.json');summary=result['summary'];representative=read(out/'representative-distributions.json')['distributions']
    for r in figures:
        png=out/r['png'];settings=read(png.with_suffix('.plot.json'))
        with Image.open(png) as im:im.verify()
        assert np.asarray(Image.open(png).convert('RGB')).std()>0
        ET.parse(out/r['svg']);assert settings['source_sha256']==digest(out/r['source'])
        assert settings['checkpoint_sha256']==read(out/'results.json')['checkpoint_sha256']
        for a in settings['axes']:
            if a['yscale']=='log':assert a['ylim'][0]>0
            for image in a['images']:
                if image['norm_class']=='LogNorm':assert image['clim']==[1/65536,1]
        name=r['png']
        if name.startswith('figures/probabilities/'):
            model,channel=Path(name).stem.rsplit('-ch',1)
            d=next(d for d in representative if d['model_id']==model and d['channel']==int(channel))
            assert settings['axes'][0]['images'][0]['values']==d['probability']
        if name.startswith('figures/crossentropy-'):
            method=Path(name).stem.split('-',1)[1];names=['IID','Boundary','Spatial-4','Spatial-8','Spatial-16']
            for axis,(kind,ch) in zip(settings['axes'],[(kind,ch) for kind in result['split_regimes'] for ch in (0,1,'total')]):
                expected=[next(d['heldout_bits_per_symbol'] for d in summary if d['split']==kind and d['channel']==ch and d['model']==model and d['method']==('none' if model in ('IID','Boundary') else method)) for model in names]
                assert [bar['height'] for bar in axis['bars']]==expected
        if name=='figures/overhead-sensitivity.png':
            for axis,baseline in zip(settings['axes'],('iid','boundary')):
                expected=[]
                for scenario in ('dense_u32','packed_u16','sparse_default_u16','no_overhead'):
                    field='primary_estimated_net_vs_'+baseline+'_bytes' if scenario=='dense_u32' else scenario+'_net_vs_'+baseline+'_bytes'
                    expected +=[next(d[field] for d in summary if d['split']=='random' and d['channel']=='total' and d['model_id']==f'quantile-Spatial-{k}') for k in (4,8,16)]
                assert [bar['height'] for bar in axis['bars']]==expected
        checks.append({'test':r['png'],'status':'PASS','source':r['source'],'png_sha256':digest(png),'svg_sha256':digest(out/r['svg'])})
    validation=read(out/'validation.json');validation['figure_checks']=checks;write(out/'validation.json',validation)
    log=[a['status']+' '+a['test']+' input='+a['input'] for a in validation['checks']]
    log +=[a['status']+' figure '+a['test']+' source='+a['source'] for a in checks]
    log +=[validation['reproducibility']+' full independent CPU repeat','NOT RUN GPU indexing; reused prior exhaustive PASS']
    (out/'validation.log').write_text('\n'.join(log)+'\n',encoding='utf-8')
    report(out,figures)
    manifest=read(out/'manifest.json');manifest.update(status='READY',figures=len(figures),source_code_sha256={p.name:digest(p) for p in Path(__file__).parent.glob('*.py')});write(out/'manifest.json',manifest)
    print(read(out/'results.json')['verdict'],len(figures),'PNG+SVG figures',flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='research/interlevel_xyz34_feasibility');args=parser.parse_args();finish((ROOT/args.output).resolve())

if __name__=='__main__':main()
