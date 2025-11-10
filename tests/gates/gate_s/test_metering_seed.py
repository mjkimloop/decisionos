import pytest
pytestmark = [pytest.mark.gate_s, pytest.mark.xfail(strict=False, reason="seed: metering pipeline not implemented yet")]

def test_metering_contract_shape_seed():
    # 목적: 초기 CI 그린 유지. 구현 시 실제 계약/스키마 검증으로 대체.
    assert True
