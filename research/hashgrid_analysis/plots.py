"""Static scientific figures with source data, artist values, and plotting settings."""
import hashlib
import os
from pathlib import Path
import numpy as np
from PIL import Image
from .common import read,write,resolve,digest

def clean(value):
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if isinstance(value,np.ndarray):return clean(value.tolist())
    if isinstance(value,np.generic):return clean(value.item())
    if isinstance(value,float) and not np.isfinite(value):return None
    return value

class Writer:
    def __init__(self,out):
        self.out=out;self.config=read(out/'config.json');self.sha=read(out/'manifest.json')['checkpoint_sha256'];self.records=[]

    def save(self,fig,name,title,source,kind='measured',limitations='',measurements=None):
        import matplotlib
        path=self.out/name;path.parent.mkdir(parents=True,exist_ok=True)
        fig.suptitle(title,fontsize=13)
        fig.tight_layout(rect=(0,0,1,.94))
        fig.savefig(path.with_suffix('.png'),dpi=150)
        fig.savefig(path.with_suffix('.svg'),metadata={'Date':None})
        axes=[]
        for ax in fig.axes:
            record={'xlabel':ax.get_xlabel(),'ylabel':ax.get_ylabel(),'title':ax.get_title(),
                'xscale':ax.get_xscale(),'yscale':ax.get_yscale(),'xlim':ax.get_xlim(),'ylim':ax.get_ylim(),
                'lines':[{'x':line.get_xdata(),'y':line.get_ydata(),'label':line.get_label()} for line in ax.lines],
                'bars':[{'x':p.get_x(),'width':p.get_width(),'height':p.get_height(),'y':p.get_y()} for p in ax.patches if hasattr(p,'get_height')],
                'images':[],'collections':[]}
            for im in ax.images:
                a=np.ma.asarray(im.get_array());filled=np.ma.filled(a,0)
                record['images'].append({'shape':list(a.shape),'clim':im.get_clim(),'norm_class':type(im.norm).__name__,
                    'norm_center':getattr(im.norm,'vcenter',None),'norm_gamma':getattr(im.norm,'gamma',None),
                    'extent':im.get_extent(),
                    'array_sha256':hashlib.sha256(filled.tobytes()).hexdigest(),
                    'mask':np.ma.getmaskarray(a) if a.size<=70000 else None,
                    'values':filled if a.size<=70000 else None,'large_array':'numeric NPZ or source PNG; no huge redundant JSON' if a.size>70000 else None})
            for col in ax.collections:
                values=col.get_array();offsets=np.asarray(col.get_offsets())
                record['collections'].append({'offsets':offsets if offsets.size<=100000 else None,
                    'values':np.ma.filled(values,0) if values is not None and values.size<=70000 else None,'clim':col.get_clim()})
            axes.append(record)
        sourcepath=self.out/source
        metadata={'title':title,'png':path.with_suffix('.png').relative_to(self.out).as_posix(),
            'svg':path.with_suffix('.svg').relative_to(self.out).as_posix(),'source':source,'source_sha256':digest(sourcepath),
            'checkpoint_sha256':self.sha,'data_type':kind,'measurements':measurements if measurements is not None else {
                'plot_numeric_values':sum(sum(len(line['x'])+len(line['y']) for line in a['lines'])+len(a['bars'])+sum(int(np.prod(im['shape'])) for im in a['images']) for a in axes),
                'independent_observations':'see per-series n/counts/rows in source; plotted values are not independent samples'},'limitations':limitations,
            'matplotlib':matplotlib.__version__,'figsize_inches':fig.get_size_inches().tolist(),'dpi':150,
            'config':self.config,'axes':clean(axes),'masked_cells':'zeros or undefined correlations are explicitly masked in heatmaps'}
        write(path.with_suffix('.plot.json'),metadata)
        self.records.append({k:metadata[k] for k in ('title','png','svg','source','source_sha256','checkpoint_sha256','data_type','measurements','limitations')})
        import matplotlib.pyplot as plt
        plt.close(fig)

def heat(ax,counts,title,xlabel,ylabel,conditional=False):
    from matplotlib.colors import LogNorm
    c=np.array(counts,dtype=np.float64)
    if conditional:c=np.divide(c,c.sum(axis=1,keepdims=True),out=np.zeros_like(c),where=c.sum(axis=1,keepdims=True)>0)
    else:c=c/c.sum() if c.sum() else c
    positive=c[c>0]
    if positive.size:
        image=ax.imshow(np.ma.masked_equal(c,0),origin='lower',aspect='auto',norm=LogNorm(vmin=max(positive.min(),1e-12),vmax=max(c.max(),positive.min()*1.01)))
        ax.figure.colorbar(image,ax=ax,label='Conditional probability' if conditional else 'Probability')
    ax.set(title=title,xlabel=xlabel,ylabel=ylabel)

