"""Validation, source-linked static dashboard, research notes and honest verdict."""
import csv
import datetime
import html
from html.parser import HTMLParser
import io
import json
import shutil
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from PIL import Image
from .common import ROOT,read,write,digest,csv_write,resolve

class Results(unittest.TextTestResult):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.details=[]
    def addSuccess(self,test):
        super().addSuccess(test);self.details.append({'test':str(test),'status':'PASS','inputs':'known arrays in tests.py','log':'tests.log'})
    def addFailure(self,test,error):
        super().addFailure(test,error);self.details.append({'test':str(test),'status':'FAIL','error':self._exc_info_to_string(error,test),'log':'tests.log'})
    def addError(self,test,error):
        super().addError(test,error);self.details.append({'test':str(test),'status':'FAIL','error':self._exc_info_to_string(error,test),'log':'tests.log'})

def unit_tests(out):
    suite=unittest.defaultTestLoader.loadTestsFromName('research.hashgrid_analysis.tests')
    with (out/'tests.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Results).run(suite)
    return {'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'details':result.details,
        'fixture_source_sha256':digest(Path(__file__).with_name('tests.py'))}

def artifact_checks(out,figures):
    checks=[]
    for figure in figures:
        path=out/figure['png'];settings=read(path.with_suffix('.plot.json'))
        assert settings['checkpoint_sha256']==read(out/'manifest.json')['checkpoint_sha256']
        assert settings['source_sha256']==digest(out/settings['source'])
        assert settings['data_type']==figure['data_type'] and settings['axes']
        with Image.open(path) as im:
            im.verify()
        image=np.asarray(Image.open(path).convert('RGB'))
        assert image.std()>0 and min(image.shape[:2])>300
        ET.parse(out/figure['svg'])
        for ax in settings['axes']:
            if ax['yscale']=='log':assert ax['ylim'][0]>0
            for im in ax['images']:
                if im['norm_class']=='TwoSlopeNorm':assert im['norm_center']==0 and im['clim'][0]==-im['clim'][1]
                if im['norm_class']=='PowerNorm':assert im['clim']==[0.,1.] and im['norm_gamma']==.5
        # Direct data-to-artist checks on the key numeric plots, beyond existence/hash.
        name=figure['png'].replace('\\','/');config=read(out/'config.json')
        if name=='memory/by-grid.png':
            expected=[r['MiB'] for r in read(out/'memory/data.json')['grids']]
            assert [r['height'] for r in settings['axes'][0]['bars']]==expected
        if name.startswith('memory/') and name.endswith('-levels.png'):
            grid=Path(name).stem.split('-')[0];rows=[r for r in read(out/'memory/data.json')['levels'] if r['grid']==grid]
            for axis,field in zip(settings['axes'],('MiB','rows')):assert [r['height'] for r in axis['bars']]==[r[field] for r in rows]
        if name.startswith('entropy/') and name.endswith('-levels.png'):
            grid=Path(name).stem.split('-')[0];data=read(out/'entropy/data.json')['levels']
            for line in settings['axes'][0]['lines']:
                rows=[r for r in data if r['grid']==grid and r['variant']==line['label']]
                assert line['x']==[r['level'] for r in rows] and line['y']==[r['entropy_bits_per_symbol'] for r in rows]
        if name.startswith('context_gains/') and '-actual-grids' in name:
            model=Path(name).stem.replace('-actual-grids','');rows=read(out/'context_gains/grids.json')
            expected=[[next(r['payload_plus_model_gain_bits'] for r in rows if r['grid']==g and r['model']==model)] for g in config['grids']]
            assert settings['axes'][0]['images'][0]['values']==expected
        if name=='collisions/fractions.png':
            data=read(out/'collisions/data.json')['grids']
            for axis,field in zip(settings['axes'],('colliding_fraction_all_slots','query_colliding_fraction_all_slots','nominal_vertices_per_slot')):
                assert {line['label'] for line in axis['lines']}==set(config['grids'])
                for line in axis['lines']:
                    rows=[r['summary'] for r in data[line['label']]]
                    assert line['x']==[r['level'] for r in rows] and line['y']==[r[field] for r in rows]
        checks.append({'test':'figure '+figure['png'],'status':'PASS','input':settings['source'],
            'plot_settings':str(path.with_suffix('.plot.json').relative_to(out)),'png_sha256':digest(path),'svg_sha256':digest(out/figure['svg']),
            'source_hash_and_numeric_artist_values_verified':True,'log':'validation.log'})
    # Verify saved error fields independently using the original PNG pairs.
    if (out/'rendering/data.json').exists():
        data=read(out/'rendering/data.json');experiments={e['id'].replace('reference-',''):e for e in data['experiments']}
        def local(folder):
            s=str(folder)
            return Path(s[5].upper()+':'+s[6:]) if s.startswith('/mnt/') else Path(s)
        for path in (out/'rendering/numeric-errors').glob('*.npz'):
            frame=path.stem+'.png';arrays={}
            arrays['GT']=np.asarray(Image.open(local(experiments['float32']['folder'])/'model/test/ours_50000/gt'/frame).convert('RGB'),np.float32)/255
            for name in ('float32','table-8','level-8','table-12'):
                arrays[name]=np.asarray(Image.open(local(experiments[name]['folder'])/'renders'/frame).convert('RGB'),np.float32)/255
            with np.load(path) as stored:
                for key in stored.files:
                    left,right=key.split('-minus-');left='float32' if left=='original' else left
                    expected=np.abs(arrays[left]-arrays[right]).mean(axis=2)
                    assert np.array_equal(expected,stored[key]) and np.isfinite(stored[key]).all()
            checks.append({'test':'RGB difference '+frame,'status':'PASS','input':str(path.relative_to(out)),'log':'validation.log'})
    # Numerical CSV and JSON must agree, not merely exist.
    if (out/'entropy/data.json').exists():
        records=read(out/'entropy/data.json')['levels']
        with (out/'entropy/levels.csv').open(encoding='utf-8') as f:csv_records=list(csv.DictReader(f))
        assert len(csv_records)==len(records)
        for a,b in zip(records,csv_records):
            assert a['grid']==b['grid'] and a['variant']==b['variant'] and a['level']==int(b['level'])
            assert a['entropy_bits_per_symbol']==float(b['entropy_bits_per_symbol'])
            assert abs(a['theoretical_bits']-a['n']*a['entropy_bits_per_symbol'])<1e-6
        config=read(out/'config.json');runtime=read(resolve(config['runtime']))
        expected={(g,l) for g in config['grids'] for l in range(runtime['trainable_parameters'][g+'_encoding.embeddings']['levels']) if config['levels'] is None or l in config['levels']}
        for variant in {r['variant'] for r in records}:assert {(r['grid'],r['level']) for r in records if r['variant']==variant}==expected
        checks.append({'test':'CSV/JSON entropy equality and selected level coverage','status':'PASS','input':'entropy/levels.csv','log':'validation.log'})
    if (out/'distributions/raw.json').exists():
        data=read(out/'distributions/raw.json')
        for g,r in data['grids'].items():
            for s in list(r['table'].values())+r['levels']:assert sum(s['counts'])==s['n']
        checks.append({'test':'full raw histogram counts','status':'PASS','input':'distributions/raw.json','log':'validation.log'})
    if (out/'channel_dependencies/data.json').exists():
        data=read(out/'channel_dependencies/data.json')
        for g,r in data.items():
            n=r['metrics']['rows'];assert np.array(r['joint_counts']).sum()==np.array(r['conditional_counts']).sum()==np.array(r['raw_joint_counts']).sum()==n
            assert len(set(r['scatter_row_indices']))==len(r['scatter_row_indices'])
        checks.append({'test':'full raw/quantized joint count equality','status':'PASS','input':'channel_dependencies/data.json','log':'validation.log'})
    if (out/'collisions/data.json').exists():
        data=read(out/'collisions/data.json')
        for grid,levels in data['grids'].items():
            for r in levels:
                s=r['summary'];d=np.array(r['nominal_multiplicity_counts']);q=np.array(r['query_multiplicity_counts'])
                assert int(d.sum())==int(q.sum())==s['table_rows']
                assert int(np.dot(d,np.arange(len(d))))==s['enumerated_vertices']
                assert int(np.dot(q,np.arange(len(q))))==s['query_unique_vertices']
        checks.append({'test':'distinct-vertex collision mass conservation','status':'PASS','input':'collisions/data.json','log':'validation.log'})
    return checks

def summary_rows(out,checks):
    entries=[('Memory by grid','memory/by-grid.png','memory/data.json'),('Memory by level','memory','memory/levels.csv'),
        ('Raw feature histograms','distributions/raw-pooled.png','distributions/raw.json'),('Quantized histograms','distributions','distributions/quantized.json'),
        ('Entropy by level','entropy','entropy/levels.csv'),('Channel joint distribution','channel_dependencies','channel_dependencies/data.json'),
        ('Conditional distribution heatmap','channel_dependencies','channel_dependencies/data.json'),('Inter-level correlation (diagnostic)','interlevel','interlevel/summary.csv'),
        ('Inter-level mutual information (diagnostic)','interlevel','interlevel/summary.csv'),('Hash collisions','collisions','collisions/data.json'),
        ('Context gain heatmap','context_gains','context_gains/grids.json'),('Rate-distortion','rate_distortion','rate_distortion/data.csv'),
        ('Bitstream breakdown','bitstream','bitstream/data.json'),('Rendering error heatmaps','rendering','rendering/numeric-errors'),
        ('Per-frame quality curves','rendering','rendering/per-frame.csv')]
    rows=[];figures=read(out/'figure-index.json')
    for name,output,source in entries:
        plotted=any(r['png'].replace('\\','/')==output if output.endswith('.png') else r['png'].replace('\\','/').startswith(output+'/') for r in figures)
        status='PASS' if plotted and (out/source).exists() and any(c['status']=='PASS' and c.get('input','').split('/')[0]==source.split('/')[0] for c in checks) else 'NOT RUN'
        rows.append({'Visualization / Analysis':name,'Status':status,'Data source':source,'Validation':'validation.json / validation.log' if status=='PASS' else 'not executed in this scope','Output':output})
    rows.extend([{'Visualization / Analysis':name,'Status':'BLOCKED BY RESEARCH DESIGN','Data source':'SPATIAL_CORRESPONDENCE.md',
        'Validation':'No actual inter-level model or canonical fine-slot correspondence chosen','Output':'interlevel/design-status.png'}
        for name in ('Actual inter-level compression gain','Collision vs inter-level prediction/codelength')])
    return rows

def notes(out):
    texts={
        'Memory structure':('Rows*2*4 bytes and cumulative fractions.','Where potential absolute savings are concentrated.',
            'xyz accounts for 92.6518% of raw embedding bytes.','Size says nothing about predictability or quality sensitivity.',
            'Only this architecture/scene; buffers and MLP/Gaussians excluded.','Measure marginal quality sensitivity by level before deciding coding priorities.'),
        'Raw/quantized distributions':('Full-array histograms, exact mean/std/quantiles/top values, both channels and every level.',
            'Marginal concentration and effects of ranges.','Spatial table has rare extreme float values and tightly concentrated 8-bit codes.',
            'Concentration may reflect unused parameters, regularization, initialization or min/max quantizer outliers.',
            'A shared code across level-wise ranges is not a shared float value; histogram similarity does not imply dependency.',
            'Compare per-level range choice and outlier sensitivity while preserving a matched distortion target.'),
        'Entropy by level':('Full unbinned plug-in H and N*H, separated from fixed/serialized/actual sizes.',
            'Marginal compressibility and absolute level cost.','Level-wise8 improves rendering relative to table-wise8 at similar raw size.',
            'Higher entropy can result from finer effective precision, not a worse compression method.',
            'Probability-table cost, finite CDF rounding, and context bias are absent from N*H.',
            'Compare actual level-wise coding at matched quality as a separately scoped future experiment.'),
        'Channel dependencies':('Raw sampled scatter; full 2D counts, MI, Pearson/Spearman, conditional H and class errors.',
            'Linear/rank/nonlinear q0-q1 association and q0-class conditioning.',
            'Payload decreases but extra transmitted distributions increase the total file for current channel context.',
            'Pooled dependence may partly reflect a mixture of levels with different marginals; per-level metrics are saved.',
            'Plug-in MI is biased in sparse cells; class predictor is in-sample; absent Pearson correlation does not exclude dependence.',
            'Compare within-level versus pooled MI and validate histogram granularity on held-out scenes, including overhead.'),
        'Inter-level exploratory analysis':('Both vertex-derived coarse contexts vs actual fine-slot targets, correlations, MI and holdout diagnostics.',
            'Whether a known coordinate retrieves statistically useful coarse information.',
            'Exact values and candidate holdout comparisons are recorded for both methods/channels; no winning codec is selected.',
            'Shared fine slots, coordinate neighborhood, quantizer scales and regularization can create apparent relationships.',
            'Vertex-weighted target repeats; 80/20 vertex split may share hash slots; full-row generalization is unproven. Original float32 coarse features are diagnostic/non-causal for the current lossy8-bit decoder.',
            'Choose a canonical slot representative/aggregation and a slot-separated or spatially separated validation split first.'),
        'Hash collisions':('d_i counts distinct nominal vertices or unique corners of diagnostic queries; d=0 retained.',
            'Collision occupancy vs feature magnitude and the valid existing channel model statistics.',
            'Spatial hashing starts at level5; temporal level31 has lookup-induced hashing, measured by full enumeration.',
            'Multiplicity may correlate with training-query frequency or untrained slots; collisions alone do not imply degradation.',
            'Large-lattice sample counts are lower bounds; historical training queries are unavailable; finite codelength is not per-slot actual bytes.',
            'Instrument future training-query coverage in a separate experiment and use collision-free/visited-slot stratification.'),
        'Context gain and bitstream composition':('Actual per-grid payload/model sections, global JSON/framing/SHA, and diagnostic per-level finite costs.',
            'Whether useful conditional information compensates for side information.',
            'IID payload saving is smaller than the additional model cost; combined JSON semantics are not artificially split.',
            'Finer histograms can overfit or spend too many parameters even with positive empirical MI.',
            'Actual per-level stream bits do not exist; no significance testing, global header is not arbitrarily allocated to levels.',
            'Predefine class count/model precision variants, count all bytes, and evaluate across independent scenes.'),
        'Rate-distortion and rendering':('All10 measured representations, quality deltas, same-frame PNG differences, worst frames.',
            'Quantizer distortion vs actual parameter size.',
            'Table8 PSNR38.7517 vs level8 41.0303 dB; all three exact coders produce the same table8 images.',
            'Different ranges/resolution settings can confound cross-study comparisons; fixed views are preserved here.',
            'Single scene/seed, upstream LPIPS VGG inputs[0,1] normalize=False, PNG quantization; no entire-scene rate claim.',
            'Compare matched-quality quantization/coding on new scenes only after explicit experiment design.')}
    lines=['# Research notes','', 'Это анализ существующего checkpoint; новый метод сжатия не реализован.','']
    for title,answers in texts.items():
        lines+=['## '+title,'']
        for question,answer in zip(('A. Что показывает','B. Какая зависимость','C. Подтверждено','D. Альтернативы','E. Ограничения','F. Следующий эксперимент'),answers):lines+=[f'**{question}:** {answer}','']
    lines+=['## Вопросы для решения исследователем','',
        '1. Target domain: fine vertices, all fine slots, or only visited slots? How to handle slots with several coordinate representatives?',
        '2. Choose nearest/interpolated/aggregated coarse context and account for reproducible representative metadata.',
        '   Decide whether coarse levels are transmitted losslessly (charge those bytes) or contexts are recomputed from decoded quantized coarse levels. Current raw-coarse diagnostics cannot settle this choice.',
        '3. Choose class resolution, model granularity and metadata budget before comparing actual coding.',
        '4. Choose split by slot/spatial region/scene and define a matched quality criterion; vertex random holdout is insufficient.',
        '5. Decide whether training-query coverage should be measured in a new instrumented run.',
        '', 'Гипотезы: outlier-sensitive table8 precision; within-level vs pooled channel dependence; collision/coverage stratification; metadata-dominated simple context. Ни одна не объявляется доказанным новым методом.','']
    (out/'RESEARCH_NOTES.md').write_text('\n'.join(lines),encoding='utf-8')

def dashboard(out,figures,verdict):
    sections=[('memory','HashGrid memory structure'),('distributions','Raw / quantized feature distributions'),('entropy','Entropy by level'),
        ('channel_dependencies','Channel-wise dependencies'),('interlevel','Inter-level exploratory dependencies'),('collisions','Hash collisions'),
        ('context_gains','Context bitrate comparison'),('rate_distortion','Rate-distortion'),('bitstream','Bitstream size composition'),('rendering','Rendering quality differences')]
    parts=['<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>Grid4D HashGrid analysis</title><style>body{font:16px/1.5 system-ui;margin:auto;max-width:1250px;padding:25px;background:#f5f7fa;color:#172335}nav{display:flex;gap:12px;flex-wrap:wrap}a{color:#1e5e9d}figure{margin:20px 0;padding:18px;background:white;border:1px solid #ccd5df;border-radius:8px}img{max-width:100%;height:auto}small{display:block}details{padding:5px}code{overflow-wrap:anywhere}h2{margin-top:45px}figcaption{font-weight:600}</style>',
        f'<h1>Grid4D HashGrid: {html.escape(verdict)}</h1>',
        '<p>Trained bouncingballs, 50000 iterations. Static, source-linked scientific report; no new context codec.</p>',
        '<p><a href="ANALYSIS_REPORT.md">Analysis report</a> · <a href="RESEARCH_NOTES.md">Research notes</a> · <a href="validation.json">Validation</a> · <a href="summary.csv">Summary CSV</a> · <a href="config.json">Reproduction config</a></p>',
        '<nav>'+''.join(f'<a href="#{key}">{label}</a>' for key,label in sections)+'</nav>']
    for key,label in sections:
        parts.append(f'<h2 id="{key}">{label}</h2>')
        if key=='interlevel':parts.append('<p>Vertex-domain diagnostics only. Actual inter-level coding and canonical slot correspondence: BLOCKED BY RESEARCH DESIGN.</p>')
        if key=='collisions':parts.append('<p>Full enumeration for small levels; observed lower bounds for sampled large levels. Query samples are diagnostic, not historical training queries.</p>')
        for record in figures:
            if record['png'].split('/')[0]!=key:continue
            settings=Path(record['png']).with_suffix('.plot.json').as_posix();axes=read(out/settings)['axes']
            axis_description='; '.join(dict.fromkeys(f'X: {a["xlabel"]}; Y: {a["ylabel"]}' for a in axes if a['xlabel'] or a['ylabel']))
            parts.append(f'<figure><figcaption>{html.escape(record["title"])}</figcaption><img loading="lazy" src="{record["png"]}" alt="{html.escape(record["title"])}">'+
                f'<small>{html.escape(axis_description)}</small><small>Type: {html.escape(record["data_type"])}; measurements: {record["measurements"] if record["measurements"] is not None else "see source counts"}</small>'+
                f'<small>Checkpoint SHA256: <code>{record["checkpoint_sha256"]}</code></small><small>{html.escape(record["limitations"])}</small>'+
                f'<a href="{record["source"]}">CSV/JSON source</a> · <a href="{settings}">Exact plotted values/settings</a> · <a href="{record["svg"]}">SVG</a></figure>')
    parts.append('</html>');(out/'dashboard.html').write_text('\n'.join(parts),encoding='utf-8')
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.images=[];self.links=[];self.sections=[]
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if tag=='img':self.images.append(attrs['src'])
            if tag=='a':self.links.append(attrs['href'])
            if tag=='h2':self.sections.append(attrs.get('id'))
    parser=Links();parser.feed((out/'dashboard.html').read_text(encoding='utf-8'))
    assert len(parser.images)==len(figures) and set(parser.images)=={r['png'] for r in figures}
    assert parser.sections==[key for key,_ in sections]
    for link in parser.images+parser.links:
        assert '\\' not in link and (link.startswith('#') or (out/link).exists()),link
    check={'test':'dashboard image coverage and local links','status':'PASS','input':'figure-index.json',
        'figures':len(parser.images),'links':len(parser.links),'sections':len(parser.sections),'log':'validation.log'}
    write(out/'dashboard-validation.json',check)
    return check

def finalize(out):
    config=read(out/'config.json');figures=read(out/'figure-index.json')
    shutil.copy2(Path(__file__).with_name('SPATIAL_CORRESPONDENCE.md'),out/'SPATIAL_CORRESPONDENCE.md')
    for figure in figures:
        for key in ('png','svg'):
            figure[key]=figure[key].replace('\\','/')
        settings_path=out/Path(figure['png']).with_suffix('.plot.json');settings=read(settings_path)
        settings.update(png=figure['png'],svg=figure['svg']);write(settings_path,settings)
        if figure['png'].startswith('interlevel/') and figure['data_type']!='BLOCKED BY RESEARCH DESIGN':
            figure['data_type']='sampled raw-coarse diagnostic; non-causal for existing 8-bit decoder'
            warning=' Original coarse float32 weights cannot be recovered from lossy8-bit symbols; lossless coarse transport or dequantized-coarse analysis is a research choice.'
            if warning not in figure['limitations']:figure['limitations']+=warning
            settings_path=out/Path(figure['png']).with_suffix('.plot.json');settings=read(settings_path)
            settings.update(data_type=figure['data_type'],limitations=figure['limitations']);write(settings_path,settings)
    write(out/'figure-index.json',figures)
    units=unit_tests(out);checks=artifact_checks(out,figures)
    validation={'A_input_integrity':read(out/'input-validation.json')['status'],'B_statistics':units['status'],
        'C_GPU_mapping':read(out/'mapping-validation.json')['status'] if (out/'mapping-validation.json').exists() else 'NOT RUN',
        'D_experiment_fairness':read(out/'experiment-fairness.json')['status'] if (out/'experiment-fairness.json').exists() else 'NOT RUN',
        'E_visualizations':'PASS' if checks else 'NOT RUN','F_rendering':'PASS' if (out/'rendering/recomputed-metrics.csv').exists() else 'NOT RUN',
        'G_reproducibility':read(out/'reproducibility.json')['status'] if (out/'reproducibility.json').exists() else 'NOT RUN'}
    verdict='ANALYSIS READY' if all(s=='PASS' for s in validation.values()) else 'ANALYSIS PARTIALLY READY'
    if any(s=='FAIL' for s in validation.values()):verdict='ANALYSIS NOT READY'
    manifest=read(out/'manifest.json');manifest.update(status=verdict,figure_count=len(figures),
        source_code_sha256={p.name:digest(p) for p in Path(__file__).parent.glob('*') if p.is_file()},
        completed=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat())
    write(out/'manifest.json',manifest)
    summary=summary_rows(out,checks)
    if config['section']=='all':assert all(r['Status']=='PASS' for r in summary if r['Status']!='BLOCKED BY RESEARCH DESIGN'),summary
    csv_write(out/'summary.csv',summary);notes(out)
    write(out/'validation.json',{'verdict':verdict,'categories':validation,'unit_tests':units,'artifact_checks':checks,
        'GPU_mapping_evidence':'mapping-validation.json','input_evidence':'input-validation.json',
        'rendering_evidence':'rendering/recomputed-metrics.csv','experiment_evidence':'experiment-fairness.json',
        'research_design_blocks':['actual inter-level codec/gain','collision vs inter-level prediction/codelength']})
    (out/'validation.log').write_text('\n'.join(f'{k}: {v}' for k,v in validation.items())+'\n'+\
        '\n'.join(c['status']+' '+c['test']+' input='+c['input'] for c in checks)+'\n',encoding='utf-8')
    report=['# Grid4D HashGrid visual analysis','',f'**{verdict}**. Date: {manifest["completed"]}.','',
        'Модуль построен поверх существующего стенда. Данные графиков, параметры построения и SHA256 сохранены; исходный Grid4D и результаты прежних фаз не изменены.',
        'Измеренные размеры файлов отделены от эмпирической энтропии и диагностической стоимости. Межуровневые графики исследуют два проверенных соответствия координат, но не задают готовый алгоритм кодирования.',
        'Для больших пространственных уровней sampled collision multiplicity является нижней границей в выбранной области, а не оценкой полного числа коллизий. Запросы обучения исторически не записывались.',
        'Первым делом изучите memory/by-grid, rate_distortion/eight-bit-scope и bitstream/waterfall; затем переходите к условным распределениям, уровням и коллизиям.', '',
        '## 1. Source and protocol','',f'Checkpoint: `{config["checkpoint"]}`; SHA256 `{manifest["checkpoint_sha256"]}`.',
        'Official Grid4D revision3ab7b74482910d22fba7d51ac60c8cae1fe24bf1; trained50000, bouncingballs, original800x800, same20 test cameras, seed0 training.',
        '4 grids /112 levels /2 channels. Actual offsets/buffers and GPU scales/lookup resolutions are checked. Allocation and lookup are kept separate.',
        'Existing Phase2 codec, existing six quantized arrays, transmitted histogram models, bitstreams and renderings reused. Upstream, objective and previous results not modified.',
        'Python3.10.21 / torch2.7.0+cu128 / NumPy1.21.6 / SciPy1.7.3 compute; CUDA12.8.93/GCC13.4.0. Existing Windows Python3.12/NumPy1.26.4/matplotlib3.9.4 plots. No new packages installed.',
        'New GPU code is a diagnostic probe of exact upstream helper source; production lookup/interpolation is unchanged. Source/config hashes and timings in manifest/computation/mapping-validation.',
        '', '## 2. Coverage and outputs','',f'{len(figures)} PNG and {len(figures)} SVG figures, each with exact artist values, settings, source SHA and checkpoint SHA in `.plot.json`.',
        '[Dashboard](dashboard.html) · [Notes](RESEARCH_NOTES.md) · [Validation](validation.json) · [Figure index](figure-index.json).','',
        '| Visualization / Analysis | Status | Data source | Validation | Output |','|---|---|---|---|---|']
    for r in summary:report.append('| '+' | '.join(str(v) for v in r.values())+' |')
    if (out/'memory/data.json').exists():
        d=read(out/'memory/data.json');report+=['','## 3. Memory','',f'Total raw embeddings: {d["total_raw_bytes"]:,} bytes ({d["total_raw_bytes"]/2**20:.6f} MiB).','',
            '| Grid | Rows | Scalars | Bytes | MiB | Percent |','|---|---:|---:|---:|---:|---:|']
        for r in d['grids']:report.append(f'| {r["grid"]} | {r["rows"]} | {r["scalars"]} | {r["bytes"]} | {r["MiB"]:.6f} | {r["percent_total"]:.6f} |')
    if (out/'channel_dependencies/data.json').exists():
        d=read(out/'channel_dependencies/data.json');report+=['','## 4. Channel statistics','',
            '| Grid | Pearson full | Spearman full | I(q0;q1), bits/row | I(class;q1), bits/row | H(q1 given class) |','|---|---:|---:|---:|---:|---:|']
        for g,r in d.items():
            m=r['metrics'];report.append(f'| {g} | {m["pearson_full"]:.7f} | {m["spearman_full"]:.7f} | {m["mutual_information_full_q0_q1"]:.7f} | {m["mutual_information_16class_q1"]:.7f} | {m["H_q1_given_class"]:.7f} |')
        report+=['','Raw statistics/top values and full counts in `distributions/`; exact entropy per112 levels and all6 variants in `entropy/levels.csv`, priority table in `entropy/priority-levels.csv`.',
            'Pearson/Spearman calculated on every row. Scatter alone sampled. Within-level channel MI/correlation in `context_gains/levels.csv` avoids conflating pooled and within-level dependence.']
    if (out/'interlevel/data.json').exists():
        report+=['','## 5. Inter-level diagnostics and collision mapping','',
            'Two explicit, GPU-checked correspondences: coarse smoothstep lookup at fine vertex and nearest coarse vertex. See `SPATIAL_CORRESPONDENCE.md`.',
            'Fine target is an actual stored fine-slot feature/symbol, sampled with vertex weighting; duplicate targets are counted and recorded. Sampling does not establish uniform table-row dependence.',
            'Channels remain separate. All adjacent-pair correlations, MI, conditional H, heldout IID/context cross entropy, and predictor MSE recorded in `interlevel/summary.csv`.',
            '80/20 deterministic vertex holdout may share fine slots between train/test. No actual inter-level codelength or gain is claimed; canonical representatives/fallback/aggregation are research decisions.',
            'Raw-coarse contexts use originalfloat32 weights and are diagnostic/non-causal for the existing lossy8-bit decoder. Lossless coarse transport (with charged bytes) or dequantized-coarse contexts must be chosen/tested separately.',
            'Collision multiplicity deduplicates vertices, keeps unused slots, and conserves mass. Exact enumeration up to configured limit; larger nominal lattices use100000 sampled vertices by default, explicitly lower bounds.',
            'Spatial lookup begins hashing at level5. All temporal last levels use hashing because actual CUDA lookup[33,33,16] exceeds allocation[32,32,16]. Full temporal collision counts are exact.',
            'Uniform query corner statistics are separate from nominal vertex statistics and are not training coverage. Magnitude/channel prediction/codelength grouping is valid channel-only diagnostics; inter-level grouping is blocked.']
    if (out/'collisions/data.json').exists():
        collisions=read(out/'collisions/data.json')
        report+=['','### Exact enumerated hashed levels','', '| Grid / Level | Vertices | Slots | Visited | Colliding | Colliding / all | Colliding / visited | Max d |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for g,records in collisions['grids'].items():
            for record in records:
                r=record['summary']
                if r['hashed_lookup'] and r['mode'].startswith('exact'):
                    report.append(f'| {g} / L{r["level"]} | {r["nominal_vertices"]} | {r["table_rows"]} | {r["visited_slots"]} | {r["colliding_slots"]} | {100*r["colliding_fraction_all_slots"]:.6f}% | {100*r["colliding_fraction_visited_slots"]:.6f}% | {r["max_multiplicity"]} |')
    if (out/'bitstream/data.json').exists():
        d=read(out/'bitstream/data.json');iid=d['iid'];ctx=d['channel_context']
        report+=['','## 6. Actual coding vs entropy estimates','',
            f'IID {iid["actual_bitstream_bytes"]:,} bytes; channel_context {ctx["actual_bitstream_bytes"]:,} bytes. Payload saving {iid["coded_payload_bytes"]-ctx["coded_payload_bytes"]:,} bytes; extra model {ctx["model_overhead_bytes"]-iid["model_overhead_bytes"]:,} bytes; JSON change {ctx["total_json_bytes"]-iid["total_json_bytes"]:,} bytes.',
            f'Total context file increases by {ctx["actual_bitstream_bytes"]-iid["actual_bitstream_bytes"]:,} bytes ({100*(ctx["actual_bitstream_bytes"]/iid["actual_bitstream_bytes"]-1):.4f}%). This negative result is preserved.',
            'Histogram/model sections and per-grid payload sizes are read from actual bitstream framing. Global JSON cannot honestly be split into quantization/buffers/other semantic byte counts, so it is shown as combined metadata.',
            'Actual per-grid payload+model gain and full-file waterfall are distinct from per-level diagnostic finite-mass codelength. No actual per-level stream exists. No significance test is claimed.']
    if (out/'rate_distortion/data.json').exists():
        d=read(out/'rate_distortion/data.json');report+=['','## 7. Measured rate-distortion','',
            '| Variant | Actual bytes | Type | PSNR | SSIM | LPIPS | MS-SSIM |','|---|---:|---|---:|---:|---:|---:|']
        for r in d:report.append(f'| {r["variant"]} | {r["bytes"]} | {r["size_type"]} | {r["PSNR"]:.7f} | {r["SSIM"]:.7f} | {r["LPIPS"]:.7f} | {r["MS-SSIM"]:.7f} |')
        report+=['','12-bit raw codes occupy uint16 containers. No invented12/16 entropy bitstreams. Independent points are not joined into a continuous curve. All sizes HashGrid-only, not a compressed entire scene.']
    report+=['','## 8. Rendering and validation','']
    if (out/'rendering/recomputed-metrics.csv').exists():report+=[
        'Stored PNG comparisons and mean absolute RGB differences on first and worst frames use identical [0,1] color limits, gamma0.5. Exact float32 error maps are in `rendering/numeric-errors/*.npz`.',
        '200 frame PSNR independently calculated on CPU; SSIM/LPIPS/MS-SSIM recomputed from existing PNGs in pinned GPU environment and compared (tolerance1e-6; PSNR1e-4). Old metric files not rewritten.',
        'Test cameras follow JSON order: renderer Scene(shuffle=False); frame index and timestamp both stored. IID/context symbols and float-render hashes agree exactly; no artificial coder image differences.',
        ]
    else:report+=['Rendering recomputation/comparisons: **NOT RUN in this requested scope**. No new rendering checks claimed.']
    report+=[f'Unit tests: {units["tests"]}, failures={units["failures"]}, errors={units["errors"]}; `tests.log`. Every figure/count/error/mapping/input test status and source is in `validation.json` / `validation.log`.','']
    if (out/'visual-review.json').exists():
        report+=['Manual visual QA and resolved plotting/report defects are recorded in [visual-review.json](visual-review.json). Neither defect changed the numerical computations.','']
    for k,v in validation.items():report.append(f'- {k}: **{v}**')
    report+=['','## 9. Reproduce','', '```powershell',
        '# From <PROJECT_ROOT>; choose a NEW output directory',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --config research/analysis_results/config.json --output research/analysis_results_new',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --section channels --output research/channel_analysis_new',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --section interlevel --grids xyz --levels 5 6 7 --sampling-budget 20000 --output research/interlevel_analysis_new',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli run --section dashboard --output research/analysis_results',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.hashgrid_analysis.cli test', '```',
        '', 'Section choices: all, histograms, entropy, channels, interlevel, collisions, rate-distortion, rendering, dashboard. Explicit checkpoint/runtime/study/repo/results, quantization filter, seed, budgets and grids/levels supported.',
        'Split commands also supported: `cli prepare`, `wsl -d Ubuntu -- bash research/run_hashgrid_analysis_compute.sh <PROJECT_ROOT>/<output>/config.json`, then `cli finish --config <output>/config.json`.',
        'Full repeat comparison: `python -m research.hashgrid_analysis.compare <first-output> <repeat-output>`; records equality of numeric data, plotted artist values, PNG/SVG and selection settings.',
        '', '## 10. Limits, hypotheses and next decisions','',
        'One synthetic scene/one trained seed; marginal empirical entropy and sparse MI are not generalization evidence. Higher MI does not guarantee a beneficial actual file. Collision frequency is not causal quality loss.',
        'LPIPS VGG upstream inputs[0,1], normalize=False kept compatible; paper/SOTA comparison not made. Encoder/model finite precision effects and overhead remain accounted for.',
        'Study first: memory/by-grid, rate_distortion/eight-bit-scope, bitstream/waterfall, channel_dependencies/summary; then entropy/priority-table8, interlevel/*-summary, collisions/fractions.',
        'Research decisions: slot/vertex target domain, canonical representatives or aggregation, collision fallback, quantization distortion target, class/model granularity and side-information cost, slot/spatial/scene holdout. See A-F notes and spatial spec.',
        'No new inter-level/temporal/collision-aware/cross-grid/NVCC/neural compression algorithm implemented. Analysis stops here.',
        '', '## Complete figure list','', '| Figure | Type | Data | Settings |','|---|---|---|---|']
    for r in figures:report.append(f'| [{r["title"]}]({r["png"]}) | {r["data_type"]} | [{r["source"]}]({r["source"]}) | [{Path(r["png"]).with_suffix(".plot.json").as_posix()}]({Path(r["png"]).with_suffix(".plot.json").as_posix()}) |')
    (out/'ANALYSIS_REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    checks.append(dashboard(out,figures,verdict))
    recorded_validation=read(out/'validation.json');recorded_validation['artifact_checks']=checks
    write(out/'validation.json',recorded_validation)
    with (out/'validation.log').open('a',encoding='utf-8') as log:
        log.write('PASS '+checks[-1]['test']+' input='+checks[-1]['input']+'\n')
    print(verdict,len(figures),'figures',flush=True)
