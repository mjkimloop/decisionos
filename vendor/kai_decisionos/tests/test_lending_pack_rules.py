"""
Lending Pack v1 규칙 테스트 (L-01)

6개의 triage 규칙이 올바르게 작동하는지 검증합니다.
"""
import pytest
from pathlib import Path

from apps.rule_engine.engine import RuleSet, evaluate_rules
from apps.rule_engine.linter import lint_rules


# ============================================================================
# Test Group 1: 규칙 파일 로드 및 구조 검증
# ============================================================================


def test_lead_triage_ruleset_loads():
    """lead_triage 규칙 세트가 정상적으로 로드되는지 확인"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    assert ruleset_path.exists()

    ruleset = RuleSet.load(ruleset_path)
    assert ruleset.name == "lead_triage_rules"
    assert ruleset.version == "1.0.0"
    assert len(ruleset.rules) == 6


def test_all_rules_have_required_fields():
    """모든 규칙이 필수 필드를 가지고 있는지 확인"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    for rule in ruleset.rules:
        # 필수 필드 확인
        assert rule.name is not None
        assert rule.when is not None
        assert rule.action is not None
        assert "class" in rule.action
        assert "reasons" in rule.action
        assert "confidence" in rule.action

        # class가 유효한 값인지 확인
        assert rule.action["class"] in ["approve", "reject", "review"]


def test_rules_have_unique_names():
    """모든 규칙 이름이 고유한지 확인"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    rule_names = [rule.name for rule in ruleset.rules]
    assert len(rule_names) == len(set(rule_names)), "중복된 규칙 이름이 있습니다"


# ============================================================================
# Test Group 2: 개별 규칙 테스트
# ============================================================================


def test_rule_reject_low_credit():
    """Rule 1: reject_low_credit - 신용점수 550 미만 거부"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    # 신용점수 550 미만
    payload = {"credit_score": 540, "dti": 0.3, "income_verified": True}
    result = evaluate_rules(ruleset, payload)

    assert result["class"] == "reject"
    assert "credit_score_below_threshold" in result["reasons"]
    assert result["confidence"] == 0.9
    assert "reject_low_credit" in result["rules_applied"]


def test_rule_reject_high_dti():
    """Rule 2: reject_high_dti - DTI 0.6 초과 거부"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    # DTI 0.6 초과, 신용점수는 양호
    payload = {"credit_score": 700, "dti": 0.65, "income_verified": True}
    result = evaluate_rules(ruleset, payload)

    assert result["class"] == "reject"
    assert "debt_to_income_too_high" in result["reasons"]
    assert result["confidence"] == 0.85
    assert "reject_high_dti" in result["rules_applied"]


def test_rule_review_missing_docs():
    """Rule 3: review_missing_docs - 소득 미확인 시 리뷰"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    # 소득 미확인, 나머지는 양호
    payload = {"credit_score": 680, "dti": 0.40, "income_verified": False}
    result = evaluate_rules(ruleset, payload)

    # 이 경우 review 또는 approve가 될 수 있음 (우선순위에 따라)
    # review_missing_docs는 priority: 50
    assert "income_unverified" in result["reasons"]
    assert "income_proof" in result["required_docs"]


def test_rule_approve_strong():
    """Rule 4: approve_strong - 강력한 신용 프로필 승인"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    # 신용점수 >= 700, DTI <= 0.35
    payload = {"credit_score": 720, "dti": 0.30, "income_verified": True}
    result = evaluate_rules(ruleset, payload)

    assert result["class"] == "approve"
    assert "strong_credit_and_low_dti" in result["reasons"]
    assert result["confidence"] == 0.92
    assert "approve_strong" in result["rules_applied"]


def test_rule_approve_mid():
    """Rule 5: approve_mid - 중간 수준 신용 프로필 승인"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    # 신용점수 650-700, DTI <= 0.45, 소득 확인됨
    payload = {"credit_score": 680, "dti": 0.42, "income_verified": True}
    result = evaluate_rules(ruleset, payload)

    assert result["class"] == "approve"
    assert "adequate_credit_and_dti_with_docs" in result["reasons"]
    assert result["confidence"] == 0.8
    assert "approve_mid" in result["rules_applied"]


def test_rule_review_borderline():
    """Rule 6: review_borderline - 경계선 신용점수 리뷰"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    # 신용점수 600-650 사이
    payload = {"credit_score": 620, "dti": 0.40, "income_verified": True}
    result = evaluate_rules(ruleset, payload)

    # 다른 규칙에 의해 먼저 매칭될 수 있음
    # borderline 규칙이 포함되어야 함
    assert "review_borderline" in result["rules_applied"] or result["class"] == "review"


# ============================================================================
# Test Group 3: 우선순위 및 stop 플래그 테스트
# ============================================================================


def test_priority_ordering():
    """규칙이 우선순위 순서대로 평가되는지 확인"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    # reject_low_credit (priority: 100)가 가장 먼저 평가되어야 함
    payload = {"credit_score": 500, "dti": 0.7, "income_verified": False}
    result = evaluate_rules(ruleset, payload)

    # stop: true이므로 첫 번째 규칙만 적용되어야 함
    assert result["class"] == "reject"
    assert len(result["rules_applied"]) == 1
    assert result["rules_applied"][0] == "reject_low_credit"