def memory(w):
    import matplotlib.pyplot as plt
    d=read(w.out/'memory/data.json');grids=d['grids']
    fig,ax=plt.subplots(figsize=(8,5));ax.bar([r['grid'] for r in grids],[r['MiB'] for r in grids])
    for i,r in enumerate(grids):ax.text(i,r['MiB'],f'{r["percent_total"]:.2f}%',ha='center',va='bottom')
    ax.set(xlabel='Grid',ylabel='Raw float32 MiB');ax.margins(y=.15)
    w.save(fig,'memory/by-grid','HashGrid memory by grid','memory/data.json',measurements=sum(r['scalars'] for r in grids))
    fig,ax=plt.subplots(figsize=(9,5))
    for g in w.config['grids']:
        rows=[r for r in d['levels'] if r['grid']==g]
        ax.plot([r['level']+1 for r in rows],[r['cumulative_percent_grid'] for r in rows],label=g)
        f,a=plt.subplots(2,1,figsize=(9,7),sharex=True)
        a[0].bar([r['level'] for r in rows],[r['MiB'] for r in rows]);a[0].set(ylabel='Raw float32 MiB')
        a[1].bar([r['level'] for r in rows],[r['rows'] for r in rows]);a[1].set(xlabel='Level',ylabel='Hash-table rows')
        w.save(f,f'memory/{g}-levels',f'{g}: memory and table rows per level','memory/data.json',measurements=len(rows))
    ax.set(xlabel='Number of included initial levels (N)',ylabel='Cumulative grid memory (%)');ax.legend();ax.grid(alpha=.2)
    w.save(fig,'memory/cumulative','Cumulative memory (each grid normalized separately)','memory/data.json')

def distributions(w):
    import matplotlib.pyplot as plt
    d=read(w.out/'distributions/raw.json');edges=np.array(d['edges']);centers=(edges[:-1]+edges[1:])/2
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for ax,(g,record) in zip(axes.flat,d['grids'].items()):
        pooled=record['table']['pooled'];counts=np.array(pooled['counts'])
        ax.stairs(counts/(pooled['n']*np.diff(edges)),edges);ax.set_yscale('log')
        ax.set(title=f'{g}: mean={pooled["mean"]:.4g}, std={pooled["std"]:.4g}',xlabel='Float32 feature',ylabel='Density (log scale)')
    w.save(fig,'distributions/raw-pooled','Raw float32 marginal densities; common full-range bins','distributions/raw.json',limitations='Marginal similarity does not establish dependence')
    for g,record in d['grids'].items():
        fig,ax=plt.subplots(figsize=(9,5))
        for ch in range(2):
            s=record['table'][f'channel{ch}'];ax.stairs(np.array(s['counts'])/s['n'],edges,label=f'channel {ch}')
        ax.set(xlabel='Float32 feature',ylabel='Bin probability (full range)',yscale='log');ax.legend()
        w.save(fig,f'distributions/{g}-channels',f'{g}: channel distributions','distributions/raw.json')
        levels=sorted({r['level'] for r in record['levels']});rows=(len(levels)+3)//4
        fig,axes=plt.subplots(rows,4,figsize=(15,rows*2.8),squeeze=False)
        for ax,l in zip(axes.flat,levels):
            for ch in range(2):
                r=next(r for r in record['levels'] if r['level']==l and r['channel']==ch)
                ax.stairs(np.array(r['counts'])/r['n'],edges,label=f'ch{ch}')
            ax.set(title=f'Level {l}',xlabel='Float32 feature',ylabel='Bin probability',yscale='log');ax.legend(fontsize=7)
        for ax in axes.flat[len(levels):]:ax.axis('off')
        w.save(fig,f'distributions/{g}-level-histograms',f'{g}: all selected levels, same bins/range','distributions/raw.json',measurements=len(levels))
        fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True)
        for ch,ax in enumerate(axes):
            box=[{**r['box'],'label':str(r['level'])} for r in record['levels'] if r['channel']==ch]
            ax.bxp(box,showfliers=False);ax.set(ylabel=f'Channel {ch} feature')
        axes[-1].set_xlabel('Level; whiskers are exact min/max, boxes Q1/median/Q3')
        w.save(fig,f'distributions/{g}-boxplots',f'{g}: exact per-level quantiles (full sample)','distributions/raw.json')
    q=read(w.out/'distributions/quantized.json')
    for g in w.config['grids']:
        for bits in (8,12,16):
            names=[f'{s}-{bits}' for s in ('table','level') if f'{s}-{bits}' in q]
            if not names:continue
            fig,axes=plt.subplots(len(names),2,figsize=(12,4*len(names)),squeeze=False)
            for row,name in enumerate(names):
                rec=q[name]['grids'][g];edges=np.array(q[name]['edges']);counts=np.array(rec['rebinned_counts']);n=counts.sum()
                axes[row,0].stairs(counts/n,edges);axes[row,0].set(title=name,xlabel='Stored integer symbol (256 display bins)',ylabel='Bin probability',yscale='log')
                level_counts=np.array([r['counts'] for r in rec['levels']]);prob=level_counts/level_counts.sum(axis=1,keepdims=True)
                heat(axes[row,1],prob,f'{name}: normalized per-level counts','Symbol display bin','Selected level',conditional=True)
                axes[row,1].set_yticks(np.arange(len(rec['levels'])),[r['level'] for r in rec['levels']])
            w.save(fig,f'distributions/{g}-quantized-{bits}',f'{g}: table/level {bits}-bit stored symbols','distributions/quantized.json',
                limitations='Level-wise equal codes can represent different float32 values; exact unbinned counts stored in JSON')

