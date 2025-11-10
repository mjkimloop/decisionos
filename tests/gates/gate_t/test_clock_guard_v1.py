import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.gate_t]


def test_clock_guard_creates_reference(tmp_path):
    ref = tmp_path / "reference_utc.txt"
    rc = subprocess.run([sys.executable, "-m", "jobs.clock_guard", "--ref", str(ref), "--max-skew-sec", "1000"], check=False)
    assert rc.returncode == 0
    assert ref.exists()
    rc = subprocess.run([sys.executable, "-m", "jobs.clock_guard", "--ref", str(ref), "--max-skew-sec", "1000"], check=False)
    assert rc.returncode == 0
