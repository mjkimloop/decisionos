import importlib, sys

# decisionos.* routes to apps.* lazily

def __getattr__(name: str):
    return importlib.import_module(f"apps.{name}")

sys.modules.setdefault(__name__, sys.modules[__name__])
