import os
import sys

import pytest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
sub_repo = os.path.join(repo_root, "kai-decisionos")
if os.path.isdir(sub_repo) and sub_repo not in sys.path:
    sys.path.insert(0, sub_repo)


@pytest.fixture
def policy_keys(monkeypatch):
    monkeypatch.setenv("DECISIONOS_POLICY_KEYS", '[{"key_id":"policy-local","secret":"policy-local-secret","state":"active"}]')
    try:
        from apps.common import policy_loader

        policy_loader._POLICY_LOADER = None
    except Exception:
        pass
    yield
    try:
        from apps.common import policy_loader

        policy_loader._POLICY_LOADER = None
    except Exception:
        pass
