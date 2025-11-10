import json
from pathlib import Path

import jsonschema
import pytest

from packages.schemas.api import Lead


BASE = Path(__file__).resolve().parents[1]
LEAD_SCHEMA = BASE / "packages" / "schemas" / "lead_payload.schema.json"


@pytest.fixture(scope="module")
def lead_jsonschema():
    return json.loads(LEAD_SCHEMA.read_text(encoding="utf-8"))


def _jsonschema_validate(schema: dict, payload: dict) -> bool:
    try:
        jsonschema.validate(instance=payload, schema=schema)
        return True
    except jsonschema.ValidationError:
        return False


def _pydantic_validate(payload: dict) -> bool:
    try:
        Lead(org_id="orgA", **payload)
        return True
    except Exception:
        return False


def test_valid_payload_passes_both(lead_jsonschema):
    payload = {"credit_score": 720, "dti": 0.35, "income_verified": True}
    assert _jsonschema_validate(lead_jsonschema, payload)
    assert _pydantic_validate(payload)


def test_invalid_payload_fails_both(lead_jsonschema):
    # credit_score 최대 850 초과, dti 범위 초과
    payload = {"credit_score": 900, "dti": 2.5, "income_verified": True}
    assert not _jsonschema_validate(lead_jsonschema, payload)
    assert not _pydantic_validate(payload)

