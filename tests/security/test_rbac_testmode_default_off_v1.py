# tests/security/test_rbac_testmode_default_off_v1.py
"""
Security test: RBAC test-mode default OFF (v0.5.11u-5).

Validates:
- Test mode disabled by default (DECISIONOS_RBAC_TEST_MODE=0)
- X-Scopes header blocked in production
- Boot failure if test-mode ON in production
"""
from __future__ import annotations

import os
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient


def test_default_testmode_is_off(monkeypatch):
    """Test mode should be OFF by default."""
    # Clear environment
    monkeypatch.delenv("DECISIONOS_RBAC_TEST_MODE", raising=False)
    monkeypatch.setenv("DECISIONOS_ENV", "dev")

    # Force reload module to pick up new env
    import importlib
    from apps.policy import rbac_enforce

    importlib.reload(rbac_enforce)

    # Default should be OFF (0)
    assert rbac_enforce._RBAC_TEST_MODE is False


def test_prod_blocks_testmode_on(monkeypatch):
    """Production environment must reject test-mode ON."""
    monkeypatch.setenv("DECISIONOS_ENV", "prod")
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")

    # Importing module should raise RuntimeError
    with pytest.raises(RuntimeError, match="RBAC test-mode must be OFF in production"):
        import importlib
        from apps.policy import rbac_enforce

        importlib.reload(rbac_enforce)


def test_testmode_off_blocks_header_scopes(monkeypatch, tmp_path):
    """Test mode OFF: X-Scopes header should be ignored."""
    # Setup environment
    monkeypatch.setenv("DECISIONOS_ENV", "dev")
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "0")

    # Create minimal RBAC map
    rbac_map = tmp_path / "rbac_map.yaml"
    rbac_map.write_text(
        """
routes:
  - path: /secure
    method: GET
    scopes: [ops:read]
"""
    )

    # Force reload
    import importlib
    from apps.policy import rbac_enforce

    importlib.reload(rbac_enforce)

    # Build test app
    from apps.policy.rbac_enforce import require_scopes

    app = FastAPI()

    @app.get("/secure", dependencies=[Depends(require_scopes("ops:read"))])
    def secure_endpoint():
        return {"ok": True}

    client = TestClient(app)

    # Test 1: X-Scopes header should be ignored (test-mode OFF)
    r = client.get("/secure", headers={"X-Scopes": "ops:read"})
    assert r.status_code == 403, "X-Scopes should be ignored when test-mode OFF"


def test_testmode_on_allows_header_scopes_in_dev(monkeypatch, tmp_path):
    """Test mode ON (dev only): X-Scopes header should work."""
    # Setup environment (dev, not prod)
    monkeypatch.setenv("DECISIONOS_ENV", "dev")
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "1")

    # Create minimal RBAC map
    rbac_map = tmp_path / "rbac_map.yaml"
    rbac_map.write_text(
        """
routes:
  - path: /secure
    method: GET
    scopes: [ops:read]
"""
    )

    # Force reload
    import importlib
    from apps.policy import rbac_enforce

    importlib.reload(rbac_enforce)

    # Build test app
    from apps.policy.rbac_enforce import require_scopes

    app = FastAPI()

    @app.get("/secure", dependencies=[Depends(require_scopes("ops:read"))])
    def secure_endpoint():
        return {"ok": True}

    client = TestClient(app)

    # Test: X-Scopes header should work in dev test-mode
    r = client.get("/secure", headers={"X-Scopes": "ops:read"})
    assert r.status_code == 200, "X-Scopes should work in dev test-mode"
    assert r.json() == {"ok": True}


def test_prod_requires_explicit_testmode_off(monkeypatch):
    """Production requires explicit test-mode=0 or unset."""
    monkeypatch.setenv("DECISIONOS_ENV", "prod")
    monkeypatch.setenv("DECISIONOS_RBAC_TEST_MODE", "0")

    # Should NOT raise
    import importlib
    from apps.policy import rbac_enforce

    importlib.reload(rbac_enforce)

    assert rbac_enforce._RBAC_TEST_MODE is False
