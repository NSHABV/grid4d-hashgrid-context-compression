"""Use the existing indexed range engine verbatim without torch imports.

Only the three function definitions are AST-extracted from the public engine.
The implementation, symbol order and constriction settings remain unchanged.
Import this public dependency before installing a decoder data-read audit so
package-version discovery does not require a data-read exception later.
"""
import ast
import hashlib
import importlib.metadata
from pathlib import Path
import sys

# The older bench package prepends its Linux-only constriction installation.
# Prefer the isolated Windows build without editing that preserved package.
_windows_vendor = Path(__file__).resolve().parents[3] / '.tools/hashed-pair-deps'
if sys.platform == 'win32' and _windows_vendor.is_dir():
    sys.path.insert(0, str(_windows_vendor))

import constriction
import numpy as np
from research.experiment_bench.models import TOTAL

SOURCE = Path(__file__).resolve().parents[1] / 'entropy.py'
SOURCE_BYTES = SOURCE.read_bytes()
SOURCE_SHA256 = hashlib.sha256(SOURCE_BYTES).hexdigest()
CODER_VERSION = '0.4.2'
RUNTIME_VERSION = importlib.metadata.version('constriction')
_tree = ast.parse(SOURCE_BYTES.decode('utf-8'))
_names = ('_indexed_inputs', 'encode_indexed', 'decode_indexed')
_definitions = [node for node in _tree.body
                if isinstance(node, ast.FunctionDef) and node.name in _names]
if {node.name for node in _definitions} != set(_names):
    raise RuntimeError('Existing indexed engine API unavailable')
_namespace = {'np': np, 'constriction': constriction, 'TOTAL': TOTAL,
              '__package__': 'research.experiment_bench'}
exec(compile(ast.Module(body=_definitions, type_ignores=[]), str(SOURCE), 'exec'), _namespace)
encode_indexed = _namespace['encode_indexed']
decode_indexed = _namespace['decode_indexed']
del _tree, _definitions, _namespace


def check_runtime():
    if RUNTIME_VERSION != CODER_VERSION:
        raise ValueError('Canonical range engine requires constriction 0.4.2')
    if np.__version__ != '1.26.4':
        raise ValueError('Canonical hashed context requires NumPy 1.26.4')
