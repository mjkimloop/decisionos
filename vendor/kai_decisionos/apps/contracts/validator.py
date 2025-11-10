from __future__ import annotations

from typing import Dict, Any

from .schema import ContractSchema


def validate_payload(schema: ContractSchema, payload: Dict[str, Any], kind: str = "input") -> list[str]:
    required = schema.input_schema.get("required", []) if kind == "input" else schema.output_schema.get("required", [])
    errors: list[str] = []
    for field in required:
        if field not in payload:
            errors.append(f"missing field: {field}")
    return errors


__all__ = ["validate_payload"]
