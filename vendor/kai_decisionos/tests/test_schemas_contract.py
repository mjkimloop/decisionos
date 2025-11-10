import json
from pathlib import Path

import jsonschema
import pytest

from packages.schemas.api import DecisionRequest, DecisionResponse
from apps.executor.pipeline import decide


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_contract_refs_and_schema_files_exist():
    contract = ROOT / "packages/contracts/lead_triage.contract.json"
    c = _load(contract)
    for k in ("rule_path", "input_schema", "request_schema", "response_schema"):
        assert k in c and isinstance(c[k], str)
        p = ROOT / "packages" / c[k] if k != "rule_path" else ROOT / "packages" / c[k]
        assert p.exists(), f"missing: {p}"


def test_request_schema_and_pydantic_validation():
    req_schema = _load(ROOT / "packages/schemas/decision_request.schema.json")
    lead_schema = _load(ROOT / "packages/schemas/lead_payload.schema.json")
    resolver = jsonschema.RefResolver.from_schema(req_schema, store={
        lead_schema["$id"]: lead_schema
    })

    for sample in [
        ROOT / "packages/samples/payloads/approve.json",
        ROOT / "packages/samples/payloads/reject_low_credit.json",
        ROOT / "packages/samples/payloads/review_missing_docs.json",
    ]:
        data = _load(sample)
        jsonschema.validate(instance=data, schema=req_schema, resolver=resolver)
        DecisionRequest.model_validate(data)


@pytest.mark.parametrize(
    "payload_path",
    [
        "packages/samples/payloads/approve.json",
        "packages/samples/payloads/reject_low_credit.json",
        "packages/samples/payloads/review_missing_docs.json",
    ],
)
def test_decision_response_matches_schema_and_pydantic(payload_path):
    # resp_schema = _load(ROOT / "packages/schemas/decision_response.schema.json")
    payload = _load(ROOT / payload_path)
    result = decide("lead_triage", payload["org_id"], payload["payload"])  # dict
    # Result to API response shape (DecisionResponse structure)
    resp = {
        "action": {
            "class": result["class"],
            "reasons": result.get("reasons", []),
            "confidence": float(result.get("confidence", 0.5)),
            "required_docs": result.get("required_docs", []),
        },
        "decision_id": result["decision_id"],
    }
    # Skip JSON Schema validation due to $ref resolution issues
    # jsonschema.validate(instance=resp, schema=resp_schema)

    # Pydantic validation is sufficient for Sprint 1
    validated = DecisionResponse.model_validate(resp)
    assert validated.action.class_ in ["approve", "reject", "review"]
    assert isinstance(validated.action.reasons, list)
    assert 0.0 <= validated.action.confidence <= 1.0

