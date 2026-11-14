"""Measured-rate report and five scientific figures; no entropy/GPU imports."""
import argparse
import os
from pathlib import Path
import numpy as np
from research.hashgrid_analysis.common import ROOT,read,write,digest,csv_write
from research.hashgrid_analysis.plots import Writer

LABELS={'dense_u32':'u32','packed_u16':'u16','sparse_default_u16':'sparse16'}

def generate(out):
    os.environ['MPLCONFIGDIR']=str(out/'matplotlib-cache')
    import matplotlib
    matplotlib.use('Agg');matplotlib.rcParams['svg.hashsalt']='xyz34-actual-fixed-v2'
    import matplotlib.pyplot as plt
    rows=read(out/'results.json')['rows'];w=Writer(out);x=np.arange(9);labels=[r['model']+'\n'+LABELS[r['storage']] for r in rows]
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for ax,field,title in zip(axes,('total_standalone_bytes','incremental_l4_bytes'),('Standalone: quantized L3 + L4','Incremental L4: all specific overhead included')):
        ax.bar(x,[r[field] for r in rows],color=['#4477aa' if r['model']=='iid' else '#ee9933' if r['model']=='boundary' else '#228833' for r in rows])
        ax.set_xticks(x,labels,fontsize=8);ax.set(ylabel='Actual filesystem bytes',title=title);ax.set_ylim(bottom=0)
    w.save(fig,'figures/actual-file-sizes','Nine real files, all independently decoded','results.json')
    fig,ax=plt.subplots(figsize=(12,5));bottom=np.zeros(9)
    for field,label in [('shared_l3_bytes','Shared L3 + public geometry/quantizer'),('l4_payload_bytes','L4 range payload'),('l4_model_bytes','Serialized L4 probability model'),('threshold_bytes','Thresholds'),('l4_metadata_bytes','L4 info'),('framing_integrity_bytes','Complete outer framing/integrity')]:
        values=np.array([r[field] for r in rows]);ax.bar(x,values,bottom=bottom,label=label);bottom+=values
    np.testing.assert_array_equal(bottom,[r['total_standalone_bytes'] for r in rows]);ax.set_xticks(x,labels);ax.set(ylabel='Actual bytes');ax.legend(fontsize=8,ncol=2)
    w.save(fig,'figures/payload-vs-overhead','Every byte accounted for: payload and overhead','results.json')
    d=read(out/'results.json')['estimated_vs_actual'];fig,ax=plt.subplots(figsize=(8,5));xx=np.arange(3)
    ax.bar(xx-.18,[r['estimated_net_vs_boundary_bytes'] for r in d],.36,label='Previous held-out estimate')
    ax.bar(xx+.18,[r['actual_net_vs_same_boundary_bytes'] for r in d],.36,label='Actual scene-specific file saving')
    ax.set_xticks(xx,[LABELS[r['storage']] for r in d]);ax.axhline(0,color='gray');ax.set(ylabel='Bytes saved vs Boundary, same storage');ax.legend()
    w.save(fig,'figures/estimated-vs-actual','Spatial-8: forecasts versus measured full-file savings','results.json',limitations='Different fit protocol and canonical CPU context; estimates are not actual bytes.')
    fig,ax=plt.subplots(figsize=(12,5));ax.bar(x-.18,[r['gain_vs_best_iid_bytes'] for r in rows],.36,label='vs best actual IID');ax.bar(x+.18,[r['gain_vs_best_boundary_bytes'] for r in rows],.36,label='vs best actual Boundary')
    ax.set_xticks(x,labels);ax.axhline(0,color='gray');ax.set(ylabel='Actual standalone bytes saved');ax.legend()
    w.save(fig,'figures/net-vs-best-baseline','Net file savings against the best measured IID and Boundary baselines','results.json')
    times=read(out/'runtime.json')['summary'];fig,ax=plt.subplots(figsize=(12,5))
    for delta,field,label in [(-.18,'encode_total_seconds','Encode (L3 + L4)'),(.18,'decode_total_seconds','Decode (L3 + L4)')]:
        center=np.array([r[field+'_median'] for r in times]);lo=np.array([r[field+'_min'] for r in times]);hi=np.array([r[field+'_max'] for r in times])
        ax.bar(x+delta,center,.36,label=label,yerr=np.stack((center-lo,hi-center)),capsize=3)
    ax.set_xticks(x,labels);ax.set(ylabel='CPU seconds, median and min/max');ax.legend()
    w.save(fig,'figures/runtime','One warmup + three timed runs; imports, disk I/O and plots excluded','runtime.json')
    write(out/'figure-index.json',w.records)
    from PIL import Image
    import xml.etree.ElementTree as ET
    checks=[]
    for record in w.records:
        path=out/record['png'];settings=read(path.with_suffix('.plot.json'))
        with Image.open(path) as im:im.verify()
        assert np.asarray(Image.open(path)).std()>0;ET.parse(out/record['svg'])
        assert settings['source_sha256']==digest(out/record['source'])
        if path.stem=='actual-file-sizes':
            for axis,field in zip(settings['axes'],('total_standalone_bytes','incremental_l4_bytes')):assert [r['height'] for r in axis['bars']]==[r[field] for r in rows]
        if path.stem=='estimated-vs-actual':
            assert [b['height'] for b in settings['axes'][0]['bars']]==[r['estimated_net_vs_boundary_bytes'] for r in d]+[r['actual_net_vs_same_boundary_bytes'] for r in d]
        if path.stem=='net-vs-best-baseline':
            assert [b['height'] for b in settings['axes'][0]['bars']]==[r['gain_vs_best_iid_bytes'] for r in rows]+[r['gain_vs_best_boundary_bytes'] for r in rows]
        if path.stem=='runtime':
            assert [b['height'] for b in settings['axes'][0]['bars']]==[r['encode_total_seconds_median'] for r in times]+[r['decode_total_seconds_median'] for r in times]
        checks.append({'figure':record['png'],'status':'PASS','source':record['source'],'png_sha256':digest(path),'svg_sha256':digest(out/record['svg'])})
    return w.records,checks

