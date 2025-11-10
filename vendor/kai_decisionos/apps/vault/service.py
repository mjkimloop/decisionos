from __future__ import annotations

import json
from pathlib import Path


VAULT_PATH = Path("var/vault.json")


def _load() -> dict:
    if VAULT_PATH.exists():
        try:
            return json.loads(VAULT_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def set_secret(key: str, value: str) -> None:
    VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load()
    data[key] = value
    VAULT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_secret(key: str) -> str | None:
    return _load().get(key)

