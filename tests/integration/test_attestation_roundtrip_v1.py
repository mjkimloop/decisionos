"""Integration test: Attestation roundtrip (generate + verify)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.mark.integration
def test_attestation_generate_and_verify(tmp_path, monkeypatch):
    """Test: Generate attestation and verify it."""
    monkeypatch.chdir(tmp_path)

    # Setup git repo
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)

    # Create dummy file and commit
    dummy_file = tmp_path / "test.txt"
    dummy_file.write_text("test")
    subprocess.run(["git", "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], check=True, capture_output=True)

    # Create policy registry
    registry_dir = tmp_path / "configs" / "policy"
    registry_dir.mkdir(parents=True)

    registry = {
        "version": 1,
        "root_hash": "test-root-hash-12345",
        "entries": [],
        "chain": [],
    }

    registry_file = registry_dir / "registry.json"
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry, f)

    # Set environment
    monkeypatch.setenv("OUT_DIR", str(tmp_path / "var" / "gate"))

    # Generate attestation
    result = subprocess.run(
        [sys.executable, "-m", "scripts.ci.attest_build"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Attestation generated" in result.stdout

    # Find attestation file
    gate_dir = tmp_path / "var" / "gate"
    attestation_files = list(gate_dir.glob("attestation-*.json"))
    assert len(attestation_files) == 1

    attestation_file = attestation_files[0]

    # Verify attestation
    result = subprocess.run(
        [sys.executable, "-m", "scripts.ci.verify_attestation", str(attestation_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Attestation verified" in result.stdout


@pytest.mark.integration
def test_attestation_policy_mismatch(tmp_path, monkeypatch):
    """Test: Attestation verification fails on policy root_hash mismatch."""
    monkeypatch.chdir(tmp_path)

    # Setup git repo
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
    dummy_file = tmp_path / "test.txt"
    dummy_file.write_text("test")
    subprocess.run(["git", "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], check=True, capture_output=True)

    # Create initial registry
    registry_dir = tmp_path / "configs" / "policy"
    registry_dir.mkdir(parents=True)

    registry = {
        "version": 1,
        "root_hash": "original-root-hash",
        "entries": [],
        "chain": [],
    }

    registry_file = registry_dir / "registry.json"
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry, f)

    # Generate attestation
    monkeypatch.setenv("OUT_DIR", str(tmp_path / "var" / "gate"))
    result = subprocess.run(
        [sys.executable, "-m", "scripts.ci.attest_build"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Modify registry (simulate policy change)
    registry["root_hash"] = "modified-root-hash"
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry, f)

    # Verify attestation (should fail due to mismatch)
    gate_dir = tmp_path / "var" / "gate"
    attestation_file = list(gate_dir.glob("attestation-*.json"))[0]

    result = subprocess.run(
        [sys.executable, "-m", "scripts.ci.verify_attestation", str(attestation_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "root_hash mismatch" in result.stderr


@pytest.mark.integration
def test_attestation_find_by_commit(tmp_path, monkeypatch):
    """Test: Find attestation by commit SHA."""
    monkeypatch.chdir(tmp_path)

    # Setup git repo
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
    dummy_file = tmp_path / "test.txt"
    dummy_file.write_text("test")
    subprocess.run(["git", "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], check=True, capture_output=True)

    # Get commit SHA
    commit_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()

    # Create registry
    registry_dir = tmp_path / "configs" / "policy"
    registry_dir.mkdir(parents=True)
    registry = {"version": 1, "root_hash": "test", "entries": [], "chain": []}
    with open(registry_dir / "registry.json", "w", encoding="utf-8") as f:
        json.dump(registry, f)

    # Generate attestation
    monkeypatch.setenv("OUT_DIR", str(tmp_path / "var" / "gate"))
    result = subprocess.run(
        [sys.executable, "-m", "scripts.ci.attest_build"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Verify by commit SHA (full)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ci.verify_attestation",
            "--commit",
            commit_sha,
            "--no-require-policy",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Attestation verified" in result.stdout

    # Verify by commit SHA (short)
    short_sha = commit_sha[:12]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.ci.verify_attestation",
            "--commit",
            short_sha,
            "--no-require-policy",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
