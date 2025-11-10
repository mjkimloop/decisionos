import json
from pathlib import Path

import jsonschema


BASE = Path(__file__).resolve().parents[1]
CONTRACT = BASE / "packages" / "contracts" / "lead_triage.contract.json"
SCHEMA = BASE / "packages" / "schemas" / "decision_contract.schema.json"


def test_contract_has_schema_version_and_is_valid():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    # 필수 메타 필드 존재 확인
    assert "$schema" in data
    assert data.get("schema_version") == "v1"
    assert isinstance(data.get("version"), str)

    # JSON Schema로 교차 검증
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=data, schema=schema)

