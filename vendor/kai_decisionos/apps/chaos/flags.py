from __future__ import annotations

import json
from pathlib import Path


FLAGS_PATH = Path("var/flags/chaos.json")


def _load() -> dict:
    if FLAGS_PATH.exists():
        try:
            return json.loads(FLAGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def is_enabled(key: str) -> bool:
    return bool(_load().get(key))


def set_flag(key: str, value: bool) -> None:
    FLAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _load()
    data[key] = bool(value)
    FLAGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

