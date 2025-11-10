"""
Test sample data validity

Ensures all sample files are properly formatted and usable.
"""
import json
import csv
from pathlib import Path
import pytest


# ============================================================================
# Offline Eval Sample CSV Tests
# ============================================================================


def test_offline_eval_sample_exists():
    """offline_eval.sample.csv exists"""
    csv_path = Path("packages/samples/offline_eval.sample.csv")
    assert csv_path.exists(), "offline_eval.sample.csv not found"


def test_offline_eval_sample_structure():
    """offline_eval.sample.csv has correct columns"""
    csv_path = Path("packages/samples/offline_eval.sample.csv")

    with csv_path.open(encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        required_columns = [
            "employment_type",
            "income_monthly",
            "property_type",
            "region",
            "estimated_value",
            "senior_loan_amt",
            "target_amt",
            "purpose",
            "label"
        ]

        for col in required_columns:
            assert col in headers, f"Missing column: {col}"


def test_offline_eval_sample_has_data():
    """offline_eval.sample.csv has at least 10 rows"""
    csv_path = Path("packages/samples/offline_eval.sample.csv")

    with csv_path.open(encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 10, f"Expected at least 10 rows, found {len(rows)}"


def test_offline_eval_sample_label_values():
    """offline_eval.sample.csv labels are 0 or 1"""
    csv_path = Path("packages/samples/offline_eval.sample.csv")

    with csv_path.open(encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            label = row.get("label", "").strip()
            assert label in ["0", "1"], f"Row {i}: Invalid label '{label}'"


def test_offline_eval_sample_numeric_fields():
    """offline_eval.sample.csv numeric fields are valid"""
    csv_path = Path("packages/samples/offline_eval.sample.csv")

    numeric_fields = [
        "income_monthly",
        "estimated_value",
        "senior_loan_amt",
        "target_amt"
    ]

    with csv_path.open(encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            for field in numeric_fields:
                value = row.get(field, "").strip()
                try:
                    int(value)
                except ValueError:
                    pytest.fail(f"Row {i}: '{field}' is not numeric: {value}")


# ============================================================================
# Lead Triage Request Samples Tests
# ============================================================================


def test_lead_triage_requests_exist():
    """10 lead_triage request samples exist"""
    requests_dir = Path("packages/samples/requests")

    for i in range(1, 11):
        filename = f"lead_triage_{i:02d}_*.json"
        matching_files = list(requests_dir.glob(filename))
        assert len(matching_files) > 0, f"Missing lead_triage request {i:02d}"


def test_lead_triage_requests_valid_json():
    """All lead_triage requests are valid JSON"""
    requests_dir = Path("packages/samples/requests")
    request_files = sorted(requests_dir.glob("lead_triage_*.json"))

    assert len(request_files) >= 10, f"Expected 10+ files, found {len(request_files)}"

    for file_path in request_files:
        try:
            with file_path.open(encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"{file_path.name} is not valid JSON: {e}")


def test_lead_triage_requests_structure():
    """All lead_triage requests have required fields"""
    requests_dir = Path("packages/samples/requests")
    request_files = sorted(requests_dir.glob("lead_triage_*.json"))

    for file_path in request_files:
        with file_path.open(encoding='utf-8') as f:
            data = json.load(f)

        # Check top-level structure
        assert "org_id" in data, f"{file_path.name}: Missing 'org_id'"
        assert "payload" in data, f"{file_path.name}: Missing 'payload'"

        # Check payload structure
        payload = data["payload"]
        assert "credit_score" in payload, f"{file_path.name}: Missing 'credit_score'"
        assert "dti" in payload, f"{file_path.name}: Missing 'dti'"
        assert "income_verified" in payload, f"{file_path.name}: Missing 'income_verified'"


def test_lead_triage_requests_field_types():
    """All lead_triage requests have correct field types"""
    requests_dir = Path("packages/samples/requests")
    request_files = sorted(requests_dir.glob("lead_triage_*.json"))

    for file_path in request_files:
        with file_path.open(encoding='utf-8') as f:
            data = json.load(f)

        # Check types
        assert isinstance(data["org_id"], str), f"{file_path.name}: org_id must be string"

        payload = data["payload"]
        assert isinstance(payload["credit_score"], int), f"{file_path.name}: credit_score must be int"
        assert isinstance(payload["dti"], (int, float)), f"{file_path.name}: dti must be numeric"
        assert isinstance(payload["income_verified"], bool), f"{file_path.name}: income_verified must be bool"


def test_lead_triage_requests_credit_score_range():
    """credit_score values are in reasonable range (300-850)"""
    requests_dir = Path("packages/samples/requests")
    request_files = sorted(requests_dir.glob("lead_triage_*.json"))

    for file_path in request_files:
        with file_path.open(encoding='utf-8') as f:
            data = json.load(f)

        credit_score = data["payload"]["credit_score"]
        assert 300 <= credit_score <= 850, \
            f"{file_path.name}: credit_score {credit_score} out of range [300, 850]"


def test_lead_triage_requests_dti_range():
    """DTI values are in reasonable range (0-2.0)"""
    requests_dir = Path("packages/samples/requests")
    request_files = sorted(requests_dir.glob("lead_triage_*.json"))

    for file_path in request_files:
        with file_path.open(encoding='utf-8') as f:
            data = json.load(f)

        dti = data["payload"]["dti"]
        assert 0.0 <= dti <= 2.0, \
            f"{file_path.name}: dti {dti} out of range [0.0, 2.0]"


def test_lead_triage_requests_coverage():
    """Sample requests cover different decision outcomes"""
    requests_dir = Path("packages/samples/requests")
    request_files = sorted(requests_dir.glob("lead_triage_*.json"))

    # Check for diversity in credit scores
    credit_scores = []
    dtis = []
    income_verified = []

    for file_path in request_files:
        with file_path.open(encoding='utf-8') as f:
            data = json.load(f)

        payload = data["payload"]
        credit_scores.append(payload["credit_score"])
        dtis.append(payload["dti"])
        income_verified.append(payload["income_verified"])

    # Should have variety
    assert len(set(credit_scores)) >= 5, "Need more variety in credit_score values"
    assert len(set(dtis)) >= 5, "Need more variety in dti values"
    assert True in income_verified and False in income_verified, \
        "Need both verified and unverified income samples"


# ============================================================================
# Integration Test - Use Samples with Rule Engine
# ============================================================================


def test_evaluate_all_sample_requests():
    """All sample requests can be evaluated by rule engine"""
    from apps.rule_engine import load_ruleset, evaluate_rules

    ruleset_path = Path("packages/rules/triage/lead_triage.yaml")
    ruleset = load_ruleset(ruleset_path)

    requests_dir = Path("packages/samples/requests")
    request_files = sorted(requests_dir.glob("lead_triage_*.json"))

    results = []
    for file_path in request_files:
        with file_path.open(encoding='utf-8') as f:
            data = json.load(f)

        result = evaluate_rules(ruleset, data["payload"])
        results.append({
            "file": file_path.name,
            "class": result["class"],
            "rules_applied": result["rules_applied"]
        })

    # Should have at least one of each class
    classes = [r["class"] for r in results]
    assert "approve" in classes, "No approve decisions in samples"
    assert "reject" in classes, "No reject decisions in samples"


# ============================================================================
# Summary Test
# ============================================================================


def test_count_sample_data_tests():
    """Meta-test: count sample data test cases"""
    import sys
    import inspect

    current_module = sys.modules[__name__]
    test_functions = [
        name for name, obj in inspect.getmembers(current_module)
        if inspect.isfunction(obj) and name.startswith("test_")
    ]

    test_count = len(test_functions) - 1  # Exclude this meta-test

    print(f"\n총 샘플 데이터 테스트: {test_count}개")
    assert test_count >= 10, f"Expected 10+ tests, found {test_count}"
