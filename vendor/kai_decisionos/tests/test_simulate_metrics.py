from apps.executor.pipeline import simulate


def test_simulate_no_label_rows():
    rows = [
        {"org_id": "a", "credit_score": 720, "dti": 0.3, "income_verified": True},
        {"org_id": "b", "credit_score": 540, "dti": 0.4, "income_verified": True},
    ]
    res = simulate("lead_triage", rows, None)
    assert 0.0 <= res["metrics"]["review_rate"] <= 1.0

