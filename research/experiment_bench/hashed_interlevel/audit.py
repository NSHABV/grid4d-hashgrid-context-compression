"""Independent stored-model/forecast audit; no target loading or test prediction."""
import argparse
import json
from pathlib import Path
import numpy as np
from .dry_model import deserialize,section_sizes
from research.hashgrid_analysis.hashed_context.runtime import write_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);run=p.parse_args().run.resolve()
    target=run/'independent-review.json'
    if target.exists():raise FileExistsError('Preserve completed independent review')
    def read(name):return json.loads((run/name).read_text(encoding='utf-8'))
    sizes=read('model-sizes.json');scores=read('test-scores.json');pred=read('predicted-net.json')
    for rec in sizes:
        d=run/rec['pair']/f'seed{rec["seed"]}_{rec["model"]}'
        data=(d/f'{rec["storage"]}.model').read_bytes()
        assert len(data)==rec['total']
        assert all(rec[k]==v for k,v in section_sizes(data).items())
        masses,thresholds,spec,metadata=deserialize(data)
        with np.load(d/'fitted.npz') as z:assert np.array_equal(z['masses'],masses)
        context=json.loads((d/'spec.json').read_text(encoding='utf-8'))
        assert spec['name']==context['name'] and spec['C']==context['C']
        for k,v in context['edges'].items():
            a=np.asarray(v,np.float64);assert a.shape==thresholds[k].shape and a.tobytes()==thresholds[k].tobytes()
    for r in pred:
        selected=[]
        for name in (r['candidate'],r['baseline']):
            records=[s for s in sizes if s['pair']==r['pair'] and s['seed']==r['seed'] and s['model']==name]
            selected.append(min(x['total'] for x in records))
        a,b=selected
        def ce(name):return next(s['CE'] for s in scores if s['pair']==r['pair'] and s['seed']==r['seed'] and s['model']==name and s['stratum']=='all' and s['channel']=='both')
        gain=ce(r['baseline'])-ce(r['candidate'])
        assert abs(gain-r['delta_CE_test'])<1e-13 and r['N_full_symbols']==1048576
        assert r['candidate_side_bytes']==a and r['baseline_side_bytes']==b and r['delta_side_bytes']==a-b
        assert abs(r['net_saving_bytes']-(1048576*gain/8-(a-b)))<1e-7
        assert r['margin_pass']==(r['gross_payload_saving_bytes']>a-b+max(4096,.2*(a-b)))
        assert r['label']=='PREDICTED' and r['actual_entropy_stream_bytes'] is None
    paired=read('paired-differences.json')
    failures=[r for r in paired if r['candidate']=='Mean4Std2' and r['channel'] in ('0','1')
        and ((r['baseline'] in ('Geometry4','Canonical8','Mean8') and r['stratum'] in ('all','G3'))
             or (r['baseline']=='Mean4' and r['stratum']=='G3')) and r['gain_bits_per_symbol']<=0]
    costs=[r for r in pred if r['candidate']=='Mean4Std2' and r['baseline'] in ('Geometry4','Canonical8','Mean8') and not r['margin_pass']]
    decision='NO-GO' if failures or costs else 'GO'
    assert decision==read('decision.json')['decision']
    write_json(target,{'status':'PASS','scope':'stored transport and already evaluated scores only, no targets',
        'dry_model_files':len(sizes),'forecast_checks':len(pred),'decision':decision,
        'nonpositive_gain_checks':len(failures),'cost_failures':len(costs),'test_prediction_repeated':False})
    print({'status':'PASS','decision':decision})

if __name__=='__main__':main()
