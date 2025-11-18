from datetime import datetime, timezone
from pathlib import Path

import pytest

from apps.ops import freeze


def test_freeze_env_flag(monkeypatch):
    monkeypatch.setenv("DECISIONOS_FREEZE", "1")
    active, reason = freeze.is_freeze_active()
    assert active
    assert reason.startswith("env")


def test_freeze_window_match(tmp_path, monkeypatch):
    cfg = tmp_path / "windows.yaml"
    cfg.write_text(
        """
windows:
  - name: "weekend"
    days: ["sat", "sun"]
    start_time: "00:00"
    end_time: "23:59"
    timezone: "UTC"
""",
        encoding="utf-8",
    )
    saturday = datetime(2025, 11, 22, 3, 0, tzinfo=timezone.utc)
    active, reason = freeze.is_freeze_active(env={"FREEZE_WINDOWS_FILE": str(cfg)}, now=saturday)
    assert active
    assert "window" in reason


def test_override_scope_allows(monkeypatch, tmp_path):
    flag = tmp_path / "freeze.flag"
    flag.write_text("manual", encoding="utf-8")
    monkeypatch.setenv("DECISIONOS_FREEZE_FILE", str(flag))
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "deploy:override_freeze")
    freeze.enforce("promote")
    assert flag.exists()
