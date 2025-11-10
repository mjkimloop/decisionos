from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import ValidationError

from .schema import LintIssue, PackSpec
from .linter import lint_spec


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]
    spec: PackSpec | None = None


def load_pack_file(path: Path) -> PackSpec:
    text = path.read_text(encoding="utf-8")
    data: Dict[str, Any]
    if path.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    return PackSpec.model_validate(data)


def validate_spec(spec: PackSpec) -> ValidationResult:
    issues = lint_spec(spec)
    errors = [i.message if not i.subject else f"{i.message}: {i.subject}" for i in issues if i.level == "error"]
    warnings = [i.message if not i.subject else f"{i.message}: {i.subject}" for i in issues if i.level == "warning"]
    infos = [i.message if not i.subject else f"{i.message}: {i.subject}" for i in issues if i.level == "info"]
    return ValidationResult(valid=not errors, errors=errors, warnings=warnings, info=infos, spec=spec)


def validate_pack_file(path: Path) -> ValidationResult:
    try:
        spec = load_pack_file(path)
    except ValidationError as exc:
        return ValidationResult(valid=False, errors=[str(exc)], warnings=[], info=[], spec=None)
    except Exception as exc:  # noqa: BLE001 simple scaffold
        return ValidationResult(valid=False, errors=[f"load_error: {exc}"], warnings=[], info=[], spec=None)
    return validate_spec(spec)


__all__ = ["ValidationResult", "load_pack_file", "validate_spec", "validate_pack_file"]

