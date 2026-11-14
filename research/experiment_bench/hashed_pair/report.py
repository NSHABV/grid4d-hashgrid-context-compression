"""Create the final immutable B report from measured files and checked records."""
import argparse,json,os,platform,statistics,sys
from pathlib import Path
import numpy as np
from .run import ROOT,read,csv_out
from research.hashgrid_analysis.hashed_context.runtime import write_json,peak_rss_mib

def make(run):
    run=Path(run).resolve();target=run/'BITSTREAM_REPORT.md'
    if target.exists():raise FileExistsError(target)
    checks=read(run/'decode-validation.json');assert checks['status']=='PASS'
    corrupt=read(run/'corruption_checks_02/corruption-checks.json');assert corrupt['status']=='PASS'
    assert read(run/'post_repair_validation/validation.json')['status']=='PASS'
    assert read(run/'B_INDEPENDENT_REVIEW.json')['status']=='PASS'
    rows=read(run/'results.json');best=read(run/'best.json');by={r['model']:r for r in best};m=by['Mean8']
    samples=read(run/'runtime-samples.json');timing=[]
    for r in best:
        values=[x for x in samples if x['model']==r['model'] and not x['warmup']]
        median=lambda section,key:statistics.median(x[section][key] for x in values)
        timing.append({'model':r['model'],'encode_median_s':median('encode','encode_total_seconds'),
            'encode_min_s':min(x['encode']['encode_total_seconds'] for x in values),
            'encode_max_s':max(x['encode']['encode_total_seconds'] for x in values),
            'strict_decode_median_s':median('decode','decode_total_seconds'),
            'strict_decode_min_s':min(x['decode']['decode_total_seconds'] for x in values),
            'strict_decode_max_s':max(x['decode']['decode_total_seconds'] for x in values),
            'context_encode_median_s':median('encode','context_seconds'),
            'context_decode_median_s':median('decode','context_seconds'),
            'canonical_validation_median_s':median('decode','canonical_validation_seconds'),
            'decode_without_reencode_median_s':statistics.median(x['decode']['decode_total_seconds']-x['decode']['canonical_validation_seconds'] for x in values),
            'cold_process_s':r['cold_decode_process_seconds'],
            'startup_and_io_excess_s':r['cold_decode_process_seconds']-r['strict_decode_seconds'],
            'decoder_peak_rss_mib':r['decoder_peak_rss_mib']})
    write_json(run/'runtime-summary.json',timing);csv_out(run/'runtime-summary.csv',timing)
    gain=[]
    for name in ('IID','Geometry4','Canonical8'):
        b=by[name];net=b['total_bytes']-m['total_bytes'];increment=b['total_bytes']-b['coarse_bytes']
        gain.append({'baseline':name,'actual_standalone_gain_bytes':net,'standalone_gain_percent':100*net/b['total_bytes'],
            'incremental_gain_bytes':net,'incremental_gain_percent':100*net/increment,
            'fine_payload_gain_bytes':b['fine_payload_bytes']-m['fine_payload_bytes'],
            'extra_probability_mass_bytes':m['model_bytes']-b['model_bytes'],
            'extra_metadata_framing_bytes':m['metadata_framing_bytes']-b['metadata_framing_bytes'],
            'finite_payload_gain_bytes':(b['finite_fine_bits']-m['finite_fine_bits'])/8})
    write_json(run/'actual-gains.json',gain);csv_out(run/'actual-gains.csv',gain)
    prior=read(ROOT/'research/hashed_dispersion_heldout_20261013_01/predicted-net.json');bridge=[]
    for name in ('Geometry4','Canonical8'):
        old=[r for r in prior if r['pair']=='L4_to_L5' and r['candidate']=='Mean8' and r['baseline']==name]
        b=by[name];g=next(x for x in gain if x['baseline']==name)
        bridge.append({'baseline':name,'old_predicted_gross_bytes':float(np.mean([r['gross_payload_saving_bytes'] for r in old])),
            'old_measured_extra_side_bytes':float(np.mean([r['delta_side_bytes'] for r in old])),
            'old_predicted_net_bytes':float(np.mean([r['net_saving_bytes'] for r in old])),
            'full_scene_finite_payload_gain_bytes':g['finite_payload_gain_bytes'],
            'actual_range_payload_gain_bytes':g['fine_payload_gain_bytes'],
            'actual_extra_side_bytes':g['extra_probability_mass_bytes']+g['extra_metadata_framing_bytes'],
            'actual_standalone_gain_bytes':g['actual_standalone_gain_bytes']})
    write_json(run/'prediction-bridge.json',bridge);csv_out(run/'prediction-bridge.csv',bridge)
    figures=run/'figures';figures.mkdir(exist_ok=False)
    cache=run/'matplotlib-cache';cache.mkdir(exist_ok=True)
    os.environ['MPLCONFIGDIR']=str(cache)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained');x=np.arange(4);bottom=np.zeros(4)
    for key,label,color in [('coarse_bytes','Shared coarse model + payload','#adb5bd'),('fine_payload_bytes','Fine range payload','#3979b7'),
                            ('model_bytes','Fine probability masses','#e9a23b'),('metadata_framing_bytes','All metadata / framing','#7b5ea7')]:
        val=np.array([r[key] for r in best])/1024;axes[0].bar(x,val,bottom=bottom,label=label,color=color);bottom+=val
    axes[0].set_xticks(x,[r['model'] for r in best]);axes[0].set_ylabel('Actual standalone KiB');axes[0].legend(fontsize=8,loc='upper left',bbox_to_anchor=(0,-.15),ncol=2)
    for i,r in enumerate(best):axes[0].text(i,bottom[i]+2,str(r['total_bytes']),ha='center',fontsize=9)
    axes[0].set_ylim(0,max(bottom)*1.14)
    axes[1].bar([r['baseline'] for r in gain],[r['actual_standalone_gain_bytes'] for r in gain],color='#24856d')
    axes[1].set_ylabel('Mean8 actual saving, bytes');axes[1].set_title('Each baseline uses its smallest verified transport')
    fig.suptitle('Frozen uint8 xyz L4+L5: measured files, exact reconstruction')
    for ext in ('png','svg'):fig.savefig(figures/('actual_sizes.'+ext),dpi=180)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.5),layout='constrained');w=.35
    ax.bar(x-w/2,[r['encode_median_s'] for r in timing],w,label='Warm encode',color='#3979b7')
    ax.bar(x+w/2,[r['strict_decode_median_s'] for r in timing],w,label='Warm strict decode',color='#24856d')
    ax.set_xticks(x,[r['model'] for r in timing]);ax.set_ylabel('Seconds, median of 3');ax.legend()
    ax.set_title('CPU; strict decode includes separately measured canonical re-encode')
    for ext in ('png','svg'):fig.savefig(figures/('runtime.'+ext),dpi=180)
    plt.close(fig)
    strongest=min((r for r in best if r['model']!='Mean8'),key=lambda r:r['total_bytes'])
    g=next(r for r in gain if r['baseline']==strongest['model']);go=all(r['actual_standalone_gain_bytes']>0 for r in gain)
    write_json(run/'decision.json',{'decision':'GO' if go else 'NO-GO','scope':'actual scene-specific standalone xyz L4+L5, table8',
        'best_baseline':strongest['model'],'gain_bytes':g['actual_standalone_gain_bytes'],'gain_percent':g['standalone_gain_percent'],
        'all_correctness_checks':'PASS','full_grid_rate_measured':False,'independent_checkpoint_generalization_tested':False})
    lines=['# Actual hashed inter-level bitstream: xyz L4 → L5','',
        '**Дата: 15 октября 2026. Статус: '+('GO' if go else 'NO-GO')+'.** Проверены реальные standalone файлы и независимое exact-symbol декодирование.',
        f"Mean8 **{m['total_bytes']} B**, сильнейший baseline {strongest['model']} **{strongest['total_bytes']} B**: экономия **{g['actual_standalone_gain_bytes']} B ({g['standalone_gain_percent']:.6f}%)**.",
        'Это actual scene-specific coding одной пары уровней одного checkpoint. Не whole-Grid4D compression ratio и не held-out generalization. Отрицательный результат Count6 и прежний NO-GO Mean4×Std2 сохраняются.',
        '', '## 1. Входы и причинный контракт', '',
        'Checkpoint `bouncingballs-reference-50000`; неизменный table-wise uint8 экспорт. q4 `[205379,2]`, q5 `[524288,2]`. SHA256 исходного checkpoint `3306dabf8057728abfa7cda87d78c723b27a357f968fd7d721ea727ebd043090`; полного xyz uint8 `b6f2676efa4c33d0cf2506271bafe0db0b133d05baeabaeb07eca8e47e939de8`. Все q4/q5 сверены с точными slices полного экспорта; повторного quantize/training нет. [Проверка входов](input-validation.json).',
        'L4: offsets [125561,330940), scale 57.3502311706543, R=59³, dense. L5: offsets [330940,855228), scale 79.63493347167969, R=81³, allocated rows 524288. uint32 stride/XOR hashing с primes 1,2654435761,805459861 и modulo allocated rows. Quantizer min −5.548852920532227, max 2.9999356269836426, step 0.03352466097065047; восстановление float64 affine → float32.',
        'Для каждого fine slot j: E_j — вершины его hash-preimage с v≤floor(scale); координаты float32(v)/float32(scale). Coarse lookup: smoothstep, восемь corners0…7, отдельные float32 операции без FMA. Mean8 использует anchored float64 mean по возрастающему x-fast ordinal, затем 8 quantile bins/channel + отдельные G0/G1. Canonical8 использует минимальный eligible ordinal. Пороговые равенства направляются вправо; repeated thresholds сохраняются.',
        'Encoder строит correspondences и coarse context без q5. Decoder сначала декодирует q4, самостоятельно восстанавливает context classes, затем декодирует q5. Fine symbols используются только encoder histogram fitting. Классы и таблица slot→vertices не передаются; class SHA служит integrity check. Fine targets не нужны для выбора класса. Все allocated rows, включая G0=183592, G1=7144, G2=200128, G3=133424, кодируются один раз, ch0 ascending slots затем ch1.',
        '', '## 2. Формат и честное сравнение', '',
        'Новый G4DHPAIR V1 изолирован от dense V2. Prefix `<8sH5Q>`; пять секций metadata/coarse_model/fine_model/coarse_payload/fine_payload; SHA256 trailer32 B. Metadata закрепляет обе geometry, hash/domain/interpolation, quantizer, arithmetic, model/engine version и integrity. Модели HDPM передают masses и binary float64 thresholds; CDF однозначно производен и не дублируется. [Точная спецификация и API](../experiment_bench/hashed_pair/README.md).',
        'Существующие indexed functions entropy.py используются verbatim через AST, без нового range coder. constriction0.4.2, Categorical(perfect=False), положительные finite16 masses суммой65536; внутренняя coder24 модель. Для actual fitting использованы все q5 symbols с прежним Laplace α=1 и stable integer rounding. Все fitted параметры оплачены.',
        'Каждый arm проверен с dense_u32, packed_u16 и sparse_default_u16; минимум выбран по реальному размеру файла независимо для каждой модели. Это минимум среди трёх проверенных transports, не доказанный глобальный optimum. Count6 не включён: A дал NO-GO, но B выполнен независимо.',
        'Общий coarse prerequisite 76130 B =75132 B q4 payload +998 B полный coarse IID model. Эти bytes идентичны во всех файлах. Центральная geometry и всё framing консервативно включены в incremental fine budget. Старый выигрыш L3→L4 сюда не добавлялся.',
        '', '## 3. Реальные физические размеры', '',
        'В колонке Model bytes указаны именно fine probability masses. Thresholds, model headers/specifications, центральная metadata и framing включены в последнюю расходную колонку. Сумма четырёх колонок точно равна filesystem size.', '',
        '| Модель / лучший transport | Coarse B | Fine payload B | Model B | Metadata/framing B | Total B |',
        '|---|---:|---:|---:|---:|---:|']
    for r in best:lines.append(f"| {r['model']} / {r['storage']} | {r['coarse_bytes']} | {r['fine_payload_bytes']} | {r['model_bytes']} | {r['metadata_framing_bytes']} | {r['total_bytes']} |")
    lines+=['','Все 12 фактических вариантов:','','| Model | dense_u32 B | packed_u16 B | sparse_default_u16 B |','|---|---:|---:|---:|']
    for name in by:lines.append('| '+name+' | '+' | '.join(str(next(r['total_bytes'] for r in rows if r['model']==name and r['storage']==s)) for s in ('dense_u32','packed_u16','sparse_default_u16'))+' |')
    lines+=['','[Точные секции и SHA каждого файла](results.json) · [CSV](results.csv) · [Лучшие файлы](best.json).',
        '', '![Физические размеры](figures/actual_sizes.png)', '', '## 4. Экономия и стоимость модели', '',
        '| Mean8 относительно | Standalone saving B | Pair % | Incremental fine % | Payload saving B | Extra model B | Extra metadata B |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in gain:lines.append(f"| {r['baseline']} | {r['actual_standalone_gain_bytes']} | {r['standalone_gain_percent']:.6f} | {r['incremental_gain_percent']:.6f} | {r['fine_payload_gain_bytes']} | {r['extra_probability_mass_bytes']} | {r['extra_metadata_framing_bytes']} |")
    lines+=['',f"Incremental Mean8 L5 =229233−76130=153103 B; Canonical8 =161255 B. Числитель экономии одинаков8152 B, знаменатели pair и incremental различны. Mean8 выигрывает8604 B payload у Canonical8, платит462 B дополнительных masses и экономит10 B прочей metadata: net8152 B.",
        'Dense Mean8243189 B проигрывает лучшему Canonical8 sparse237385 B; компактная сериализация имеет практическое значение. Нельзя обосновывать выигрыш одним payload. [Все gains](actual-gains.json).',
        '', '## 5. Held-out прогноз и actual результат', '',
        '| Baseline | Старый PREDICTED gross B | Старый measured extra side B | Старый PREDICTED net B | Full-scene finite gross B | Actual payload gain B | Actual extra side B | Actual net B |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in bridge:lines.append('| '+r['baseline']+' | '+' | '.join(f"{r[k]:.3f}" for k in ('old_predicted_gross_bytes','old_measured_extra_side_bytes','old_predicted_net_bytes','full_scene_finite_payload_gain_bytes','actual_range_payload_gain_bytes','actual_extra_side_bytes','actual_standalone_gain_bytes'))+' |')
    lines+=['', 'Прогноз был экстраполяцией test CE и train-fitted model costs. Actual refit использует всю сцену: меняются quantile thresholds, histogram masses и число sparse exceptions. Новый container учитывает свои реальные headers/thresholds/metadata. Разность full-scene finite и actual payload дополнительно отражает coder24 rounding/finalization. CPU arithmetic не менялась; GPU approximation здесь не участвовала. [Численное разложение](prediction-bridge.json). Старые Mean8/Mean4×Std2 результаты не переименованы в новый независимый held-out опыт.',
        '', '## 6. Correctness и устойчивость', '',
        '- 12 первоначальных fresh processes +12 повторных после исправления обработки ошибок: только один bin как experiment data input; checkpoint/export/targets/parent contexts/models не читаются.',
        '- Exact q4/q5 для1459334 symbols на файл, оба канала и все slots; class IDs также exact. 16 warm encodes и12 повторных encodes дают byte-identical файлы.',
        '- Все masses strictly positive, sums65536, transports exact; общие coarse bytes идентичны. Внешняя проверка сверяет все массивы, а не только hashes.',
        f"- {read(run/'corruption_checks_02/unit-tests.json').get('tests',15)} unit tests PASS; {corrupt['checks_total']} malformed/corrupted cases PASS с исправленным внешним SHA для semantic attacks. Включены geometry, quantizer, hash, threshold, mass, payload truncation/extra words/bitflip.",
        '- 7 явных запрещённых чтений отклонены. Python open audit — проверка поведения данного decoder, не OS security sandbox; public software imports/version metadata загружаются отдельно.',
        '- Независимый reviewer отдельно разобрал framing и физические lengths, проверил decoded arrays, classes, masses, storage selection и учёт расходов без fitting/encoding.',
        '', '[Decode validation](decode-validation.json) · [Повтор после исправления](post_repair_validation/validation.json) · [Corruption PASS](corruption_checks_02/corruption-checks.json) · [Независимый аудит](B_INDEPENDENT_REVIEW.json).',
        'Первый adversarial run сохранён:24/594 checks получили AssertionError библиотеки вместо требуемого ValueError API. Ни один повреждённый файл не был принят; valid decode не расходился. Новый adapter нормализует только эту ошибку. Старый engine и bytes не изменены; полный набор проверок повторён. [История](failure-history.json).',
        '', '## 7. Время и память', '',
        'Один warmup +3 measured repeats каждого лучшего файла. Warm time исключает startup/import/disk IO; strict decode включает canonical re-encoding для выявления игнорируемых trailing words. Этот overhead показан отдельно. Cold column — отдельный fresh process вместе с imports/IO; это не измерение пустого OS disk cache.',
        '', '| Model | Encode median s | Strict decode s | Context encode / decode s | Canonical validation s | Decode без re-encode s | Cold process s |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in timing:lines.append(f"| {r['model']} | {r['encode_median_s']:.4f} | {r['strict_decode_median_s']:.4f} | {r['context_encode_median_s']:.4f} / {r['context_decode_median_s']:.4f} | {r['canonical_validation_median_s']:.4f} | {r['decode_without_reencode_median_s']:.4f} | {r['cold_process_s']:.4f} |")
    lines+=['',f"Peak encoder parent RSS {checks['peak_encoder_parent_rss_mib']:.2f} MiB; peak fresh decoder max {max(r['decoder_peak_rss_mib'] for r in rows):.2f} MiB. Это process working set, не сумма всей системы. GPU не использован, выделено0 VRAM. Не приписывается GPU ускорение. Canonical8 пока вызывает полный context builder с лишними mean/Std: его runtime характеризует текущую реализацию, не оптимальную lower bound.",
        '[Medians/min/max](runtime-summary.json) · [Все repeats](runtime-samples.json) · [Pilot](pilot-agent.json). Повтор после error-wrapper служит correctness check и не заменяет исходный benchmark.',
        '', '![CPU runtime](figures/runtime.png)', '', '## 8. Воспроизведение и пределы вывода', '',
        'Windows x86_64, Python3.12.14, NumPy1.26.4, constriction0.4.2; существующий plotting env. Новый Windows constriction установлен отдельно в `.tools/hashed-pair-deps` без обновления старого окружения. Runtime контракт закреплён; универсальная CPU/GPU portability не заявляется. [Runtime metadata](environment.json) и [requirements](requirements-research.txt).',
        'Из `<PROJECT_ROOT>` для нового уникального run:', '', '```powershell',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.hashed_pair.run prepare --run research/hashed_mean8_bitstream_NEW',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.hashed_pair.run execute --run research/hashed_mean8_bitstream_NEW',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.hashed_pair.replay --input research/hashed_mean8_bitstream_NEW/streams/Mean8__sparse_default_u16.bin --output research/decoded_NEW',
        '.tools/phase2-plotting-env/Scripts/python.exe -m unittest research.experiment_bench.hashed_pair.test_format -v',
        '.tools/phase2-plotting-env/Scripts/python.exe -m research.experiment_bench.hashed_pair.corruption --run research/hashed_mean8_bitstream_NEW --output research/hashed_mean8_bitstream_NEW/corruption_checks_NEW',
        '```', '',
        'Изменения только в новом исследовательском модуле hashed_pair и новых каталогах результатов. Upstream Grid4D, dense V2, квантованные symbols и прежние исследования сохранены. [Финальная проверка сохранности и source snapshot](final-validation.json).',
        'Точное entropy decoding добавляет нулевое искажение относительно frozen table8, но не устраняет прежнюю quantization error. Не кодируются остальные xyz levels, temporal tables, Gaussian PLY и deformation MLP. Нет проверки независимого checkpoint, всей сцены или RD-кривой. Mean8 не объявляется научной новизной.',
        'Следующий минимальный опыт: заранее зафиксированный Mean8 против тех же сильных baselines на независимом checkpoint с прежними scope/precision/arithmetic/transport rules. Новые count buckets на изученном test не подбирались. Этот следующий опыт здесь не запускался.']
    with target.open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
    write_json(run/'report-generation.json',{'status':'PASS','figures':2,'peak_rss_mib':peak_rss_mib(),'python':sys.version})
    print({'report':str(target),'decision':'GO' if go else 'NO-GO'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);make(p.parse_args().run)
