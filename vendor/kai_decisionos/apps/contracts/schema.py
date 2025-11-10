from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel


class ContractSchema(BaseModel):
    name: str
    version: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


def _maybe_load_schema(value: str | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    schema_path = Path(value)
    if not schema_path.is_absolute():
        schema_path = Path("packages") / value if not Path(value).exists() else Path(value)
    return json.loads(schema_path.read_text(encoding="utf-8"))


def load_contract(path: str | Path) -> ContractSchema:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    raw["input_schema"] = _maybe_load_schema(raw.get("input_schema", {}))
    raw["output_schema"] = _maybe_load_schema(raw.get("output_schema", {}))
    return ContractSchema.model_validate(raw)


__all__ = ["ContractSchema", "load_contract"]
