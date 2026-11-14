"""Small read-only parity probe of the existing pinned Grid4D CUDA extension.

This diagnostic loads already-built extension binaries directly. It does not
load a checkpoint, compile an extension, quantize parameters, or fit a model.
CPU replay remains authoritative; tolerance parity is not a bin-class claim.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[3]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def cached_cuda():
    """Import the exact compiled bindings without torch's compilation frontend."""
    repo = ROOT / 'external/Grid4D-audit-clean'
    source = repo / 'hashencoder/src/hashencoder.cu'
    probe = ROOT / '.tools/hashgrid-analysis-probe/grid4d_analysis_probe.so'
    backend = repo / 'tmp_build/_hash_encoder.so'
    helper = ROOT / '.tools/hashgrid-analysis-probe/upstream_index.inc'
    text = source.read_text()
    begin = text.index('template <uint32_t D>\n__device__ uint32_t fast_hash')
    end = text.index('template <uint32_t D>\n__device__ uint32_t get_grid_index(const uint32_t pos_grid[D])', begin)
    if helper.read_text() != text[begin:end]:
        raise ValueError('Cached indexing helper differs from current upstream source')
    modules = []
    for name, path in [('grid4d_analysis_probe', probe), ('_hash_encoder', backend)]:
        if not path.is_file():
            raise FileNotFoundError('Existing CUDA binary unavailable: ' + str(path))
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    sources = {str(p.relative_to(ROOT)): sha256(p) for p in [source, probe, backend, helper]}
    return modules[0], modules[1], sources


def point_queries(fine, budget=512, seed=20261013):
    """Boundary, nominal vertices, and random inputs with a fixed small budget."""
    if not 128 <= budget <= 512:
        raise ValueError('GPU queries restricted to 128..512')
    rng = np.random.default_rng(seed)
    r = np.asarray(fine['lookup_resolution'], dtype=np.int64)
    scale = np.asarray(fine['scale'], dtype=np.float32)
    queries = []
    labels = []
    def add(value, label):
        queries.append(np.asarray(value, dtype=np.float32))
        labels.append(label)
    for corner in range(8):
        add([(corner >> d) & 1 for d in range(3)], 'unit_cube_boundary')
    add([.5, .5, .5], 'unit_cube_center')
    for axis in range(3):
        for value in [np.nextafter(np.float32(0), np.float32(-1)),
                      np.nextafter(np.float32(0), np.float32(1)),
                      np.nextafter(np.float32(1), np.float32(0)),
                      np.nextafter(np.float32(1), np.float32(2))]:
            u = np.full(3, np.float32(.5))
            u[axis] = value
            add(u, 'nextafter_boundary')
    for axis in range(3):
        for value in [0, int(np.floor(scale[axis])), int(r[axis] - 1)]:
            vertex = np.zeros(3, dtype=np.float32)
            vertex[axis] = value
            add(vertex / scale, 'real_fine_vertex_boundary')
    for _ in range(192):
        vertex = np.array([rng.integers(0, int(x)) for x in r], dtype=np.float32)
        add(vertex / scale, 'real_fine_nominal_vertex')
    while len(queries) < budget:
        add(rng.random(3).astype(np.float32), 'random_unit_cube')
    return np.ascontiguousarray(queries[:budget], dtype=np.float32), labels[:budget]


def vertex_queries(resolution, budget=512, seed=20261013):
    """All vertex-lattice boundaries plus independent scalar-overflow cases."""
    rng = np.random.default_rng(seed)
    r = np.asarray(resolution, dtype=np.int64)
    result = []
    for corner in range(8):
        result.append([int(r[d] - 1) if (corner >> d) & 1 else 0 for d in range(3)])
    # uint32 products overflow for ordinary y/z coordinates as well; these
    # additional values explicitly stress wrapping arithmetic in the helper.
    result.extend([[2147483647, 2147483647, 2147483647],
                   [2147483647, 0, 0], [0, 2147483647, 0], [0, 0, 2147483647]])
    while len(result) < budget:
        result.append([int(rng.integers(0, int(x))) for x in r])
    return np.ascontiguousarray(result[:budget], dtype=np.int32)


