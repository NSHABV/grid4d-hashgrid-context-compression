"""Render immutable Count6 report and final independent numerical checks."""
import argparse,json,os,re,shutil,time
from pathlib import Path
import numpy as np
from .study import read,csv_out,ROOT,OLD,DIAG,PAIRS,ARMS,STORAGES,sha,timing
from research.hashgrid_analysis.hashed_context.runtime import write_json,peak_rss_mib
from research.experiment_bench.hashed_interlevel.dry_model import deserialize,section_sizes

def audit(run):
    t=time.perf_counter();cpu=time.process_time();scores=read(run/'test-scores.json');gains=read(run/'paired-differences.json');sizes=read(run/'model-sizes.json');forecasts=read(run/'predicted-net.json')
    checked=0
    for pair in PAIRS:
        with np.load(DIAG/pair/'contexts.npz') as z:geom=z['geometry'];point=z['point_count'];nominal=z['nominal_count']
        q=np.load(DIAG/pair/'fine_symbols.npy')
        # Independent declarative Count6 vector, avoiding production classifier.
        expected=np.zeros(len(q),np.uint8);expected[(nominal>0)&(point==0)]=1
        for k in (1,2,3):expected[point==k]=k+1
        expected[point>=4]=5
        with np.load(run/pair/'expected-classes.npz') as z:
            assert np.array_equal(z['Count6'],np.column_stack((expected,expected)))
        for seed in (0,1,2):
            with np.load(run/pair/f'splits_seed{seed}.npz') as z:train=z['train'];test=z['test']
            assert sha(run/pair/f'splits_seed{seed}.npz')==sha(OLD/pair/f'splits_seed{seed}.npz')
            masks={'all':np.ones(len(test),bool),**{f'G{k}':geom[test]==k for k in range(4)},
                   'G3_K2':point[test]==2,'G3_K3':point[test]==3,'G3_K4plus':point[test]>=4}
            with np.load(run/pair/f'test_losses_seed{seed}.npz') as loss:
                for name,C in ARMS.items():
                    cls=geom if name=='Geometry4' else expected
                    with np.load(run/pair/f'seed{seed}_{name}/fitted.npz') as z:
                        cnt=z['train_counts'];mass=z['masses']
                    for ch in (0,1):
                        for k in range(C):
                            np.testing.assert_array_equal(cnt[ch,k],np.bincount(q[train[cls[train]==k],ch],minlength=256))
                        independent=16-np.log2(mass[ch,cls[test],q[test,ch]].astype(np.float64))
                        np.testing.assert_allclose(loss[name][:,ch],independent,rtol=0,atol=2e-15)
                    if name=='Geometry4':
                        with np.load(OLD/pair/f'test_losses_seed{seed}.npz') as z:np.testing.assert_array_equal(loss[name],z[name])
                    for r in [r for r in scores if r['pair']==pair and r['seed']==seed and r['model']==name]:
                        x=loss[name][masks[r['stratum']]];x=x if r['channel']=='both' else x[:,int(r['channel'])]
                        assert abs(float(x.mean())-r['CE'])<1e-13;checked+=1
                for r in [r for r in gains if r['pair']==pair and r['seed']==seed]:
                    x=(loss['Geometry4']-loss['Count6'])[masks[r['stratum']]];x=x if r['channel']=='both' else x[:,int(r['channel'])]
                    assert abs(float(x.mean())-r['gain_bits_per_symbol'])<1e-13
    for r in sizes:
        p=run/r['pair']/f"seed{r['seed']}_{r['model']}"/f"{r['storage']}.model";blob=p.read_bytes()
        assert p.stat().st_size==r['total'];assert section_sizes(blob)['total']==r['total'];deserialize(blob)
    for r in forecasts:
        p=r['pair'];seed=r['seed'];best={name:min([z for z in sizes if z['pair']==p and z['seed']==seed and z['model']==name],key=lambda z:(z['total'],STORAGES.index(z['storage']))) for name in ARMS}
        d=best['Count6']['total']-best['Geometry4']['total'];g=next(z['gain_bits_per_symbol'] for z in gains if z['pair']==p and z['seed']==seed and z['stratum']=='all' and z['channel']=='both')
        assert d==r['delta_side_bytes'] and abs(g*1048576/8-d-r['net_bytes'])<1e-8
    write_json(run/'independent-audit.json',{'status':'PASS','score_records':checked,'train_histograms':'independent per-class bincount',
          'former_Geometry4_test_losses':'exactly equal','serializer_roundtrips':len(sizes),'forecasts':len(forecasts),**timing(t,cpu)})