def entropy(w):
    import matplotlib.pyplot as plt
    d=read(w.out/'entropy/data.json');levels=d['levels'];names=sorted({r['variant'] for r in levels})
    for g in w.config['grids']:
        fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=True)
        for name in names:
            rows=[r for r in levels if r['grid']==g and r['variant']==name]
            axes[0].plot([r['level'] for r in rows],[r['entropy_bits_per_symbol'] for r in rows],label=name,linestyle='-' if name.startswith('table') else '--')
            axes[1].plot([r['level'] for r in rows],[r['theoretical_bytes']/2**20 for r in rows],label=name)
        axes[0].set(ylabel='Empirical H (bits / symbol)');axes[1].set(xlabel='Level',ylabel='N * H / 8 (theoretical MiB)')
        axes[0].legend(ncol=3);axes[0].grid(alpha=.2);axes[1].grid(alpha=.2)
        w.save(fig,f'entropy/{g}-levels',f'{g}: entropy and absolute level cost','entropy/data.json',kind='full-array empirical/theoretical',limitations='Not an actual entropy stream; pooled feature channels')
    rows=sorted([r for r in levels if r['variant']=='table-8'],key=lambda r:-r['theoretical_bits'])[:20]
    if rows:
        fig,ax=plt.subplots(figsize=(11,7));ax.barh([f'{r["grid"]} L{r["level"]}' for r in rows][::-1],[r['theoretical_bytes']/2**20 for r in rows][::-1])
        ax.set(xlabel='N * H / 8 (theoretical MiB)',ylabel='Level priority')
        w.save(fig,'entropy/priority-table8','Largest marginal entropy costs; table-wise 8-bit','entropy/data.json',kind='theoretical',limitations='A high absolute cost does not demonstrate predictable context')
    fig,ax=plt.subplots(figsize=(11,5));variants=d['variants'];x=np.arange(len(variants))
    ax.bar(x-.2,[r['ideal_fixed_bits']/8/2**20 for r in variants],.4,label='Ideal fixed width (calculated)')
    ax.bar(x+.2,[r['real_serialized_bytes']/2**20 for r in variants],.4,label='Actual serialized directory')
    ax.set_xticks(x,[r['variant'] for r in variants]);ax.set_ylabel('MiB');ax.legend()
    w.save(fig,'entropy/fixed-vs-serialized','Container size vs ideal fixed-width cost','entropy/data.json',limitations='12-bit actual containers are uint16; no 12/16 entropy streams')

