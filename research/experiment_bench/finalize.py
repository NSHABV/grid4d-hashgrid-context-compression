"""Independent final artifact checks and A-K report; no invented PASS results."""
import hashlib
import json
import re
import datetime
from pathlib import Path
import numpy as np
import torch
from PIL import Image, ImageDraw
from research.grid4d.codec import KEYS, _read_array, import_tables, sha, write_json
from .cli import ROOT, REVISION, source_identity, aggregate
from .entropy import parse

OUT=ROOT/'research/experiment_bench'
SOURCE=ROOT/'outputs/grid4d/bouncingballs-reference-50000'


def verify_previous():
    for doc, model in (('research/baseline-artifacts.json','outputs/grid4d/bouncingballs-smoke-200'),
                       ('research/audit/verification.json','outputs/grid4d/bouncingballs-audit-200')):
        for relative, record in json.loads((ROOT/doc).read_text())['artifacts'].items():
            assert sha(ROOT/model/relative)==record['sha256'], relative
    for path, dataset in (('research/dataset-manifest.json','data/dnerf'),
                          ('research/audit/dataset-manifest.json','research/audit/data/dnerf')):
        for record in json.loads((ROOT/path).read_text())['files']:
            assert sha(ROOT/dataset/record['path'])==record['sha256'],record['path']
    legacy=json.loads((ROOT/'research/phase2/summary.json').read_text())
    for name in ('lossless','table-16','table-12','table-8','level-16','level-12','level-8'):
        _,_,manifest=import_tables(ROOT/'research/phase2'/name)
        assert manifest['source_sha256']==legacy['source_checkpoint_sha256']
    return True


