import json
import pathlib

import yaml


def validate_schema(data: dict, schema: dict):
    errors = []
    if "meta" not in data:
        errors.append("meta missing")
    else:
        for key in ("version", "date", "status", "summary"):
            if key not in data["meta"]:
                errors.append(f"meta.{key} missing")
    patches = data.get("patches", {})
    for key in ("techspec", "plan"):
        for item in patches.get(key, []) or []:
            if item.get("mode") not in ("replace", "append", "ensure"):
                errors.append("mode invalid")
            for field in ("section", "mode", "content"):
                if field not in item:
                    errors.append(f"{field} missing")
    return errors


def test_work_order_schema_valid():
    schema = json.loads(pathlib.Path("scripts/schemas/work_order.schema.json").read_text(encoding="utf-8"))
    assert schema["type"] == "object"
    wo = yaml.safe_load(pathlib.Path("docs/work_orders/wo-v0.1.2-gate-a-autodoc.yaml").read_text(encoding="utf-8"))
    errors = validate_schema(wo, schema)
    assert not errors


def test_work_order_schema_invalid_mode(tmp_path):
    bad = {
        "meta": {"version": "v0", "date": "2025-01-01", "status": "locked", "summary": ""},
        "patches": {"techspec": [{"section": "A", "mode": "bad", "content": "x"}]},
    }
    schema = json.loads(pathlib.Path("scripts/schemas/work_order.schema.json").read_text(encoding="utf-8"))
    errors = validate_schema(bad, schema)
    assert errors