def channels(w):
    import matplotlib.pyplot as plt
    d=read(w.out/'channel_dependencies/data.json')
    for g,r in d.items():
        sample=np.array(r['scatter_values'])
        fig,axes=plt.subplots(1,2,figsize=(12,5))
        axes[0].scatter(sample[:,0],sample[:,1],s=2,alpha=.3);axes[0].set(xlabel='Float32 channel 0',ylabel='Float32 channel 1',title=f'Sampled scatter, n={len(sample)}')
        axes[1].hexbin(sample[:,0],sample[:,1],gridsize=55,bins='log',mincnt=1);axes[1].set(xlabel='Float32 channel 0',ylabel='Float32 channel 1',title='Sampled 2D hexbin density (log)')
        w.save(fig,f'channel_dependencies/{g}-scatter',f'{g}: raw feature channels','channel_dependencies/data.json',kind='deterministic sampled raw pairs',measurements=len(sample))
        fig,axes=plt.subplots(1,2,figsize=(12,5))
        for ax,field,edge_field,label in [(axes[0],'raw_joint_counts','raw_joint_edges','Full common range'),(axes[1],'raw_zoom_counts','raw_zoom_edges','Common [-0.15,0.15] zoom')]:
            if field not in r:ax.axis('off');continue
            heat(ax,r[field],label,'Float32 channel 1','Float32 channel 0')
            edges=r[edge_field]
            if ax.images:ax.images[0].set_extent([edges[0],edges[-1],edges[0],edges[-1]])
        w.save(fig,f'channel_dependencies/{g}-raw-joint',f'{g}: full-array raw 2D histogram','channel_dependencies/data.json',measurements=r['metrics']['rows'],
            limitations=f'Zoom includes {r.get("raw_zoom_included_rows","not computed")} rows; zoom probability normalized on included pairs; tails shown in full-range panel')
        fig,axes=plt.subplots(1,2,figsize=(13,5))
        heat(axes[0],r['joint_counts'],'Full joint distribution','q1','q0')
        heat(axes[1],r['conditional_counts'],'Full conditional distribution','q1','q0 >> 4 class',conditional=True)
        w.save(fig,f'channel_dependencies/{g}-probabilities',f'{g}: all table-wise 8-bit rows','channel_dependencies/data.json',measurements=r['metrics']['rows'],limitations='Plug-in MI can be biased, especially for sparse groups')
        fig,axes=plt.subplots(2,2,figsize=(12,8))
        axes[0,0].bar(range(16),r['class_rows']);axes[0,0].set(xlabel='Context class',ylabel='Rows')
        axes[0,1].bar(range(16),r['class_entropy']);axes[0,1].set(xlabel='Context class',ylabel='H(q1 | class) bits/symbol')
        axes[1,0].bar(range(16),r['prediction_mse']);axes[1,0].set(xlabel='Context class',ylabel='In-sample mean predictor MSE (code units squared)')
        heat(axes[1,1],r['prediction_error_counts'],'Error mass by class','Residual bin: q1 - class mean','Context class',conditional=True)
        w.save(fig,f'channel_dependencies/{g}-classes',f'{g}: context occupancy, entropy and diagnostic prediction','channel_dependencies/data.json',limitations='Empty classes have zero plotted entropy/mass; predictor is in-sample and is not an implemented codec')
    fig,axes=plt.subplots(1,2,figsize=(12,5));gs=list(d);x=np.arange(len(gs))
    axes[0].bar(x-.18,[d[g]['metrics']['pearson_full'] for g in gs],.36,label='Pearson')
    axes[0].bar(x+.18,[d[g]['metrics']['spearman_full'] for g in gs],.36,label='Spearman');axes[0].set_xticks(x,gs);axes[0].set_ylabel('Full-row correlation');axes[0].legend()
    axes[1].bar(x-.18,[d[g]['metrics']['mutual_information_full_q0_q1'] for g in gs],.36,label='I(q0;q1)')
    axes[1].bar(x+.18,[d[g]['metrics']['mutual_information_16class_q1'] for g in gs],.36,label='I(q0_class;q1)');axes[1].set_xticks(x,gs);axes[1].set_ylabel('Empirical mutual information (bits / row)');axes[1].legend()
    w.save(fig,'channel_dependencies/summary','Linear, rank and discrete statistical dependence','channel_dependencies/data.json',limitations='No linear correlation does not exclude nonlinear dependence')

