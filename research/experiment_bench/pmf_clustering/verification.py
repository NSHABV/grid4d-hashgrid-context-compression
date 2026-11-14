"""Run technical tests into a unique directory. No scene H4 clustering."""
import importlib
import io
from pathlib import Path
import sys
import time
import unittest
from . import preservation


def run(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    expected = preservation.baseline()
    preservation.write_json(output / 'integrity-initial.json', preservation.verify(expected))
    modules = [importlib.import_module(__package__ + '.' + name) for name in
               ('test_optimizer', 'test_geometry_oracle', 'test_integration')]
    modules[-1].ARTIFACT_DIR = output
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module) for module in modules)
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    with (output / 'tests.log').open('x', encoding='utf-8') as file:
        file.write(log.getvalue())
    print(log.getvalue(), flush=True)
    preservation.write_json(output / 'integrity-final.json', preservation.verify(expected))
    sources = {p.relative_to(preservation.ROOT).as_posix(): preservation.sha(p) for p in Path(__file__).parent.glob('*.py')}
    artifacts = {p.relative_to(output).as_posix(): preservation.sha(p) for p in output.rglob('*') if p.is_file()}
    preservation.write_json(output / 'VALIDATION.json', {'status': 'PASS' if result.wasSuccessful() else 'FAIL',
        'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'protected_files_unchanged': len(expected), 'seconds': time.perf_counter() - started,
        'python': sys.version, 'source_sha256': sources, 'artifact_sha256': artifacts,
        'full_scene_clustering_runs': 0})
    if not result.wasSuccessful():
        raise SystemExit(1)
