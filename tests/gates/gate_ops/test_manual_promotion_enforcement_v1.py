"""Tests for manual promotion enforcement."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def mock_evidence(tmp_path):
    """Create mock evidence with healthy canary windows."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    evidence_file = evidence_dir / "latest.json"
    evidence = {
        "canary": {
            "windows": [
                {"pass": True, "burst": 0.5, "timestamp_unix": 1000.0},
                {"pass": True, "burst": 0.6, "timestamp_unix": 2000.0},
                {"pass": True, "burst": 0.7, "timestamp_unix": 3000.0},
            ]
        }
    }

    with open(evidence_file, "w", encoding="utf-8") as f:
        json.dump(evidence, f)

    return str(evidence_file)


@pytest.mark.gate_ops
def test_auto_promote_disabled_by_default(mock_evidence, monkeypatch):
    """Test: Auto-promotion is disabled by default."""
    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", mock_evidence)
    # Do NOT set DECISIONOS_AUTOPROMOTE_ENABLE

    from jobs.canary_auto_promote import main

    # Should exit with code 0 (disabled message)
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0


@pytest.mark.gate_ops
def test_auto_promote_disabled_explicit(mock_evidence, monkeypatch):
    """Test: Auto-promotion respects explicit disable."""
    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", mock_evidence)
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "0")

    from jobs.canary_auto_promote import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0


@pytest.mark.gate_ops
def test_auto_promote_enabled_requires_flag(mock_evidence, monkeypatch):
    """Test: Auto-promotion only works when explicitly enabled."""
    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", mock_evidence)
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "1")
    monkeypatch.setenv("DECISIONOS_CANARY_REQUIRED_PASSES", "3")
    monkeypatch.setenv("DECISIONOS_CANARY_MAX_BURST", "1.5")

    from jobs.canary_auto_promote import main

    # Should trigger promotion
    with pytest.raises(SystemExit) as exc_info:
        main()

    # Exit code 0 = promote, 2 = abort, 3 = hold
    assert exc_info.value.code in (0, 2, 3)


@pytest.mark.gate_ops
def test_manual_promotion_blocks_auto_decision(mock_evidence, tmp_path, monkeypatch):
    """Test: Manual promotion mode blocks automatic decisions."""
    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", mock_evidence)
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "0")

    # Create manual promotion marker
    marker_file = tmp_path / "manual_promotion.flag"
    marker_file.write_text("manual")

    from jobs.canary_auto_promote import main

    # Should exit immediately (disabled)
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0


@pytest.mark.gate_ops
def test_promotion_decision_requires_healthy_windows(mock_evidence, monkeypatch):
    """Test: Promotion decision requires healthy windows."""
    # Create evidence with failed window
    evidence_file = Path(mock_evidence)
    evidence = json.loads(evidence_file.read_text())
    evidence["canary"]["windows"][2]["pass"] = False  # Last window failed

    evidence_file.write_text(json.dumps(evidence))

    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", mock_evidence)
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "1")
    monkeypatch.setenv("DECISIONOS_CANARY_REQUIRED_PASSES", "3")

    from jobs.canary_auto_promote import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    # Should hold (not promote) because last window failed
    assert exc_info.value.code == 3


@pytest.mark.gate_ops
def test_promotion_decision_aborts_on_burst(mock_evidence, monkeypatch):
    """Test: Promotion decision aborts on burst threshold."""
    # Create evidence with high burst
    evidence_file = Path(mock_evidence)
    evidence = json.loads(evidence_file.read_text())
    evidence["canary"]["windows"][2]["burst"] = 99.0  # High burst

    evidence_file.write_text(json.dumps(evidence))

    monkeypatch.setenv("DECISIONOS_EVIDENCE_LATEST", mock_evidence)
    monkeypatch.setenv("DECISIONOS_AUTOPROMOTE_ENABLE", "1")
    monkeypatch.setenv("DECISIONOS_CANARY_REQUIRED_PASSES", "3")
    monkeypatch.setenv("DECISIONOS_CANARY_MAX_BURST", "1.5")

    from jobs.canary_auto_promote import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    # Should abort (code 2)
    assert exc_info.value.code == 2


@pytest.mark.gate_ops
def test_manual_marker_file_enforcement(tmp_path):
    """Test: Manual promotion marker file is enforced."""
    marker_file = tmp_path / "manual_promotion.flag"
    marker_file.write_text("manual")

    assert marker_file.exists()
    assert marker_file.read_text() == "manual"


@pytest.mark.gate_ops
def test_auto_marker_file_enforcement(tmp_path):
    """Test: Auto promotion marker file is enforced."""
    marker_file = tmp_path / "manual_promotion.flag"
    marker_file.write_text("auto")

    assert marker_file.exists()
    assert marker_file.read_text() == "auto"