def main():
    verify_previous()
    figure_names=('bitrate-psnr.png','bitrate-ssim.png','bitrate-lpips.png','compression-ratio.png','coding-times.png')
    for name in figure_names:
        with Image.open(OUT/'figures'/name) as figure:
            figure.verify()
    core=source_identity(ROOT/'external/Grid4D-audit-clean')
    training=json.loads((OUT/'reference-training.json').read_text())
    assert training['success'] and training['finite_loss_checks']==50000
    assert training['all_checked_losses_finite'] and np.isfinite(training['loss_values']).all()
    runtime=json.loads((OUT/'reference-runtime.json').read_text())
    assert runtime['all_model_state_exact_loaded'] and runtime['all_state_finite'] and runtime['predicted_outputs_finite']
    assert runtime['checkpoint_sha256']==sha(SOURCE/'deform/iteration_50000/deform.pth')
    forward=json.loads((OUT/'reference-forward.json').read_text())
    assert forward['passed'] and forward['lossless_outputs_torch_equal']
    tests=json.loads((OUT/'tests.json').read_text())
    assert tests['unit_tests']['status']=='PASS' and all(v=='PASS' for v in tests['categories'].values())
    names=['float32','table-16','table-12','table-8','level-16','level-12','level-8','fixed8','iid','channel_context']
    records=[]
    for name in names:
        folder=ROOT/f'experiments/reference-{name}'
        config=json.loads((folder/'config.json').read_text())
        manifest=json.loads((folder/'manifest.json').read_text())
        comp=json.loads((folder/'compression.json').read_text())
        metrics=json.loads((folder/'metrics.json').read_text())
        verification=json.loads((folder/'verification.json').read_text())
        assert config['iteration']==50000 and manifest['checkpoint_sha256']==runtime['checkpoint_sha256']
        assert verification['passed'] and verification['frames']==20 and metrics['status']=='PASS'
        assert manifest['core_source_sha256']==core
        if name in ('fixed8','iid','channel_context'):
            assert verification['symbols_exact'] and verification['decoder_new_process']
            assert verification['float_render_png_metrics_equal_reference']
            assert (folder/'bitstream.bin').stat().st_size==comp['actual_bitstream_bytes']==comp['total_compressed_bytes']
            assert comp['coded_payload_bytes']+comp['model_overhead_bytes']+comp['metadata_framing_bytes']==comp['actual_bitstream_bytes']
            header, model_bytes, payload=parse(folder/'bitstream.bin')
            assert len(model_bytes)==comp['model_overhead_bytes'] and len(payload)==comp['coded_payload_bytes']
            decoded_manifest=json.loads((folder/'decoded/manifest.json').read_text())
            quant=OUT/'reference-study/table-8'
            quant_manifest=json.loads((quant/'manifest.json').read_text())
            for key in KEYS:
                a=_read_array(quant,quant_manifest['grids'][key]['payload'])
                b=_read_array(folder/'decoded',decoded_manifest['grids'][key]['payload'])
                assert np.array_equal(a,b)
        records.append({'variant':name,**comp,'metrics':metrics['values']})
    fixed=next(r for r in records if r['variant']=='fixed8')['total_compressed_bytes']
    for r in records:
        r['compression_ratio_fixed8_total']=fixed/r['total_compressed_bytes']
    aggregate(ROOT/'experiments',OUT/'aggregate')
    gpu=json.loads((OUT/'reference-training-gpu.json').read_text())
    peaks=[s['device_used_mib'] for s in gpu if 'device_used_mib' in s]
    training_summary={k:v for k,v in training.items() if k!='loss_values'}
    training_summary.update(loss_first=training['loss_values'][0],loss_last=training['loss_values'][-1],
        loss_min=min(training['loss_values']),sampled_peak_total_device_mib=max(peaks) if peaks else None)
    log=(OUT/'logs/reference-training.log').read_text()
    intermediate=[{'iteration':int(i),'l1':float(l1),'psnr_float':float(p)} for i,l1,p in
        re.findall(r'\[ITER (\d+)\] Evaluating test: L1 ([-+0-9.eE]+) PSNR ([-+0-9.eE]+)',log)]
    write_json(OUT/'training-summary.json',{'final':training_summary,'intermediate_evaluation':intermediate})
    verification={'verdict':'READY FOR RESEARCH','trained_reference_50000':True,
        'source_revision':REVISION,'checkpoint_sha256':runtime['checkpoint_sha256'],
        'original_artifacts_datasets_unchanged':True,'upstream_algorithm_core_unchanged':True,
        'lossless_gpu_forward_exact':True,'all_tests':tests,'trained_metrics':records[0]['metrics'],
        'actual_entropy_bitstreams':True,'iid_context_symbols_exact':True,'decoder_restart_no_source':True,
        'decoded_render_float_png_metrics_equal_direct_quantization':True,
        'reference_experiments':records,'training':training_summary,
        'non_implemented':['inter-level context','temporal context','collision-aware context','cross-grid context','NVCC','neural probability models','CUDA entropy coder']}
    write_json(OUT/'verification.json',verification)
    preview=Image.new('RGB',(2000,435),'white')
    draw=ImageDraw.Draw(preview)
    paths=[('GT',ROOT/'experiments/reference-float32/model/test/ours_50000/gt/00000.png'),
        ('Trained float32',ROOT/'experiments/reference-float32/renders/00000.png'),
        ('Fixed8 decoded',ROOT/'experiments/reference-fixed8/renders/00000.png'),
        ('IID decoded',ROOT/'experiments/reference-iid/renders/00000.png'),
        ('Context decoded',ROOT/'experiments/reference-channel_context/renders/00000.png')]
    for i,(label,path) in enumerate(paths):
        draw.text((400*i+10,10),label,fill='black')
        preview.paste(Image.open(path).convert('RGB').resize((400,400),Image.Resampling.LANCZOS),(400*i,35))
    preview.save(OUT/'preview.png')
    date=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).date().isoformat()
    lines=['# Grid4D experimental bench', '', f'Дата: {date}. Вердикт: **READY FOR RESEARCH**.', '',
        '## A. Environment and reproducibility', '',
        'Official upstream: [Grid4D](https://github.com/JiaweiXu8/Grid4D), revision `'+REVISION+'`.',
        'Сохранены Python 3.10.21, PyTorch 2.7.0+cu128, torchvision 0.22.0+cu128, CUDA Toolkit 12.8.93, GCC/G++ 13.4.0; WSL2 Ubuntu, RTX 5060 Laptop 8151 MiB, sm120.',
        'Использован существующий audit-env; baseline conda/pip locks не менялись. `constriction==0.4.2` установлен отдельно в `.tools/bench-python` (413874-byte wheel).',
        'Wheel SHA256 `2f104f35a6156809e9240ab11ee3b321a7b390df54b4dd43942257f3018a6346`; dependency NumPy>=1.16,<3, используется прежняя 1.21.6. License choice MIT; license texts в `experiment_bench/licenses/`.',
        'Sources: [constriction 0.4.2](https://pypi.org/project/constriction/0.4.2/), [API](https://bamler-lab.github.io/constriction/apidoc/python/stream/model.html).',
        'Matplotlib 3.9.4/NumPy 1.26.4 используются только в ранее созданном отдельном Windows plotting env. Новых CUDA kernels, source patches, training objective изменений нет.',
        'Минимальные изменения старого research-кода: Phase2 study/prepare_model и forward test получили iteration/path arguments; inference wrapper получил source/repo environment overrides. Старые defaults и outputs сохранены.', '',
        '## B. Trained reference checkpoint', '',
        'Подходящий official pretrained checkpoint не найден в README/project page и [releases](https://github.com/JiaweiXu8/Grid4D/releases); это ограниченный отрицательный результат поиска.',
        'Reference обучен локально с нуля; финальный snapshot выбран по фиксированной iteration=50000, не по best test score.',
        'Checkpoint: `outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth`, SHA256 `'+runtime['checkpoint_sha256']+'`.',
        'Gaussian PLY: `point_cloud/iteration_50000/point_cloud.ply`. cfg_args + scene config + cameras также обязательны. Optimizer/RNG не сохраняются upstream; exact resume не заявляется.',
        'Dataset прежний D-NeRF bouncingballs, 150 train/20 test, 800x800, black background. Полный стандартный protocol: 50000 iterations, warm-up3000, densification >500 и <15000 каждые100, threshold0.0002, opacity reset3000.',
        'LR: xyz1.6e-4→1.6e-6, max_steps35000; SH feature0.0025, opacity0.05, scaling0.001, rotation0.001; grid scale50, network scale5, deform LR max_steps45000.',
        'Objective: (1-.2)L1+.2(1-SSIM)+.5 spatial TV+.5 temporal TV; perturb/downsample как в official scene config. Original training densify_and_prune сохранён; отдельный research pruning не реализован.',
        'Runtime отличие: `--load2gpu_on_the_fly` для экономии VRAM; `--resolution 1` явно задаёт исходные 800x800. Warm-up, densification и iterations не уменьшались.',
        'Предварительный smoke3600: 132.42s, all3600 losses finite, save/load/20-view render PASS, torch reserved2.70GiB; это отдельный технический snapshot, не reference.',
        f'Full training: {training_summary["wall_seconds"]:.2f}s ({training_summary["wall_seconds"]/60:.2f}min), loss first={training_summary["loss_first"]:.8g}, last={training_summary["loss_last"]:.8g}, min={training_summary["loss_min"]:.8g}; все50000 checks finite.',
        f'Peak torch allocated={training_summary["peak_torch_allocated_bytes"]/2**30:.3f}GiB, reserved={training_summary["peak_torch_reserved_bytes"]/2**30:.3f}GiB; sampled total device peak={training_summary["sampled_peak_total_device_mib"]}MiB (includes desktop/other apps, samples5s).',
        'Все стандартные промежуточные snapshots сохранены отдельно, best snapshots также создаёт upstream. Intermediate test PSNR/L1: `training-summary.json`; loss values/timings: `reference-training.json`; TensorBoard events и training log доступны.',
        'Ресурсы до smoke: GPU free6779MiB (nvidia-smi), WSL availableRAM6828MiB из7579, swap2048MiB свободен; disk D free≈125GiB. Нехватки ресурсов/OOM не возникло.', '',
        '## C. Phase2 repeated results', '',
        '`reference-study/`: lossless export/import, структуры/buffers, 112-level statistics CSV/JSON, 6 scalar variants и empirical entropy CSV/JSON.',
        'HashGrid ровно4 trainable tables: xyz[6098108,2]L16; xyt/yzt/xzt[161213,2]L32. 13163494 scalars, 52653976 rawfloat32 bytes. Actual offsets/resolutions взяты из checkpoint и GPU runtime metadata.',
        'Allocation vs lookup temporal last resolution [32,32,16] vs [33,33,16] сохранены раздельно. All buffers unchanged; float32 equality и live GPU forward parity проверены.',
        'Quantization прежняя: min/max affine, nearest-even, float64 arithmetic, float32 reconstruction. table и level scopes,8/12/16bits. 12-bit serialized containers uint16; ideal12-bit cost отдельно, packing12 не реализован.', '',
        '| Variant | Actual serialized bytes | Parameter MSE | PSNR | SSIM | LPIPS | MS-SSIM |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in records[:7]:
        m=r['metrics']
        lines.append(f'| {r["variant"]} | {r["total_compressed_bytes"]} | {r["parameter_mse"]:.9g} | {m["PSNR"]:.7f} | {m["SSIM"]:.7f} | {m["LPIPS"]:.7f} | {m["MS-SSIM"]:.7f} |')
    lines += ['', 'Table-level empirical entropy/fixed ideal sizes (without probability header, not real entropy file sizes):', '',
        '| Variant | Ideal fixed bits | Empirical H bits/symbol | H*N bits | Serialized payload bytes | Metadata+buffers bytes |',
        '|---|---:|---:|---:|---:|---:|']
    study=json.loads((OUT/'reference-study/summary.json').read_text())
    for r in study['variants'][1:]:
        lines.append(f'| {r["variant"]} | {r["fixed_code_bits"]} | {r["empirical_bits_per_symbol"]:.7f} | {r["theoretical_entropy_bits"]:.3f} | {r["payload_bytes"]} | {r["metadata_json_bytes"]+r["buffer_bytes"]} |')
    lines += ['', '## D. Entropy coding', '',
        'Настоящий CPU range coder constriction0.4.2; `fixed8` — raw uint8 control с тем же metadata/framing. Self-contained formatv1: little-endian magic/version/section lengths, JSON, transmitted finite histograms, coded uint32 words, trailing SHA256.',
        'Decoder принимает только bitstream path и fresh output; в новом process восстанавливает uint8 symbols, quantization min/max/step, shapes/offsets/resolutions и exact float32 buffers. После этого Phase2 importer деквантует значения.',
        'Original checkpoint и quantized input не доступны isolated decoder tests: synthetic source directory физически удаляется перед restart decoding. Actual experiment decoder CLI также получает только bitstream/output.',
        'Exact symbol equality проверена для всех4 tables всех3 coding models. CRC/hash, version, section length, CDF/symbol failures дают exception/nonzero exit. Диагностические `.pth`, PLY, renders и logs не включены в compressed size.', '',
        '## E. Probability models', '',
        'IID: p(q0)p(q1) отдельно для каждой из4 таблиц. Context: p(q0)p(q1|q0>>4),16 classes; та же table/channel granularity и то же table-wise8-bit quantization.',
        'Schedule: decode allq0 rows ascending, затем q1 по class0..15, stable row order. Context extraction принимает только уже decodedq0. Encoder.fit видит всю сцену для двухпроходного histogram fit; все полученные distributions переданы и оплачены.',
        'Laplace alpha1, minimum finite mass1, largest-remainder normalization sum65536. Serialized masses uint32; CDF strict increasing, all256 symbols nonzero. Empty classes uniform. Constriction constructs its own deterministic24-bit model, perfect=False.',
        'IID model cost8192bytes; context69632bytes. Metadata/framing посчитаны по реальным секциям. Quantization parameters, bounds и buffers включены в JSON cost.',
        'Empirical H — plug-in entropy, finite histogram cross entropy — отдельная оценка по переданным masses; реальное coder rounding/finalization учитывается actual bytes. Теоретические числа не называются размером bitstream.', '',
        '## F. Experimental comparison', '',
        '| Method | Actual total bytes | Bits/symbol | CR vs raw float32 | CR vs fixed8 total | PSNR | SSIM | LPIPS | Encode s | Decode s |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    primary=[r for r in records if r['variant'] in ('float32','fixed8','iid','channel_context')]
    for r in primary:
        m=r['metrics']
        en='N/A' if r.get('encode_seconds') is None else f'{r["encode_seconds"]:.5f}'
        de='N/A' if r.get('decode_seconds') is None else f'{r["decode_seconds"]:.5f}'
        lines.append(f'| {r["variant"]} | {r["total_compressed_bytes"]} | {r["bits_per_symbol"]:.7f} | {r["compression_ratio_float32"]:.5f} | {r["compression_ratio_fixed8_total"]:.5f} | {m["PSNR"]:.7f} | {m["SSIM"]:.7f} | {m["LPIPS"]:.7f} | {en} | {de} |')
    lines += ['', 'Float32 reference actual cost — lossless serialized Phase2 directory (raw payload+buffers+manifest), не entropy stream. CR numerator rawfloat32=52653976bytes; fixed8 total ratio использует полный измеренный файл fixed8 с overhead.', '',
        '| Model | Payload bytes | Histogram bytes | Metadata/framing bytes | Empirical bits | Finite cross entropy bits | Actual payload bits - empirical | Actual total bits - empirical |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in primary[1:]:
        lines.append(f'| {r["variant"]} | {r["coded_payload_bytes"]} | {r["model_overhead_bytes"]} | {r["metadata_framing_bytes"]} | {r["theoretical_empirical_bits"]:.3f} | {r["finite_histogram_cross_entropy_bits"]:.3f} | {r["actual_minus_empirical_payload_bits"]:.3f} | {r["actual_minus_empirical_total_bits"]:.3f} |')
    iid=next(r for r in records if r['variant']=='iid')
    ctx=next(r for r in records if r['variant']=='channel_context')
    difference=iid['total_compressed_bytes']-ctx['total_compressed_bytes']
    lines += ['',f'Channel context vs IID: {difference:+d}bytes saved ({100*difference/iid["total_compressed_bytes"]:+.4f}%). Это измеренная разница полного файла, включая дополнительные histograms; отрицательное число означает ухудшение.',
        'Все3 coded methods восстанавливают одни и те же quantized symbols и float32 embeddings; float RGB, PNG и все4 mean metrics точно совпадают с direct-table8. Их качество одинаково по построению и фактической проверке.',
        'Encode/decode timers включают fit/serialization/hash/I/O, но исключают Python import/startup; отдельно сохранён decoder process wall time. Скорость не профилировалась повторными microbenchmarks; это один измеренный end-to-end run.',
        'Actual bytes относятся исключительно к HashGrid. MLP, Gaussian PLY и cameras требуются для rendering отдельно; сжатие всей сцены не заявляется.', '',
        '## G. Automated verification', '',
        f'{tests["unit_tests"]["tests_run"]} unit tests PASS, failures=0/errors=0. Log: `experiment_bench/logs/tests.log`; подробные статусы `tests.json`.', '',
        '| Test | Status |', '|---|---|']
    for test in tests['unit_tests']['details']:
        lines.append(f'| {test["test"]} | {test["status"]} |')
    lines += ['', 'Categories A–H: environment/import/data, export/import, quantization, coder/CDF/corruption, causal contexts, GPU forward/render, independent CPU PSNR+SSIM+LPIPS integration, new-process reproducibility — все PASS.',
        'Independent references: context class=int(q0)//16; exact entropy example Hq0=8,Hq1|class=4; known PSNR for constant difference0.5; schedule partition checks ensure each q1 once, ordered, no duplicate/missing rows.',
        'Experiment-level verification paths: `experiments/reference-*/verification.json`, `inference.json`, `model/per_view.json`; decoder reports/logs also сохранены.', '',
        '## H. Reproducibility', '',
        'Основная команда запуска одного нового эксперимента:', '', '```powershell',
        'wsl -d Ubuntu -- bash research/run_bench.sh cli run research/experiment_bench/configs/reference-iid.json',
        'wsl -d Ubuntu -- bash research/run_bench.sh tests', '```', '',
        'Config output_dir должен быть новым: для повторного запуска копировать config и выбрать новый output_dir/id; все остальные параметры неизменны. Optional shared lossless/quantized inputs можно убрать — pipeline выполнит extraction/quantization сам.',
        'Из Linux pinned env: `python -m research.experiment_bench.cli run <config.json>`. JSON выбран вместо YAML, без новой зависимости.',
        'Полное обучение с новым model path: команда из `reference-training.json` (default50000, warm-up3000). `run_bench.sh train` защищён guard и не перезаписывает existing reference.',
        'Повтор полного study: `python -m research.grid4d.study --source <model> --runtime <runtime.json> --out <fresh-study> --iteration 50000`.',
        'Проверка GPU lossless restore: `python -m research.grid4d.test_forward --out <study> --checkpoint <pth> --repo <repo> --record <fresh-record.json>`.',
        'Standalone decoder: `python -m research.experiment_bench.cli decode <bitstream.bin> <fresh-directory>`; checkpoint/source paths отсутствуют в CLI.',
        'Aggregation: `python -m research.experiment_bench.cli aggregate experiments research/experiment_bench/aggregate`.',
        'Complete first-run controller `research/run_reference_experiments.sh` требует завершённый standard training и отсутствующие study/experiment dirs. Это последовательность реально выполненных действий; повтор требует новые output paths.',
        'Figures: `.tools/phase2-plotting-env/Scripts/python.exe research/experiment_bench/plot_results.py`; output `experiment_bench/figures/`.', '',
        '## I. Limitations', '',
        'Одна synthetic сцена, один seed, один standard training. Bitwise независимых training runs не гарантируется CUDA atomicAdd; save/load/decoded rendering данного snapshot exact.',
        'LPIPS protocol сохранён как Phase2: VGG inputs[0,1],normalize=False. Сравнения с внешними papers/SOTA не заявляются.',
        'Smoke200/3600 не смешиваются с trained50000; aggregate хранит iteration/checkpoint hash, plots выбирают только50000.',
        'Only8-bit entropy streams; 12/16 quantization пока direct serialized references. No CUDA coding. No optimizer/RNG resume. Probability models fitted на кодируемой сцене и оплачены полностью; это технический contextual baseline, не основной метод НИР.',
        'Format checks are integrity validation, not cryptographic authentication. Trusted research-sized data; maximum section lengths ограничены. Version/coder/model semantics pin обязательны.', '',
        '## J. Extension guide', '',
        'Рабочие интерфейсы и binary spec: `experiment_bench/API.md`. Subclass/register model in MODELS, define decoder-available context/schedule, probability vectors, fitted-parameter serialization; выбрать model name в config.',
        'Для новых schedules beyond q0-first/q1 partitions нужен versioned schedule и отдельные independent causal tests; текущий baseline честно предоставляет именно q0-derived context + immutable public metadata.',
        'Renderer/training/checkpoint structure не меняются. После добавления модели выполнить test command, standalone restart decode, actual-byte accounting и parity с direct quantization.',
        'Inter-level, temporal, cross-grid, collision-aware и neural models не реализованы.', '',
        '## K. Readiness verdict', '',
        '**READY FOR RESEARCH**: standard50000 reference получен, quantization повторён, настоящие IID/context streams восстановлены точно, GPU render/evaluation совпали с direct quantization, actual rates/times измерены и все critical checks PASS.',
        'Фаза реализации основного межуровневого/временного метода не запускалась. Следующий эксперимент должен быть отдельной задачей.', '']
    (ROOT/'research/EXPERIMENT_BENCH_REPORT.md').write_text('\n'.join(lines))
    print('Independent final checks PASS; report generated')


if __name__=='__main__':
    main()
