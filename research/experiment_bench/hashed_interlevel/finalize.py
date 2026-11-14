"""Read-only validation of study artifacts, immutable source snapshots and hashes."""
import argparse
import ast
import json
from pathlib import Path
import re
import shutil
import time
import numpy as np
from research.hashgrid_analysis.hashed_context.core import ROOT,sha
from research.hashgrid_analysis.hashed_context.runtime import write_json,peak_rss_mib

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);a=p.parse_args();run=a.run.resolve()
    assert not (run/'final-validation.json').exists()
    started=time.perf_counter()
    def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
    protected=read(run/'protected-input-hashes.json')
    for name,h in protected.items():assert sha(ROOT/name)==h,name
    freeze=read(run/'MODEL_FREEZE.json')
    for name,h in freeze['frozen_artifacts'].items():assert sha(run/name)==h,name
    for name,h in freeze['source_sha256'].items():assert sha(ROOT/name)==h,name
    for f in ('input-validation.json','unit-tests.json','replay-validation.json','independent-review.json'):
        assert read(run/f)['status']=='PASS',f
    decision=read(run/'decision.json');assert decision['test_evaluations']==1
    scores=read(run/'test-scores.json');paired=read(run/'paired-differences.json');forecast=read(run/'predicted-net.json')
    # Validate stored evaluation products; do not access targets or run test prediction again.
    from .core import strata
    checked=0
    for pair in ('L4_to_L5','L5_to_L6'):
        with np.load(ROOT/'research/hashed_context_diagnostic_20261013_01'/pair/'contexts.npz') as z:
            ctx={k:z[k] for k in ('geometry','point_count')}
        for seed in (0,1,2):
            with np.load(run/pair/f'test_losses_seed{seed}.npz') as z:
                rows=z['slot_index'];masks=strata(ctx,rows)
                for r in scores:
                    if r['pair']!=pair or r['seed']!=seed:continue
                    x=z[r['model']][masks[r['stratum']]]
                    if r['channel']!='both':x=x[:,int(r['channel'])]
                    assert r['symbols']==x.size and (r['CE'] is None if not x.size else abs(float(x.mean())-r['CE'])<1e-14)
                    checked+=1
                for r in paired:
                    if r['pair']!=pair or r['seed']!=seed:continue
                    d=(z[r['baseline']]-z[r['candidate']])[masks[r['stratum']]]
                    d=d.mean(axis=1) if r['channel']=='both' else d[:,int(r['channel'])]
                    assert r['slots']==len(d) and (r['gain_bits_per_symbol'] is None if not len(d) else abs(float(d.mean())-r['gain_bits_per_symbol'])<1e-14)
                    checked+=1
    for r in forecast:
        assert r['label']=='PREDICTED' and r['actual_entropy_stream_bytes'] is None
        assert abs(r['net_saving_bytes']-(r['N_full_symbols']*r['delta_CE_test']/8-r['delta_side_bytes']))<1e-9
        assert r['margin_pass']==(r['gross_payload_saving_bytes']>r['delta_side_bytes']+max(4096,.2*r['delta_side_bytes']))
    report=run/'HELDOUT_REPORT.md';text=report.read_text(encoding='utf-8')
    links=[];width=None;tables=0
    for item in re.findall(r'\]\(([^)]+)\)',text):
        if item.startswith(('https://','http://')):continue
        path=Path(re.sub(r':\d+$','',item.strip('<>')))
        assert path.is_absolute() and path.exists(),item
        links.append(item)
    for line in text.splitlines():
        if line.startswith('|'):
            n=len(re.findall(r'(?<!\\)\|',line))
            if width is None:width=n;tables+=1
            assert n==width,line
        else:width=None
    snapshot=run/'source_snapshot';snapshot.mkdir(exist_ok=False)
    sourcepaths=set((ROOT/'research/experiment_bench/hashed_interlevel').glob('*.py'))
    sourcepaths.update(ROOT/name for name in protected if name.endswith('.py') and '/hashed_context/' in name and '/source_snapshot/' not in name and '/finalize_attempt' not in name)
    sourcepaths.add(ROOT/'research/experiment_bench/models.py')
    sources={}
    for path in sorted(sourcepaths):
        ast.parse(path.read_text(encoding='utf-8'))
        rel=path.relative_to(ROOT);dest=snapshot/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        assert sha(dest)==sha(path)
        sources[rel.as_posix()]=sha(path)
    write_json(run/'source-hashes.json',sources)
    artifact_hashes={p.relative_to(run).as_posix():sha(p) for p in run.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                     and 'matplotlib_config' not in p.parts}
    write_json(run/'final-validation.json',{'status':'PASS','decision':decision['decision'],
        'previous_files_unchanged':len(protected),'frozen_model_artifacts_unchanged':len(freeze['frozen_artifacts']),
        'stored_score_records_independently_checked':checked,'forecast_checks':len(forecast),
        'source_snapshot_files':len(sources),'report_local_links':len(links),'markdown_tables':tables,
        'artifact_hashes':artifact_hashes,'report_sha256':sha(report),'wall_seconds':time.perf_counter()-started,
        'peak_rss_mib':peak_rss_mib(),'test_prediction_repeated':False,'actual_entropy_coding':False})
    print(json.dumps({'status':'PASS','decision':decision['decision'],'protected_files':len(protected),'score_checks':checked,
                      'artifact_files':len(artifact_hashes),'seconds':time.perf_counter()-started}))

if __name__=='__main__':main()
