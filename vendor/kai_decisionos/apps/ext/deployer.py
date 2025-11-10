from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from apps.ext.models import ExtensionManifest, ExtensionInstall
from apps.ext.registry.oci import REGISTRY, Artifact
from apps.ext.signing.verify import verify_signature


INSTALLS: Dict[tuple[str, str], ExtensionInstall] = {}


def _artifact_manifest(artifact: Artifact, manifest_data: dict | None) -> ExtensionManifest:
    data = manifest_data or artifact.metadata.get("manifest") or {}
    base = {
        "name": artifact.name,
        "version": artifact.version,
        "type": data.get("type", artifact.metadata.get("type", "decision")),
        "entrypoint": data.get("entrypoint", artifact.metadata.get("entrypoint", "extension:handle")),
        "permissions": data.get("permissions", artifact.metadata.get("permissions", [])),
        "runtime": data.get("runtime", artifact.metadata.get("runtime", "python-3.11")),
        "resources": data.get("resources", artifact.metadata.get("resources", {})),
        "network": data.get("network", artifact.metadata.get("network", {})),
        "secrets": data.get("secrets", artifact.metadata.get("secrets", [])),
        "compat": data.get("compat", artifact.metadata.get("compat", {})),
        "config": data.get("config", artifact.metadata.get("config", {})),
    }
    return ExtensionManifest(**base)


def install_extension(
    *,
    org_id: str,
    artifact_ref: str,
    signature: str,
    manifest: dict | None = None,
    channel: str | None = None,
) -> ExtensionInstall:
    artifact = REGISTRY.get(artifact_ref)
    if not verify_signature(Path(artifact.path), signature):
        raise ValueError("signature_invalid")
    ext_manifest = _artifact_manifest(artifact, manifest)
    install = ExtensionInstall(
        org_id=org_id,
        artifact_ref=artifact_ref,
        manifest=ext_manifest,
        channel=channel or artifact.metadata.get("channel", artifact.channel),
    )
    INSTALLS[(org_id, ext_manifest.name)] = install
    return install


def enable_extension(org_id: str, name: str, version: str) -> ExtensionInstall:
    install = _require_install(org_id, name)
    if install.manifest.version != version:
        raise ValueError("version_mismatch")
    install.enabled = True
    if not install.enabled_at:
        install.enabled_at = datetime.now(timezone.utc).isoformat()
    INSTALLS[(org_id, name)] = install
    return install


def disable_extension(org_id: str, name: str) -> ExtensionInstall:
    install = _require_install(org_id, name)
    install.enabled = False
    INSTALLS[(org_id, name)] = install
    return install


def list_extensions(org_id: str) -> List[ExtensionInstall]:
    return [install for (oid, _), install in INSTALLS.items() if oid == org_id]


def clear_installations() -> None:
    INSTALLS.clear()


def _require_install(org_id: str, name: str) -> ExtensionInstall:
    key = (org_id, name)
    if key not in INSTALLS:
        raise KeyError("extension_not_installed")
    return INSTALLS[key]


__all__ = [
    "install_extension",
    "enable_extension",
    "disable_extension",
    "list_extensions",
    "clear_installations",
]