def interlevel(w):
    import matplotlib.pyplot as plt
    d=read(w.out/'interlevel/data.json');rows=d['rows'];methods=sorted({r['method'] for r in rows})
    for g in w.config['grids']:
        fig,axes=plt.subplots(2,3,figsize=(16,9))
        metrics=('pearson','mutual_information','conditional_entropy','heldout_cross_entropy','heldout_prediction_mse','spearman')
        for ax,metric in zip(axes.flat,metrics):
            for method in methods:
                for ch in range(2):
                    rs=[r for r in rows if r['grid']==g and r['method']==method and r['channel']==ch]
                    ax.plot([r['fine_level'] for r in rs],[r[metric] for r in rs],label=f'{"interp" if "interpolation" in method else "nearest"} ch{ch}',linestyle='-' if ch==0 else '--')
            units='bits / sampled vertex' if metric in ('mutual_information','conditional_entropy','heldout_cross_entropy') else 'float32 feature squared' if metric=='heldout_prediction_mse' else 'Correlation'
            ax.set(title=metric,xlabel='Fine level (coarse = fine - 1)',ylabel=units);ax.grid(alpha=.2)
        axes[0,0].legend(fontsize=8)
        w.save(fig,f'interlevel/{g}-summary',f'{g}: vertex-domain exploratory correspondences','interlevel/data.json',kind='sampled diagnostic',limitations='Duplicated target hash slots; not table-uniform or a rate claim; deterministic 80/20 holdout')
        candidates=[r for r in rows if r['grid']==g];fine=max(r['fine_level'] for r in candidates)
        for method in methods:
            for ch in range(2):
                name=f'{g}-l{fine}-{method}-ch{ch}';r=d['examples'][name]
                if r['scatter'] is None:continue
                sample=np.array(r['scatter']);fig,axes=plt.subplots(2,2,figsize=(12,9))
                axes[0,0].scatter(sample[:,0],sample[:,1],s=2,alpha=.3);axes[0,0].set(xlabel='Coarse context feature',ylabel='Fine slot feature',title='Scatter')
                hb=axes[0,1].hexbin(sample[:,0],sample[:,1],gridsize=45,mincnt=1,bins='log');fig.colorbar(hb,ax=axes[0,1],label='Sampled pairs (log)');axes[0,1].set(xlabel='Coarse context feature',ylabel='Fine slot feature',title='2D hexbin density')
                heat(axes[1,0],r['joint_counts'],'Diagnostic joint distribution','Fine stored 8-bit q','Coarse 16-bin class')
                heat(axes[1,1],r['joint_counts'],'Diagnostic conditional distribution','Fine stored 8-bit q','Coarse 16-bin class',conditional=True)
                w.save(fig,f'interlevel/{g}-{method}-ch{ch}',f'{g} L{fine-1} -> L{fine}, {method}, channel {ch}','interlevel/data.json',kind='sampled vertex-domain diagnostic',measurements=len(sample),limitations='Sample coordinates are public; a canonical context for each fine table slot remains a research decision')

def collisions(w):
    import matplotlib.pyplot as plt
    d=read(w.out/'collisions/data.json');fig,fraction_axes=plt.subplots(3,1,figsize=(12,11),sharex=True)
    for g,rs in d['grids'].items():
        rows=[r['summary'] for r in rs]
        fraction_axes[0].plot([r['level'] for r in rows],[r['colliding_fraction_all_slots'] for r in rows],label=g)
        fraction_axes[1].plot([r['level'] for r in rows],[r['query_colliding_fraction_all_slots'] for r in rows],label=g)
        fraction_axes[2].plot([r['level'] for r in rows],[r['nominal_vertices_per_slot'] for r in rows],label=g)
        nrows=(len(rs)+3)//4
        f,a=plt.subplots(nrows,4,figsize=(15,nrows*2.7),squeeze=False)
        for ax,r in zip(a.flat,rs):
            for field,label in [('nominal_multiplicity_counts','nominal vertices'),('query_multiplicity_counts','query corners')]:
                c=np.array(r[field]);ids=np.flatnonzero(c);ax.plot(ids,c[ids],marker='.',label=label)
            s=r['summary'];ax.set(title=f'L{s["level"]}: {"exact" if s["mode"].startswith("exact") else "sample lower bound"}',xlabel='Distinct vertices per slot (d)',ylabel='Slots',yscale='log');ax.legend(fontsize=6)
        for ax in a.flat[len(rs):]:ax.axis('off')
        w.save(f,f'collisions/{g}-multiplicities',f'{g}: collision multiplicity, including d=0 slots','collisions/data.json',limitations='Query counts deduplicate vertices; sampled nominal counts are lower bounds, not estimates of full collision fraction')
        f,axes=plt.subplots(1,3,figsize=(16,5))
        for r in rs:
            if not r['summary']['hashed_lookup']:continue
            groups=r['feature_groups']
            for ax,field,label in zip(axes,('mean_abs_feature','channel_predictor_mse_code_squared','channel_context_finite_bits_per_scalar'),
                ('Mean absolute raw feature','In-sample channel prediction MSE (code squared)','Channel context finite model bits/scalar')):
                ax.plot([s['multiplicity'] for s in groups],[s[field] for s in groups],marker='.',label=f'L{r["summary"]["level"]}');ax.set(xlabel='Observed distinct vertices per slot',ylabel=label)
        axes[0].legend(fontsize=7,ncol=3)
        w.save(f,f'collisions/{g}-feature-magnitude',f'{g}: multiplicity vs magnitude and valid channel diagnostics','collisions/data.json',kind='exact or sampled-domain grouped statistics',limitations='Channel q0->q1 is valid slot context; these are in-sample/finite costs, not inter-level predictions or actual per-slot bits')
    fraction_axes[0].set(ylabel='Nominal sampled/full slots with d>1 / all slots');fraction_axes[1].set(ylabel='Query slots with d>1 / all slots')
    fraction_axes[2].set(xlabel='Level',ylabel='Nominal vertices / rows (exact calculated full-domain mean d)',yscale='log')
    fraction_axes[0].legend();fraction_axes[1].legend();fraction_axes[2].legend()
    w.save(fig,'collisions/fractions','Observed colliding slot fractions; exact small levels and sampled large levels','collisions/data.json',limitations='These are diagnostic uniform queries, not recorded training queries')

