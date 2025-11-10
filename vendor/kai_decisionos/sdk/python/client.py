from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class ExtensionsClient:
    def __init__(self, base_url: str, api_key: str, role: str = "admin", tenant: str = "demo-tenant") -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-Api-Key": api_key,
            "X-Role": role,
            "X-Tenant-ID": tenant,
        }

    def install(self, org_id: str, artifact_ref: str, signature: str, manifest: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "org_id": org_id,
            "artifact_ref": artifact_ref,
            "signature": signature,
            "manifest": manifest,
        }
        with httpx.Client(timeout=15, headers=self.headers) as client:
            resp = client.post(f"{self.base_url}/api/v1/ext/install", json=payload)
            resp.raise_for_status()
            return resp.json()

    def enable(self, org_id: str, name: str, version: str) -> Dict[str, Any]:
        payload = {"org_id": org_id, "name": name, "version": version}
        with httpx.Client(timeout=10, headers=self.headers) as client:
            resp = client.post(f"{self.base_url}/api/v1/ext/enable", json=payload)
            resp.raise_for_status()
            return resp.json()

    def disable(self, org_id: str, name: str) -> Dict[str, Any]:
        payload = {"org_id": org_id, "name": name}
        with httpx.Client(timeout=10, headers=self.headers) as client:
            resp = client.post(f"{self.base_url}/api/v1/ext/disable", json=payload)
            resp.raise_for_status()
            return resp.json()

    def list(self, org_id: str) -> Dict[str, Any]:
        with httpx.Client(timeout=10, headers=self.headers) as client:
            resp = client.get(f"{self.base_url}/api/v1/ext/list", params={"org_id": org_id})
            resp.raise_for_status()
            return resp.json()


__all__ = ["ExtensionsClient"]
