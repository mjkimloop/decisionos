import os
import sys

import pytest


def run_module(module, argv):
    old_argv = sys.argv
    sys.argv = argv
    try:
        return __import__(module, fromlist=["main"]).main()
    finally:
        sys.argv = old_argv


def test_checks_skip_without_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("DECISIONOS_VISIBILITY_ENABLE", "1")
    monkeypatch.setenv("CI_REPO", "owner/repo")
    monkeypatch.setenv("GITHUB_SHA", "deadbeef")
    rc = run_module("scripts.ci.github_checks", ["github_checks.py"])
    assert rc == 0


def test_annotate_skip_without_token(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("DECISIONOS_VISIBILITY_ENABLE", "1")
    monkeypatch.setenv("PRE_GATE_RESULT", "success")
    monkeypatch.setenv("GATE_RESULT", "success")
    monkeypatch.setenv("POST_GATE_RESULT", "success")
    out = tmp_path / "comment.md"
    rc = run_module(
        "scripts.ci.annotate_release_gate",
        [
            "annotate_release_gate.py",
            "--output",
            str(out),
            "--artifacts",
            "",
        ],
    )
    assert rc == 0
    assert out.exists()
