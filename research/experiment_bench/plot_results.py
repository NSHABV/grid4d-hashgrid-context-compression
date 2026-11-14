"""Scientific figures from measured trained-reference experiments only."""
import json
import os
from pathlib import Path

root=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(root/'matplotlib-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

rows=json.loads((root/'aggregate/results.json').read_text())
primary=[r for r in rows if r['iteration']==50000 and r['model'] in ('float32','fixed8','iid','channel_context')]
if len(primary)!=4:
    raise ValueError('Expected four measured trained-reference models')
order={'float32':0,'fixed8':1,'iid':2,'channel_context':3}
label_offsets={'float32':(-58,8),'fixed8':(8,10),'iid':(-24,-22),'channel_context':(10,10)}
primary.sort(key=lambda r:order[r['model']])
folder=root/'figures'
folder.mkdir(exist_ok=True)
for metric in ('PSNR','SSIM','LPIPS'):
    fig,ax=plt.subplots(figsize=(8,5))
    for r in primary:
        ax.scatter(r['bits_per_symbol'],r[metric],s=65,label=r['model'])
        ax.annotate(r['model'],(r['bits_per_symbol'],r[metric]),xytext=label_offsets[r['model']],textcoords='offset points')
    ax.set_xlabel('Measured total representation bits / HashGrid scalar')
    ax.set_xlim(0,max(r['bits_per_symbol'] for r in primary)*1.1)
    ax.margins(y=.18)
    ax.set_ylabel(metric+' (dB)' if metric=='PSNR' else metric)
    ax.set_title('Trained bouncingballs, 50000 iterations\nSame quantization for fixed8 / IID / channel context')
    ax.grid(alpha=.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(folder/f'bitrate-{metric.lower()}.png',dpi=180)
    plt.close(fig)
fig,ax=plt.subplots(figsize=(8,5))
ax.bar([r['model'] for r in primary],[r['compression_ratio_float32'] for r in primary],color='#287ca5')
ax.set_ylabel('Raw float32 HashGrid bytes / actual total bytes')
ax.set_title('Measured compression ratios; metadata/model included')
ax.grid(axis='y',alpha=.25)
fig.tight_layout();fig.savefig(folder/'compression-ratio.png',dpi=180);plt.close(fig)
coded=[r for r in primary if r['model']!='float32']
fig,ax=plt.subplots(figsize=(8,5))
x=np.arange(len(coded))
ax.bar(x-.18,[r['encode_seconds'] for r in coded],.36,label='Encode (fit+I/O)')
ax.bar(x+.18,[r['decode_seconds'] for r in coded],.36,label='Decode (I/O)')
ax.set_xticks(x,[r['model'] for r in coded])
ax.set_ylabel('Seconds; excludes interpreter startup')
ax.set_title('One measured end-to-end run; CPU range coder')
ax.legend();ax.grid(axis='y',alpha=.25)
fig.tight_layout();fig.savefig(folder/'coding-times.png',dpi=180);plt.close(fig)
print('Saved five measured-result figures')
