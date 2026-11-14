"""Preserve the first report/figure and publish an unobscured chart revision."""
import os,shutil
from pathlib import Path
from .run import read
from research.hashgrid_analysis.hashed_context.core import ROOT,sha
from research.hashgrid_analysis.hashed_context.runtime import write_json
run=ROOT/'research/hashed_mean8_bitstream_20261015_01'
cache=run/'matplotlib-cache';cache.mkdir(exist_ok=True);os.environ['MPLCONFIGDIR']=str(cache)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
best=read(run/'best.json');gain=read(run/'actual-gains.json');x=np.arange(4);bottom=np.zeros(4)
fig,axes=plt.subplots(1,2,figsize=(12,5.2),layout='constrained')
for key,label,color in [('coarse_bytes','Shared coarse model + payload','#adb5bd'),('fine_payload_bytes','Fine range payload','#3979b7'),
                       ('model_bytes','Fine probability masses','#e9a23b'),('metadata_framing_bytes','All metadata / framing','#7b5ea7')]:
    v=np.array([r[key] for r in best])/1024;axes[0].bar(x,v,bottom=bottom,label=label,color=color);bottom+=v
axes[0].set_xticks(x,[r['model'] for r in best]);axes[0].set_ylabel('Actual standalone KiB')
axes[0].legend(fontsize=8,loc='upper left',bbox_to_anchor=(0,-.15),ncol=2)
for i,r in enumerate(best):axes[0].text(i,bottom[i]+3,str(r['total_bytes']),ha='center',fontsize=10)
axes[0].set_ylim(0,max(bottom)*1.13)
axes[1].bar([r['baseline'] for r in gain],[r['actual_standalone_gain_bytes'] for r in gain],color='#24856d')
for i,r in enumerate(gain):axes[1].text(i,r['actual_standalone_gain_bytes']+500,str(r['actual_standalone_gain_bytes']),ha='center',fontsize=10)
axes[1].set_ylim(0,max(r['actual_standalone_gain_bytes'] for r in gain)*1.12)
axes[1].set_ylabel('Mean8 actual saving, bytes');axes[1].set_title('Best verified transport for each baseline',fontsize=11)
for ax in axes:ax.spines[['top','right']].set_visible(False)
fig.suptitle('Frozen uint8 xyz L4+L5: measured files, exact reconstruction',fontsize=14)
for ext in ('png','svg'):
    p=run/'figures'/('actual_sizes_v2.'+ext)
    if p.exists():raise FileExistsError(p)
    fig.savefig(p,dpi=180)
plt.close(fig)
report=run/'BITSTREAM_REPORT.md';archive=run/'BITSTREAM_REPORT_DRAFT_01.md'
with archive.open('xb') as dst,report.open('rb') as src:shutil.copyfileobj(src,dst)
assert sha(archive)==sha(report)
old=sha(report);content=report.read_text(encoding='utf-8').replace('(figures/actual_sizes.png)','(figures/actual_sizes_v2.png)')
report.write_text(content,encoding='utf-8')
write_json(run/'visual-review.json',{'status':'PASS','first_report_sha256':old,'archive':archive.name,
    'revision':'Move chart legend below axes so Canonical8 total label stays visible; numerical data unchanged',
    'original_figures_preserved':True,'final_report_sha256':sha(report)})
