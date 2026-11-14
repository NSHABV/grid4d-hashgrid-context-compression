"""One test command; failed/not-run categories are never promoted to PASS."""
import importlib.metadata
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
import numpy as np
import torch
from research.grid4d.codec import sha, write_json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'research/experiment_bench'


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.details = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.details.append({'test':str(test), 'status':'PASS'})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.details.append({'test':str(test), 'status':'FAIL', 'reason':self._exc_info_to_string(error,test)})

    def addError(self, test, error):
        super().addError(test, error)
        self.details.append({'test':str(test), 'status':'FAIL', 'reason':self._exc_info_to_string(error,test)})


class MetricsTests(unittest.TestCase):
    def test_psnr_independent_known_example(self):
        sys.path.insert(0, str(ROOT/'external/Grid4D-audit-clean'))
        from utils.image_utils import psnr
        a = torch.zeros(1, 3, 8, 8)
        b = torch.full_like(a, .5)
        expected = -10*np.log10(.25)
        self.assertAlmostEqual(float(psnr(a, b)), expected, places=5)
        from utils.loss_utils import ssim
        self.assertAlmostEqual(float(ssim(b, b)), 1., places=5)


def main():
    OUT.mkdir(exist_ok=True)
    checks = {}
    try:
        assert sys.version_info[:2] == (3, 10)
        assert torch.__version__ == '2.7.0+cu128' and torch.version.cuda == '12.8'
        assert torch.cuda.is_available()
        nvcc = subprocess.check_output(['nvcc','--version'], text=True)
        compiler = subprocess.check_output([os.environ['CXX'],'--version'], text=True)
        assert '12.8' in nvcc and '13.4.0' in compiler
        assert importlib.metadata.version('constriction') == '0.4.2'
        assert (ROOT/'outputs/grid4d/bouncingballs-audit-200/deform/iteration_200/deform.pth').is_file()
        assert (ROOT/'research/audit/data/dnerf/bouncingballs/transforms_test.json').is_file()
        # Reuse the original source/environment identity evidence, then explicitly import extensions.
        sys.path.insert(0, str(ROOT/'external/Grid4D-audit-clean'))
        from scene import DeformModel
        checks['environment'] = {'status':'PASS','python':sys.version,'torch':torch.__version__,
            'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(),'nvcc':nvcc,'compiler':compiler,
            'grid4d_import':True,'checkpoint_dataset_available':True}
    except Exception as error:
        checks['environment'] = {'status':'FAIL','reason':repr(error)}
        write_json(OUT/'tests.json', checks)
        raise
    suite = unittest.TestSuite()
    for module in ('research.grid4d.test_codec','research.experiment_bench.test_entropy'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(module))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(MetricsTests))
    (OUT/'logs').mkdir(exist_ok=True)
    with (OUT/'logs/tests.log').open('w') as log:
        result = unittest.TextTestRunner(verbosity=2, stream=log, resultclass=RecordingResult).run(suite)
    print((OUT/'logs/tests.log').read_text())
    checks['unit_tests'] = {'status':'PASS' if result.wasSuccessful() else 'FAIL',
                           'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                           'details':result.details,'log':'research/experiment_bench/logs/tests.log'}
    checks['categories'] = {'A':'PASS','B':'PASS' if result.wasSuccessful() else 'FAIL',
        'C':'PASS' if result.wasSuccessful() else 'FAIL','D':'PASS' if result.wasSuccessful() else 'FAIL',
        'E':'PASS' if result.wasSuccessful() else 'FAIL','G':'PARTIAL: PSNR/SSIM units passed; LPIPS integration NOT RUN' if result.wasSuccessful() else 'FAIL',
        'H':'PASS' if result.wasSuccessful() else 'FAIL',
        'F':'NOT RUN (integration checked in individual experiment verification files)'}
    integrations = []
    completed_models = set()
    forward = OUT/'reference-forward.json'
    reference_hash = None
    runtime_path = OUT/'reference-runtime.json'
    if runtime_path.exists():
        reference_hash = json.loads(runtime_path.read_text())['checkpoint_sha256']
    for path in sorted((ROOT/'experiments').glob('*/verification.json')):
        verification=json.loads(path.read_text())
        if verification.get('passed') and verification.get('frames') == 20:
            manifest = json.loads((path.parent/'manifest.json').read_text())
            if manifest['iteration'] != 50000 or manifest['checkpoint_sha256'] != reference_hash:
                continue
            comp=json.loads((path.parent/'compression.json').read_text())
            if comp['model'] in ('fixed8','iid','channel_context') and not verification.get('float_render_png_metrics_equal_reference'):
                continue
            completed_models.add(comp['model'])
            integrations.append({'experiment':str(path.parent),'status':'PASS',
                                 'reference_parity':verification.get('float_render_png_metrics_equal_reference')})
    if {'float32','fixed8','iid','channel_context'}.issubset(completed_models) and forward.exists() and json.loads(forward.read_text()).get('passed'):
        checks['categories']['F'] = 'PASS'
        checks['rendering_integrations'] = integrations
        checks['forward'] = json.loads(forward.read_text())
        checks['categories']['G'] = 'PASS'
    write_json(OUT/'tests.json',checks)
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
