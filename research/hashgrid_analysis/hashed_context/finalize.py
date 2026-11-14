"""Snapshot effective sources and validate the completed diagnostic report once."""
import argparse
import ast
import json
import re
import shutil
import time
from pathlib import Path

from .core import ROOT, sha
from .runtime import write_json


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('run', type=Path)
    run = p.parse_args().run.resolve()
    for name in ('source_snapshot', 'source-hashes.json', 'final-validation.json'):
        if (run / name).exists():
            raise FileExistsError(f'Immutable output already exists: {name}')
    start = time.perf_counter()
    manifest = json.loads((run / 'run-manifest.json').read_text(encoding='utf-8'))
    module = ROOT / 'research/hashgrid_analysis/hashed_context'
    paths = {ROOT / name for name in manifest['source_hashes']}
    paths.update(x for x in module.iterdir() if x.is_file() and x.suffix in ('.py', '.md', '.sh'))
    gpu_sources = {}
    for pair in ('L4_to_L5', 'L5_to_L6'):
        evidence = json.loads((run / 'gpu_checks' / pair / 'gpu-parity.json').read_text())
        for name, expected in evidence['source_sha256'].items():
            path = ROOT / name
            assert sha(path) == expected, name
            paths.add(path)
            gpu_sources[name] = expected

    initial_source_checks = {}
    for name, expected in manifest['source_hashes'].items():
        if name.endswith('/diagnostic.py'):
            initial = run / 'source_stage0/diagnostic.py'
            # Subsequent replays of this workflow start with the corrected driver,
            # so no historical driver copy is needed if its source has not changed.
            reference = initial if initial.exists() else ROOT / name
        else:
            reference = ROOT / name
        assert sha(reference) == expected, name
        initial_source_checks[name] = expected

    snapshot = run / 'source_snapshot'
    snapshot.mkdir()
    registry = {}
    for path in sorted(paths):
        rel = path.relative_to(ROOT)
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        dest = snapshot / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        expected = sha(path)
        assert sha(dest) == expected
        registry[rel.as_posix()] = {'sha256': expected,
                                    'snapshot': dest.relative_to(run).as_posix()}
    write_json(run / 'source-hashes.json', {
        'status': 'PASS', 'effective_sources': registry,
        'stage0_reference_checks': initial_source_checks,
        'stage0_driver_snapshot': 'source_stage0/diagnostic.py' if (run / 'source_stage0/diagnostic.py').exists() else None,
        'driver_change': 'synthetic unittest invocation only; context core unchanged',
        'gpu_compiled_source_checks': gpu_sources,
    })

    report = run / 'DIAGNOSTIC_REPORT.md'
    body = report.read_text(encoding='utf-8')
    links = []
    for destination in re.findall(r'\]\(([^)]+)\)', body):
        if destination.startswith(('https://', 'http://')):
            continue
        file_name = re.sub(r':\d+$', '', destination)
        path = Path(file_name.strip('<>'))
        assert path.is_absolute() and path.is_file(), destination
        links.append(destination)
    tables_checked = 0
    width = None
    for line in body.splitlines():
        if line.startswith('|'):
            count = line.count('|')
            if width is None:
                width = count
                tables_checked += 1
            assert count == width, line
        else:
            width = None

    artifacts = {}
    for path in sorted(run.rglob('*')):
        if (not path.is_file() or 'matplotlib_config' in path.parts
                or '__pycache__' in path.parts or path.is_relative_to(snapshot)):
            continue
        artifacts[path.relative_to(run).as_posix()] = sha(path)
    statuses = {}
    for name in ('context-validation.json', 'synthetic-tests.json', 'example_verification/validation.json',
                 'integrity_checks/validation.json', 'gpu_checks/cross-cpu-parity.json'):
        item = json.loads((run / name).read_text(encoding='utf-8'))
        assert item['status'] == 'PASS', name
        statuses[name] = item['status']
    write_json(run / 'final-validation.json', {
        'status': 'PASS', 'source_snapshot_files': len(registry),
        'source_sha_checks': 'PASS', 'syntax_checks': 'PASS',
        'local_report_links_checked': len(links), 'markdown_tables_checked': tables_checked,
        'report_sha256': sha(report), 'artifact_hashes': artifacts,
        'checks': statuses, 'probability_models': 'NOT RUN', 'entropy_coding': 'NOT RUN',
        'new_quantization': 'NOT RUN', 'training': 'NOT RUN',
        'elapsed_seconds': time.perf_counter() - start,
    })
    print(json.dumps({'status': 'PASS', 'source_files': len(registry), 'report_links': len(links),
                      'artifacts': len(artifacts), 'report': str(report)}))


if __name__ == '__main__':
    main()
