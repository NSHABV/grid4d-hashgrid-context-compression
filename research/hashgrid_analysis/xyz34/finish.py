"""Plot saved verified pairs and publish the limited-scope Russian report."""
import argparse
import os
from pathlib import Path
import numpy as np
from PIL import Image
from research.hashgrid_analysis.common import ROOT,read,write,digest
from research.hashgrid_analysis.plots import Writer

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    out=Path(args.output).resolve();manifest=read(out/'manifest.json');validation=read(out/'validation.json')
    if validation['status']!='PASS':raise ValueError('Pair validation must pass before plotting')
    assert digest(out/'pairs.npz')==manifest['pair_sha256'] and digest(out/'pairs.csv')==manifest['csv_sha256']
    pairs=np.load(out/'pairs.npz',allow_pickle=False);valid=pairs['lookup_in_bounds'];n=len(valid)
    os.environ['MPLCONFIGDIR']=str(out/'matplotlib-cache')
    import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    plt.rcParams.update({'font.size':10,'svg.fonttype':'none','svg.hashsalt':'xyz34-decoder-pairs-v1'})
    seed=read(out/'config.json')['seed'];selection=np.sort(np.random.default_rng(seed).choice(n,min(n,10000),replace=False))
    histograms=[]
    for ch in range(2):
        x=pairs['coarse_context'][:,ch];y=pairs['fine_features_dequantized'][:,ch]
        xedges=np.linspace(float(x.min()),float(x.max()),65);yedges=np.linspace(float(y.min()),float(y.max()),65)
        all_counts,_,_=np.histogram2d(x,y,bins=(xedges,yedges));inside_counts,_,_=np.histogram2d(x[valid],y[valid],bins=(xedges,yedges))
        assert all_counts.sum()==n and inside_counts.sum()==valid.sum()
        histograms.append({'channel':ch,'x_edges':xedges.tolist(),'y_edges':yedges.tolist(),
            'all_counts':all_counts.astype(np.int64).tolist(),'in_bounds_counts':inside_counts.astype(np.int64).tolist()})
    source={'pairs_npz':'pairs.npz','pairs_csv':'pairs.csv','pairs_sha256':digest(out/'pairs.npz'),'checkpoint_sha256':manifest['checkpoint_sha256'],
        'seed':seed,'scatter_indices':selection.tolist(),'scatter_rows':len(selection),'all_rows':n,'in_bounds_rows':int(valid.sum()),
        'fine_feature_definition':'existing 8-bit symbols dequantized with their original quantization metadata; not raw fine floats',
        'histograms':histograms,'interpretation':'counts/scatter only; no conditional distribution, entropy, compression gain, or model fitted'}
    write(out/'visualization.json',source);writer=Writer(out)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ch,ax in enumerate(axes):
        inside=selection[valid[selection]];outside=selection[~valid[selection]]
        ax.scatter(pairs['coarse_context'][inside,ch],pairs['fine_features_dequantized'][inside,ch],s=5,alpha=.18,label=f'in-bounds sample n={len(inside)}')
        ax.scatter(pairs['coarse_context'][outside,ch],pairs['fine_features_dequantized'][outside,ch],s=8,alpha=.3,c='#c85b16',label=f'OOB zero-context sample n={len(outside)}')
        ax.set(xlabel=f'Decoded L3 interpolated feature {ch}',ylabel=f'Decoded L4 symbol feature {ch}',title=f'Channel {ch}');ax.legend(fontsize=8)
    writer.save(fig,'figures/scatter','xyz L3 -> L4: decoder-available context and fine feature','visualization.json',kind='deterministic sampled measured pairs',
        measurements=len(selection),limitations='GPU float32 context; fine feature is dequantized 8-bit label. OOB vertices have upstream zero context. Appearance is not coding evidence.')
    fig,axes=plt.subplots(2,2,figsize=(12,10))
    for ch,h in enumerate(histograms):
        positive=np.asarray(h['all_counts']);top=positive.max()
        for row,(label,field,count) in enumerate((('All stored rows','all_counts',n),('In-bounds vertex subset','in_bounds_counts',int(valid.sum())))):
            counts=np.array(h[field]);ax=axes[row,ch]
            im=ax.imshow(np.ma.masked_equal(counts.T,0),origin='lower',aspect='auto',interpolation='nearest',
                extent=[h['x_edges'][0],h['x_edges'][-1],h['y_edges'][0],h['y_edges'][-1]],norm=LogNorm(vmin=1,vmax=top))
            ax.set(xlabel=f'Decoded L3 interpolated feature {ch}',ylabel=f'Decoded L4 symbol feature {ch}',title=f'{label}, channel {ch}, n={count}')
            fig.colorbar(im,ax=ax,label='Vertex / stored-row count (log scale)')
    writer.save(fig,'figures/histogram-2d','Full-population coarse/fine histograms; boundary rows separated','visualization.json',kind='measured full-array counts',
        measurements=n,limitations='Identical bins/color limits for full and in-bounds panels within each channel; zero-count bins masked. No usefulness-of-compression claim.')
    write(out/'figure-index.json',writer.records)
    checks=[]
    for r in writer.records:
        with Image.open(out/r['png']) as image:image.verify()
        values=np.asarray(Image.open(out/r['png']).convert('RGB'));assert values.std()>0
        import xml.etree.ElementTree as ET
        ET.parse(out/r['svg']);settings=read((out/r['png']).with_suffix('.plot.json'))
        assert settings['source_sha256']==digest(out/'visualization.json') and settings['checkpoint_sha256']==manifest['checkpoint_sha256']
        if r['png'].endswith('histogram-2d.png'):
            image_axes=[a for a in settings['axes'] if a['images']]
            for row in range(2):
                for ch in range(2):
                    actual=image_axes[row*2+ch]['images'][0];h=histograms[ch]
                    assert actual['values']==np.array(h['all_counts' if row==0 else 'in_bounds_counts']).T.tolist()
                    assert actual['clim']==image_axes[ch]['images'][0]['clim']
        if r['png'].endswith('scatter.png'):
            for ch,ax in enumerate(settings['axes']):
                for col,mask in zip(ax['collections'],(valid[selection],~valid[selection])):
                    rows=selection[mask];expected=np.column_stack((pairs['coarse_context'][rows,ch],pairs['fine_features_dequantized'][rows,ch]))
                    np.testing.assert_array_equal(col['offsets'],expected)
        checks.append({'test':r['png'],'status':'PASS','source':'visualization.json','png_sha256':digest(out/r['png']),
            'svg_sha256':digest(out/r['svg']),'numeric_values_verified':True})
    validation['figure_checks']=checks;write(out/'validation.json',validation)
    with (out/'validation.log').open('a',encoding='utf-8') as log:
        for r in checks:log.write('PASS figure '+r['test']+' input='+r['source']+'\n')
    meta=manifest['metadata'];coarse=meta['coarse'];fine=meta['fine'];examples=read(out/'examples.json')
    report=['# Decoder-available пары G_xyz: уровни 3 → 4','', '**PAIRS VERIFIED** — только подготовка пар и проверка соответствия.','',
        '## Источники и результат','',f'Checkpoint: `{manifest["checkpoint"]}`; SHA256 `{manifest["checkpoint_sha256"]}`.',
        f'Уровни нумеруются с нуля. Использован существующий `{manifest["scope"]}-8` export и `research/grid4d/codec.py`; исходные данные не изменены.',
        f'L3: offsets [{coarse["offset_start"]}, {coarse["offset_end"]}), resolution {coarse["lookup_resolution"]}, {coarse["rows"]:,} строк.',
        f'L4: offsets [{fine["offset_start"]}, {fine["offset_end"]}), resolution {fine["lookup_resolution"]}, {fine["rows"]:,} строк.',
        f'Сохранено ровно **{n:,} пар**: {int(valid.sum()):,} вершин внутри [0,1]³ и {int((~valid).sum()):,} граничных вершин вне диапазона.',
        'Файлы: [pairs.csv](pairs.csv), [pairs.npz](pairs.npz), [decoder bundle](decoder_bundle/decoder_metadata.json), [validation](validation.json), [tests.log](tests.log), [fresh decoder audit](decoder-replay.audit.json).','',
        '## Математическое соответствие','',
        'Проверено полное совпадение allocation и CUDA lookup resolutions. Число строк равно произведению resolutions, поэтому используется плотная x-fastest индексация, без hash collisions и padding:',
        '`slot = vx + Rx*vy + Rx*Ry*vz`; `vx=slot%Rx`, `vy=(slot//Rx)%Ry`, `vz=slot//(Rx*Ry)`.',
        'Глобальный индекс строки равен `offsets[4] + slot`.',
        'CUDA получает `log2(saved_per_level_scale)` и вычисляет `s_l[d]=exp2f(l*log_q[d])*base[d]-1`; `R_l[d]=ceil(s_l[d])+1`.',
        f'Фактические scales: L3={coarse["scale"]}, L4={fine["scale"]}.',
        'Нормализованная координата вершины: `u=v/s_4`. NPZ содержит математическое отношение float64 и фактический float32 input CUDA.',
        'В допустимой области `p=u*s_3`, `b=floor(p)`, `h=(p-b)^2*(3-2*(p-b))`. Контекст — сумма восьми **деквантованных L3** признаков с весами произведений `h`/`1-h`.',
        'В CSV/NPZ оба fine symbols берутся из существующего uint8 payload с точным offset. Деквантованные fine features сохранены только для графиков и проверок; они не входят в вычисление контекста.','',
        '## Важное граничное ограничение','',
        'Отсутствие коллизий не означает, что все номинальные вершины лежат внутри [0,1]³. Здесь последняя fine-плоскость имеет координату `58/57.350231... > 1`.',
        'Эти вершины являются внешними опорными вершинами интерполяции. Официальный `kernel_grid` для запросов вне [0,1] возвращает ноль до lookup.',
        '**Все строки сохранены**, координаты не обрезаются и не заменяются на `v/(R-1)`. Для внешних вершин контекст равен официальному OOB zero и `lookup_in_bounds=0`.',
        'Это decoder-available fallback, а не ненулевая интерполяция в физически допустимой точке. Ненулевой контекст для этих строк потребует отдельного выбора правила представителя/продолжения; оно здесь не вводилось.','',
        '## Decoder-side reproducibility','',
        'Bundle содержит только L3 uint8 symbols и публичную metadata: offsets, resolutions, сохранённые base/per_level_scale, scales, quantizer min/max/step и правила float32 вычисления.',
        'При table-wise квантовании глобальные min/max/step являются известной metadata экспорта; decoder получает их заранее. Они не вычисляются повторно по fine-параметрам. Стоимость metadata не объявляется нулевой.',
        'Отдельный процесс восстановил все CPU и GPU контексты **побитово**. Аудит чтений разрешал только два bundle-файла среди исследовательских данных и запрещал checkpoint, исходные quantized payloads и файлы с fine targets.',
        'В GPU tensor для контекста присутствуют только строки до offsets[4]; L4 и последующие параметры отсутствуют. L0–L2 заполнены нулями и не влияют на output L3, потому что upstream kernel обрабатывает каждый уровень отдельно.',
        'CPU/GPU интерполяция сравнивается с измеренной погрешностью. Побитовое GPU воспроизведение доказано для текущего pinned окружения; переносимость floating-point контекста между платформами пока не заявляется.','',
        '## Проверки','', '| Проверка | Результат | Числа / доказательство |','|---|---|---|']
    for r in validation['checks']:
        details={k:v for k,v in r.items() if k not in ('test','status','input','log','core_source_sha256')}
        report.append(f'| {r["test"]} | {r["status"]} | `{details}` |')
    report+=['','6 независимых synthetic tests: обратная x-fastest индексация неквадратной сетки, отказ при padding/hash layout, дробная граница без clamp, аналитическая smoothstep интерполяция квантованных весов, OOB zero/отсутствие target dependency, известные symbols существующего quantizer.',
        'GPU проверки: все coarse и fine индексы, все контексты, fine vertex lookup внутри диапазона и дополнительная маленькая synthetic grid.','',
        '## Примеры','', '| fine slot | vertex | normalized u | in bounds | coarse context (2) | fine symbols (2) |','|---:|---|---|---:|---|---|']
    for r in examples:report.append(f'| {r["fine_slot_index"]} | {[r[k] for k in ("vertex_x","vertex_y","vertex_z")]} | {[round(r[k],8) for k in ("u_x","u_y","u_z")]} | {r["lookup_in_bounds"]} | {[round(r[k],8) for k in ("coarse_context_0","coarse_context_1")]} | {[r[k] for k in ("fine_symbol_0","fine_symbol_1")]} |')
    report+=['','## Визуализации','',
        '[Scatter](figures/scatter.png): deterministic sample 10000 строк; внешние вершины отмечены отдельно.',
        '[2D histogram](figures/histogram-2d.png): полный массив и только in-bounds вершины; общие bins/color limits внутри каждого feature channel.',
        'PNG, SVG, точные данные, settings и checkpoint/source SHA сохранены. Графики показывают пары, но не доказывают полезность контекста для сжатия. Никакие условные вероятности, MI/entropy, neural/collision-aware/temporal модели или coder здесь не строились.','',
        '## Воспроизведение','', 'Из <PROJECT_ROOT>, в новую директорию:', '```powershell',
        'wsl -d Ubuntu -- bash research/run_xyz34_compute.sh --output <PROJECT_ROOT>/research/interlevel_xyz34_new',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.xyz34.finish --output research/interlevel_xyz34_new', '```',
        'Для отдельного decoder replay:', '```powershell',
        'wsl -d Ubuntu -- bash research/run_xyz34_compute.sh decoder --bundle <PROJECT_ROOT>/research/interlevel_xyz34_results/decoder_bundle --output <PROJECT_ROOT>/research/interlevel_xyz34_results/replay_new.npz --gpu', '```',
        f'Compute этап: {manifest["seconds"]:.2f} s. Окружение: `{manifest["environment"]}`.',
        'Следующий этап — отдельно заданное построение/оценка условных распределений с явно выбранной обработкой внешних вершинок и правилами контекстной арифметики. Здесь работа остановлена.','']
    (out/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    manifest.update(status='PAIRS VERIFIED AND PLOTTED',figure_count=len(writer.records),plotting_environment={'python':__import__('sys').version,'numpy':np.__version__,'matplotlib':matplotlib.__version__})
    manifest['source_code_sha256']={f.name:digest(f) for f in Path(__file__).parent.glob('*.py')};write(out/'manifest.json',manifest)
    print('PAIRS VERIFIED AND PLOTTED:',n,'rows;',len(writer.records),'PNG+SVG figures')

if __name__=='__main__':main()
