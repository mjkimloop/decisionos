#!/usr/bin/env python
"""
PII Coverage Check - Verify tokenization coverage on fixture data.

Ensures at least 80% of detected PII patterns are tokenized.
"""
import json
import re
import os
from pathlib import Path

# Set token key
os.environ["DECISIONOS_PII_TOKEN_KEY"] = os.getenv("DECISIONOS_PII_TOKEN_KEY", "secret")

from apps.security.pii.redactor import redact_text

# Load configuration
cfg_path = Path("configs/pii/patterns_kr.json")
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

# Load fixture
fixture_path = Path("data/pii/fixture_kr.txt")
src = fixture_path.read_text(encoding="utf-8")

# Redact
red = redact_text(src, cfg)

# Count tokens
tokens = len(re.findall(r"TKN:[a-z_]+:", red))

# Count original PII patterns (approximate)
# Mobile phones, emails, resident IDs
finds = sum(1 for _ in re.finditer(
    r"(01[016789]-?\d{3,4}-?\d{4})|(@)|(\d{6}-\d{7})",
    src
))

# Calculate coverage ratio
ratio = tokens / max(1, finds)

print(f"Tokens: {tokens}")
print(f"Detected PII: {finds}")
print(f"Coverage: {ratio:.2%}")

if ratio < 0.8:
    print("❌ FAIL: Coverage below 80%")
    exit(1)
else:
    print("✅ PASS: Coverage >= 80%")
    exit(0)