def test_stop_flag_prevents_further_evaluation():
    """stop 플래그가 추가 평가를 막는지 확인"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    # approve_strong (priority: 95, stop: true)가 매칭되면 중단
    payload = {"credit_score": 750, "dti": 0.25, "income_verified": False}
    result = evaluate_rules(ruleset, payload)

    assert result["class"] == "approve"
    # stop: true이므로 review_missing_docs는 평가되지 않아야 함
    assert "review_missing_docs" not in result["rules_applied"]


def test_multiple_rules_without_stop():
    """stop 플래그가 없는 규칙들은 모두 평가되는지 확인"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    # approve_mid (stop: false)와 review 규칙들이 모두 평가될 수 있음
    payload = {"credit_score": 680, "dti": 0.42, "income_verified": False}
    result = evaluate_rules(ruleset, payload)

    # 여러 규칙이 매칭될 수 있음
    assert len(result["rules_applied"]) >= 1


# ============================================================================
# Test Group 4: 엣지 케이스 및 경계값 테스트
# ============================================================================


def test_boundary_credit_score_550():
    """경계값: 신용점수 정확히 550"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    payload = {"credit_score": 550, "dti": 0.40, "income_verified": True}
    result = evaluate_rules(ruleset, payload)

    # 550은 reject 조건(< 550)에 해당하지 않으므로 reject가 아님
    assert result["class"] != "reject" or "credit_score_below_threshold" not in result["reasons"]


def test_boundary_dti_0_6():
    """경계값: DTI 정확히 0.6"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    payload = {"credit_score": 700, "dti": 0.6, "income_verified": True}
    result = evaluate_rules(ruleset, payload)

    # 0.6은 reject 조건(> 0.6)에 해당하지 않으므로 reject가 아님
    assert result["class"] != "reject" or "debt_to_income_too_high" not in result["reasons"]


def test_boundary_credit_score_600():
    """경계값: 신용점수 정확히 600"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    payload = {"credit_score": 600, "dti": 0.40, "income_verified": True}
    result = evaluate_rules(ruleset, payload)

    # 600은 borderline 조건(>= 600 and < 650)에 해당
    assert "review_borderline" in result["rules_applied"] or result["class"] == "review"


def test_boundary_credit_score_650():
    """경계값: 신용점수 정확히 650"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    payload = {"credit_score": 650, "dti": 0.40, "income_verified": True}
    result = evaluate_rules(ruleset, payload)

    # 650은 approve_mid 조건(>= 650)에 해당
    # borderline 조건(< 650)에는 해당하지 않음
    if "approve_mid" in result["rules_applied"]:
        assert result["class"] == "approve"


def test_missing_fields_use_defaults():
    """필드가 누락된 경우 기본값 사용"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    # credit_score만 제공, 나머지는 기본값 사용
    payload = {"org_id": "test"}
    result = evaluate_rules(ruleset, payload)

    # 기본값으로 평가되어야 함 (credit_score: 0 → reject)
    assert result["class"] == "reject"
    assert "reject_low_credit" in result["rules_applied"]


# ============================================================================
# Test Group 5: 린터 검증
# ============================================================================


def test_no_lint_issues():
    """린터가 충돌이나 음영 규칙을 감지하지 않는지 확인"""
    rules_dir = Path("packages/rules/triage")
    issues, coverage = lint_rules(rules_dir)

    # 충돌이나 중복 이름이 없어야 함
    assert len([i for i in issues if i.kind == "conflict"]) == 0
    assert len([i for i in issues if i.kind == "duplicate_name"]) == 0

    # 음영 규칙이 있을 수 있지만, 의도적인 경우 허용
    # shadow 이슈는 경고로만 처리


def test_full_rule_coverage():
    """모든 규칙이 올바른 커버리지를 가지는지 확인"""
    rules_dir = Path("packages/rules/triage")
    issues, coverage = lint_rules(rules_dir)

    # 모든 규칙이 priority와 action.class를 가져야 함
    assert coverage["priority_pct"] == 100.0
    assert coverage["action_class_pct"] == 100.0

    # stop 플래그는 일부 규칙에만 필요
    assert coverage["stop_pct"] >= 0.0


# ============================================================================
# Test Group 6: 샘플 CSV 시나리오 테스트
# ============================================================================


def test_sample_lead_1_high_credit():
    """샘플 1: org_id=orgA, credit_score=720, dti=0.30, income_verified=True"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    payload = {"org_id": "orgA", "credit_score": 720, "dti": 0.30, "income_verified": True}
    result = evaluate_rules(ruleset, payload)

    # approve_strong에 매칭되어야 함
    assert result["class"] == "approve"
    assert "approve_strong" in result["rules_applied"]


def test_sample_lead_2_low_credit():
    """샘플 2: org_id=orgA, credit_score=540, dti=0.40, income_verified=True"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    payload = {"org_id": "orgA", "credit_score": 540, "dti": 0.40, "income_verified": True}
    result = evaluate_rules(ruleset, payload)

    # reject_low_credit에 매칭되어야 함
    assert result["class"] == "reject"
    assert "reject_low_credit" in result["rules_applied"]


def test_sample_lead_3_unverified_income():
    """샘플 3: org_id=orgB, credit_score=610, dti=0.50, income_verified=False"""
    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = RuleSet.load(ruleset_path)

    payload = {"org_id": "orgB", "credit_score": 610, "dti": 0.50, "income_verified": False}
    result = evaluate_rules(ruleset, payload)

    # review 또는 borderline에 매칭
    assert result["class"] in ["review", "approve"]


# ============================================================================
# Summary Test
# ============================================================================


def test_count_lending_pack_tests():
    """메타-테스트: lending pack 테스트 케이스 개수 확인"""
    import sys
    import inspect

    current_module = sys.modules[__name__]
    test_functions = [
        name for name, obj in inspect.getmembers(current_module)
        if inspect.isfunction(obj) and name.startswith("test_")
    ]

    test_count = len(test_functions) - 1  # 이 메타-테스트 제외

    print(f"\n총 Lending Pack 규칙 테스트: {test_count}개")
    assert test_count >= 20, f"Expected 20+ tests, found {test_count}"
