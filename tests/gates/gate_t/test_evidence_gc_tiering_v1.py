import json
import os
import time
from pathlib import Path

import pytest

from apps.obs.evidence.indexer import write_index
from jobs.evidence_gc import run as gc_run

pytestmark = [pytest.mark.gate_t]


def _iso_now() -> str:
    return "2025-11-11T00:00:00Z"


def _write_dummy(path: Path) -> None:
    path.write_text("{}", encoding="utf-8")


def test_gc_dry_run_and_delete(tmp_path):
    root = tmp_path / "evidence"
    root.mkdir(parents=True, exist_ok=True)
    old = root / "evidence-old.json"
    _write_dummy(old)
    very_old = root / "evidence-very-old.json"
    _write_dummy(very_old)
    locked = root / "evidence-good.locked.json"
    _write_dummy(locked)

    past = time.time() - (10 * 24 * 3600)
    os.utime(old, (past, past))
    os.utime(very_old, (past, past))

    write_index(str(root))

    dry = gc_run(str(root), wip_retain_days=7, dry_run=True)
    assert sorted(dry) == ["evidence-old.json", "evidence-very-old.json"]
    assert locked.name not in dry

    deleted = gc_run(str(root), wip_retain_days=7, dry_run=False)
    assert sorted(deleted) == ["evidence-old.json", "evidence-very-old.json"]
    assert not old.exists() and not very_old.exists()
    assert locked.exists()
