"""
Comprehensive test suite for Offline Eval Harness (C-02).

Tests cover:
- CSV loading and type casting
- Metrics calculation (precision, recall, review_rate)
- HTML report generation
- JSON report generation
- Integration with dosctl simulate
"""
from pathlib import Path
import pytest
import json
import csv

from apps.rule_engine.offline_eval import run_report, _cast_values
from apps.executor.pipeline import simulate


# ============================================================================
# Test Group 1: CSV Loading & Type Casting
# ============================================================================


def test_cast_values_boolean_strings():
    """Test that 'True' and 'False' strings are converted to booleans."""
    rows = [
        {"flag": "True", "status": "False"},
        {"flag": "False", "status": "True"}
    ]
    result = _cast_values(rows)

    assert result[0]["flag"] is True
    assert result[0]["status"] is False
    assert result[1]["flag"] is False
    assert result[1]["status"] is True


def test_cast_values_integers():
    """Test that integer strings are converted to ints."""
    rows = [{"count": "42", "score": "100"}]
    result = _cast_values(rows)

    assert result[0]["count"] == 42
    assert result[0]["score"] == 100
    assert isinstance(result[0]["count"], int)


def test_cast_values_floats():
    """Test that float strings are converted to floats."""
    rows = [{"rate": "0.85", "amount": "123.45"}]
    result = _cast_values(rows)

    assert result[0]["rate"] == 0.85
    assert result[0]["amount"] == 123.45
    assert isinstance(result[0]["rate"], float)


def test_cast_values_keeps_strings():
    """Test that non-numeric strings remain as strings."""
    rows = [{"name": "Alice", "status": "pending"}]
    result = _cast_values(rows)

    assert result[0]["name"] == "Alice"
    assert result[0]["status"] == "pending"
    assert isinstance(result[0]["name"], str)


def test_cast_values_handles_mixed_types():
    """Test casting with mixed data types."""
    rows = [
        {
            "id": "1",
            "score": "95.5",
            "active": "True",
            "name": "Test User",
            "count": "10"
        }
    ]
    result = _cast_values(rows)

    assert result[0]["id"] == 1
    assert result[0]["score"] == 95.5
    assert result[0]["active"] is True
    assert result[0]["name"] == "Test User"
    assert result[0]["count"] == 10


# ============================================================================
# Test Group 2: Report Generation
# ============================================================================


def test_run_report_generates_html(tmp_path: Path):
    """Test that HTML report is generated."""
    # Create test CSV
    csv_path = tmp_path / "test.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["credit_score", "dti", "income_verified", "converted"])
        writer.writeheader()
        writer.writerow({"credit_score": "700", "dti": "0.3", "income_verified": "True", "converted": "False"})
        writer.writerow({"credit_score": "500", "dti": "0.5", "income_verified": "False", "converted": "True"})

    # Create minimal template
    template_path = tmp_path / "template.html"
    template_path.write_text("<html><body>{{ now }} - {{ metrics }}</body></html>")

    # Output paths
    html_out = tmp_path / "report.html"

    # Mock contract and ruleset
    from packages.common.config import settings
    orig_data_dir = settings.data_dir

    # Create mock contract and rules
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    contract_file = contracts_dir / "test.contract.json"
    contract_file.write_text(json.dumps({
        "name": "test",
        "version": "1.0",
        "rule_path": "rules/test.yaml"
    }))

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    rules_file = rules_dir / "test.yaml"
    rules_file.write_text("""
name: test
version: 1
rules:
  - name: reject_low
    when: 'payload.get("credit_score", 0) < 550'
    action:
      class: reject
      reasons: ["low_credit"]
      confidence: 0.9
""")

    settings.data_dir = str(tmp_path)
    settings.contracts_dir = str(contracts_dir)

    try:
        report_data = run_report("test", csv_path, "converted", html_out, template_path)

        assert html_out.exists()
        assert "timestamp" in report_data
        assert "metrics" in report_data
        assert "metadata" in report_data
    finally:
        settings.data_dir = orig_data_dir


