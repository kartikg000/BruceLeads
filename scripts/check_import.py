import importlib, traceback

try:
    importlib.import_module('backend.main')
    print('IMPORT_OK')
except Exception:
    traceback.print_exc()
