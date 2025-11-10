from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from packages.common.config import settings
from apps.packs.schema import PackSpec
from apps.packs.validator import load_pack_file, validate_pack_file, validate_spec
from apps.packs.simulator import simulate_pack


router = APIRouter(prefix="/api/v1/packs", tags=["packs"])


class PackSimulationRequest(BaseModel):
    pack: PackSpec
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    label_key: str | None = None


def _candidate_dirs() -> List[Path]:
    root = Path(__file__).resolve().parents[3]
    candidates = [
        Path(settings.data_dir) / "packs",
        root / "packages" / "packs",
    ]
    resolved: List[Path] = []
    for cand in candidates:
        target = cand if cand.is_absolute() else (root / cand)
        if target.exists() and target not in resolved:
            resolved.append(target)
    return resolved


def _iter_pack_files() -> Iterable[Path]:
    for directory in _candidate_dirs():
        yield from directory.glob("*.yml")
        yield from directory.glob("*.yaml")
        yield from directory.glob("*.json")


@router.get("")
def list_packs() -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    for path in _iter_pack_files():
        result = validate_pack_file(path)
        item: Dict[str, Any] = {
            "path": str(path),
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        if result.spec:
            item.update(
                identifier=result.spec.identifier(),
                name=result.spec.meta.name,
                version=result.spec.meta.version,
                domain=result.spec.meta.domain,
            )
        items.append(item)
    return {"items": items}


@router.get("/{pack_name}")
def load_pack(pack_name: str) -> Dict[str, Any]:
    for path in _iter_pack_files():
        if path.stem == pack_name:
            spec = load_pack_file(path)
            return spec.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="pack not found")


@router.post("/validate")
def validate_pack(payload: Dict[str, Any]) -> Dict[str, Any]:
    spec = PackSpec.model_validate(payload.get("pack", payload))
    result = validate_spec(spec)
    return {
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "info": result.info,
        "identifier": spec.identifier(),
    }


@router.post("/simulate")
def simulate(request: PackSimulationRequest) -> Dict[str, Any]:
    result = simulate_pack(request.pack, request.rows, request.label_key)
    return result
