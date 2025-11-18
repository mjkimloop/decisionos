import subprocess
import sys


def test_freeze_override_scope(tmp_path, monkeypatch):
    flag = tmp_path / "freeze.flag"
    flag.write_text("manual", encoding="utf-8")
    monkeypatch.setenv("DECISIONOS_FREEZE_FILE", str(flag))
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "deploy:override_freeze")
    result = subprocess.run(
        [sys.executable, "-m", "apps.ops.freeze", "--action", "promote"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
