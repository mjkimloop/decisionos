import pathlib

import yaml


def test_prometheus_rules_schema():
    p = pathlib.Path("configs/alerts/cards_alerts.yml")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "groups" in data and data["groups"], "no alert groups"
