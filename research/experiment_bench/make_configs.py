"""Create explicit reusable configs for one trained reference and six direct variants."""
import copy
from pathlib import Path
from research.grid4d.codec import write_json

ROOT = Path(__file__).resolve().parents[2]
folder = ROOT/'research/experiment_bench/configs'
folder.mkdir(exist_ok=True)
base = {'scene':'bouncingballs','checkpoint':'outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth',
    'runtime_metadata':'research/experiment_bench/reference-runtime.json', 'iteration':50000,
    'repo':'external/Grid4D-audit-clean','dataset':'research/audit/data/dnerf/bouncingballs','seed':0,
    'lossless_input':'research/experiment_bench/reference-study/lossless',
    'evaluation':{'render':True,'psnr':True,'ssim':True,'lpips':True,'ms_ssim':True}}


def save(name, model, bits, scope, reference=None):
    config=copy.deepcopy(base)
    config.update(id=f'reference-{name}',output_dir=f'experiments/reference-{name}',
        quantization={'bits':bits,'scope':scope}, compression={'coder':'range' if model in ('iid','channel_context') else 'raw','model':model})
    if model != 'float32':
        config['quantized_input']=f'research/experiment_bench/reference-study/{scope}-{bits}'
    if reference:
        config['direct_render_reference']=f'experiments/reference-{reference}'
    write_json(folder/f'reference-{name}.json',config)


save('float32','float32',32,'none')
for scope in ('table','level'):
    for bits in (16,12,8):
        save(f'{scope}-{bits}','quantized',bits,scope)
for name in ('fixed8','iid','channel_context'):
    save(name,name,8,'table','table-8')
print('Wrote 10 trained-reference experiment configurations')
