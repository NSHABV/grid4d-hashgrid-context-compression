"""Recompute published scalar attribution; no PMF fitting or entropy coding."""
from pathlib import Path
import csv,json,statistics
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'research/previous8_reserve_batch_20261108_01'
def read(name):
    with (R/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
s=read('SIX_SCENE_SUMMARY.csv')
assert len(s)==6 and len({r['scene'] for r in s})==6
for r in s:
    x,i,p=map(int,(r['X_B'],r['I_B'],r['P_B']))
    assert (x-i,i-p,x-p)==tuple(int(r[k]) for k in ('X_to_I_B','I_to_P_B','X_to_P_B'))
    assert x-p==(x-i)+(i-p)
reserve=[r for r in s if r['group']=='RESERVE_FOR_PREVIOUS8']
ip=sum(int(r['I_to_P_B']) for r in reserve);xp=sum(int(r['X_to_P_B']) for r in reserve)
assert ip==23390 and xp==324800
levels=read('PER_LEVEL_COSTS.csv')
assert len(levels)==20 and len({(r['scene'],r['level']) for r in levels})==20
for r in levels:
    assert int(r['I_payload_B'])+int(r['I_model_B'])-int(r['P_payload_B'])-int(r['P_model_B'])==int(r['I_to_P_before_common_framing_B'])
print(json.dumps({'status':'PASS','reserve_context_bytes':ip,'reserve_total_bytes':xp,
    'context_share_percent':100*ip/xp,'new_experiment':False},indent=2))