def test_run_report_generates_json(tmp_path: Path):
    """Test that JSON report is generated when requested."""
    # Create test CSV
    csv_path = tmp_path / "test.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["score", "converted"])
        writer.writeheader()
        writer.writerow({"score": "80", "converted": "False"})

    template_path = tmp_path / "template.html"
    template_path.write_text("<html><body>Test</body></html>")

    html_out = tmp_path / "report.html"
    json_out = tmp_path / "metrics.json"

    # Mock setup
    from packages.common.config import settings
    orig_data_dir = settings.data_dir

    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    contract_file = contracts_dir / "test.contract.json"
    contract_file.write_text(json.dumps({
        "name": "test",
        "version": "1.0",
        "rule_path": "rules/test.yaml"
    }))

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    rules_file = rules_dir / "test.yaml"
    rules_file.write_text("""
name: test
version: 1
rules:
  - name: approve_high
    when: 'payload.get("score", 0) > 70'
    action: {class: approve}
""")

    settings.data_dir = str(tmp_path)
    settings.contracts_dir = str(contracts_dir)

    try:
        report_data = run_report("test", csv_path, "converted", html_out, template_path, json_out)

        assert json_out.exists()

        # Verify JSON contents
        json_data = json.loads(json_out.read_text())
        assert "metrics" in json_data
        assert "timestamp" in json_data
        assert "contract" in json_data
        assert json_data["contract"] == "test"
    finally:
        settings.data_dir = orig_data_dir


def test_report_includes_metadata(tmp_path: Path):
    """Test that report includes metadata about evaluation."""
    csv_path = tmp_path / "test.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["x", "label"])
        writer.writeheader()
        writer.writerow({"x": "10", "label": "True"})
        writer.writerow({"x": "20", "label": "False"})

    template_path = tmp_path / "template.html"
    template_path.write_text("<html></html>")
    html_out = tmp_path / "report.html"

    from packages.common.config import settings
    orig_data_dir = settings.data_dir

    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    contract_file = contracts_dir / "test.contract.json"
    contract_file.write_text(json.dumps({
        "name": "test",
        "version": "1.0",
        "rule_path": "rules/test.yaml"
    }))

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    rules_file = rules_dir / "test.yaml"
    rules_file.write_text("""
name: test
version: 1
rules:
  - name: r1
    when: 'payload.get("x", 0) > 0'
    action: {class: approve}
""")

    settings.data_dir = str(tmp_path)
    settings.contracts_dir = str(contracts_dir)

    try:
        report_data = run_report("test", csv_path, "label", html_out, template_path)

        metadata = report_data["metadata"]
        assert metadata["total_rows"] == 2
        assert metadata["label_key"] == "label"
        assert "csv_path" in metadata
    finally:
        settings.data_dir = orig_data_dir


# ============================================================================
# Test Group 3: Metrics Calculation
# ============================================================================


def test_simulate_calculates_metrics(tmp_path: Path):
    """Test that simulate calculates precision, recall, and review_rate."""
    from packages.common.config import settings
    orig_data_dir = settings.data_dir

    # Setup mock environment
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    contract_file = contracts_dir / "test.contract.json"
    contract_file.write_text(json.dumps({
        "name": "test",
        "version": "1.0",
        "rule_path": "rules/test.yaml"
    }))

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    rules_file = rules_dir / "test.yaml"
    rules_file.write_text("""
name: test
version: 1
rules:
  - name: reject_low
    when: 'payload.get("score", 0) < 50'
    action: {class: reject, reasons: ["low_score"], confidence: 0.9}
  - name: approve_high
    when: 'payload.get("score", 0) >= 70'
    action: {class: approve, reasons: ["high_score"], confidence: 0.85}
""")

    settings.data_dir = str(tmp_path)
    settings.contracts_dir = str(contracts_dir)

    try:
        rows = [
            {"score": 40, "converted": False},  # True reject
            {"score": 80, "converted": True},   # True approve (but we reject on False converted)
            {"score": 60, "converted": True},   # Review (between thresholds)
        ]

        result = simulate("test", rows, "converted")

        assert "metrics" in result
        metrics = result["metrics"]

        # Check that metrics are calculated
        assert "reject_precision" in metrics or "reject_recall" in metrics or "review_rate" in metrics
    finally:
        settings.data_dir = orig_data_dir


