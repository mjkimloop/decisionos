"""
Gate AH — Blue/Green switch tests
"""
import os
from apps.experiment.controller import BlueGreenController

def test_default_stage_is_blue():
    """Test default stage is blue"""
    controller = BlueGreenController()
    assert controller.get_current_stage() == "blue"

def test_cutover_to_green():
    """Test cutover from blue to green"""
    controller = BlueGreenController()
    os.environ["HEALTH_GREEN"] = "ok"

    success, message = controller.cutover("green")
    assert success
    assert controller.get_current_stage() == "green"

    del os.environ["HEALTH_GREEN"]

def test_cutover_fails_on_unhealthy():
    """Test cutover fails if target stage unhealthy"""
    controller = BlueGreenController()
    os.environ["HEALTH_GREEN"] = "degraded"

    success, message = controller.cutover("green")
    assert not success
    assert "unhealthy" in message
    assert controller.get_current_stage() == "blue"

    del os.environ["HEALTH_GREEN"]

def test_rollback_switches_stage():
    """Test rollback switches to previous stage"""
    controller = BlueGreenController()
    controller.current_stage = "green"

    success, message = controller.rollback()
    assert success
    assert controller.get_current_stage() == "blue"

def test_cutover_skip_health_check():
    """Test cutover can skip health check"""
    controller = BlueGreenController()
    os.environ["HEALTH_GREEN"] = "degraded"

    success, message = controller.cutover("green", check_health=False)
    assert success
    assert controller.get_current_stage() == "green"

    del os.environ["HEALTH_GREEN"]
