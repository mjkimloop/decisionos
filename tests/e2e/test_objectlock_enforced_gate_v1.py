import json
import subprocess
import sys
from pathlib import Path


def _make_upload(path: Path, applied: bool):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "mode": "stub",
        "counts": {"uploaded": 1, "skipped": 0, "failed": 0},
        "object_lock": {"applied": applied, "mode": "GOVERNANCE" if not applied else "COMPLIANCE"},
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_objectlock_enforced_gate(tmp_path):
    upload = tmp_path / "upload-report.json"
    _make_upload(upload, applied=False)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ci.validate_artifacts",
            "--upload",
            str(upload),
            "--objectlock-enforce",
        ],
        capture_output=True,
    )
    assert proc.returncode != 0
