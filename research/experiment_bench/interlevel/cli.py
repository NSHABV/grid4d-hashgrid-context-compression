import argparse
import importlib.metadata
import sys
import numpy as np

def main():
    p=argparse.ArgumentParser();p.add_argument('command');args,rest=p.parse_known_args()
    if args.command=='probe':
        import constriction
        print(sys.version,np.__version__,importlib.metadata.version('constriction'))
        print(constriction.stream.queue.RangeEncoder.encode.__doc__)
        print(constriction.stream.model.Categorical.__doc__)
    elif args.command=='gate':
        from .workflow import gate,OUTPUT
        q=argparse.ArgumentParser();q.add_argument('--output',type=__import__('pathlib').Path,default=OUTPUT);a=q.parse_args(rest);gate(a.output)
    elif args.command=='gate-decode':
        from .workflow import gate_decode
        gate_decode(*rest)
    elif args.command=='decode':
        from .format import decode
        decode(*rest)
    elif args.command=='encode':
        from .workflow import encode
        q=argparse.ArgumentParser();q.add_argument('output');q.add_argument('--model',required=True,choices=['iid','boundary','spatial8']);q.add_argument('--storage',required=True,choices=['dense_u32','packed_u16','sparse_default_u16']);a=q.parse_args(rest)
        print(encode(a.output,a.model,a.storage))
    elif args.command in ('run','validate','benchmark'):
        from . import workflow
        q=argparse.ArgumentParser();q.add_argument('--output',type=__import__('pathlib').Path,default=workflow.OUTPUT);q.add_argument('--repeats',type=int,default=3);a=q.parse_args(rest)
        if args.command=='benchmark':workflow.benchmark(a.output,a.repeats)
        else:getattr(workflow,args.command)(a.output)
    elif args.command=='tests':
        import unittest
        q=argparse.ArgumentParser();q.add_argument('--log');a=q.parse_args(rest)
        suite=unittest.defaultTestLoader.loadTestsFromNames(['research.experiment_bench.interlevel.tests','research.experiment_bench.test_entropy','research.grid4d.test_codec'])
        stream=open(a.log,'w') if a.log else sys.stderr
        if not unittest.TextTestRunner(stream=stream,verbosity=2).run(suite).wasSuccessful():sys.exit(1)
    elif args.command=='compare':
        from .workflow import comparisons,compare_runs,OUTPUT
        q=argparse.ArgumentParser();q.add_argument('--output',type=__import__('pathlib').Path,default=OUTPUT);q.add_argument('--against',type=__import__('pathlib').Path);a=q.parse_args(rest)
        if a.against:compare_runs(a.output,a.against)
        else:comparisons(a.output)
    elif args.command=='finish':
        from .report import finish
        q=argparse.ArgumentParser();q.add_argument('--output',type=__import__('pathlib').Path,default=__import__('pathlib').Path('research/interlevel_xyz34_bitstream'));a=q.parse_args(rest);finish(a.output)
    else:raise ValueError('Not implemented yet')

if __name__=='__main__':main()
