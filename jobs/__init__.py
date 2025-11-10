import pkgutil
from pathlib import Path

__path__ = pkgutil.extend_path(__path__, __name__)
alt_path = Path(__file__).resolve().parents[1] / "kai-decisionos" / "jobs"
if alt_path.is_dir():
    __path__.append(str(alt_path))
