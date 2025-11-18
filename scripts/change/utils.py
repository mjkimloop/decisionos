from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def update_status(status_path: str, name: str, state: str, info: Dict[str, Any]) -> None:
    path = Path(status_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_json(path) or []
    data = [entry for entry in data if entry.get("name") != name]
    data.append({"name": name, "state": state, "info": info})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_reason(reason_path: str, code: str, message: str) -> None:
    path = Path(reason_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_json(path) or []
    if isinstance(data, dict):
        # legacy format single object
        data = [data]
    data.append({"code": code, "message": message, "count": 1})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_csv(value: str) -> List[str]:
    tokens: List[str] = []
    for chunk in value.replace(",", " ").split():
        chunk = chunk.strip()
        if chunk:
            tokens.append(chunk)
    return tokens