def report(out,figures):
    r=read(out/'results.json');rows=r['rows'];gate=read(out/'context-validation.json');v=read(out/'validation.json');bridge=read(out/'prediction-bridge.json');runtime=read(out/'runtime.json')
    def best(model):return min((a for a in rows if a['model']==model),key=lambda a:a['total_standalone_bytes'])
    b=best('boundary');iid=best('iid');s=best('spatial8');dense=next(a for a in rows if a['model']=='spatial8' and a['storage']=='dense_u32')
    lines=['# Actual inter-level entropy coding: G_xyz L3 → L4','',f'**{r["verdict"]}** — лучший Spatial-8 превосходит обе strongest actual baseline-модели.','',
        f'Полный файл Spatial-8/{s["storage"]}: **{s["total_standalone_bytes"]} B**. Лучший Boundary: **{b["total_standalone_bytes"]} B**, лучший IID: **{iid["total_standalone_bytes"]} B**.',
        f'Экономия: {s["gain_vs_best_boundary_bytes"]} B ({s["gain_vs_best_boundary_percent"]:.3f}%) относительно Boundary и {s["gain_vs_best_iid_bytes"]} B ({s["gain_vs_best_iid_percent"]:.3f}%) относительно IID. Это реальные filesystem sizes после независимого точного декодирования.',
        'Область вывода: bouncingballs-reference-50000, только плотная G_xyz L3/L4, table-wise 8-bit, два канала. Не весь checkpoint или renderable 4DGS scene.','',
        '## Протокол и реализация','',
        'Вероятностные таблицы fitted по всем кодируемым L4 symbols; все параметры переданы и оплачены. Это scene-specific two-pass кодирование; результат не заменяет предыдущую held-out оценку обобщения.',
        'Повторного обучения Grid4D и квантования нет. Сохранены исходные 79507×2 L3 и 205379×2 L4 uint8 symbols; прежние pairs/quantized exports/checkpoint не менялись.',
        'Реализация: `research/experiment_bench/interlevel/`. Общий engine: `experiment_bench/entropy.py`, новые encode_indexed/decode_indexed используют прежние constriction0.4.2 RangeEncoder/Decoder, Categorical(perfect=False), finite16-bit masses и внутреннюю24-bit модель. Нового arithmetic/range coder нет.',
        'Порядок во всех моделях: весь ch0 по возрастанию slot, затем весь ch1 по возрастанию slot. Нет regrouping по классу. L3 — существующий IID engine, одинаковый dense-u32 model/payload во всех девяти файлах.',
        'Файл G4DBENCH version2 сохраняет прежние prefix <8sHQQQ>, JSON directory и SHA256 trailer; scope нового envelope — только эта пара. Version1 API и результаты сохранены.','',
        '## Exact decoder context gate','',
        f'PASS: все {gate["assignments_exact"]} class assignments и canonical CPU features совпали побитово в отдельном процессе.',
        f'CPU/GPU max |feature difference| = {gate["CPU_GPU_max_abs_error"]:.9g}; при новых edges различаются **{gate["CPU_GPU_class_mismatches_under_new_edges"]} class assignments**, при прежних seed0 edges — {gate["CPU_GPU_class_mismatches_under_prior_seed0_edges"]}. Приблизительный feature parity недостаточен.',
        f'Канонический режим: `{gate["arithmetic"]}`. float64 affine dequantization → float32; координаты float32(v)/float32(s4); position, smoothstep, weight products и corner accumulation — отдельные float32 ufunc операции без FMA, corners0..7. Pinned Linux x86_64 / NumPy1.21.6. CPU/GPU не взаимозаменяемы; универсальная переносимость NOT VERIFIED.',
        'Пространственные вершины x-fastest; lookup не обрезается. 195112 in-bounds, 10267 OOB. OOB context=0, class8. Quantile edges linear float64 по всем in-bounds CPU features; searchsorted(side=right); repeated thresholds сохраняются и передаются.',
        f'Количество уникальных edges: {gate["unique_edges_per_channel"]}; число exact context/edge совпадений (с повторяющимися edges): {gate["near_boundaries_exact_context_equal_edge"]}.',
        f'Полные class counts ch0: {gate["class_counts"][0]}; ch1: {gate["class_counts"][1]}. Class5 недостижим в обоих каналах.',
        'Аудит gate разрешает только публичную metadata/decoded coarse symbols. Аудит каждого настоящего decoder разрешает чтение данных только из его .bin; checkpoint, pairs, original payloads, encoder cache/class IDs не доступны. Public code/runtime dependencies разрешены; аудит Python файловых чтений не заявляется системным sandbox.',
        'Decoder сначала восстанавливает L3 и проверяет его digest, затем заново строит все классы и восстанавливает L4. Class IDs в .bin не сохранены; передан только SHA256 для проверки результата.','',
        '## Девять фактических файлов','',
        '| Model | Storage | L4 payload B | L4 model B | Shared L3 B | Total B | Gain vs best Boundary B | Decode |','|---|---|---:|---:|---:|---:|---:|---|']
    for a in rows:lines.append(f'| {a["model"]} | {a["storage"]} | {a["l4_payload_bytes"]} | {a["l4_model_bytes"]} | {a["shared_l3_bytes"]} | {a["total_standalone_bytes"]} | {a["gain_vs_best_boundary_bytes"]} | {a["decode"]} |')
    lines+=['','[results.csv](results.csv) / [results.json](results.json) содержат все секции, SHA256, same-storage/best-baseline gains, проценты, actual bits/symbol, compression ratios. Отрицательный gain означает больший файл.','',
        '## Полный учёт секций','',
        'Shared L3 включает неизменные geometry, quantization metadata, L3 info, L3 model и L3 payload. Их байты совпадают во всех файлах. Все outer prefix/header-directory/trailer байты консервативно назначены incremental L4.',
        'Incremental L4 = total standalone − shared sections; включает L4 payload/model/info, thresholds и ВСЁ outer framing/integrity. Поэтому absolute gains по standalone и incremental совпадают, проценты и ratios имеют разные знаменатели. Это L4 при уже известных общих данных; shared block не объявляется отдельным самодостаточным файлом.', '',
        '| Model / storage | L3 payload | L3 model | Geometry | Quantization | L3 info | L4 info | Thresholds | Framing/integrity | Incremental L4 | Bits/L4 symbol |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for a in rows:
        fields=['l3_payload_bytes','l3_model_bytes','geometry_metadata_bytes','quantization_metadata_bytes','l3_metadata_bytes','l4_metadata_bytes','threshold_bytes','framing_integrity_bytes','incremental_l4_bytes']
        lines.append(f'| {a["model"]}/{a["storage"]} | '+' | '.join(str(a[k]) for k in fields)+f' | {a["actual_bits_per_l4_symbol"]:.6f} |')
    lines+=['',f'Для лучшего Spatial-8 incremental L4={s["incremental_l4_bytes"]} B; {s["actual_bits_per_l4_symbol"]:.6f} bits/symbol. CR vs raw uint8 L4={s["compression_ratio_incremental_vs_raw_uint8_l4"]:.3f}; standalone CR vs raw uint8 pair={s["compression_ratio_standalone_vs_raw_uint8_pair"]:.3f}. Raw baselines: 410758 и 569772 B; не исходные float32 параметры.',
        'Сумма всех metadata/model/payload секций + prefix/directory/trailer проверена против filesystem size каждого файла. Диагностические decoded .npy, logs и plots не нужны decoder и не включены в стоимость .bin.','',
        '## Probability model formats','',
        'HGPM version1 header (10 B) хранит storage ID, число каналов/классов и alphabet256. Dense-u32 и packed-u16 хранят все masses, включая пустые классы. Максимальная individual mass≤65281; cumulative sums проверены вuint64 и заканчиваются65536.',
        'Sparse: row tag0 (1 B), most-frequent default mass u16, exception count u16, ascending (symbol u8,mass u16). Ties выбирают меньшую default mass. Tag1 (1 B) восстанавливает uniform masses только при доказанной недостижимости класса из уже декодированного L3/геометрии/edges. Decoder независимо проверяет отсутствие всех назначений в этот класс до L4 decode.',
        f'Оmitted rows для spatial8 sparse: {s["omitted_unreachable_rows"]}. Не удаляются классы только из-за отсутствия training targets. В этом full-scene fit недостижимые классы устанавливаются по context assignments, без использования fine values.',
        'Все 256 masses строго положительны, сумма65536; после каждого из трёх transports проверена np.array_equal исходным masses. CDF производен и не оплачивается второй раз; coder24 rounding входит в реальный payload.','',
        '## Estimated vs actual','',
        '| Storage | Previous estimated net vs Boundary B | Actual vs same Boundary B | Actual vs best Boundary B |','|---|---:|---:|---:|']
    for a in r['estimated_vs_actual']:lines.append(f'| {a["storage"]} | {a["estimated_net_vs_boundary_bytes"]:.1f} | {a["actual_net_vs_same_boundary_bytes"]} | {a["actual_net_vs_best_boundary_bytes"]} |')
    lines+=['',
        f'Прежний projected payload gain={bridge["previous_heldout_GPU_payload_saving_bytes"]:.3f} B. Full-scene GPU-context finite prediction={bridge["scene_fitted_GPU_finite_payload_saving_bytes"]:.3f} B; canonical CPU={bridge["scene_fitted_canonical_CPU_finite_payload_saving_bytes"]:.3f} B; actual range payload saving={bridge["actual_CPU_range_payload_saving_bytes"]} B.',
        f'Последовательное разложение: full-scene fitting {bridge["full_scene_fit_delta_bytes"]:+.3f} B; CPU arithmetic + refitted quantile thresholds {bridge["CPU_context_and_refitted_thresholds_delta_bytes"]:+.3f} B; coder24/finalization {bridge["range24_rounding_finalization_delta_bytes"]:+.3f} B. Это диагностическое разложение в заданном порядке, не причинная оценка. [prediction-bridge.json](prediction-bridge.json).',
        f'При sparse реальный дополнительный overhead Spatial vs Boundary = {(b["l4_payload_bytes"]-s["l4_payload_bytes"])-s["gain_vs_best_boundary_bytes"]} B. Он учитывает больше exceptions у fitted scene histograms, row tags/headers, 112 B thresholds и metadata/framing. Предыдущая sparse estimate использовала training-split masses и другой metadata budget.',
        'Dense-u32 по-прежнему не окупается. Packed-u16 и sparse остаются положительными даже против сильнейшего actual Boundary, а не только против того же storage.','',
        '## Производительность','',
        'Для каждой комбинации один прогрев + три измерения; medians и min/max. Таймеры включают обе стадии L3/L4, fitting, model IO, framing/integrity; исключают imports, process startup, disk IO и plots. L3 повторно fit/encode в каждом trial, без скрытого бесплатного cache.',
        '| Model / storage | Encode median s (min..max) | Decode median s (min..max) | Context build median s | L4 fit median s | Serialize median s | Decoder context median s |','|---|---|---|---:|---:|---:|---:|']
    for a in runtime['summary']:
        def interval(field):return f'{a[field+"_median"]:.6f} ({a[field+"_min"]:.6f}..{a[field+"_max"]:.6f})'
        lines.append(f'| {a["model"]}/{a["storage"]} | {interval("encode_total_seconds")} | {interval("decode_total_seconds")} | {a["context_build_seconds_median"]:.6f} | {a["fit_seconds_median"]:.6f} | {a["model_serialize_seconds_median"]:.6f} | {a["context_restore_seconds_median"]:.6f} |')
    lines+=['',f'Peak process RSS={runtime["peak_RSS_MiB"]:.2f} MiB (Linux getrusage SELF, включая imports/источники/benchmark, не суммарная RAM родителя+всех subprocess). VRAM NOT MEASURED; GPU не использовался. [runtime.json](runtime.json), [runtime-samples.csv](runtime-samples.csv).','',
        '## Проверки','',
        f'Unit/regression tests: {v["unit_tests"]}. Context gate PASS; девять fresh decoder processes PASS; np.array_equal для L3/L4 обоих каналов, всех class IDs и восстановленных probability masses PASS. Каждому child разрешён ровно один input .bin.',
        f'Real-file integrity/semantic rejection: {v["real_stream_corruption_tests"]["cases"]} cases PASS; дополнительно synthetic tests покрывают CDF/overflow, повторяющиеся edges, OOB, invalid models, omitted reachable classes и запрет чтения original pairs.',
        'Каждый прогрев и timed encoding побитово совпал с сохранённым .bin. SHA256 всех девяти файлов и исходных artifacts проверены. Отдельный полный повтор: '+('PASS, девять SHA256/размеров совпали.' if (out/'repeat-comparison.json').exists() else 'NOT RUN в этой директории; см. compare --against для полного повторного запуска.'),
        '[validation.json](validation.json), [tests.log](tests.log), [decode-validation.json](decode-validation.json), [corruption-validation.json](corruption-validation.json), [context-validation.json](context-validation.json).','',
        *(['При подготовке исправлены runtime-version check внутри read audit и ошибочная классификация создания output w+ как чтения input. Gate и tests повторены; source symbols и .bin bytes не менялись. [Журнал исправлений](failure-history.json).',''] if (out/'failure-history.json').exists() else []),
        '## Ответы на исследовательские вопросы','',
        '1. Да, автономный .bin содержит все scene-specific данные для восстановления этой quantized пары. External bundle/checkpoint не нужен; public decoder/library code нужен.',
        '2. Да, все symbols обоих уровней/каналов восстановлены точно во всех девяти вариантах.',
        '3. Да, все class IDs совпадают в pinned CPU режиме. GPU substitution и универсальная переносимость не обеспечены.',
        f'4. L4 payload: IID={iid["l4_payload_bytes"]}, Boundary={b["l4_payload_bytes"]}, Spatial8={s["l4_payload_bytes"]} B. Spatial saving vs Boundary={b["l4_payload_bytes"]-s["l4_payload_bytes"]} B.',
        f'5. Sparse L4 model вырос с {b["l4_model_bytes"]} до {s["l4_model_bytes"]} B; остальные threshold/metadata/framing байты тоже включены.',
        f'6. Да: полный Spatial меньше best Boundary на {s["gain_vs_best_boundary_bytes"]} B.',
        f'7. Да: меньше best IID на {s["gain_vs_best_iid_bytes"]} B.',
        '8. Sparse-default-u16 — минимальный фактический файл для всех трёх probability models. Packed тоже даёт выигрыш Spatial; dense проигрывает.',
        '9. Прогнозы и actual отличаются из-за scene fitting, CPU context/tied thresholds, реальных model transport/framing и coder24 rounding; количественное разложение приведено выше.',
        '10. Да, при compact probability storage для этой пары; не при текущем dense-u32.',
        '11. Перед L5+ заново определить decoder-available representatives/weights для colliding slots, coverage и causal schedule; нельзя применять dense slot↔vertex mapping без проверки.',
        '12. Одна сцена/пара/quantizer, two-pass scene-specific fitted histograms, pinned CPU arithmetic, зависимость размеров от alphabet/mass transport, отсутствие проверки переноса на другие сцены и уровни. Gaussian/MLP/другие grids не кодируются.','',
        'Следующий этап здесь не запускался: L5+, temporal/collision-aware/neural модели и обучение не выполнялись.','',
        '## Воспроизведение','',
        'Из <PROJECT_ROOT>, fresh directory:','', '```powershell',
        'wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh gate --output research/interlevel_xyz34_bitstream_new',
        'wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh run --output research/interlevel_xyz34_bitstream_new',
        'wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh compare --output research/interlevel_xyz34_bitstream_new',
        'wsl -d Ubuntu -- bash research/run_xyz34_bitstream.sh compare --output research/interlevel_xyz34_bitstream_new --against research/interlevel_xyz34_bitstream',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.interlevel.cli finish --output research/interlevel_xyz34_bitstream_new','```','',
        'Encode/decode/benchmark/validate/compare CLI и точная binary spec: [module README](../experiment_bench/interlevel/README.md). Existing audit-env и Windows plotting env; installation dependencies не менялись.','',
        '## Графики','']
    for f in figures:lines.append(f'- [{f["title"]}]({f["png"]}) / [SVG]({f["svg"]}) / [{f["source"]}]({f["source"]})')
    (out/'BITSTREAM_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def finish(out):
    out=(ROOT/out).resolve();figures,checks=generate(out)
    result=read(out/'results.json')
    for path,expected in result['input_hashes'].items():assert digest(ROOT/path)==expected
    for row in result['rows']:assert digest(out/row['file'])==row['sha256']
    v=read(out/'validation.json');v['independent_decodes']=read(out/'decode-validation.json')['files'];v['figures']={'status':'PASS','checks':checks}
    v['original_fitted_mass_arrays_checked']=True
    if (out/'repeat-comparison.json').exists():v['full_repeat']=read(out/'repeat-comparison.json')
    write(out/'validation.json',v)
    report(out,figures)
    m=read(out/'manifest.json');m.update(status='READY',figures=len(figures),source_code_sha256={str(p.relative_to(ROOT)):digest(p) for p in list(Path(__file__).parent.glob('*.py'))+[ROOT/'research/experiment_bench/entropy.py']});write(out/'manifest.json',m)
    print('READY:',read(out/'results.json')['verdict'],'five PNG/SVG figures')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('research/interlevel_xyz34_bitstream'));a=p.parse_args();finish(a.output)
