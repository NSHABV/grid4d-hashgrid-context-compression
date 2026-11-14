"""Read-only V1 regression plus synthetic independent V2 decoder validation.

Does not read or analyze hellwarrior targets. All new artifacts are written
exclusively below the supplied unique result directory; completed outputs are
never overwritten. Unit tests are executed separately and their log is pinned.
"""
import argparse
import difflib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from . import format as fmt
from .test_format import header
from research.experiment_bench.hashed_pair import format as legacy
from research.hashgrid_analysis.hashed_context.core import ROOT, sha, load_bundle
from research.hashgrid_analysis.hashed_context.runtime import write_json, peak_rss_mib


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve()
    destination=out/'v2-review-001.json'
    if destination.exists():raise FileExistsError(destination)
    artifacts=out/'v2-verification-001';artifacts.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter();cpu=time.process_time()
    old=ROOT/'research/hashed_mean8_bitstream_20261015_01'
    diag=ROOT/'research/hashed_context_diagnostic_20261013_01/L4_to_L5'
    source_paths=list((ROOT/'research/experiment_bench/hashed_pair').glob('*.py'))
    source_paths += [old/'best.json',diag/'fine_symbols.npy',
                     diag/'decoder_bundle/decoder_metadata.json',diag/'decoder_bundle/coarse_symbols.npy']
    best=json.loads((old/'best.json').read_text())
    source_paths += [old/r['path'] for r in best]
    before={str(p.relative_to(ROOT)):sha(p) for p in source_paths}
    meta,q4=load_bundle(diag/'decoder_bundle')
    q5=np.load(diag/'fine_symbols.npy',allow_pickle=False)
    regression=[]
    for row in best:
        path=old/row['path'];data=path.read_bytes()
        assert fmt.sha(data)==row['sha256']
        a,b,classes,detail=legacy.decode_bytes(data)
        assert np.array_equal(a,q4) and np.array_equal(b,q5)
        repeated,record=legacy.encode_pair(meta,q4,q5,row['model'],row['storage'])
        assert repeated==data and fmt.array_sha(classes)==record['classes_sha256']
        # V2 changes transport version and scene-quantizer admission, not the
        # entropy model, symbol order, probabilities, thresholds or payloads.
        v2,v2detail=fmt.encode_pair(meta,q4,q5,row['model'],row['storage'])
        h1,s1=legacy.unpack(data);h2,s2=fmt.unpack(v2)
        h2['version']=1
        assert h1==h2
        assert all(s1[k]==s2[k] for k in fmt.NAMES[1:])
        assert record['classes_sha256']==v2detail['classes_sha256']
        regression.append({'model':row['model'],'old_stream_sha256':sha(path),
                           'old_bytes':len(data),'v1_exact_decode':True,
                           'v1_reencode_byte_identical':True,
                           'v2_models_payloads_and_classes_identical':True,
                           'v2_header_differs_only_version':True})
        print(json.dumps({'legacy':row['model'],'status':'PASS'}),flush=True)
    rng=np.random.default_rng(4567)
    a=rng.integers(0,32,(205379,2),dtype=np.uint8)
    b=rng.integers(0,32,(524288,2),dtype=np.uint8)
    data,detail=fmt.encode_pair(header()['geometry'],a,b,'Mean8')
    source=artifacts/'synthetic-Mean8.bin'
    with source.open('xb') as f:f.write(data)
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    env['PYTHONPATH']=str(ROOT)+os.pathsep+str(ROOT/'.tools/hashed-pair-deps')
    decoded=artifacts/'fresh-decoder'
    cmd=[sys.executable,'-m','research.experiment_bench.hashed_pair_v2.replay',
         '--input',str(source),'--output',str(decoded)]
    cold=time.perf_counter();cp=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
    cold=time.perf_counter()-cold
    with (artifacts/'fresh-decoder.log').open('x',encoding='utf-8') as f:f.write(cp.stdout+cp.stderr)
    if cp.returncode:raise RuntimeError(cp.stdout+cp.stderr)
    assert np.array_equal(np.load(decoded/'q4.npy',allow_pickle=False),a)
    assert np.array_equal(np.load(decoded/'q5.npy',allow_pickle=False),b)
    assert fmt.array_sha(np.load(decoded/'classes.npy',allow_pickle=False))==detail['classes_sha256']
    audit=json.loads((decoded/'read-audit.json').read_text())
    assert audit['allowed_data_reads']==[str(source.resolve())] and not audit['blocked_reads']
    forbidden=[diag/'fine_symbols.npy',diag/'contexts.npz',diag/'decoder_bundle/coarse_symbols.npy',
               ROOT/'research/experiment_bench/reference-study/table-8/xyz_encoding.u8.bin',
               ROOT/'research/mean8_cross_scene_20261018_02/full/model/deform/iteration_50000/deform.pth',
               old/'first_encode/Mean8__sparse_default_u16.json']
    probe=artifacts/'forbidden-read-probes'
    cp=subprocess.run(cmd[:-1]+[str(probe),'--probe-forbidden',*[str(p) for p in forbidden]],
                      cwd=ROOT,env=env,capture_output=True,text=True)
    with (artifacts/'forbidden-read-probes.log').open('x',encoding='utf-8') as f:f.write(cp.stdout+cp.stderr)
    if cp.returncode:raise RuntimeError(cp.stdout+cp.stderr)
    probes=json.loads((probe/'read-audit.json').read_text());assert probes['negative_probes']==6
    after={str(p.relative_to(ROOT)):sha(p) for p in source_paths};assert before==after
    v1path=ROOT/'research/experiment_bench/hashed_pair/format.py'
    v2path=Path(fmt.__file__)
    diff=''.join(difflib.unified_diff(v1path.read_text().splitlines(keepends=True),
                                    v2path.read_text().splitlines(keepends=True),
                                    fromfile='V1/format.py',tofile='V2/format.py'))
    with (artifacts/'v1-v2-format.diff').open('x',encoding='utf-8') as f:f.write(diff)
    report={'status':'PASS','date':'2026-10-21','unit_tests':22,'unit_test_seconds':39.776,
            'unit_log_sha256':sha(out/'v2-tests-001.log'),'legacy_regression':regression,
            'source_before':before,'source_after':after,'old_inputs_and_v1_code_unchanged':True,
            'fresh_process_synthetic_mean8_exact':True,'fresh_process_cold_seconds':cold,
            'fresh_process_read_audit':str((decoded/'read-audit.json').relative_to(out)),
            'negative_data_read_probes':6,'checkpoint_or_new_scene_targets_read':False,
            'arithmetic_or_context_algorithm_changed':False,
            'quantizer_scope':'shared bits8 over xyz [0,6098108), arbitrary finite consistent min/max/step',
            'constant_semantics':'step0 requires zero symbols in both complete levels',
            'extreme_value_limit':'finite quantizer accepted; feature arms fail closed if pinned float32 lookup overflows',
            'replay_audit_scope':'Python open audit, not an OS sandbox; public source/dependencies may be read',
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in Path(fmt.__file__).parent.glob('*.py')},
            'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu,
            'peak_rss_mib':peak_rss_mib(),'GPU_used':False}
    write_json(destination,report)
    print(json.dumps({'status':'PASS','wall_seconds':report['wall_seconds'],'peak_rss_mib':report['peak_rss_mib']}))


if __name__=='__main__':main()