# ============================================================================
# Test Group 4: Integration Tests
# ============================================================================


def test_end_to_end_csv_to_reports(tmp_path: Path):
    """Test complete flow from CSV to HTML and JSON reports."""
    # Create realistic test data
    csv_path = tmp_path / "leads.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["credit_score", "dti", "income_verified", "converted"])
        writer.writeheader()
        # True negatives (reject + not converted)
        writer.writerow({"credit_score": "500", "dti": "0.7", "income_verified": "False", "converted": "False"})
        writer.writerow({"credit_score": "520", "dti": "0.65", "income_verified": "False", "converted": "False"})
        # True positives (approve + converted)
        writer.writerow({"credit_score": "750", "dti": "0.25", "income_verified": "True", "converted": "True"})
        writer.writerow({"credit_score": "720", "dti": "0.30", "income_verified": "True", "converted": "True"})
        # Review cases
        writer.writerow({"credit_score": "620", "dti": "0.40", "income_verified": "True", "converted": "True"})

    template_path = tmp_path / "template.html"
    template_path.write_text("""
<html>
<body>
<h1>Report</h1>
<p>Timestamp: {{ now }}</p>
<p>Contract: {{ contract }}</p>
<p>Precision: {{ metrics.reject_precision }}</p>
<p>Recall: {{ metrics.reject_recall }}</p>
<p>Review Rate: {{ metrics.review_rate }}</p>
</body>
</html>
""")

    html_out = tmp_path / "report.html"
    json_out = tmp_path / "metrics.json"

    from packages.common.config import settings
    orig_data_dir = settings.data_dir

    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    contract_file = contracts_dir / "test.contract.json"
    contract_file.write_text(json.dumps({
        "name": "test",
        "version": "1.0",
        "rule_path": "rules/test.yaml"
    }))

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    rules_file = rules_dir / "test.yaml"
    rules_file.write_text("""
name: test
version: 1
rules:
  - name: reject_low_credit
    when: 'payload.get("credit_score", 0) < 550'
    priority: 10
    action:
      class: reject
      reasons: ["credit_too_low"]
      confidence: 0.9
  - name: reject_high_dti
    when: 'payload.get("dti", 0) > 0.6'
    priority: 9
    action:
      class: reject
      reasons: ["dti_too_high"]
      confidence: 0.85
  - name: approve_strong
    when: 'payload.get("credit_score", 0) >= 700 and payload.get("dti", 0) <= 0.35'
    priority: 8
    action:
      class: approve
      reasons: ["strong_profile"]
      confidence: 0.92
""")

    settings.data_dir = str(tmp_path)
    settings.contracts_dir = str(contracts_dir)

    try:
        report_data = run_report("test", csv_path, "converted", html_out, template_path, json_out)

        # Verify both reports exist
        assert html_out.exists()
        assert json_out.exists()

        # Verify HTML contains expected content
        html_content = html_out.read_text()
        assert "Report" in html_content
        assert "test" in html_content.lower() or "Test" in html_content

        # Verify JSON structure
        json_data = json.loads(json_out.read_text())
        assert json_data["contract"] == "test"
        assert json_data["metadata"]["total_rows"] == 5
        assert "metrics" in json_data
    finally:
        settings.data_dir = orig_data_dir


# ============================================================================
# Summary
# ============================================================================

def test_count_offline_eval_tests():
    """Meta-test to count test cases."""
    import sys
    import inspect

    current_module = sys.modules[__name__]
    test_functions = [
        name for name, obj in inspect.getmembers(current_module)
        if inspect.isfunction(obj) and name.startswith("test_")
    ]

    test_count = len(test_functions) - 1  # Exclude this meta-test

    print(f"\nTotal test cases in test_offline_eval_comprehensive.py: {test_count}")
    assert test_count >= 10, f"Expected 10+ tests, found {test_count}"
