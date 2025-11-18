"""Tests for Evidence integrity validation CI gate."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def test_evidence_dir(tmp_path):
    """Create test evidence directory with valid structure."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    # Create valid evidence files
    evidence_files = {
        "latest.json": {
            "judges": [{"key_id": "k1", "status": "active"}],
            "perf": {"p50_ms": 10, "p99_ms": 50},
            "perf_judge": {"decision_time_ms": 5},
            "canary": {"percent": 25, "status": "healthy"}
        },
        "2025-01-15.json": {
            "judges": [{"key_id": "k1", "status": "active"}],
            "perf": {"p50_ms": 12, "p99_ms": 55},
            "perf_judge": {"decision_time_ms": 6},
            "canary": {"percent": 10, "status": "healthy"}
        }
    }

    checksums = {}
    for filename, content in evidence_files.items():
        file_path = evidence_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f)

        # Compute SHA256
        import hashlib
        with open(file_path, "rb") as f:
            checksums[filename] = hashlib.sha256(f.read()).hexdigest()

    # Create index.json
    index = {
        "version": 1,
        "tampered": False,
        "entries": [
            {"file": filename, "sha256": checksums[filename]}
            for filename in evidence_files.keys()
        ]
    }

    index_path = evidence_dir / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f)

    return str(evidence_dir)


@pytest.mark.gate_t
def test_evidence_integrity_valid(test_evidence_dir):
    """Test: Valid evidence passes integrity check."""
    script = Path("scripts/ci/validate_evidence_integrity.sh")
    result = subprocess.run(
        ["bash", str(script), "--evidence-dir", test_evidence_dir],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "✓✓✓ EVIDENCE INTEGRITY: VALID ✓✓✓" in result.stdout


@pytest.mark.gate_t
def test_evidence_integrity_tampered_flag(test_evidence_dir):
    """Test: Tampered flag blocks validation."""
    # Modify index to set tampered=true
    index_path = Path(test_evidence_dir) / "index.json"
    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    index["tampered"] = True

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f)

    script = Path("scripts/ci/validate_evidence_integrity.sh")
    result = subprocess.run(
        ["bash", str(script), "--evidence-dir", test_evidence_dir],
        capture_output=True,
        text=True
    )

    assert result.returncode == 1
    assert "✗ Evidence has been tampered with (BLOCKING)" in result.stderr


@pytest.mark.gate_t
def test_evidence_integrity_missing_field(test_evidence_dir):
    """Test: Missing required field blocks validation."""
    # Remove 'canary' field from one evidence file
    evidence_file = Path(test_evidence_dir) / "latest.json"
    with open(evidence_file, "r", encoding="utf-8") as f:
        evidence = json.load(f)

    del evidence["canary"]  # Remove required field

    with open(evidence_file, "w", encoding="utf-8") as f:
        json.dump(evidence, f)

    script = Path("scripts/ci/validate_evidence_integrity.sh")
    result = subprocess.run(
        ["bash", str(script), "--evidence-dir", test_evidence_dir],
        capture_output=True,
        text=True
    )

    assert result.returncode == 1
    assert "✗ Missing required field: canary" in result.stderr


@pytest.mark.gate_t
def test_evidence_integrity_sha256_mismatch(test_evidence_dir):
    """Test: SHA256 mismatch blocks validation."""
    # Modify evidence file without updating index
    evidence_file = Path(test_evidence_dir) / "latest.json"
    with open(evidence_file, "r", encoding="utf-8") as f:
        evidence = json.load(f)

    evidence["perf"]["p50_ms"] = 999  # Change content

    with open(evidence_file, "w", encoding="utf-8") as f:
        json.dump(evidence, f)

    script = Path("scripts/ci/validate_evidence_integrity.sh")
    result = subprocess.run(
        ["bash", str(script), "--evidence-dir", test_evidence_dir],
        capture_output=True,
        text=True
    )

    assert result.returncode == 1
    assert "✗ SHA256 mismatch" in result.stderr


@pytest.mark.gate_t
def test_evidence_integrity_missing_file(test_evidence_dir):
    """Test: Missing evidence file blocks validation."""
    # Remove evidence file but keep index entry
    evidence_file = Path(test_evidence_dir) / "latest.json"
    evidence_file.unlink()

    script = Path("scripts/ci/validate_evidence_integrity.sh")
    result = subprocess.run(
        ["bash", str(script), "--evidence-dir", test_evidence_dir],
        capture_output=True,
        text=True
    )

    assert result.returncode == 1
    assert "✗ File not found" in result.stderr


@pytest.mark.gate_t
def test_evidence_integrity_empty_strict_mode(tmp_path):
    """Test: Empty evidence blocks in strict mode."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    # Create empty index
    index_path = evidence_dir / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "tampered": False, "entries": []}, f)

    script = Path("scripts/ci/validate_evidence_integrity.sh")
    result = subprocess.run(
        ["bash", str(script), "--evidence-dir", str(evidence_dir), "--strict"],
        capture_output=True,
        text=True,
        env={**os.environ, "DECISIONOS_EVIDENCE_STRICT": "1"}
    )

    assert result.returncode == 1
    assert "✗ Empty evidence in strict mode (BLOCKING)" in result.stderr


@pytest.mark.gate_t
def test_evidence_integrity_empty_lenient_mode(tmp_path):
    """Test: Empty evidence passes in lenient mode."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    # Create empty index
    index_path = evidence_dir / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "tampered": False, "entries": []}, f)

    script = Path("scripts/ci/validate_evidence_integrity.sh")
    result = subprocess.run(
        ["bash", str(script), "--evidence-dir", str(evidence_dir), "--lenient"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0


@pytest.mark.gate_t
def test_evidence_integrity_all_required_fields(test_evidence_dir):
    """Test: All required fields are validated."""
    script = Path("scripts/ci/validate_evidence_integrity.sh")
    result = subprocess.run(
        ["bash", str(script), "--evidence-dir", test_evidence_dir],
        capture_output=True,
        text=True
    )

    # Should validate all 4 required fields
    assert "✓ Field present: judges" in result.stdout
    assert "✓ Field present: perf" in result.stdout
    assert "✓ Field present: perf_judge" in result.stdout
    assert "✓ Field present: canary" in result.stdout
