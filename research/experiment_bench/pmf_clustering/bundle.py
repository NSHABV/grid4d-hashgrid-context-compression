"""Read-only adapter to sealed H3 bundles, retaining original Mean8 sources."""
import hashlib
import json
from pathlib import Path
import numpy as np
from . import codec, geometry, optimizer

FILES = ('encoder_inputs.npz', 'decoder_bundle/geometry.json',
         'original_coarse_model.dat', 'original_coarse_payload.dat')


def sha_file(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def verify_seal(folder):
    folder = Path(folder).resolve()
    parent = folder.parent
    seal_path = parent / 'FINAL_VALIDATION.json'
    seal = json.loads(seal_path.read_text(encoding='utf-8'))
    if seal.get('status') != 'PASS_COMPLETED':
        raise ValueError('Input bundle must belong to a completed sealed run')
    found = {}
    for relative in FILES:
        path = (folder / relative).resolve()
        if not path.is_relative_to(folder):
            raise ValueError('Bundle component points outside the sealed case')
        key = path.relative_to(parent).as_posix()
        actual = sha_file(path)
        if actual != seal['artifacts'][key]['sha256']:
            raise ValueError('Frozen bundle file hash mismatch: ' + relative)
        found[relative] = actual
    return {'seal_sha256': sha_file(seal_path), 'files': found}


def fingerprints(a):
    arrays = {key: codec.legacy.array_sha(a[key]) for key in
              ('coarse', 'fine', 'classes', 'original', 'thresholds', 'counts')}
    return {'arrays': arrays, 'geometry': codec.legacy.sha(codec.dm._json_bytes(a['geometry'])),
            'profile': a['profile'], 'coarse_model': codec.legacy.sha(a['coarse_model']),
            'coarse_payload': codec.legacy.sha(a['coarse_payload']), 'coarse_storage': a['coarse_storage']}


def load(folder):
    provenance = verify_seal(folder)
    folder = Path(folder)
    with np.load(folder / 'encoder_inputs.npz', allow_pickle=False) as z:
        values = {key: z[key] for key in ('coarse', 'fine', 'mean_classes', 'mean_pmf', 'edges')}
    g = json.loads((folder / 'decoder_bundle/geometry.json').read_text(encoding='utf-8'))
    geometry.validate(g, geometry.PRODUCTION)
    for role in ('coarse', 'fine'):
        q = values[role]
        if q.dtype != np.uint8 or q.shape != (g[role]['rows'], 2):
            raise ValueError('Invalid frozen symbol shapes')
    classes = geometry.contexts(g, values['coarse'], values['edges'], geometry.PRODUCTION)
    if values['mean_classes'].dtype != np.uint8 or not np.array_equal(classes, values['mean_classes']):
        raise ValueError('Saved classes differ from coarse-only Mean8')
    cm = (folder / 'original_coarse_model.dat').read_bytes()
    cp = (folder / 'original_coarse_payload.dat').read_bytes()
    _, storage, _ = codec.dm._parts(cm)
    restored, fc, ids = codec.decode_coarse(cm, cp, g, storage)
    if not np.array_equal(restored, values['coarse']) or codec.engine.encode_indexed(restored, ids, fc) != cp:
        raise ValueError('Invalid original standalone coarse prerequisite')
    result = {'geometry': g, 'profile': geometry.PRODUCTION,
              'coarse': values['coarse'], 'fine': values['fine'], 'classes': classes,
              'original': values['mean_pmf'], 'thresholds': values['edges'],
              'counts': optimizer.histogram(values['fine'], classes),
              'coarse_model': cm, 'coarse_payload': cp, 'coarse_storage': storage,
              'metadata_bytes': codec.outer_side_bytes(g, geometry.PRODUCTION, storage),
              'sealed_input': provenance}
    # Detect a component changing between checksum and loading.
    if verify_seal(folder) != provenance:
        raise ValueError('Bundle changed while loading')
    return result
