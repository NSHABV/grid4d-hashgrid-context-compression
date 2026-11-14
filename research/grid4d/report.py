"""Verify complete study artifacts and generate the phase-2 report."""
import json
import math
import tarfile
from pathlib import Path
import numpy as np
import torch
from PIL import Image, ImageDraw
from .codec import KEYS, import_tables, load_checkpoint, sha, write_json
from .study import ROOT, SOURCE, OUT, csv_save


def run():
    summary = json.loads((OUT / 'summary.json').read_text())
    audit = json.loads((ROOT / 'research/audit/verification.json').read_text())
    identity = json.loads((ROOT / 'research/audit/identity.json').read_text())
    assert sha(ROOT / 'research/grid4d-blackwell-compat.patch') == identity['patch_sha256']
    assert sha(ROOT / 'research/audit/grid4d-upstream.tar') == identity['upstream_archive_sha256']
    source_count = 0
    with tarfile.open(ROOT / 'research/audit/grid4d-upstream.tar') as archive:
        for item in archive:
            if not item.isfile() or '__pycache__' in Path(item.name).parts:
                continue
            expected = ((ROOT / 'external/Grid4D' / item.name).read_bytes().replace(b'\r\n', b'\n')
                        if item.name in identity['source_patches'] else archive.extractfile(item).read())
            assert (ROOT / 'external/Grid4D-audit-clean' / item.name).read_bytes() == expected, item.name
            source_count += 1
    dataset_files = 0
    for manifest_path, dataset_root in ((ROOT / 'research/dataset-manifest.json', ROOT / 'data/dnerf'),
                                       (ROOT / 'research/audit/dataset-manifest.json', ROOT / 'research/audit/data/dnerf')):
        for record in json.loads(manifest_path.read_text())['files']:
            assert sha(dataset_root / record['path']) == record['sha256'], record['path']
            dataset_files += 1
        assert sha(dataset_root / 'bouncingballs/points3d.ply') == 'f9a2601f8b96bb7381e8b9086c70d97790c4d93026932e332838e0e9e256c971'
    for relative, record in json.loads((ROOT / 'research/baseline-artifacts.json').read_text())['artifacts'].items():
        assert sha(ROOT / 'outputs/grid4d/bouncingballs-smoke-200' / relative) == record['sha256']
    for relative, record in audit['artifacts'].items():
        assert sha(SOURCE / relative) == record['sha256'], relative
    original = load_checkpoint(SOURCE / 'deform/iteration_200/deform.pth')
    tables, buffers, manifest = import_tables(OUT / 'lossless')
    assert all(torch.equal(original[0][k], tables[k]) and
               original[0][k].numpy().tobytes() == tables[k].numpy().tobytes() for k in KEYS)
    assert all(torch.equal(original[0][k], v) for k, v in buffers.items())
    assert json.loads((OUT / 'forward-test.json').read_text())['passed']
    inference = {}
    metrics = {}
    image_checks = {}
    for name in ('original', 'restored', 'table-16', 'table-12', 'table-8', 'level-16', 'level-12', 'level-8'):
        folder = OUT / name
        inference[name] = json.loads((folder / 'inference.json').read_text())
        assert inference[name]['steps'] == 20 and inference[name]['strict_load']
        assert inference[name]['all_non_embeddings_unchanged']
        model = folder / 'model'
        metrics[name] = json.loads((model / 'results.json').read_text())['ours_200']
        per_view = json.loads((model / 'per_view.json').read_text())['ours_200']
        assert set(metrics[name]) == {'PSNR', 'SSIM', 'LPIPS', 'MS-SSIM'}
        assert all(math.isfinite(v) for v in metrics[name].values())
        assert all(len(v) == 20 and all(math.isfinite(x) for x in v.values()) for v in per_view.values())
        assert sha(model / 'point_cloud/iteration_200/point_cloud.ply') == audit['artifacts']['point_cloud/iteration_200/point_cloud.ply']['sha256']
        frame_checks = []
        for category in ('renders', 'gt', 'depth'):
            images = sorted((model / f'test/ours_200/{category}').glob('*.png'))
            assert len(images) == 20
            for p in images:
                image = np.asarray(Image.open(p))
                assert image.shape[:2] == (400, 400) and image.std() > 0
                if category == 'gt':
                    assert sha(p) == sha(SOURCE / f'test/ours_200/gt/{p.name}')
                if category == 'renders':
                    frame_checks.append(sha(p))
        image_checks[name] = frame_checks
    assert inference['original']['frames'] == inference['restored']['frames']
    assert image_checks['original'] == image_checks['restored']
    assert metrics['original'] == metrics['restored']
    assert image_checks['original'] == [sha(p) for p in sorted((SOURCE / 'test/ours_200/renders').glob('*.png'))]
    for key in metrics['original']:
        assert abs(metrics['original'][key] - audit['metrics'][key]) < 1e-6
    for row in summary['variants']:
        row['metrics'] = metrics[row['variant']]
        row['delta_metrics'] = {k: v - metrics['original'][k] for k, v in row['metrics'].items()}
    write_json(OUT / 'summary-evaluated.json', summary)
    csv_save(OUT / 'comparison.csv', [{**{k: v for k, v in r.items() if k not in ('metrics', 'delta_metrics')},
                                     **r['metrics']} for r in summary['variants']])
    verification = {'passed': True, 'source_artifacts_sha256_unchanged': True,
                    'upstream_source_files_verified': source_count,
                    'original_and_audit_dataset_files_verified': dataset_files,
                    'lossless_bitwise_float32': True, 'level_buffers_exact': True,
                    'gpu_forward_parity': True, 'float_render_parity_20_views': True,
                    'png_render_parity_20_views': True, 'original_audit_png_parity': True,
                    'all_8_variants_finite_forward_and_render': True,
                    'same_gt_cameras_20': True, 'metrics': metrics}
    write_json(OUT / 'verification.json', verification)
    preview = Image.new('RGB', (1600, 435), 'white')
    draw = ImageDraw.Draw(preview)
    for i, (label, path) in enumerate((('Ground truth', SOURCE / 'test/ours_200/gt/00000.png'),
                     ('Original float32', OUT / 'original/model/test/ours_200/renders/00000.png'),
                     ('Table 8-bit', OUT / 'table-8/model/test/ours_200/renders/00000.png'),
                     ('Level 8-bit', OUT / 'level-8/model/test/ours_200/renders/00000.png'))):
        draw.text((i * 400 + 10, 10), label, fill='black')
        preview.paste(Image.open(path).convert('RGB'), (i * 400, 35))
    preview.save(OUT / 'preview.png')
    stats = json.loads((OUT / 'statistics.json').read_text())
    lines = ['# Фаза 2: экспорт, статистика и scalar quantization HashGrid Grid4D', '',
        'Дата: 2026-10-09. **PASS**: lossless round trip, GPU forward/render parity и все шесть quantization variants проверены.', '',
        '## A–B. Модули и тесты', '',
        '`research/grid4d/codec.py`: отдельный versioned raw interchange, CPU decoder, uniform min/max quantization, empirical entropy.',
        '`study.py`: статистика, гистограммы, 6 вариантов и копии inference bundles. `test_codec.py`: автоматические unit tests.',
        '`test_forward.py`: подстановка lossless tensors в настоящую GPU модель и torch.equal outputs на 257 coordinates, включая OOB.',
        '`inference_check.py`: wrapper upstream render.py; strict states, неизменность buffers/MLP, finite деформации/RGB/depth каждого view.',
        '`report.py`: проверка всех artifacts, float32 render hashes и PNG parity 20 views, метрик и сохранности исходных artifacts.', '',
        '5 unit tests PASS (каждый проверяет несколько bit depths/arrays). GPU test PASS. Original/restored forward и 20 float32 RGB frames bitwise equal.',
        'Все 8 запусков (original, restored, 6 quantized) создали по 20 RGB/GT/depth frames 400×400; 4 метрики ×20 views конечны.',
        'Evidence: `phase2/tests.log`, `forward-test.json`, `verification.json`, variant `inference.json`, `model/results.json`, `model/per_view.json`.', '',
        '## C. Lossless export/import и metadata', '',
        'Источник: `outputs/grid4d/bouncingballs-audit-200/deform/iteration_200/deform.pth`, SHA256 ' + summary['source_checkpoint_sha256'] + '.',
        'Grid4D official commit `3ab7b74482910d22fba7d51ac60c8cae1fe24bf1`; Python 3.10.21, torch 2.7.0+cu128, nvcc 12.8.93, GCC 13.4.0, sm120.',
        'Использовано существующее audit-env, без новых Grid4D dependencies. Upstream, исходные snapshots и datasets не изменялись; training не запускался.',
        'Matplotlib figures построены отдельно в Windows `.tools/phase2-plotting-env`: Python 3.12, NumPy 1.26.4, matplotlib 3.9.4; exact closure `phase2/plotting-requirements.txt`.',
        'Неизменность: проверены 1620 upstream source/resource files, SHA256 обеих исходных model bundles, 193+193 dataset files и обоих generated points3d.ply.', '',
        'Формат `phase2/lossless/manifest.json` + little-endian raw `.bin`: float32 embeddings, int32 offsets, float32 base_resolution/per_level_scale.',
        'Metadata включают имена, shapes/dtypes, feature dimensions, counts/bytes, L, offsets, table rows, allocation resolutions и actual CUDA lookup resolutions, config и source/runtime hashes.',
        'Metadata сверены с реальными checkpoint buffers; resolutions взяты из ранее проверенного GPU runtime record, а не выведены из shape.',
        'Temporal last level: allocation [32,32,16], CUDA lookup [33,33,16]. Их нельзя подменять друг другом.', '',
        'Программный интерфейс (из workspace root, в Grid4D environment):', '', '```python',
        'from pathlib import Path',
        'from research.grid4d.codec import export_lossless, import_tables, load_checkpoint, substitute',
        'checkpoint = Path("outputs/grid4d/bouncingballs-audit-200/deform/iteration_200/deform.pth")',
        'export_lossless(checkpoint, "research/audit/hashgrid-runtime.json", Path("research/new-export"))',
        'tables, buffers, metadata = import_tables("research/new-export")',
        'restored_state = substitute(load_checkpoint(checkpoint), tables, buffers)',
        '```', '',
        'Decoder использует только exported payload и metadata; исходные float32 нужны лишь для сравнения и неизменяемых MLP/Gaussians.',
        'Для настоящей модели: copy_ в `deform.grid4d.get_parameter(key)` под no_grad; сброс `deform.deform.attention_score=None` после подстановки.',
        'Исходные offsets и buffers не меняются. Gaussian PLY, deformation MLP, cfg_args/config, cameras и normalization остаются внешними необходимыми компонентами.', '',
        '## D. Статистика', '',
        'Population std (ddof=0), exact np.unique float32, нулевая доля включает ±0; histograms 80 bins. Статистика объединяет оба channels.',
        'JSON содержит counts/edges; CSV все уровни. PNG: `phase2/plots/tables.png` (bin probabilities, common x range) и четыре `*-levels.png` (per-level counts, individual x ranges); y scale logarithmic.', '',
        '| Grid | N | min | max | mean | std | unique | zero fraction |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for key, s in stats['tables'].items():
        lines.append(f'| {key} | {s["parameters"]} | {s["min"]:.7g} | {s["max"]:.7g} | {s["mean"]:.7g} | {s["std"]:.7g} | {s["unique_values"]} | {s["zero_fraction"]:.7g} |')
    lines += ['', 'G_xyz содержит большую часть scalar parameters; spatial/temporal marginal ranges и variances приведены отдельно. Сходство гистограмм не доказывает межуровневую/межсеточную зависимость.', '',
              '| Grid | Level | N | min | max | mean | std | unique | zero fraction |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in stats['levels']:
        lines.append(f'| {s["grid"].split("_")[0]} | {s["level"]} | {s["parameters"]} | {s["min"]:.6g} | {s["max"]:.6g} | {s["mean"]:.6g} | {s["std"]:.6g} | {s["unique_values"]} | {s["zero_fraction"]:.6g} |')
    lines += ['', '## E–G. Квантование, энтропия и rendering', '',
        'Uniform scalar min/max affine, round-to-nearest-even, arithmetic float64, decoded float32; диапазон 0..2^b-1. Scope table: одна пара min/max на grid; scope level: на каждый level.',
        'Constant arrays: zero symbols, step=0, exact constant reconstruction. Empty/nonfinite/wrong dtype rejected. Extreme float32 и subnormal arrays tested.',
        'Quantization params (bits/min/max/step/row interval/rounding) сохранены в manifest; decoder не читает original embeddings.', '',
        'Размер ниже — реально сериализованные embeddings/symbols + 12 buffers + JSON manifest, без Gaussians/MLP и без diagnostic inference copies.',
        '12-bit symbols сохранены в uint16, поэтому фактический payload совпадает по контейнерному размеру с 16-bit. Packed 12-bit stream не реализован.',
        'MSE вычислен float64, взвешен по всем 13163494 scalar values. Все quality metrics mean на тех же 20 камерах и PNG upstream protocol.', '',
        '| Вариант | Реальный размер, bytes | H, bits/symbol | MSE параметров | PSNR dB | SSIM | LPIPS |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in summary['variants']:
        h = '—' if r['empirical_bits_per_symbol'] is None else f'{r["empirical_bits_per_symbol"]:.6f}'
        m = r['metrics']
        lines.append(f'| {r["variant"]} | {r["serialized_bytes"]} | {h} | {r["mse"]:.8g} | {m["PSNR"]:.8f} | {m["SSIM"]:.8f} | {m["LPIPS"]:.8f} |')
    lines += ['', '| Вариант | Payload bytes | JSON+buffers bytes | Fixed codes bits | Fixed codes+metadata bytes | H*N bits | H*N/8+metadata bytes | Fixed reduction vs f32 | Entropy reduction vs f32 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in summary['variants'][1:]:
        lines.append(f'| {r["variant"]} | {r["payload_bytes"]} | {r["metadata_json_bytes"]+r["buffer_bytes"]} | {r["fixed_code_bits"]} | {r["fixed_with_metadata_bytes"]} | {r["theoretical_entropy_bits"]:.3f} | {r["theoretical_with_metadata_bytes"]:.3f} | {100*r["fixed_reduction_vs_float32"]:.3f}% | {100*r["entropy_reduction_vs_float32"]:.3f}% |')
    lines += ['', 'Fixed и entropy reductions в последней паре columns относятся к scalar payload без metadata; с metadata размеры указаны отдельно.',
        'H=-sum p log2 p. Для scope table итог — сумма N_g H_g; для scope level — сумма N_gl H_gl. Это marginal IID plug-in entropy, не contextual entropy.',
        '`phase2/entropy.csv/json`: H, unique symbols, theoretical bits и fixed bits для каждой таблицы и каждого уровня всех шести variants.',
        '**H*N — теоретическая оценка. Ни probability-count header, ни coder termination/framing, ни actual encoded bitstream не реализованы.** JSON и buffers учтены; незаданный entropy model/coder overhead не выдумывался.',
        'Saved reconstructed `model/deform/...pth` — диагностическая float32 копия для upstream inference, не compressed payload и не участвует в size columns.', '',
        'Одинаковые cameras, resolution=2 (400x400), black background, iteration=200, skip_train, Gaussian PLY и MLP. LPIPS net=vgg, upstream [0,1] normalize=False; протокол не менялся.',
        'Все metrics delta к original в `summary-evaluated.json`; per-view в каждом `model/per_view.json`. MS-SSIM также сохранён.',
        'Пример GT/original/table8/level8: `phase2/preview.png`. Lossless restored картинки и float RGB hashes совпали с original; original PNG также совпали с Phase1 audit.', '',
        '## H. Ограничения', '',
        'Только checkpoint после 200 iterations, warm_up=10, без densification, downsampled resolution. Качественно обученный snapshot не доступен в текущих artifacts и не обучался на этой фазе.',
        'Результаты подтверждают работоспособность инструментов, finite inference и локальную чувствительность smoke weights; они не являются полноценным rate-distortion исследованием.',
        'Энтропия зависит от histogram symbol counts и выбранного min/max; её нельзя считать достижимым размером без передачи/моделирования распределения.',
        'Snapshot inference-only, без optimizer/RNG. Quantized bundles не предназначены для продолжения обучения.', '',
        '## I. Следующий этап — только рекомендации', '',
        'Сначала получить один converged reference checkpoint той же сцены с неизменённым objective и зафиксировать 20-view baseline, затем повторить этот scalar study.',
        'До inter-level coding определить порядок symbols (grid, level, row, channel), доступность decoder-side context и causal schedule, сохранять exact buffers/resolutions и правила addressing.',
        'Нужно измерять conditional likelihood на отделённых данных и сравнивать с текущей marginal entropy, учитывать стоимость model/metadata и проверять decoder round trip.',
        'Текущий export интерфейс даёт tables/level slices и stable metadata; сходство marginal histograms не обосновывает context модель.',
        'Фаза 3 не запускалась. NVCC/CNC/neural models, temporal/collision/cross-grid context, bitstream encoder/decoder и CUDA changes не реализованы.', '',
        '## J. Воспроизведение', '', 'Из PowerShell в workspace:', '', '```powershell',
        'wsl -d Ubuntu -- bash research/run_phase2.sh tests',
        'wsl -d Ubuntu -- bash research/run_phase2.sh study',
        'wsl -d Ubuntu -- bash research/run_phase2.sh forward',
        'wsl -d Ubuntu -- bash research/run_phase2.sh render',
        'wsl -d Ubuntu -- bash research/run_phase2.sh metrics',
        'wsl -d Ubuntu -- bash research/run_phase2.sh verify', '```', '',
        'Запуски с сохранением logs и wall times: `powershell -NoProfile -ExecutionPolicy Bypass -File research/run_phase2_checks.ps1` после study. Bypass относится только к процессу, системная ExecutionPolicy не меняется.',
        'Для matplotlib графиков отдельно: создать `.tools/phase2-plotting-env` через Windows Python `-m venv`, установить `-r research/phase2/plotting-requirements.txt`, выполнить `.tools/phase2-plotting-env/Scripts/python.exe research/plot_phase2.py`.',
        '`study` требует отсутствующую output directory и не перезаписывает существующие данные. Для нового study: `python -m research.grid4d.study --out research/phase2-new` после source env_common; runtime stages здесь привязаны к phase2, выбрать соответствующие paths для нового output.',
        '`tests/forward/render/metrics/verify` повторяемы поверх research outputs; оригинальные artifacts не затрагиваются.',
        f'CPU study elapsed: {summary["cpu_study_seconds"]:.2f}s. Runtime logs: `phase2/render.log`, `metrics.log`; wall time стадий `phase2/stage-times.json`.',
        'Max GPU memory специально не профилировалась; Phase1 resource baseline остаётся в AUDIT_PHASE1.md.',
        'Сбой Windows sandbox setup refresh потребовал разрешённого запуска команд вне sandbox. Windows ExecutionPolicy блокировала .ps1: использован process-only Bypass; stderr warnings записаны без прерывания, проверяется native exit code.',
        'Новый cwd для GPU forward вызвал обычную JIT сборку encoder в root/tmp_build (102s стадия forward); CUDA source/flags не менялись. Rendering использует уже собранный upstream cache.',
        'В штатном bundled Python отсутствовал matplotlib, поэтому вспомогательный plotting env отделён от Grid4D. Исследовательский runtime остаётся locked Phase1.',
        'Итог определяется verification, а не одним exit code upstream metrics.py, который скрывает исключения.', '']
    (ROOT / 'research/PHASE2_REPORT.md').write_text('\n'.join(lines))
    print('Phase2 artifact verification PASS; report generated')


if __name__ == '__main__':
    run()