def render(run):
    assert read(run/'independent-audit.json')['status']=='PASS'
    t=time.perf_counter();cpu=time.process_time();scores=read(run/'test-scores.json');gains=read(run/'paired-differences.json');fore=read(run/'predicted-net.json');sizes=read(run/'model-sizes.json');decision=read(run/'decision.json');geometry=read(run/'geometry-summary.json')
    plots=run/'plots';plots.mkdir();os.environ['MPLCONFIGDIR']=str(plots/'matplotlib_config')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    def avg(data,field,**filters):return float(np.mean([r[field] for r in data if all(r[k]==v for k,v in filters.items())]))
    fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    groups=['all','G3','G3_K2','G3_K3','G3_K4plus']
    for ax,pair in zip(axs,PAIRS):
        for seed in (0,1,2):ax.plot(groups,[avg(gains,'gain_bits_per_symbol',pair=pair,seed=seed,stratum=g,channel='both') for g in groups],marker='o',label=f'seed {seed}')
        ax.axhline(0,color='black',linewidth=.8);ax.set(title=pair,ylabel='Geometry4 CE − Count6 CE [bits/symbol]');ax.legend()
    fig.savefig(plots/'paired_gain.png',dpi=160);fig.savefig(plots/'paired_gain.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    for i,pair in enumerate(PAIRS):
        r=[z for z in fore if z['pair']==pair];ax.bar(np.arange(3)+i*4,[z['net_bytes'] for z in r],label=pair)
    ax.axhline(4096,color='red',linestyle='--',label='4096 B safety margin');ax.axhline(0,color='black',linewidth=.8)
    ax.set(xticks=[0,1,2,4,5,6],xticklabels=['L5 s0','L5 s1','L5 s2','L6 s0','L6 s1','L6 s2'],ylabel='PREDICTED net bytes');ax.legend()
    fig.savefig(plots/'predicted_net.png',dpi=160);fig.savefig(plots/'predicted_net.svg');plt.close(fig)
    lines=['# Multiplicity Count6: exploratory held-out исследование', '',
      '14 октября 2026. Отдельный эксперимент A; `bouncingballs-reference-50000`, xyz L4→L5 и L5→L6, existing table-wise uint8. CPU Python 3.12.14 / NumPy 1.26.4. GPU не использовался.', '',
      '**Это follow-up exploratory study на той же сцене, checkpoint и ранее анализировавшихся test/K-подгруппах.** Предварительная фиксация нового протокола предотвращает настройку Count6 после результата, но не превращает повторное использование данных в независимое подтверждение. Новые случайные seeds также не сделали бы данные независимыми.', '',
      '## Итог отдельно от эксперимента B', '',
      *[f"- {p}: **{decision['pairs'][p]['decision']}**; средний ΔCE={decision['pairs'][p]['mean_delta_CE']:+.9f} bits/symbol; PREDICTED net={decision['pairs'][p]['mean_predicted_net_bytes']:+.2f} B; safety margin PASS {decision['pairs'][p]['margin_pass_seeds']}/3 seeds." for p in PAIRS], '',
      'Решение относится к фиксированному Count6, а не ко всем геометрическим контекстам. Здесь не создан entropy bitstream. Реальный Mean8 codec — отдельный эксперимент B, который продолжается независимо от знака Count6 при PASS correctness.', '',
      '## Геометрия и decoder-only контракт', '',
      'Count6: class0=G0 (nominal_count=0); class1=G1 (nominal>0, point_count=0); class2=K1; class3=K2; class4=K3; class5=K≥4. Geometry4 объединяет классы 3–5 в G3. K означает **point_count**, не nominal multiplicity. Классы одинаковы для двух каналов, PMF обучаются отдельно по каналам.', '',
      'Decoder получает только geometry-metadata.json: fine actual float32 scale, resolution, rows, offsets, domain convention, uint32 hash specification. Он перебирает nominal lattice в x-fast order; E допускает вершины v≤floor(scale). Hash — официальный stride/dense switch, unsigned 32-bit wrap, XOR primes (1,2654435761,805459861), modulo rows. Counts целочисленные и не зависят от порядка chunk accumulation. Ни coarse feature values, ни coarse symbols, ни occupancy, ни fine targets не нужны.', '',
      '| Fine | G0 | G1 | K1 | K2 | K3 | K≥4 | allocated |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in geometry:lines.append('| '+r['pair']+' | '+' | '.join(map(str,r['Count6_histogram']))+f" | {r['allocated']} |")
    lines += ['', '## Протокол и статистика', '',
      'Оригинальные splits скопированы byte-for-byte: seeds 0/1/2, train 335545 / validation 83886 / test 104857 slots (64/16/20% с прежним округлением). Оба канала slot принадлежат одному split. Laplace α=1, минимальная integer mass=1, stable largest remainder, сумма65536. Все probability distributions fit только на train; пустой train class получает uniform256. Validation только описательна; число классов, smoothing и bucket boundaries не настраивались. MODEL_FREEZE создан до exact decoder replay и единственного test evaluation.', '',
      'GO объявлен заранее отдельно для каждого уровня: положительные gains all/G3 в каждом seed/channel и PREDICTED net каждого seed выше max(4096 B, 0.2·max(Δside,0)). Это консервативный gate для последующего кодирования, а не статистическая значимость. Парные SE в CSV описательны; пространственная зависимость и overlap seeds не дают независимых реплик.', '',
      '| Fine | Geometry4 all | Count6 all | ΔCE all | Geometry4 G3 | Count6 G3 | ΔCE G3 |', '|---|---:|---:|---:|---:|---:|---:|']
    for p in PAIRS:
        v=[avg(scores,'CE',pair=p,model=m,stratum=g,channel='both') for g in ('all','G3') for m in ARMS]
        lines.append(f'| {p} | {v[0]:.9f} | {v[1]:.9f} | {v[0]-v[1]:+.9f} | {v[2]:.9f} | {v[3]:.9f} | {v[2]-v[3]:+.9f} |')
    lines += ['', 'Средние трёх повторных holdout seeds; положительное ΔCE означает выигрыш Count6. По каналам и подгруппам:', '',
      '| Fine | Group | Test slots min…max | Geometry4 ch0/ch1 | Count6 ch0/ch1 | ΔCE ch0/ch1 | Gain min…max seed/channel |', '|---|---|---:|---|---|---|---|']
    for p in PAIRS:
        for g in groups:
            sel=[r for r in gains if r['pair']==p and r['stratum']==g and r['channel'] in ('0','1')]
            def twins(model):return [avg(scores,'CE',pair=p,model=model,stratum=g,channel=ch) for ch in ('0','1')]
            a,b=twins('Geometry4'),twins('Count6');vals=[r['gain_bits_per_symbol'] for r in sel]
            lines.append(f"| {p} | {g} | {min(r['slots'] for r in sel)}…{max(r['slots'] for r in sel)} | {a[0]:.6f} / {a[1]:.6f} | {b[0]:.6f} / {b[1]:.6f} | {a[0]-b[0]:+.6f} / {a[1]-b[1]:+.6f} | {min(vals):+.6f}…{max(vals):+.6f} |")
    lines += ['',f'![Paired gain]({(plots/"paired_gain.png").as_posix()})', '',
      'Все K-подгруппы удовлетворяют заранее заданному минимуму 100 test slots. Группы не использовались для выбора новых bucket configurations. G0/G1/K1 PMF полностью совпадают с Geometry4, потому что train observations этих классов не изменились; дополнительная модель разделяет только G3.', '',
      '## Реальная стоимость модели и прогноз payload', '',
      'Проверены существующие dry transports dense_u32, packed_u16 и sparse_default_u16 (36 файлов, exact roundtrip). Для каждого arm/seed независимо выбран самый короткий actual serialized model file. CDF не дублируется. Common metadata сохранена идентичной предыдущему held-out experiment, включая coarse prerequisite/quantizer/provenance; это консервативный общий envelope, хотя Count6 decoder для классов использует лишь geometry. Model rule names имеют разную длину; эта разность оплачена. C6 уже поддерживается serializer, исходный код не изменён.', '',
      '| Fine | seed | Model | Storage | Mass bytes | Threshold bytes | Spec bytes | Metadata | Header | Total side |','|---|---:|---|---|---:|---:|---:|---:|---:|---:|']
    for p in PAIRS:
        for seed in (0,1,2):
            for m in ARMS:
                r=min([r for r in sizes if r['pair']==p and r['seed']==seed and r['model']==m],key=lambda r:(r['total'],STORAGES.index(r['storage'])))
                lines.append(f"| {p} | {seed} | {m} | {r['storage']} | {r['probability_masses']} | {r['context_thresholds']} | {r['model_specification']} | {r['mandatory_metadata']} | {r['header']} | {r['total']} |")
    lines += ['', 'N_full=524288×2=1048576 symbols; gross=N_full·ΔCE/8; net=gross−Δside. Все следующие значения **PREDICTED**, перенос test CE на весь уровень; реальный payload и coder framing не измерялись.', '',
      '| Fine | Seed | ΔCE | Gross B | Δmodel B | Δmetadata/framing B | Net B | margin PASS |','|---|---:|---:|---:|---:|---:|---:|---|']
    for r in fore:lines.append(f"| {r['pair']} | {r['seed']} | {r['delta_CE']:+.9f} | {r['gross_bytes']:+.2f} | {r['candidate_model_bytes']-r['baseline_model_bytes']:+d} | {r['delta_metadata_bytes']:+d} | {r['net_bytes']:+.2f} | {r['margin_pass']} |")
    lines += ['',f'![PREDICTED net]({(plots/"predicted_net.png").as_posix()})','',
      '## Сопоставление с уже известными Mean8 и Mean4×Std2', '',
      'Следующие числа старых моделей взяты из сохранённого предыдущего эксперимента; это **не новый независимый эксперимент или refit**. Geometry4 losses дополнительно побитно сверены с прежними для каждого seed. Все относятся к тому же checkpoint, quantizer и splits.', '',
      '| Fine | Geometry4 CE | Count6 CE | old Mean8 CE | old Mean4×Std2 CE |','|---|---:|---:|---:|---:|']
    old_scores=read(OLD/'test-scores.json')
    for p in PAIRS:
        vs=[avg(scores,'CE',pair=p,model=m,stratum='all',channel='both') for m in ARMS]
        vs +=[avg(old_scores,'CE',pair=p,model=m,stratum='all',channel='both') for m in ('Mean8','Mean4Std2')]
        lines.append('| '+p+' | '+' | '.join(f'{v:.9f}' for v in vs)+' |')
    lines += ['',f'[Прежний HELDOUT_REPORT.md]({(OLD/"HELDOUT_REPORT.md").as_posix()}). NO-GO прежнего Mean4×Std2 не пересматривается.', '',
      '## Correctness, ресурсы и воспроизводимость', '',
      'PASS: 5 новых synthetic tests (scalar uint32 hash/wrap, colliding tiny grids/boundaries, chunk1/7/65536, шесть классов, недопустимые counts, train-only fitting). Full geometry counts и 524288 class rows ×2 channels обеих пар точно совпадают с сохранённой диагностикой; нет gaps/duplicates. Два fresh decoder process читают только geometry JSON; ни coarse symbols, ни checkpoint, ни fine symbols. Шесть forbidden-read probes на пару отклонены. Python audit hook — инструмент контроля чтения этого decoder, не OS sandbox.', '',
      'PASS: train histograms независимо проверены per-class bincount; masses положительны, сумма65536; 36 serialization roundtrips; 288 CE записей перепроверены по сохранённым losses и независимой формуле; forecast арифметика проверена отдельно. Полные splits/схемы/модели/точные classes/losses/CSV находятся в текущем каталоге.', '',
      '| Stage | Wall s | CPU s | Peak total RSS MiB |','|---|---:|---:|---:|']
    for f,label in [('input-validation.json','Input preservation hashes + prepare'),('MODEL_FREEZE.json','Fit + validation + model serialization'),('decision.json','Test + forecasts'),('independent-audit.json','Independent checks')]:
        r=read(run/f);lines.append(f"| {label} | {r['wall_seconds']:.3f} | {r['cpu_seconds']:.3f} | {r['peak_rss_mib']:.2f} |")
    for r in read(run/'replay-validation.json')['records']:
        lines.append(f"| Geometry decoder {r['pair']} warm body | {r['wall_seconds']:.3f} | {r['cpu_seconds']:.3f} | {r['peak_rss_mib']:.2f} |")
        lines.append(f"| Decoder {r['pair']} cold process, import+I/O | {r['cold_wall_seconds']:.3f} | — | — |")
    pilot=read(run/'pilot.json')
    lines += ['',f"Pilot geometry projection: {pilot['geometry_projection_cpu_seconds']:.3f} s, conservative whole-study180 s CPU/256 MiB. Runtime stages measured separately; development time not included. RSS is measured total process working set; GPU/VRAM not used.", '',
      'Репликация из <PROJECT_ROOT>, всегда новый run path:', '', '```powershell',
      "$env:PYTHONDONTWRITEBYTECODE='1'", "$py='.tools/phase2-plotting-env/Scripts/python.exe'", "$run='research/hashed_multiplicity_study_<NEW_UNIQUE_ID>'",
      *[f'& $py -m research.experiment_bench.multiplicity.study {s} --run $run' for s in ('prepare','fit','replay','test')],
      '& $py -m research.experiment_bench.multiplicity.report --run $run','```','',
      '## Допустимый научный вывод и следующий шаг', '',
      'Положительная held-out ΔCE означает дополнительную предиктивную связь multiplicity с fine symbols сверх G3, но не причинность и не независимое подтверждение. Оплата двух дополнительных классов оценивается отдельно. Отрицательный net не означает отсутствия любой геометрической зависимости. Count6 сам по себе является простой предзаданной категоризацией; научная новизна не заявляется.', '',
      'Для GO уровня минимальный следующий validation — тот же frozen Count6 protocol на независимом checkpoint, без подбора bucket configurations. При NO-GO отдельный Count6 codec не обоснован этим gate; Mean8 actual experiment B выполняется независимо. Смешанный geometry+feature context в этой работе не реализуется.', '',
      'Ни entropy coding, ни quantization, ни обучение Grid4D не выполнялись. Preserved source hashes и source snapshot, final-validation.json и все предыдущие отчёты сохраняются; завершённые файлы не перезаписываются.', '',
      *[f'[{f}]({(run/f).as_posix()})' for f in ('PREREGISTERED_PROTOCOL.json','decision.json','test-scores.csv','paired-differences.csv','model-sizes.csv','predicted-net.csv','replay-validation.json','independent-audit.json','final-validation.json')]]
    with (run/'MULTIPLICITY_REPORT.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
    write_json(run/'report-resource.json',timing(t,cpu))

def finalize(run):
    t=time.perf_counter();c=time.process_time();protected=read(run/'protected-input-hashes.json')
    for p,h in protected.items():assert sha(ROOT/p)==h,p
    freeze=read(run/'MODEL_FREEZE.json')
    for p,h in freeze['frozen_artifacts'].items():assert sha(run/p)==h,p
    for p,h in freeze['source_sha256'].items():assert sha(ROOT/p)==h,p
    sources={};snapshot=run/'source_snapshot';snapshot.mkdir()
    for p in list(Path(__file__).parent.glob('*.py'))+[ROOT/'research/experiment_bench/hashed_interlevel/core.py',ROOT/'research/experiment_bench/hashed_interlevel/dry_model.py',ROOT/'research/experiment_bench/models.py']:
        name=p.relative_to(ROOT);target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True)
        with p.open('rb') as f,target.open('xb') as g:shutil.copyfileobj(f,g)
        assert sha(p)==sha(target);sources[name.as_posix()]=sha(p)
    write_json(run/'source-hashes.json',sources)
    report=run/'MULTIPLICITY_REPORT.md';text=report.read_text(encoding='utf-8')
    for link in re.findall(r'\]\(([^)]+)\)',text):
        if link.endswith('/final-validation.json'):continue
        assert Path(link).exists(),link
    hashes={p.relative_to(run).as_posix():sha(p) for p in run.rglob('*') if p.is_file() and 'matplotlib_config' not in p.parts}
    write_json(run/'final-validation.json',{'status':'PASS','protected_files_unchanged':len(protected),'frozen_artifacts_unchanged':len(freeze['frozen_artifacts']),
          'source_files_snapshotted':len(sources),'artifact_hashes':hashes,'actual_entropy_coding':False,'GPU_used':False,**timing(t,c)})
    print(json.dumps({'status':'PASS','report':str(report),'protected_files_unchanged':len(protected)}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);a=ap.parse_args();run=Path(a.run).resolve()
    audit(run);render(run);finalize(run)
