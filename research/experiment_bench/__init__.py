"""Grid4D experimental bench; no changes to upstream training or rendering."""
import sys
from pathlib import Path

# A separate, tiny CPU dependency. The original Grid4D prefixes remain unchanged.
vendor = Path(__file__).resolve().parents[2] / '.tools/bench-python'
if vendor.is_dir():
    sys.path.insert(0, str(vendor))