def cuda_lookup(backend, coordinates, coarse_table, prefix_offsets, per_level_scale, base_resolution):
    """Call official forward with original global offsets and zero lower levels."""
    offsets = np.asarray(prefix_offsets, dtype=np.int32)
    if len(offsets) < 2 or offsets[-1] - offsets[-2] != len(coarse_table):
        raise ValueError('Coarse prefix offsets mismatch')
    u = torch.from_numpy(coordinates).cuda()
    prefix = torch.zeros((int(offsets[-1]), 2), device='cuda', dtype=torch.float32)
    prefix[int(offsets[-2]):] = torch.from_numpy(np.ascontiguousarray(coarse_table)).cuda()
    off = torch.from_numpy(offsets).cuda()
    q = torch.tensor(per_level_scale, device='cuda', dtype=torch.float32)
    base = torch.tensor(base_resolution, device='cuda', dtype=torch.float32)
    q_log = torch.log2(q)
    levels = len(offsets) - 1
    output = torch.empty((levels, len(u), 2), device='cuda', dtype=torch.float32)
    derivative = torch.empty(1, device='cuda', dtype=torch.float32)
    with torch.no_grad():
        backend.hash_encode_forward(u, prefix, off, output, len(u), 3, 2,
                                    levels, q_log, base, False, derivative)
    return output[-1].cpu().numpy(), q_log, base, prefix.nbytes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    bundle = Path(args.bundle).resolve()
    out = Path(args.output).resolve()
    if out.exists():
        raise FileExistsError('GPU output directory must be new')
    start = time.perf_counter()
    # Import only the causal CPU implementation, never a checkpoint reader.
    from . import core
    allowed_artifacts = {bundle / 'decoder_metadata.json', bundle / 'coarse_symbols.npy'}
    artifact_reads = []
    blocked_reads = []
    def read_audit(event, values):
        if event != 'open' or not isinstance(values[0], (str, bytes)):
            return
        path = Path(os.fsdecode(values[0])).resolve()
        mode = values[1]
        if mode is not None and not ('r' in mode and '+' not in mode):
            return
        if not path.is_relative_to(ROOT) or path.is_relative_to(out):
            return
        if path in allowed_artifacts:
            artifact_reads.append(str(path))
            return
        if path.suffix in {'.py', '.pyc', '.so', '.cu', '.inc', '.cpp', '.h'}:
            return
        blocked_reads.append(str(path))
        raise PermissionError('GPU replay attempted forbidden research-data read: ' + str(path))
    sys.addaudithook(read_audit)
    meta, symbols = core.load_bundle(bundle)
    table = core.dequantize_symbols(symbols, meta['coarse']['quantization'])
    coarse = meta['coarse']
    fine = meta['fine']
    implementation = meta['implementation']
    instrument, backend, sources = cached_cuda()
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    before_memory = torch.cuda.memory_allocated()
    torch.cuda.reset_peak_memory_stats()
    u, labels = point_queries(fine)
    cpu = core.lookup_cpu(u, table, coarse['scale'], coarse['lookup_resolution'])
    gpu, q_log, base, prefix_bytes = cuda_lookup(
        backend, u, table, implementation['coarse_prefix_offsets'],
        implementation['per_level_scale'], implementation['base_resolution'])
    scale_gpu, resolution_gpu = instrument.scales(q_log, base, int(fine['level']) + 1)
    scales = scale_gpu.cpu().numpy()
    resolutions = resolution_gpu.cpu().numpy()
    np.testing.assert_array_equal(scales[int(coarse['level'])], np.asarray(coarse['scale'], dtype=np.float32))
    np.testing.assert_array_equal(resolutions[int(coarse['level'])], np.asarray(coarse['lookup_resolution']))
    np.testing.assert_array_equal(scales[int(fine['level'])], np.asarray(fine['scale'], dtype=np.float32))
    np.testing.assert_array_equal(resolutions[int(fine['level'])], np.asarray(fine['lookup_resolution']))
    np.testing.assert_array_equal(q_log.cpu().numpy(), np.asarray(implementation['kernel_log2_per_level_scale'], dtype=np.float32))
    np.testing.assert_allclose(cpu, gpu, atol=5e-6, rtol=2e-5)
    in_bounds = np.all((u >= 0) & (u <= 1), axis=1)
    np.testing.assert_array_equal(cpu[~in_bounds], 0)
    np.testing.assert_array_equal(gpu[~in_bounds], 0)
    index_checks = []
    arrays = {'coordinates': u, 'cpu_features': cpu, 'gpu_features': gpu,
              'lookup_in_bounds': in_bounds}
    for level in [coarse, fine]:
        vertices = vertex_queries(level['lookup_resolution'], seed=20261013 + int(level['level']))
        cpu_index = core.slot_indices(vertices, level['lookup_resolution'], int(level['rows']))
        gpu_index = instrument.indices(torch.from_numpy(vertices).cuda(),
            torch.tensor(level['lookup_resolution'], device='cuda', dtype=torch.int32),
            int(level['rows'])).cpu().numpy()
        np.testing.assert_array_equal(cpu_index, gpu_index)
        index_checks.append({'level': int(level['level']), 'vertices': len(vertices), 'exact_equal': True,
                             'includes_uint32_overflow': True})
        arrays['vertices_L' + str(level['level'])] = vertices
        arrays['cpu_indices_L' + str(level['level'])] = cpu_index
        arrays['gpu_indices_L' + str(level['level'])] = gpu_index
    torch.cuda.synchronize()
    result = {
        'status': 'PASS', 'pair': meta.get('pair', 'xyz hashed pair'),
        'queries': len(u), 'oob_queries': int((~in_bounds).sum()),
        'input_labels_counts': {label: labels.count(label) for label in sorted(set(labels))},
        'index_checks': index_checks, 'scales_and_resolutions_exact': True,
        'feature_max_abs_error': float(np.max(np.abs(cpu - gpu))),
        'feature_atol': 5e-6, 'feature_rtol': 2e-5,
        'feature_bitwise_equal': bool(np.array_equal(cpu, gpu)),
        'context_classes_checked': False,
        'context_classes_note': 'No context classes were constructed. GPU tolerance parity does not establish class equality.',
        'cpu_is_decoder_reference': True, 'original_checkpoint_loaded': False,
        'fine_symbols_loaded': False, 'new_quantization': False,
        'allowed_artifact_reads': sorted(set(artifact_reads)), 'blocked_reads': blocked_reads,
        'source_sha256': sources, 'bundle': str(bundle),
        'metadata_sha256': sha256(bundle / 'decoder_metadata.json'),
        'coarse_symbols_sha256': sha256(bundle / 'coarse_symbols.npy'),
        'coarse_prefix_tensor_bytes': prefix_bytes,
        'torch_peak_allocated_bytes': int(torch.cuda.max_memory_allocated()),
        'torch_before_allocated_bytes': before_memory,
        'process_peak_rss_bytes': int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024,
        'seconds': time.perf_counter() - start,
        'environment': {'python': sys.version, 'numpy': np.__version__, 'torch': torch.__version__,
                        'CUDA': torch.version.cuda, 'GPU': torch.cuda.get_device_name()},
        'pid': os.getpid(),
    }
    out.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(out / 'gpu-parity-samples.npz', **arrays)
    with (out / 'gpu-parity-samples.csv').open('x', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['query', 'type', 'u_x', 'u_y', 'u_z', 'in_bounds',
                         'cpu_0', 'cpu_1', 'gpu_0', 'gpu_1'])
        for i in range(len(u)):
            writer.writerow([i, labels[i], *u[i].tolist(), int(in_bounds[i]), *cpu[i].tolist(), *gpu[i].tolist()])
    result['samples_sha256'] = sha256(out / 'gpu-parity-samples.npz')
    with (out / 'gpu-parity.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ['status', 'pair', 'queries', 'feature_max_abs_error',
                                                'feature_bitwise_equal', 'torch_peak_allocated_bytes', 'seconds']}), flush=True)


if __name__ == '__main__':
    main()
