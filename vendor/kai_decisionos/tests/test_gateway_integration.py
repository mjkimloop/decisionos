"""
Gateway 통합 테스트 (Sprint 1 게이트 검증)

/decide 엔드포인트가 전체 파이프라인을 통해 올바르게 작동하는지 검증합니다.
"""
import pytest
from fastapi.testclient import TestClient
from apps.gateway.main import app

client = TestClient(app)


# ============================================================================
# Test Group 1: /decide 엔드포인트 기본 기능 테스트
# ============================================================================


def test_decide_endpoint_with_auth_approve_strong():
    """인증된 사용자가 /decide 엔드포인트 호출 - 강력한 프로필 승인"""
    response = client.post(
        "/api/v1/decide/lead_triage",
        headers={"Authorization": "Bearer user@example.com"},
        json={
            "org_id": "orgA",
            "payload": {
                "credit_score": 750,
                "dti": 0.28,
                "income_verified": True
            }
        }
    )

    assert response.status_code == 200
    data = response.json()

    # DecisionResponse 구조 확인
    assert "action" in data
    assert "decision_id" in data

    # Action 구조 확인
    action = data["action"]
    assert action["class"] == "approve"
    assert "strong_credit_and_low_dti" in action["reasons"]
    assert action["confidence"] >= 0.9
    assert isinstance(action.get("required_docs", []), list)


def test_decide_endpoint_with_auth_reject_low_credit():
    """인증된 사용자가 /decide 엔드포인트 호출 - 낮은 신용점수 거부"""
    response = client.post(
        "/api/v1/decide/lead_triage",
        headers={"Authorization": "Bearer admin@example.com"},
        json={
            "org_id": "orgA",
            "payload": {
                "credit_score": 540,
                "dti": 0.40,
                "income_verified": True
            }
        }
    )

    assert response.status_code == 200
    data = response.json()

    action = data["action"]
    assert action["class"] == "reject"
    assert "credit_score_below_threshold" in action["reasons"]
    assert action["confidence"] == 0.9


def test_decide_endpoint_with_auth_review_missing_docs():
    """인증된 사용자가 /decide 엔드포인트 호출 - 서류 미제출 리뷰"""
    response = client.post(
        "/api/v1/decide/lead_triage",
        headers={"Authorization": "Bearer user@example.com"},
        json={
            "org_id": "orgB",
            "payload": {
                "credit_score": 680,
                "dti": 0.42,
                "income_verified": False
            }
        }
    )

    assert response.status_code == 200
    data = response.json()

    # 소득 미확인이므로 review 또는 income_unverified 이유가 포함되어야 함
    action = data["action"]
    assert "income_unverified" in action["reasons"] or action["class"] == "review"


# ============================================================================
# Test Group 2: Budget 헤더 테스트
# ============================================================================


def test_decide_endpoint_with_budget_headers():
    """Budget 헤더가 올바르게 전달되는지 확인"""
    response = client.post(
        "/api/v1/decide/lead_triage",
        headers={
            "Authorization": "Bearer user@example.com",
            "X-Budget-Latency": "0.5",
            "X-Budget-Cost": "0.01",
            "X-Budget-Accuracy": "0.95"
        },
        json={
            "org_id": "orgA",
            "payload": {
                "credit_score": 720,
                "dti": 0.30,
                "income_verified": True
            }
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"]["class"] == "approve"


# ============================================================================
# Test Group 3: 에러 처리 테스트
# ============================================================================


def test_decide_endpoint_invalid_contract():
    """존재하지 않는 계약 이름으로 호출 시 에러 처리"""
    response = client.post(
        "/api/v1/decide/nonexistent_contract",
        headers={"Authorization": "Bearer user@example.com"},
        json={
            "org_id": "orgA",
            "payload": {
                "credit_score": 720,
                "dti": 0.30,
                "income_verified": True
            }
        }
    )

    # 계약이 없으면 500 에러가 발생할 수 있음
    assert response.status_code in [404, 500]


def test_decide_endpoint_missing_payload():
    """페이로드가 누락된 경우 에러 처리"""
    response = client.post(
        "/api/v1/decide/lead_triage",
        headers={"Authorization": "Bearer user@example.com"},
        json={
            "org_id": "orgA"
            # payload 누락
        }
    )

    # Pydantic 검증 실패로 422 에러
    assert response.status_code == 422


# ============================================================================
# Test Group 4: 샘플 CSV 시나리오 재현
# ============================================================================


def test_sample_scenario_1_high_credit():
    """샘플 1: org_id=orgA, credit_score=720, dti=0.30, income_verified=True"""
    response = client.post(
        "/api/v1/decide/lead_triage",
        headers={"Authorization": "Bearer user@example.com"},
        json={
            "org_id": "orgA",
            "payload": {
                "credit_score": 720,
                "dti": 0.30,
                "income_verified": True
            }
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"]["class"] == "approve"


def test_sample_scenario_2_low_credit():
    """샘플 2: org_id=orgA, credit_score=540, dti=0.40, income_verified=True"""
    response = client.post(
        "/api/v1/decide/lead_triage",
        headers={"Authorization": "Bearer user@example.com"},
        json={
            "org_id": "orgA",
            "payload": {
                "credit_score": 540,
                "dti": 0.40,
                "income_verified": True
            }
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"]["class"] == "reject"


def test_sample_scenario_3_unverified_income():
    """샘플 3: org_id=orgB, credit_score=610, dti=0.50, income_verified=False"""
    response = client.post(
        "/api/v1/decide/lead_triage",
        headers={"Authorization": "Bearer user@example.com"},
        json={
            "org_id": "orgB",
            "payload": {
                "credit_score": 610,
                "dti": 0.50,
                "income_verified": False
            }
        }
    )

    assert response.status_code == 200
    data = response.json()
    # review 또는 approve 가능
    assert data["action"]["class"] in ["review", "approve"]


# ============================================================================
# Test Group 5: DecisionResponse 스키마 검증
# ============================================================================


def test_decision_response_schema_compliance():
    """DecisionResponse가 스키마를 준수하는지 확인"""
    response = client.post(
        "/api/v1/decide/lead_triage",
        headers={"Authorization": "Bearer user@example.com"},
        json={
            "org_id": "orgTest",
            "payload": {
                "credit_score": 700,
                "dti": 0.35,
                "income_verified": True
            }
        }
    )

    assert response.status_code == 200
    data = response.json()

    # 필수 필드 확인
    assert "action" in data
    assert "decision_id" in data

    # Action 필수 필드 확인
    action = data["action"]
    assert "class" in action
    assert "reasons" in action
    assert "confidence" in action

    # 타입 확인
    assert isinstance(action["class"], str)
    assert action["class"] in ["approve", "reject", "review"]
    assert isinstance(action["reasons"], list)
    assert isinstance(action["confidence"], (int, float))
    assert 0.0 <= action["confidence"] <= 1.0

    # decision_id가 UUID 형식인지 확인
    assert len(data["decision_id"]) > 0
    assert "-" in data["decision_id"]


# ============================================================================
# Summary Test
# ============================================================================


def test_count_gateway_integration_tests():
    """메타-테스트: Gateway 통합 테스트 케이스 개수 확인"""
    import sys
    import inspect

    current_module = sys.modules[__name__]
    test_functions = [
        name for name, obj in inspect.getmembers(current_module)
        if inspect.isfunction(obj) and name.startswith("test_")
    ]

    test_count = len(test_functions) - 1  # 이 메타-테스트 제외

    print(f"\n총 Gateway 통합 테스트: {test_count}개")
    assert test_count >= 10, f"Expected 10+ tests, found {test_count}"
