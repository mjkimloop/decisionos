import pytest
import json
import re

def _hex_ok(c):
    return bool(re.fullmatch(r"[0-9a-fA-F]{6}", c))

@pytest.mark.gate_q
def test_palette_colors_are_hex():
    catalog = json.load(open("configs/labels/label_catalog_v2.json","r",encoding="utf-8"))
    for _, meta in catalog.get("groups", {}).items():
        assert _hex_ok(meta["color"])
    for _, meta in catalog.get("labels", {}).items():
        assert _hex_ok(meta["color"])
