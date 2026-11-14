import argparse
from pathlib import Path
import numpy as np
from research.hashgrid_analysis.common import ROOT,read,write,digest
from .finish import finish

def compare(first,second):
    a=read(first/'config.json');b=read(second/'config.json')
    assert {k:v for k,v in a.items() if k!='output'}=={k:v for k,v in b.items() if k!='output'}
    checks=[]
    for name in ('results.json','summary.csv','per-split-results.csv','class-occupancy.csv','overhead-sensitivity.csv','model-selection.json','split-validation.json','representative-distributions.json','input-validation.json'):
        assert digest(first/name)==digest(second/name),name
        checks.append({'test':name,'status':'PASS','sha256':digest(first/name)})
    for name in ('splits.npz','fitted_histograms.npz'):
        x=np.load(first/name,allow_pickle=False);y=np.load(second/name,allow_pickle=False)
        assert x.files==y.files
        for key in x.files:np.testing.assert_array_equal(x[key],y[key])
        checks.append({'test':name,'status':'PASS','arrays_compared':len(x.files)})
    figures=read(first/'figure-index.json');assert [r['png'] for r in figures]==[r['png'] for r in read(second/'figure-index.json')]
    for r in figures:
        assert digest(first/r['png'])==digest(second/r['png']) and digest(first/r['svg'])==digest(second/r['svg']),r['png']
        settings=Path(r['png']).with_suffix('.plot.json');assert read(first/settings)['axes']==read(second/settings)['axes']
        checks.append({'test':r['png'],'status':'PASS','PNG_SVG_bitwise_equal':True,'numeric_artist_values_equal':True})
    result={'status':'PASS','same_config_except_output':True,'numeric_and_plotted_data_exact':True,'checks':checks}
    for out in (first,second):
        write(out/'reproducibility.json',result);v=read(out/'validation.json');v['reproducibility']='PASS';write(out/'validation.json',v)
        (out/'reproducibility.log').write_text('\n'.join('PASS '+r['test'] for r in checks)+'\n',encoding='utf-8')
        finish(out,replot=False)
    print('Full independent CPU repeat PASS:',len(checks),'comparisons')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('first');p.add_argument('second');args=p.parse_args();compare((ROOT/args.first).resolve(),(ROOT/args.second).resolve())
