import os
import pytest
from apps.common.pii.masker import mask_text, mask_event

pytestmark = pytest.mark.gate_sec


def test_mask_text_email(monkeypatch):
    monkeypatch.setenv("DECISIONOS_PII_MASK_TOKEN", "[MASK]")
    masked = mask_text("contact test@example.com")
    assert "test@example.com" not in masked
    assert "[MASK]" in masked


def test_mask_event_dict(monkeypatch):
    monkeypatch.setenv("DECISIONOS_PII_MASK_TOKEN", "[MASK]")
    data = {"message": "call 010-1234-5678"}
    masked = mask_event(data)
    assert masked["message"] != data["message"]
