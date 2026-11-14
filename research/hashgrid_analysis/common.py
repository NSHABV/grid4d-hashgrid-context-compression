import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GRIDS=('xyz','xyt','yzt','xzt')
SHA='3306dabf8057728abfa7cda87d78c723b27a357f968fd7d721ea727ebd043090'

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def resolve(path):
    p=Path(path)
    return p if p.is_absolute() else ROOT/p

def csv_write(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def defaults():
    return {'checkpoint':'outputs/grid4d/bouncingballs-reference-50000/deform/iteration_50000/deform.pth',
        'runtime':'research/experiment_bench/reference-runtime.json','study':'research/experiment_bench/reference-study',
        'experiments':'experiments','repo':'external/Grid4D-audit-clean','seed':0,'sampling_budget':20000,
        'collision_budget':100000,'enumeration_limit':250000,'grids':list(GRIDS),'levels':None,
        'quantization':'all','output':'research/analysis_results','section':'all','histogram_bins':128}
