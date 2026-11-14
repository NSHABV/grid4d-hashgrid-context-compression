"""Windows orchestration using existing Linux compute and Windows plotting environments."""
import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path
from .common import ROOT,defaults,read,write,resolve,digest

SECTIONS=('all','histograms','entropy','channels','interlevel','collisions','rate-distortion','rendering','dashboard')

def configuration(args):
    config=defaults()
    if args.config:config.update(read(args.config))
    for name in ('checkpoint','runtime','study','repo','experiments','output','seed','sampling_budget','collision_budget','enumeration_limit','quantization','grids','levels','section'):
        value=getattr(args,name,None)
        if value is not None:config[name]=value
    return config

def prepare(config):
    out=resolve(config['output']);out.mkdir(parents=True,exist_ok=False)
    write(out/'config.json',config)
    write(out/'manifest.json',{'status':'IN PROGRESS','config':config,'checkpoint_sha256':digest(resolve(config['checkpoint'])),
        'created':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat(),
        'source_code_sha256':{p.name:digest(p) for p in Path(__file__).parent.glob('*') if p.is_file()},
        'plotting_python':sys.version})
    return out

def main():
    p=argparse.ArgumentParser(description='Read-only HashGrid analysis; existing pinned artifacts')
    p.add_argument('command',choices=('run','prepare','finish','replot','test'))
    p.add_argument('--config');p.add_argument('--section',choices=SECTIONS)
    p.add_argument('--replot-section',choices=('memory','distributions','entropy','channels','interlevel','collisions','context_gains','rate_distortion','bitstream','rendering'))
    for name in ('checkpoint','runtime','study','repo','experiments','output'):p.add_argument('--'+name)
    p.add_argument('--quantization',choices=('all','table-8','table-12','table-16','level-8','level-12','level-16'))
    for name in ('seed','sampling-budget','collision-budget','enumeration-limit'):p.add_argument('--'+name,type=int)
    p.add_argument('--grids',nargs='+',choices=('xyz','xyt','yzt','xzt'));p.add_argument('--levels',nargs='+',type=int)
    args=p.parse_args();config=configuration(args)
    if args.command=='test':
        subprocess.run([sys.executable,'-m','unittest','research.hashgrid_analysis.tests','-v'],cwd=ROOT,check=True);return
    out=resolve(config['output'])
    if args.command in ('run','prepare'):
        if config['section']=='dashboard':
            if not out.is_dir():raise ValueError('Dashboard requires previously computed analysis output')
        else:prepare(config)
    if args.command=='prepare':print(out);return
    if args.command=='run' and config['section']!='dashboard':
        if os.name!='nt':raise ValueError('Use the documented WSL compute + Windows finish steps on this split environment')
        linux_config='/mnt/'+out.drive[0].lower()+out.as_posix()[2:]+'/config.json'
        with (out/'compute.log').open('w',encoding='utf-8') as log:
            subprocess.run(['wsl','-d','Ubuntu','--','bash','research/run_hashgrid_analysis_compute.sh',linux_config],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    if args.command in ('run','finish','replot'):
        from .plots import generate
        from .report import finalize
        if config['section']!='dashboard':generate(out,only={args.replot_section} if args.replot_section else None)
        finalize(out)
    print('HashGrid analysis finished:',out)

if __name__=='__main__':main()
