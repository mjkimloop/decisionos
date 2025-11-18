"""
Gate OPS — Runtime flags tests
"""
import os
import json
import tempfile
from apps.runtime.flags import RuntimeFlags

def test_flags_load_from_config():
    """Test flags load from configuration"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "flags": {
                "feature_a": {"enabled": True},
                "feature_b": {"enabled": False}
            }
        }, f)
        config_path = f.name

    try:
        flags = RuntimeFlags(config_path)
        assert flags.is_enabled("feature_a")
        assert not flags.is_enabled("feature_b")
    finally:
        os.unlink(config_path)

def test_flags_hot_reload():
    """Test flags hot reload when file changes"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"flags": {"feature": {"enabled": False}}}, f)
        config_path = f.name

    try:
        flags = RuntimeFlags(config_path)
        assert not flags.is_enabled("feature")

        # Modify file
        import time
        time.sleep(0.01)  # Ensure mtime changes
        with open(config_path, "w") as f2:
            json.dump({"flags": {"feature": {"enabled": True}}}, f2)

        # Should reload
        assert flags.is_enabled("feature")
    finally:
        os.unlink(config_path)

def test_get_flag_value():
    """Test getting flag value"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "flags": {
                "mode": {"enabled": True, "value": "strict"}
            }
        }, f)
        config_path = f.name

    try:
        flags = RuntimeFlags(config_path)
        assert flags.get("mode") == "strict"
        assert flags.get("missing", "default") == "default"
    finally:
        os.unlink(config_path)

def test_kill_switch():
    """Test kill switch functionality"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "flags": {
                "_kill_switches": {
                    "feature_x": True,
                    "feature_y": False
                }
            }
        }, f)
        config_path = f.name

    try:
        flags = RuntimeFlags(config_path)
        assert flags.is_killed("feature_x")
        assert not flags.is_killed("feature_y")
    finally:
        os.unlink(config_path)
