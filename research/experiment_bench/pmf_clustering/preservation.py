"""Read-only audits of artifacts predating H4; results go to a unique directory."""
import argparse
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
H3 = ROOT / 'research/hybrid_context_selection_20261027_01'


def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as file:
        json.dump(value, file, indent=2, ensure_ascii=False, allow_nan=False)


def baseline():
    old = json.loads((H3 / 'protected-input-hashes.json').read_text(encoding='utf-8'))
    seal = json.loads((H3 / 'FINAL_VALIDATION.json').read_text(encoding='utf-8'))
    if seal['status'] != 'PASS_COMPLETED':
        raise ValueError('H3 is not sealed')
    old.update({(H3 / p).relative_to(ROOT).as_posix(): v['sha256'] for p, v in seal['artifacts'].items()})
    old.update(seal['source_hashes'])
    old[(H3 / 'FINAL_VALIDATION.json').relative_to(ROOT).as_posix()] = sha(H3 / 'FINAL_VALIDATION.json')
    return old


def verify(expected):
    started = time.perf_counter()
    for name, digest in expected.items():
        if sha(ROOT / name) != digest:
            raise AssertionError('Protected artifact differs: ' + name)
    return {'status': 'PASS', 'files': len(expected), 'seconds': time.perf_counter() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--initialize', action='store_true')
    args = parser.parse_args()
    run = Path(args.run).resolve()
    if args.initialize:
        run.mkdir(parents=True, exist_ok=False)
        expected = baseline()
        write_json(run / 'protected-input-hashes.json', expected)
        result = verify(expected)
        write_json(run / 'integrity-initial.json', result)
    else:
        expected = json.loads((run / 'protected-input-hashes.json').read_text())
        result = verify(expected)
        write_json(run / 'integrity-final.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
