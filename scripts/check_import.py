import importlib
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    importlib.import_module("backend.main")
    print("IMPORT_OK")
except Exception:
    traceback.print_exc()
    raise SystemExit(1)
