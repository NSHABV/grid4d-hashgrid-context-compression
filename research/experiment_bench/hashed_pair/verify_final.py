"""Fresh independent decodes and unchanged encodes after robustness repair."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import numpy as np
from .run import ROOT,source_arrays,read,ARMS
from .format import encode_pair
from research.hashgrid_analysis.hashed_context.runtime import write_json
from research.hashgrid_analysis.hashed_context.core import sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();run=a.run.resolve()
    out=run/'post_repair_validation';out.mkdir(exist_ok=False)
    meta,q4,q5=source_arrays();records=[];env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    env['PYTHONPATH']=str(ROOT)+os.pathsep+str(ROOT/'.tools/hashed-pair-deps')
    for r in read(run/'results.json'):
        path=run/r['path'];dest=out/(r['model']+'__'+r['storage'])
        cp=subprocess.run([sys.executable,'-m','research.experiment_bench.hashed_pair.replay','--input',str(path),'--output',str(dest)],
             cwd=ROOT,env=env,capture_output=True,text=True)
        if cp.returncode:raise RuntimeError(cp.stdout+cp.stderr)
        audit=read(dest/'read-audit.json');assert not audit['blocked_reads']
        for name,q in [('q4',q4),('q5',q5)]:assert np.array_equal(np.load(dest/(name+'.npy')),q)
        old=run/r['decode_directory']/'classes.npy'
        assert np.array_equal(np.load(old),np.load(dest/'classes.npy'))
        assert sha(path)==r['sha256']
        # All twelve transports, not only the selected four, remain byte-identical.
        data,detail=encode_pair(meta,q4,q5,r['model'],r['storage']);assert data==path.read_bytes()
        records.append({'model':r['model'],'storage':r['storage'],'exact_q4_q5_classes':True,
            'byte_identical':True,'one_bin_data_input':audit['allowed_data_reads']==[str(path)],'sha256':r['sha256']})
        print(r['model'],r['storage'],'PASS',flush=True)
    write_json(out/'validation.json',{'status':'PASS','streams':records,'scope':'Correctness revalidation after error normalization; not a performance benchmark',
        'format_source_sha256':sha(Path(__file__).with_name('format.py'))})

if __name__=='__main__':main()
