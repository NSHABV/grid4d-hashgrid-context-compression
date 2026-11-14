"""Fresh decoder accepts one .bin plus public code; data-read audit."""
import argparse,os,sys,json,time
from pathlib import Path
import numpy as np
from . import codec
from research.hashgrid_analysis.hashed_context.runtime import peak_rss_mib
ROOT=Path(__file__).resolve().parents[3]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);a=parser.parse_args();source=Path(a.input).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
 seen=set();blocked=[]
 def audit(event,args):
  if event!='open' or not isinstance(args[0],(str,bytes)):return
  p=Path(os.fsdecode(args[0])).resolve();mode,flags=args[1:3]
  if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
   if not p.is_relative_to(out):raise PermissionError('Forbidden decoder write')
   return
  if p==source:seen.add(str(p));return
  if p.suffix in ('.py','.pyc','.pyd','.dll','.so') and any(p.is_relative_to(d) for d in (ROOT/'research',ROOT/'.tools',Path(sys.prefix),Path(sys.base_prefix))):return
  blocked.append(str(p));raise PermissionError('Forbidden decoder data read')
 sys.addaudithook(audit)
 def reject(*a,**kw):raise AssertionError('No histogram fitting in decoder')
 codec.legacy.fit_masses=codec.legacy.fit_spec=reject
 started=time.perf_counter();coarse,fine,ids,detail=codec.decode(source.read_bytes(),strict=True)
 for name,array in (('coarse',coarse),('fine',fine),('routes',ids)):
  with (out/(name+'.npy')).open('xb') as f:np.save(f,array,allow_pickle=False)
 if seen!={str(source)} or blocked:raise AssertionError('Decoder dependency audit')
 probes=[]
 for bad in (ROOT/'outputs/checkpoint.pth',ROOT/'experiments/xyz.u8.bin',source.parent.parent/'encoder_inputs.npz'):
  try:bad.open('rb')
  except PermissionError:probes.append(str(bad))
  else:raise AssertionError('Forbidden probe accepted')
 with (out/'audit.json').open('x',encoding='utf-8') as f:json.dump({'status':'PASS','detail':detail,'only_bin_data_read':True,'data_reads':sorted(seen),'forbidden_actual_reads':[],'forbidden_probes_denied':probes,'peak_rss_mib':peak_rss_mib(),'wall_with_output_seconds':time.perf_counter()-started},f,indent=2)
 print('PASS '+detail['mask'])
if __name__=='__main__':main()
