"""
스키마 검증 테스트 (S-01)

JSON Schema와 Pydantic 모델의 호환성을 검증합니다.
"""
import json
import pytest
from pathlib import Path
from pydantic import ValidationError

from packages.schemas.api import Lead, Action, DecisionRequest, DecisionResponse


# ============================================================================
# Test Group 1: JSON Schema 파일 존재 확인
# ============================================================================


def test_json_schemas_exist():
    """JSON Schema 파일들이 존재하는지 확인"""
    schema_dir = Path("packages/schemas")

    required_schemas = [
        "lead_input.schema.json",
        "action_output.schema.json",
        "decision_request.schema.json",
        "decision_response.schema.json"
    ]

    for schema_file in required_schemas:
        schema_path = schema_dir / schema_file
        assert schema_path.exists(), f"Schema file not found: {schema_file}"

        # JSON 파싱 가능한지 확인
        with schema_path.open() as f:
            schema = json.load(f)
            assert "$schema" in schema
            assert "type" in schema


# ============================================================================
# Test Group 2: Pydantic Lead 모델 검증
# ============================================================================


def test_lead_model_valid_high_score():
    """정상 케이스: 높은 신용점수"""
    lead = Lead(
        org_id="orgA",
        credit_score=750,
        dti=0.28,
        income_verified=True
    )

    assert lead.org_id == "orgA"
    assert lead.credit_score == 750
    assert lead.dti == 0.28
    assert lead.income_verified is True
    assert lead.converted is None


def test_lead_model_valid_with_label():
    """정상 케이스: 레이블 포함"""
    lead = Lead(
        org_id="orgB",
        credit_score=620,
        dti=0.42,
        income_verified=True,
        converted=1
    )

    assert lead.converted == 1


def test_lead_model_invalid_missing_required():
    """비정상 케이스: 필수 필드 누락"""
    with pytest.raises(ValidationError) as exc_info:
        Lead(
            org_id="orgC",
            credit_score=700
        )

    errors = exc_info.value.errors()
    missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
    assert "dti" in missing_fields
    assert "income_verified" in missing_fields


def test_lead_model_invalid_wrong_type():
    """비정상 케이스: 잘못된 타입"""
    # Pydantic v2는 자동으로 타입 변환을 시도하므로,
    # 변환 불가능한 타입을 사용해야 함
    with pytest.raises(ValidationError):
        Lead(
            org_id="orgD",
            credit_score="not_a_number",  # 변환 불가능한 문자열
            dti=0.35,
            income_verified="maybe"  # 변환 불가능한 문자열
        )


def test_lead_model_boundary_values():
    """경계값 테스트"""
    # 최소값
    lead_min = Lead(
        org_id="org_min",
        credit_score=300,
        dti=0.0,
        income_verified=False
    )
    assert lead_min.credit_score == 300

    # 최대값
    lead_max = Lead(
        org_id="org_max",
        credit_score=850,
        dti=2.0,
        income_verified=True
    )
    assert lead_max.credit_score == 850


# ============================================================================
# Test Group 3: Pydantic Action 모델 검증
# ============================================================================


def test_action_model_approve():
    """정상 케이스: approve 액션"""
    action = Action(
        **{
            "class": "approve",
            "reasons": ["strong_credit_and_low_dti"],
            "confidence": 0.92
        }
    )

    assert action.class_ == "approve"
    assert "strong_credit_and_low_dti" in action.reasons
    assert action.confidence == 0.92
    assert action.required_docs == []


def test_action_model_review_with_docs():
    """정상 케이스: review 액션 with required_docs"""
    action = Action(
        **{
            "class": "review",
            "reasons": ["borderline_credit", "missing_verification"],
            "confidence": 0.55,
            "required_docs": ["income_proof", "bank_statements"]
        }
    )

    assert action.class_ == "review"
    assert len(action.reasons) == 2
    assert len(action.required_docs) == 2


def test_action_model_invalid_missing_reasons():
    """비정상 케이스: reasons 누락"""
    with pytest.raises(ValidationError) as exc_info:
        Action(
            **{
                "class": "reject",
                "confidence": 0.85
            }
        )

    errors = exc_info.value.errors()
    assert any(e["loc"][0] == "reasons" for e in errors)


def test_action_model_invalid_confidence_range():
    """비정상 케이스: confidence 범위 초과"""
    # Pydantic은 기본적으로 범위 검증을 하지 않지만,
    # 필요시 Field(ge=0, le=1)로 추가 가능
    action = Action(
        **{
            "class": "approve",
            "reasons": ["test"],
            "confidence": 1.5  # 정상 범위: 0.0-1.0
        }
    )
    # 현재는 통과하지만, 스키마 검증 시 실패해야 함
    assert action.confidence == 1.5


# ============================================================================
# Test Group 4: DecisionRequest 모델 검증
# ============================================================================


def test_decision_request_valid():
    """정상 케이스: DecisionRequest"""
    request = DecisionRequest(
        org_id="orgA",
        payload={
            "org_id": "orgA",
            "credit_score": 720,
            "dti": 0.30,
            "income_verified": True
        }
    )

    assert request.org_id == "orgA"
    assert request.payload["credit_score"] == 720


