"""Immutable environment record, source snapshots and previous-artifact audit."""
import argparse,ast,importlib.metadata,json,platform,re,shutil,sys,time
from pathlib import Path
from . import engine
from .run import ROOT,A,read
from research.hashgrid_analysis.hashed_context.core import sha
from research.hashgrid_analysis.hashed_context.runtime import write_json,peak_rss_mib

def environment(run):
    versions={k:importlib.metadata.version(k) for k in ('numpy','constriction','matplotlib')}
    write_json(run/'environment.json',{'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),
        'versions':versions,'executable':sys.executable,'engine_source_sha256':engine.SOURCE_SHA256,
        'installation':'Existing phase2-plotting-env unchanged; pip --target .tools/hashed-pair-deps --no-deps constriction==0.4.2',
        'Windows_constriction_binary_sha256':{p.name:sha(p) for p in (ROOT/'.tools/hashed-pair-deps').rglob('*.pyd')},
        'GPU_used':False,'canonical_context':'NumPy1.26.4 CPU separate f32 operations, anchored f64 ordered reduction',
        'arbitrary_platform_portability_verified':False})
    with (run/'requirements-research.txt').open('x',encoding='utf-8') as f:
        f.write('# Python 3.12.14, Windows x86_64. matplotlib only needed for reports.\n')
        f.write('\n'.join(k+'=='+v for k,v in versions.items())+'\n')

def finish(run):
    started=time.perf_counter();protected=read(run/'protected-input-hashes.json')
    for name,h in protected.items():assert sha(ROOT/name)==h,name
    a_sources=read(A/'source-hashes.json')
    for name,h in a_sources.items():assert sha(ROOT/name)==h,name
    assert read(run/'corruption_checks_02/corruption-checks.json')['status']=='PASS'
    assert read(run/'post_repair_validation/validation.json')['status']=='PASS'
    assert read(run/'B_INDEPENDENT_REVIEW.json')['status']=='PASS'
    assert read(run/'decode-validation.json')['status']=='PASS'
    for r in read(run/'results.json'):
        p=run/r['path'];assert sha(p)==r['sha256'] and p.stat().st_size==r['total_bytes']
    sources=list(Path(__file__).parent.glob('*.py'))+[Path(__file__).with_name('README.md')]
    sources += [ROOT/name for name in (
        'research/hashgrid_analysis/hashed_context/core.py','research/hashgrid_analysis/hashed_context/runtime.py',
        'research/experiment_bench/hashed_interlevel/core.py','research/experiment_bench/hashed_interlevel/dry_model.py',
        'research/experiment_bench/models.py','research/experiment_bench/entropy.py','research/experiment_bench/__init__.py',
        'research/grid4d/codec.py','research/continuation_AB_20261014_01/review_b.py','AGENTS.md')]
    hashes={};snapshot=run/'source_snapshot';snapshot.mkdir(exist_ok=False)
    for p in sources:
        name=p.relative_to(ROOT);destination=snapshot/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,destination);h=sha(p);assert sha(destination)==h;hashes[name.as_posix()]=h
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'))
    write_json(run/'source-hashes.json',hashes)
    status=ROOT/'research/HASHED_CONTEXT_RESEARCH_STATUS_20261015_01.md'
    assert status.is_file()
    links=[]
    for document in (run/'BITSTREAM_REPORT.md',status):
        content=document.read_text(encoding='utf-8')
        for value in re.findall(r'\]\(([^)]+)\)',content):
            value=value.strip('<>').split('#')[0]
            if not value or value.startswith(('http:','https:')):continue
            p=Path(value)
            if not p.is_absolute():p=document.parent/p
            if p.resolve()==(run/'final-validation.json').resolve():continue
            assert p.exists(),f'{document}: missing {p}'
            links.append(str(p))
    artifacts={p.relative_to(run).as_posix():sha(p) for p in run.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    write_json(run/'final-validation.json',{'status':'PASS','protected_files_unchanged':len(protected),
        'A_live_source_files_unchanged':len(a_sources),'new_source_files_snapshotted':len(sources),
        'streams_unchanged':12,'local_document_links_checked':len(links),'report_sha256':sha(run/'BITSTREAM_REPORT.md'),
        'combined_status_sha256':sha(status),'artifact_hashes':artifacts,'source_sha256':hashes,
        'wall_seconds':time.perf_counter()-started,'peak_rss_mib':peak_rss_mib()})
    print({'status':'PASS','protected':len(protected),'artifacts':len(artifacts),'local_links':len(links)})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['environment','finish']);p.add_argument('--run',type=Path,required=True)
    a=p.parse_args();globals()[a.stage](a.run.resolve())
