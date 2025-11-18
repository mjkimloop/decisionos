"""
Gate AJ — SLO Saturation tests
"""
import json
from apps.judge import slo_judge

def test_saturation_cpu_over_limit():
    """Test CPU saturation over limit fails"""
    evidence = {
        "meta": {}, "witness": {}, "usage": {"cpu_percent": 95.0}, "rating": {},
        "quota": {}, "budget": {}, "anomaly": {}, "integrity": {"signature_sha256": "abc"}
    }
    slo = {
        "version": "v1",
        "saturation": {"max_cpu_percent": 90.0, "fail_closed": True}
    }
    
    verdict, reasons = slo_judge.evaluate(evidence, slo)
    
    assert verdict == "fail"
    assert any("infra.saturation.cpu" in r for r in reasons)

def test_saturation_mem_over_limit():
    """Test memory saturation over limit fails"""
    evidence = {
        "meta": {}, "witness": {}, "usage": {"mem_percent": 90.0}, "rating": {},
        "quota": {}, "budget": {}, "anomaly": {}, "integrity": {"signature_sha256": "abc"}
    }
    slo = {
        "version": "v1",
        "saturation": {"max_mem_percent": 85.0, "fail_closed": True}
    }
    
    verdict, reasons = slo_judge.evaluate(evidence, slo)
    
    assert verdict == "fail"
    assert any("infra.saturation.mem" in r for r in reasons)

def test_saturation_qps_over_limit():
    """Test QPS saturation over limit fails"""
    evidence = {
        "meta": {}, "witness": {}, "usage": {"qps": 15000}, "rating": {},
        "quota": {}, "budget": {}, "anomaly": {}, "integrity": {"signature_sha256": "abc"}
    }
    slo = {
        "version": "v1",
        "saturation": {"max_qps": 10000, "fail_closed": True}
    }
    
    verdict, reasons = slo_judge.evaluate(evidence, slo)
    
    assert verdict == "fail"
    assert any("infra.saturation.qps" in r for r in reasons)

def test_saturation_within_limits_passes():
    """Test saturation within limits passes"""
    evidence = {
        "meta": {}, "witness": {}, "usage": {"cpu_percent": 80.0, "mem_percent": 70.0, "qps": 5000},
        "rating": {}, "quota": {}, "budget": {}, "anomaly": {}, "integrity": {"signature_sha256": "abc"}
    }
    slo = {
        "version": "v1",
        "saturation": {"max_cpu_percent": 90.0, "max_mem_percent": 85.0, "max_qps": 10000}
    }
    
    verdict, reasons = slo_judge.evaluate(evidence, slo)
    
    # Should not have saturation reasons
    assert not any("saturation" in r for r in reasons)

def test_production_config_loads():
    """Test production saturation config loads"""
    import os
    if not os.path.exists("configs/slo/slo-judge-saturation.json"):
        import pytest
        pytest.skip("Production config not found")
    
    with open("configs/slo/slo-judge-saturation.json", "r") as f:
        config = json.load(f)
    
    assert "saturation" in config
    assert config["saturation"]["max_cpu_percent"] == 90.0