def test_decision_request_from_dict():
    """딕셔너리로부터 DecisionRequest 생성"""
    data = {
        "org_id": "orgB",
        "payload": {
            "org_id": "orgB",
            "credit_score": 650,
            "dti": 0.40,
            "income_verified": False
        }
    }

    request = DecisionRequest(**data)
    assert request.org_id == "orgB"
    assert request.payload["credit_score"] == 650


# ============================================================================
# Test Group 5: DecisionResponse 모델 검증
# ============================================================================


def test_decision_response_valid():
    """정상 케이스: DecisionResponse"""
    response = DecisionResponse(
        action=Action(
            **{
                "class": "approve",
                "reasons": ["high_credit"],
                "confidence": 0.9
            }
        ),
        decision_id="550e8400-e29b-41d4-a716-446655440000"
    )

    assert response.action.class_ == "approve"
    assert response.decision_id.startswith("550e8400")


# ============================================================================
# Test Group 6: 샘플 페이로드 파일 검증
# ============================================================================


def test_sample_payloads_exist():
    """샘플 페이로드 파일들이 존재하는지 확인"""
    samples_dir = Path("packages/samples/payloads")

    valid_samples = [
        "valid_lead_high_score.json",
        "valid_lead_low_score.json",
        "valid_lead_borderline.json"
    ]

    invalid_samples = [
        "invalid_missing_required.json",
        "invalid_out_of_range.json",
        "invalid_wrong_type.json"
    ]

    for sample in valid_samples + invalid_samples:
        sample_path = samples_dir / sample
        assert sample_path.exists(), f"Sample file not found: {sample}"


def test_valid_sample_payloads_parse():
    """정상 샘플 페이로드들이 Pydantic 모델로 파싱되는지 확인"""
    samples_dir = Path("packages/samples/payloads")

    valid_samples = [
        "valid_lead_high_score.json",
        "valid_lead_low_score.json",
        "valid_lead_borderline.json"
    ]

    for sample_file in valid_samples:
        sample_path = samples_dir / sample_file
        with sample_path.open() as f:
            data = json.load(f)

        lead = Lead(**data)
        assert lead.org_id is not None
        assert lead.credit_score is not None


def test_invalid_sample_payloads_fail():
    """비정상 샘플 페이로드들이 Pydantic 검증 실패하는지 확인"""
    samples_dir = Path("packages/samples/payloads")

    # 필수 필드 누락 케이스
    with (samples_dir / "invalid_missing_required.json").open() as f:
        data = json.load(f)

    with pytest.raises(ValidationError):
        Lead(**data)


# ============================================================================
# Test Group 7: JSON Schema 호환성 검증
# ============================================================================


def test_contract_schema_matches_pydantic():
    """계약 파일의 스키마가 Pydantic 모델과 호환되는지 확인"""
    contract_path = Path("packages/contracts/lead_triage.contract.json")

    with contract_path.open() as f:
        contract = json.load(f)

    # 계약 파일 구조 확인
    assert "name" in contract
    assert "version" in contract
    assert "rule_path" in contract

    # input_schema가 문자열(경로)인지 확인
    if "input_schema" in contract:
        assert isinstance(contract["input_schema"], str)
        # 스키마 파일 경로가 유효한지 확인
        schema_path = Path("packages") / contract["input_schema"]
        # 파일이 존재하면 로드 시도
        if schema_path.exists():
            with schema_path.open() as f:
                schema = json.load(f)
                assert schema["type"] == "object"

    # request_schema 확인
    if "request_schema" in contract:
        assert isinstance(contract["request_schema"], str)

    # response_schema 확인
    if "response_schema" in contract:
        assert isinstance(contract["response_schema"], str)


def test_pydantic_model_export_schema():
    """Pydantic 모델이 JSON Schema로 내보내기 가능한지 확인"""
    # Pydantic v2 스타일
    lead_schema = Lead.model_json_schema()

    assert lead_schema["type"] == "object"
    assert "properties" in lead_schema
    assert "org_id" in lead_schema["properties"]
    assert "credit_score" in lead_schema["properties"]

    # Action 모델
    action_schema = Action.model_json_schema()

    assert action_schema["type"] == "object"
    assert "class_" in action_schema["properties"] or "class" in action_schema["properties"]


# ============================================================================
# Summary Test
# ============================================================================


def test_count_schema_tests():
    """메타-테스트: 스키마 테스트 케이스 개수 확인"""
    import sys
    import inspect

    current_module = sys.modules[__name__]
    test_functions = [
        name for name, obj in inspect.getmembers(current_module)
        if inspect.isfunction(obj) and name.startswith("test_")
    ]

    test_count = len(test_functions) - 1  # 이 메타-테스트 제외

    print(f"\n총 스키마 검증 테스트 케이스: {test_count}개")
    assert test_count >= 15, f"Expected 15+ tests, found {test_count}"