def gain_heatmap(w,rows,field,name,title,source,levels=False):
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm
    grids=w.config['grids'];width=32 if levels else 1;matrix=np.full((len(grids),width),np.nan)
    for r in rows:
        if r['grid'] in grids:matrix[grids.index(r['grid']),r['level'] if levels else 0]=r[field]
    limit=max(float(np.nanmax(np.abs(matrix))),1e-8)
    fig,ax=plt.subplots(figsize=(12 if levels else 7,4));im=ax.imshow(np.ma.masked_invalid(matrix),aspect='auto',cmap='RdBu',norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit))
    ax.set_yticks(range(len(grids)),grids);ax.set(xlabel='Level' if levels else 'Full grid (global JSON not allocated)',ylabel='Grid')
    if not levels:ax.set_xticks([0],['baseline minus context'])
    fig.colorbar(im,ax=ax,label=field);w.save(fig,name,title,source,kind='diagnostic' if levels else 'actual measured grid sections',limitations='Positive saves bits; negative increases bits; missing levels masked. Global header charged separately.')

def context_gains(w):
    rows=read(w.out/'context_gains/grids.json')
    for model in sorted({r.get('model','channel_context') for r in rows}):
        selected=[r for r in rows if r.get('model','channel_context')==model]
        gain_heatmap(w,selected,'payload_plus_model_gain_bits',f'context_gains/{model}-actual-grids',f'Actual IID - {model} payload+model bits by grid','context_gains/grids.json')
        gain_heatmap(w,selected,'gain_payload_bits_per_scalar',f'context_gains/{model}-payload-rate',f'{model}: actual payload gain per original scalar','context_gains/grids.json')
    if (w.out/'context_gains/levels.json').exists():
        levels=read(w.out/'context_gains/levels.json')
        gain_heatmap(w,levels,'gain_bits_per_original_scalar','context_gains/diagnostic-levels','Finite transmitted-model diagnostic codelength gain per level','context_gains/levels.json',levels=True)

def rate_distortion(w):
    import matplotlib.pyplot as plt
    rows=read(w.out/'rate_distortion/data.json')
    for metric in ('PSNR','SSIM','LPIPS','MS-SSIM'):
        fig,ax=plt.subplots(figsize=(12,6))
        for r in rows:
            marker='o' if r['size_type']=='actual bitstream' else '^' if r['scope']=='level' else 's'
            ax.scatter(r['MiB'],r[metric],marker=marker,s=60,label=f'{r["variant"]} [{r["size_type"]}]')
        ax.set(xlabel='Actual HashGrid representation MiB (all recorded overhead)',ylabel=metric+' (dB)' if metric=='PSNR' else metric);ax.grid(alpha=.2)
        ax.legend(fontsize=8,loc='center left',bbox_to_anchor=(1, .5))
        w.save(fig,f'rate_distortion/{metric.lower()}',f'Measured rate-distortion: {metric}, trained 50000','rate_distortion/data.json',limitations='Points are not joined; 12-bit raw containers are uint16. Gaussians/MLP excluded.')
    original=next(r for r in rows if r['variant']=='float32')['PSNR']
    fig,ax=plt.subplots(figsize=(12,5));ax.bar([r['variant'] for r in rows],[original-r['PSNR'] for r in rows]);ax.tick_params(axis='x',rotation=35);ax.set(ylabel='Original PSNR - variant PSNR (dB)',xlabel='Measured variant')
    w.save(fig,'rate_distortion/psnr-loss','PSNR loss relative to original float32','rate_distortion/data.json')
    rs=[r for r in rows if r['variant'] in ('table-8','level-8')];fig,axes=plt.subplots(1,2,figsize=(10,5))
    axes[0].bar([r['variant'] for r in rs],[r['MiB'] for r in rs]);axes[0].set_ylabel('Actual serialized MiB')
    axes[1].bar([r['variant'] for r in rs],[r['PSNR'] for r in rs]);axes[1].set_ylabel('PSNR dB')
    w.save(fig,'rate_distortion/eight-bit-scope','Table vs level 8-bit: similar container size, different distortion','rate_distortion/data.json')

