"""Repeat-run verification from real computations and independently regenerated figures."""
import argparse
from pathlib import Path
from .common import read,write,resolve,digest
from .report import finalize

def compare(first,second):
    a=read(first/'config.json');b=read(second/'config.json')
    assert {k:v for k,v in a.items() if k!='output'}=={k:v for k,v in b.items() if k!='output'}
    files=['input-validation.json','mapping-validation.json','memory/data.json','distributions/raw.json','distributions/quantized.json',
        'entropy/data.json','channel_dependencies/data.json','interlevel/data.json','collisions/data.json','context_gains/levels.json',
        'context_gains/grids.json','rate_distortion/data.json','bitstream/data.json','rendering/data.json','rendering/recomputed-metrics.csv','experiment-fairness.json']
    records=[]
    for name in files:
        if not (first/name).exists() and not (second/name).exists():continue
        assert (first/name).exists() and (second/name).exists(),name
        assert digest(first/name)==digest(second/name),('data mismatch',name)
        records.append({'test':'numeric data '+name,'status':'PASS','sha256':digest(first/name)})
    fa=read(first/'figure-index.json');fb=read(second/'figure-index.json')
    assert [r['png'] for r in fa]==[r['png'] for r in fb]
    for r in fa:
        png=r['png'];settings=Path(png).with_suffix('.plot.json')
        assert read(first/settings)['axes']==read(second/settings)['axes'],('artist mismatch',png)
        assert digest(first/png)==digest(second/png),('PNG mismatch',png)
        assert digest(first/r['svg'])==digest(second/r['svg']),('SVG mismatch',r['svg'])
        records.append({'test':'repeated figure '+png,'status':'PASS','png_sha256':digest(first/png),'svg_sha256':digest(first/r['svg'])})
    record={'status':'PASS','first_run':str(first),'repeat_run':str(second),'same_settings_except_output':True,
        'numeric_data_exact':True,'plotted_values_exact':True,'png_svg_exact':True,'details':records}
    for out in (first,second):
        write(out/'reproducibility.json',record)
        (out/'reproducibility.log').write_text('\n'.join('PASS '+r['test'] for r in records)+'\n',encoding='utf-8')
        finalize(out)
    print('Full analysis reproduction PASS:',len(records),'comparisons')

def main():
    p=argparse.ArgumentParser();p.add_argument('first');p.add_argument('second');args=p.parse_args()
    compare(resolve(args.first),resolve(args.second))

if __name__=='__main__':main()
