"""
Prometheus 알람 YAML 스키마 검증 테스트

알람 규칙 파일의 YAML 구조와 필수 필드를 검증합니다.
"""
import yaml
from pathlib import Path


def test_alerts_yaml_valid_structure():
    """알람 YAML 파일이 유효한 구조를 가지는지 검증"""
    alert_file = Path("configs/alerts/cards_alerts.yml")
    assert alert_file.exists(), "Alert file must exist"

    with open(alert_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "groups" in data, "Must have groups field"
    assert isinstance(data["groups"], list), "groups must be a list"
    assert len(data["groups"]) > 0, "Must have at least one group"


def test_alerts_yaml_required_fields():
    """각 알람 규칙이 필수 필드를 포함하는지 검증"""
    alert_file = Path("configs/alerts/cards_alerts.yml")
    with open(alert_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for group in data["groups"]:
        assert "name" in group, "Group must have name"
        assert "rules" in group, "Group must have rules"

        for rule in group["rules"]:
            # 필수 필드
            assert "alert" in rule, "Rule must have alert name"
            assert "expr" in rule, "Rule must have expr (query)"
            assert "labels" in rule, "Rule must have labels"
            assert "annotations" in rule, "Rule must have annotations"

            # Labels 필수 필드
            labels = rule["labels"]
            assert "severity" in labels, "Must have severity label"
            assert labels["severity"] in ["info", "warning", "critical"], f"Invalid severity: {labels['severity']}"

            # Annotations 필수 필드
            annotations = rule["annotations"]
            assert "summary" in annotations, "Must have summary"
            assert "description" in annotations, "Must have description"


def test_alerts_yaml_expression_syntax():
    """알람 표현식이 기본 PromQL 구문을 따르는지 검증"""
    alert_file = Path("configs/alerts/cards_alerts.yml")
    with open(alert_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for group in data["groups"]:
        for rule in group["rules"]:
            expr = rule["expr"]
            # 기본 구문 검증 (rate, histogram_quantile 등 함수 사용)
            assert isinstance(expr, str), "expr must be a string"
            assert len(expr.strip()) > 0, "expr cannot be empty"

            # 메트릭 이름이 포함되어야 함
            assert "decisionos_" in expr, "expr should reference DecisionOS metrics"


def test_alerts_yaml_coverage():
    """필수 알람 규칙이 모두 정의되어 있는지 검증"""
    alert_file = Path("configs/alerts/cards_alerts.yml")
    with open(alert_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    alert_names = []
    for group in data["groups"]:
        for rule in group["rules"]:
            alert_names.append(rule["alert"])

    # 필수 알람 규칙
    required_alerts = [
        "CardsETagHitRateDropped",
        "HTTPRetryRateSpiked",
        "CardsP95LatencySpiked",
    ]

    for required in required_alerts:
        assert required in alert_names, f"Missing required alert: {required}"


def test_alerts_yaml_severity_distribution():
    """알람 심각도 분포가 적절한지 확인"""
    alert_file = Path("configs/alerts/cards_alerts.yml")
    with open(alert_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    severity_count = {"info": 0, "warning": 0, "critical": 0}

    for group in data["groups"]:
        for rule in group["rules"]:
            severity = rule["labels"]["severity"]
            severity_count[severity] += 1

    # 최소 1개의 critical, warning 알람이 있어야 함
    assert severity_count["critical"] >= 1, "Must have at least 1 critical alert"
    assert severity_count["warning"] >= 1, "Must have at least 1 warning alert"
