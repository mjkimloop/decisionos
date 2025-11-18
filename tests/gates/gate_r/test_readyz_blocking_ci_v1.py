"""Tests for readyz blocking CI gate enforcement."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def mock_readyz_server(tmp_path, monkeypatch):
    """Mock readyz endpoint via file-based responses."""
    response_file = tmp_path / "readyz_response.json"

    def set_response(status, checks=None):
        data = {"status": status}
        if checks:
            data["checks"] = checks
        response_file.write_text(json.dumps(data), encoding="utf-8")

    # Mock curl via script wrapper
    curl_mock = tmp_path / "curl"
    curl_mock.write_text(f"""#!/usr/bin/env bash
cat "{response_file}"
""", encoding="utf-8")
    curl_mock.chmod(0o755)

    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")

    return set_response


@pytest.mark.gate_r
def test_readyz_blocking_ok(tmp_path, mock_readyz_server):
    """Test: Readyz OK passes gate."""
    mock_readyz_server("ok", {
        "redis": {"status": "ok"},
        "kms": {"status": "ok"},
        "clock": {"status": "ok"}
    })

    script = Path("scripts/ci/check_readyz_blocking.sh")
    result = subprocess.run(
        ["bash", str(script), "--url", "http://mock/readyz"],
        capture_output=True,
        text=True,
        env={**os.environ, "DECISIONOS_READYZ_FAIL_CLOSED": "1"}
    )

    assert result.returncode == 0
    assert "✓ Readyz: OK" in result.stdout


@pytest.mark.gate_r
def test_readyz_blocking_degraded_fail_closed(tmp_path, mock_readyz_server):
    """Test: Degraded readyz blocks in fail-closed mode."""
    mock_readyz_server("degraded", {
        "redis": {"status": "ok"},
        "kms": {"status": "degraded", "error": "slow response"},
        "clock": {"status": "ok"}
    })

    script = Path("scripts/ci/check_readyz_blocking.sh")
    result = subprocess.run(
        ["bash", str(script), "--url", "http://mock/readyz"],
        capture_output=True,
        text=True,
        env={**os.environ, "DECISIONOS_READYZ_FAIL_CLOSED": "1"}
    )

    assert result.returncode == 1
    assert "✗ Readyz: degraded (BLOCKING" in result.stderr


@pytest.mark.gate_r
def test_readyz_blocking_degraded_fail_open(tmp_path, mock_readyz_server):
    """Test: Degraded readyz passes in fail-open mode."""
    mock_readyz_server("degraded", {
        "redis": {"status": "ok"},
        "kms": {"status": "degraded"},
        "clock": {"status": "ok"}
    })

    script = Path("scripts/ci/check_readyz_blocking.sh")
    result = subprocess.run(
        ["bash", str(script), "--url", "http://mock/readyz", "--fail-open"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "⚠ Readyz: degraded (allowed in fail-open mode)" in result.stdout


@pytest.mark.gate_r
def test_readyz_blocking_error(tmp_path, mock_readyz_server):
    """Test: Error readyz blocks in both modes."""
    mock_readyz_server("error", {
        "redis": {"status": "error", "error": "connection refused"},
        "kms": {"status": "ok"},
        "clock": {"status": "ok"}
    })

    script = Path("scripts/ci/check_readyz_blocking.sh")
    result = subprocess.run(
        ["bash", str(script), "--url", "http://mock/readyz"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 2
    assert "✗ Readyz: error (BLOCKING)" in result.stderr


@pytest.mark.gate_r
def test_readyz_blocking_unreachable(tmp_path, monkeypatch):
    """Test: Unreachable endpoint blocks."""
    # No mock server - curl will fail
    monkeypatch.setenv("PATH", os.environ["PATH"])  # Use real curl

    script = Path("scripts/ci/check_readyz_blocking.sh")
    result = subprocess.run(
        ["bash", str(script), "--url", "http://unreachable.invalid:9999/readyz"],
        capture_output=True,
        text=True,
        env={**os.environ, "READYZ_TIMEOUT": "1"}
    )

    # Should treat unreachable as error
    assert result.returncode == 2
    assert "✗ Readyz:" in result.stderr


@pytest.mark.gate_r
def test_readyz_blocking_custom_timeout(tmp_path, mock_readyz_server):
    """Test: Custom timeout configuration."""
    mock_readyz_server("ok")

    script = Path("scripts/ci/check_readyz_blocking.sh")
    result = subprocess.run(
        ["bash", str(script), "--url", "http://mock/readyz", "--timeout", "5"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "Timeout: 5s" in result.stdout


@pytest.mark.gate_r
def test_readyz_blocking_failed_checks_detail(tmp_path, mock_readyz_server):
    """Test: Failed checks are detailed in output."""
    mock_readyz_server("error", {
        "redis": {"status": "error", "error": "timeout"},
        "kms": {"status": "degraded", "error": "slow"},
        "clock": {"status": "ok"}
    })

    script = Path("scripts/ci/check_readyz_blocking.sh")
    result = subprocess.run(
        ["bash", str(script), "--url", "http://mock/readyz"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 2
    # Should show failed check count
    assert "Failed checks:" in result.stderr or "redis: error" in result.stdout
