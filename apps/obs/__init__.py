import pkgutil
from pathlib import Path

__path__ = pkgutil.extend_path(__path__, __name__)
alt_path = Path(__file__).resolve().parents[2] / "kai-decisionos" / "apps" / "obs"
if alt_path.is_dir():
    __path__.append(str(alt_path))
