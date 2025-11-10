from __future__ import annotations

import time
from typing import Any, Callable, Dict

from ..security.egress_guard import NetworkPolicy, enforce_network_policy
from ..security.perm_model import PermissionSet, require_permissions
from ..security.secrets_vault import SecretsVault
from .limits import ResourceLimits, DEFAULT_LIMITS


class SandboxViolation(RuntimeError):
    pass


class SandboxRunner:
    def __init__(self, secrets: SecretsVault | None = None) -> None:
        self.secrets = secrets or SecretsVault()

    def execute(
        self,
        entrypoint: Callable[[dict, dict], Any],
        ctx: dict,
        manifest: Dict[str, Any],
        limits: ResourceLimits | None = None,
        permissions: PermissionSet | None = None,
        network: NetworkPolicy | None = None,
    ) -> Any:
        limits = limits or DEFAULT_LIMITS
        permissions = permissions or PermissionSet()
        self._validate_manifest(manifest, limits)
        require_permissions(permissions, manifest.get("permissions", []))
        enforce_network_policy(network or NetworkPolicy.deny_all(), manifest.get("network", {}))

        start = time.perf_counter()
        secrets_scope = self.secrets.issue_scope(manifest.get("secrets", []))
        sandbox_ctx = {
            **ctx,
            "trace_id": ctx.get("trace_id") or "trace-" + ctx.get("extension", "unknown"),
            "secrets": secrets_scope,
        }
        result = entrypoint(manifest.get("config", {}), sandbox_ctx)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms > limits.timeout_ms:
            raise SandboxViolation(f"timeout_exceeded:{elapsed_ms:.2f}ms")
        return result

    def _validate_manifest(self, manifest: Dict[str, Any], limits: ResourceLimits) -> None:
        resources = manifest.get("resources", {})
        if resources.get("cpu_ms", limits.cpu_ms) > limits.cpu_ms:
            raise SandboxViolation("cpu_limit_exceeded")
        if resources.get("mem_mb", limits.memory_mb) > limits.memory_mb:
            raise SandboxViolation("memory_limit_exceeded")
        if resources.get("tmp_mb", limits.tmp_mb) > limits.tmp_mb:
            raise SandboxViolation("tmp_limit_exceeded")


__all__ = ["SandboxRunner", "SandboxViolation"]