def bitstream(w):
    import matplotlib.pyplot as plt
    data=read(w.out/'bitstream/data.json');names=['fixed8','iid','channel_context']
    fields=['coded_payload_bytes','model_overhead_bytes','total_json_bytes','prefix_bytes','integrity_bytes']
    labels=['Symbols payload','Probability model','Combined quantization/buffers/other JSON','Prefix framing','Integrity SHA256']
    for relative in (False,True):
        fig,ax=plt.subplots(figsize=(12,6));bottom=np.zeros(3)
        for field,label in zip(fields,labels):
            y=np.array([data[n][field] for n in names],np.float64)
            y=y/np.array([data[n]['actual_bitstream_bytes'] for n in names])*100 if relative else y/2**20
            ax.bar(names,y,bottom=bottom,label=label);bottom+=y
        ax.set_ylabel('Percent of actual bitstream' if relative else 'Actual bitstream MiB');ax.legend(fontsize=8,loc='center left',bbox_to_anchor=(1,.5))
        w.save(fig,f'bitstream/{"relative" if relative else "absolute"}','Actual bitstream sections (exact byte accounting)','bitstream/data.json',limitations='Quantization, buffers and other metadata share JSON; semantic bytes not invented')
    iid=data['iid'];ctx=data['channel_context'];delta=[iid['actual_bitstream_bytes'],ctx['coded_payload_bytes']-iid['coded_payload_bytes'],ctx['model_overhead_bytes']-iid['model_overhead_bytes'],ctx['total_json_bytes']-iid['total_json_bytes'],ctx['actual_bitstream_bytes']]
    fig,ax=plt.subplots(figsize=(11,6));current=0
    for i,value in enumerate(delta):
        if i in (0,4):bottom=0;height=value
        else:bottom=min(current,current+value);height=abs(value)
        ax.bar(i,height,bottom=bottom,color='#287ca5' if i in (0,4) else '#269b63' if value<0 else '#c44545')
        if i==0:current=value
        elif i<4:current+=value
        ax.text(i,bottom+height,f'{value:+,} B' if i not in (0,4) else f'{value:,} B',ha='center',va='bottom',fontsize=9)
    ax.set_xticks(range(5),['IID total','Payload change','Model change','JSON change','Context total']);ax.set_ylabel('Bytes');ax.margins(y=.15)
    w.save(fig,'bitstream/waterfall','IID -> channel context: payload saving vs overhead','bitstream/data.json')
    fig,ax=plt.subplots(figsize=(9,5));values=[iid['coded_payload_bytes']-ctx['coded_payload_bytes'],ctx['model_overhead_bytes']-iid['model_overhead_bytes'],ctx['actual_bitstream_bytes']-iid['actual_bitstream_bytes']]
    ax.bar(['Payload saved','Extra model','Total file increase'],values,color=['#269b63','#c44545','#c44545']);ax.set_ylabel('Measured bytes')
    w.save(fig,'bitstream/payload-vs-overhead','Smaller payload does not imply a smaller total file','bitstream/data.json')

