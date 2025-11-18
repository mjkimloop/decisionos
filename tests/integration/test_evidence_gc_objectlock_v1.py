import json
import pathlib
import tempfile

from jobs.evidence_gc_lockcheck import run


def test_gc_lockcheck_dry_run():
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / "ev.json"
        p.write_text(json.dumps({"tier": "WIP", "meta": {"generated_at": "2024-01-01T00:00:00Z"}}), encoding="utf-8")
        result = run(tmp, dry_run=True)
        assert result["scanned"] == 1
        assert result["expired"] == 1
