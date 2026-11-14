"""Actual upstream GPU forward parity after importing lossless tables."""
import importlib.util
import argparse
import json
import sys
from pathlib import Path
import torch
from .codec import KEYS, import_tables, load_checkpoint, write_json

ROOT = Path(__file__).resolve().parents[2]


def run(out=ROOT / 'research/phase2', checkpoint=None, repo=None, record=None):
    repo = repo or ROOT / 'external/Grid4D-audit-clean'
    sys.path.insert(0, str(repo))
    from scene import DeformModel
    spec = importlib.util.spec_from_file_location('config', repo / 'arguments/dnerf/bouncingballs.py')
    conf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conf)
    original = load_checkpoint(checkpoint or ROOT / 'outputs/grid4d/bouncingballs-audit-200/deform/iteration_200/deform.pth')
    tables, buffers, _ = import_tables(out / 'lossless')
    model = DeformModel(conf.grid_args, conf.network_args, reg_spatial_able=False, reg_temporal_able=False)
    model.grid4d.load_state_dict(original[0], strict=True)
    model.deform.load_state_dict(original[1], strict=True)
    torch.manual_seed(42)
    xyz = torch.rand(257, 3, device='cuda') * 4 - 2
    t = torch.linspace(0, 1, 257, device='cuda')[:, None]
    with torch.no_grad():
        before = model.step(xyz, t, fixed_attention=True)
        # Deliberately populate the spatial attention cache, then replace parameters.
        for key, value in tables.items():
            model.grid4d.get_parameter(key).copy_(value.cuda())
        model.deform.attention_score = None
        after = model.step(xyz, t, fixed_attention=True)
        for key, value in before.items():
            if value is not None:
                assert torch.equal(value, after[key]), key
                assert torch.isfinite(value).all()
        for key, value in model.grid4d.state_dict().items():
            assert torch.equal(value.cpu(), original[0][key]), key
    write_json(record or out / 'forward-test.json', {'passed': True, 'coordinates': 257,
               'lossless_outputs_torch_equal': True, 'all_grid_state_unchanged': True,
               'attention_cache_reset': True, 'finite': True})
    print('GPU forward round trip: PASS')


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,default=ROOT/'research/phase2')
    p.add_argument('--checkpoint',type=Path)
    p.add_argument('--repo',type=Path)
    p.add_argument('--record',type=Path)
    args=p.parse_args()
    run(args.out,args.checkpoint,args.repo,args.record)
