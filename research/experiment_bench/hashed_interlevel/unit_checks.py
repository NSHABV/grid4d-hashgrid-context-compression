"""Run the synthetic checks once, preserving a fresh run's log and status."""
import argparse
import io
from pathlib import Path
import time
import unittest
from research.hashgrid_analysis.hashed_context.runtime import write_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);run=p.parse_args().run.resolve()
    if not run.is_dir() or any((run/n).exists() for n in ('unit-tests.log','unit-tests.json')):
        raise FileExistsError('Existing run directory with no earlier unit-test results required')
    suite=unittest.TestSuite()
    for name in ('test_classes','test_dry_model','test_fit'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName('research.experiment_bench.hashed_interlevel.'+name))
    log=io.StringIO();started=time.perf_counter()
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    with (run/'unit-tests.log').open('x',encoding='utf-8') as f:f.write(log.getvalue())
    status={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),'seconds':time.perf_counter()-started}
    write_json(run/'unit-tests.json',status)
    print(status)
    if not result.wasSuccessful():raise SystemExit(1)

if __name__=='__main__':main()
