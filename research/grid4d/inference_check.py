"""Instrument the unmodified upstream renderer to assert finite outputs/state identity."""
import hashlib
import json
import os
import runpy
import sys
from pathlib import Path
import torch

ROOT = Path(__file__).resolve().parents[2]
repo = Path(os.environ.get('GRID4D_BENCH_REPO', ROOT / 'external/Grid4D-audit-clean'))
source_checkpoint = Path(os.environ.get('GRID4D_BENCH_SOURCE', ROOT / 'outputs/grid4d/bouncingballs-audit-200/deform/iteration_200/deform.pth'))
sys.path.insert(0, str(repo))
from scene import DeformModel
import gaussian_renderer

record_path = Path(sys.argv[1])
sys.argv = [str(repo / 'render.py'), *sys.argv[2:]]
records = {'frames': [], 'steps': 0, 'strict_load': False, 'all_non_embeddings_unchanged': False}
load = DeformModel.load_weights
step = DeformModel.step
render = gaussian_renderer.render


def checked_load(self, model_path, iteration=-1):
    load(self, model_path, iteration)
    state = torch.load(Path(model_path) / f'deform/iteration_{iteration}/deform.pth', map_location='cpu', weights_only=True)
    original = torch.load(source_checkpoint, map_location='cpu', weights_only=True)
    for module, expected in zip((self.grid4d, self.deform), state):
        keys = module.load_state_dict(expected, strict=True)
        assert not keys.missing_keys and not keys.unexpected_keys
        assert all(torch.equal(value.cpu(), expected[key]) for key, value in module.state_dict().items())
    for idx, current in enumerate(state):
        for key, value in current.items():
            assert torch.isfinite(value).all()
            if idx == 1 or not key.endswith('.embeddings'):
                assert torch.equal(value, original[idx][key]), key
    records['strict_load'] = records['all_non_embeddings_unchanged'] = True
    self.deform.attention_score = None


def checked_step(self, *args, **kwargs):
    result = step(self, *args, **kwargs)
    assert all(torch.isfinite(v).all() for v in result.values() if v is not None)
    records['steps'] += 1
    return result


def checked_render(*args, **kwargs):
    result = render(*args, **kwargs)
    for key in ('render', 'depth'):
        assert torch.isfinite(result[key]).all(), key
    rgb = result['render'].detach().cpu().numpy()
    records['frames'].append({'float32_rgb_sha256': hashlib.sha256(rgb.tobytes()).hexdigest(),
                              'shape': list(rgb.shape), 'min': float(rgb.min()), 'max': float(rgb.max())})
    return result


DeformModel.load_weights = checked_load
DeformModel.step = checked_step
gaussian_renderer.render = checked_render
runpy.run_path(sys.argv[0], run_name='__main__')
assert records['steps'] == 20 and len(records['frames']) == 20
record_path.write_text(json.dumps(records, indent=2) + '\n')
print('Finite forward/render and non-embedding state invariance: PASS')
