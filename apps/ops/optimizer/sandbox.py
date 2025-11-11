from __future__ import annotations
import json, os
from typing import Dict

def write_sandbox_catalog(base_catalog_path: str,
                          suggested_weights: Dict[str, float],
                          out_path: str = "var/sandbox/label_catalog.sandbox.json") -> str:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cat = json.load(open(base_catalog_path, "r", encoding="utf-8"))
    for g in cat.get("groups", {}):
        if g in suggested_weights:
            cat["groups"][g]["weight"] = float(suggested_weights[g])
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)
    return out_path
