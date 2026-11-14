"""Explicit synthetic suite; never discover historical scene-dependent tests."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
MODULES=[
 'tests.test_public_previous8',
 'research.hashgrid_analysis.hashed_context.test_synthetic',
 'research.experiment_bench.hashed_interlevel.test_dry_model',
 'research.experiment_bench.hashed_pair.test_format',
 'research.experiment_bench.pmf_clustering.test_optimizer',
 'research.experiment_bench.pmf_clustering.test_geometry_oracle',
]
suite=unittest.defaultTestLoader.loadTestsFromNames(MODULES)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