def rendering(w):
    import matplotlib.pyplot as plt
    from matplotlib.colors import PowerNorm
    d=read(w.out/'rendering/data.json');rows=d['per_frame'];selected=('float32','table-8','level-8','table-12')
    for metric in ('PSNR','SSIM','LPIPS','delta_PSNR','delta_SSIM','delta_LPIPS'):
        fig,ax=plt.subplots(figsize=(11,5))
        for name in selected:
            rs=[r for r in rows if r['variant']==name];ax.plot([r['timestamp'] for r in rs],[r[metric] for r in rs],marker='.',label=name)
        ax.set(xlabel='D-NeRF test timestamp',ylabel=metric+' (dB)' if 'PSNR' in metric else metric);ax.legend();ax.grid(alpha=.2)
        w.save(fig,f'rendering/{metric.lower()}-time',f'Per-frame {metric}: same cameras and timestamps','rendering/data.json',measurements=20)
    byname={e['id'].replace('reference-',''):e for e in d['experiments']}
    frames=list(dict.fromkeys(['00000.png']+[r['frame'] for r in d['worst_frames']]))
    w.out.joinpath('rendering/numeric-errors').mkdir(exist_ok=True)
    for frame in frames:
        arrays={}
        original=Path(byname['float32']['folder']);original=resolve(original) if not original.is_absolute() else original
        # WSL paths in saved records are mapped explicitly to this Windows workspace.
        def local(folder):
            s=str(folder)
            if s.startswith('/mnt/'):s=s[5].upper()+':'+s[6:]
            return Path(s)
        gt=np.asarray(Image.open(local(byname['float32']['folder'])/'model/test/ours_50000/gt'/frame).convert('RGB'),dtype=np.float32)/255
        arrays['GT']=gt
        for name in ('float32','table-8','level-8','table-12'):
            arrays[name]=np.asarray(Image.open(local(byname[name]['folder'])/'renders'/frame).convert('RGB'),dtype=np.float32)/255
        fig,axes=plt.subplots(1,5,figsize=(18,4))
        for ax,(name,a) in zip(axes,arrays.items()):ax.imshow(a);ax.set_title(name);ax.axis('off')
        w.save(fig,f'rendering/frame-{frame[:5]}-comparison',f'Test frame {frame}: GT and existing renders','rendering/data.json',limitations='Same bitstream-decoded symbols imply identical IID/context images; no artificial differences')
        errors={}
        for name in ('float32','table-8','level-8'):errors['GT-minus-'+name]=np.abs(gt-arrays[name]).mean(axis=2)
        for name in ('table-8','level-8','table-12'):errors['original-minus-'+name]=np.abs(arrays['float32']-arrays[name]).mean(axis=2)
        numeric=w.out/f'rendering/numeric-errors/{frame[:5]}.npz';np.savez_compressed(numeric,**errors)
        fig,axes=plt.subplots(2,3,figsize=(13,9))
        for ax,(name,a) in zip(axes.flat,errors.items()):
            im=ax.imshow(a,cmap='magma',norm=PowerNorm(gamma=.5,vmin=0,vmax=1));ax.set_title(name);ax.axis('off');fig.colorbar(im,ax=ax,label='Mean absolute RGB error [0,1] (sqrt color scale)')
        w.save(fig,f'rendering/frame-{frame[:5]}-errors',f'Actual PNG RGB differences: frame {frame}','rendering/data.json',limitations='Identical color limits [0,1], gamma=0.5 for all panels; exact error arrays in numeric-errors NPZ')

def generate(out,only=None):
    os.environ['MPLCONFIGDIR']=str(out/'matplotlib-cache')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.titlesize':10,'svg.fonttype':'none','svg.hashsalt':'grid4d-analysis-v1'})
    w=Writer(out)
    blocks=[('memory/data.json',memory),('distributions/raw.json',distributions),('entropy/data.json',entropy),
        ('channel_dependencies/data.json',channels),('interlevel/data.json',interlevel),('collisions/data.json',collisions),
        ('context_gains/grids.json',context_gains),('rate_distortion/data.json',rate_distortion),('bitstream/data.json',bitstream),('rendering/data.json',rendering)]
    scope={'histograms':{'distributions'},'entropy':{'entropy'},'channels':{'channels','context_gains','bitstream'},
        'interlevel':{'interlevel'},'collisions':{'collisions'},'rate-distortion':{'rate_distortion'},'rendering':{'rendering'}}
    for source,fn in blocks:
        if (out/source).exists() and (only is None or fn.__name__ in only) and (w.config['section']=='all' or fn.__name__ in scope.get(w.config['section'],set())):
            print('Plotting',fn.__name__,flush=True);fn(w)
    if only is None and (out/'mapping-validation.json').exists() and w.config['section'] in ('all','interlevel','collisions'):
        status={'status':'BLOCKED BY RESEARCH DESIGN','analyses':['actual inter-level coding gain','collision vs inter-level prediction/codelength'],
            'reason':'Canonical fine-slot representatives, aggregation, coverage/fallback and causal traversal are not selected',
            'available':'Two verified vertex-domain diagnostic correspondences; valid existing q0->q1 channel statistics'}
        write(out/'interlevel/design-status.json',status)
        fig,ax=plt.subplots(figsize=(10,4));ax.axis('off')
        ax.text(.5,.68,status['status'],ha='center',fontsize=16,color='#9a5816')
        ax.text(.5,.38,'Actual inter-level coding gain and collision-conditioned inter-level prediction\nrequire a reproducible context for each fine hash slot.\nCurrent vertex diagnostics are available; no result is fabricated.',ha='center',fontsize=11)
        w.save(fig,'interlevel/design-status','Research design still required','interlevel/design-status.json',kind='BLOCKED BY RESEARCH DESIGN',measurements=0,limitations=status['reason'])
    if only is not None:
        old=read(out/'figure-index.json');new={r['png']:r for r in w.records}
        w.records=[new.pop(r['png'],r) for r in old]+list(new.values())
    write(out/'figure-index.json',w.records)
    print('Saved',len(w.records),'PNG+SVG figures with exact plotting data',flush=True)
