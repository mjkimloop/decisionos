"""Tests for rotation labels CI script."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest


@pytest.mark.ci
def test_labels_skip_without_token(monkeypatch):
    """Test: Skips when GITHUB_TOKEN is missing."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("CI_REPO", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    r = subprocess.run(
        [sys.executable, "-m", "scripts.ci.ensure_rotation_labels"], capture_output=True, text=True
    )

    assert r.returncode == 0
    assert "skip" in r.stdout.lower()


@pytest.mark.ci
@pytest.mark.skipif("GITHUB_TOKEN" not in os.environ, reason="Requires GITHUB_TOKEN")
def test_labels_sync_with_token():
    """Test: Syncs labels when token is available."""
    # This test requires actual GitHub API access
    # In production, this would use a test repo or mock
    r = subprocess.run([sys.executable, "-m", "scripts.ci.ensure_rotation_labels"], capture_output=True, text=True)

    # Should succeed (exit 0) even if no changes needed
    assert r.returncode == 0


@pytest.mark.ci
def test_labels_palette_coverage():
    """Test: Palette defines all required labels."""
    from scripts.ci.ensure_rotation_labels import PALETTE

    assert len(PALETTE) == 3
    names = {p["name"] for p in PALETTE}
    assert "rotation:soon-14" in names
    assert "rotation:soon-7" in names
    assert "rotation:soon-3" in names

    # Verify colors are hex
    for p in PALETTE:
        assert len(p["color"]) == 6
        assert p["description"]
