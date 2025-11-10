from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from packages.common.config import settings


@dataclass
class TenantConfig:
    tenant_id: str
    name: str
    ip_allowlist: List[str]
    rbac_map: Dict[str, List[str]]
    budgets: Dict[str, Any]
    secrets_path: Optional[str] = None


_TENANT: Optional[TenantConfig] = None


def _resolve_config_path() -> Path:
    p = Path(settings.tenant_config_path)
    if p.exists():
        return p
    # try repo base
    base = Path(__file__).resolve().parents[2]
    q = base / settings.tenant_config_path
    if q.exists():
        return q
    raise FileNotFoundError(str(p))


def load_tenant() -> TenantConfig:
    global _TENANT
    if _TENANT is not None:
        return _TENANT
    p = _resolve_config_path()
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    _TENANT = TenantConfig(
        tenant_id=str(data.get("tenant_id", "dev-tenant")),
        name=str(data.get("name", "Dev Tenant")),
        ip_allowlist=list(data.get("ip_allowlist", [])),
        rbac_map=dict(data.get("rbac_map", {})),
        budgets=dict(data.get("budgets", {})),
        secrets_path=data.get("secrets_path"),
    )
    return _TENANT


def get_tenant() -> TenantConfig:
    return load_tenant()
