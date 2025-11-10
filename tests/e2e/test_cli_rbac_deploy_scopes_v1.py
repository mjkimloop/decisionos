import subprocess
import sys
import pytest

pytestmark = [pytest.mark.gate_aj]

if sys.platform.startswith("win"):
    pytest.skip("requires bash environment", allow_module_level=True)


def test_rbac_promote_denied(monkeypatch, tmp_path):
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "judge:run")
    monkeypatch.setenv("ROLLOUT_MODE", "argo")
    monkeypatch.setenv("KUBECONFIG", str(tmp_path / "dummy"))
    rc = subprocess.call(
        ["bash", "-c", "pipeline/release/promote.sh"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    assert rc != 0


@pytest.mark.skip(reason="Requires kubectl/argo in CI environment")
def test_rbac_promote_allowed(monkeypatch):
    monkeypatch.setenv("DECISIONOS_ALLOW_SCOPES", "judge:run,deploy:promote")
    rc = subprocess.call(["bash", "-c", "pipeline/release/promote.sh"])
    assert rc == 0
