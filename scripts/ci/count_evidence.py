#!/usr/bin/env python3
"""Count evidence entries from index."""
import json
from pathlib import Path

try:
    data = json.loads(Path("var/evidence/index.json").read_text())
    print(data.get("count", 0))
except Exception:
    print("n/a")
