"""
Runtime Flags/Kill Switches - File-based feature flags with hot reload
"""
import os
import json
import time
from typing import Dict, Any, Optional

class RuntimeFlags:
    """
    Runtime feature flags with file-based configuration.
    Supports hot reload without service restart.
    """
    
    def __init__(self, config_path: str = "configs/flags/flags.json"):
        self.config_path = config_path
        self._flags: Dict[str, Any] = {}
        self._last_mtime: float = 0.0
        self._load_flags()
    
    def _load_flags(self) -> None:
        """Load flags from config file"""
        if not os.path.exists(self.config_path):
            print(f"[WARN] Flags config not found: {self.config_path}")
            return
        
        try:
            mtime = os.path.getmtime(self.config_path)
            
            # Only reload if file changed
            if mtime <= self._last_mtime:
                return
            
            with open(self.config_path, "r") as f:
                config = json.load(f)
            
            self._flags = config.get("flags", {})
            self._last_mtime = mtime
            
            print(f"[INFO] Loaded {len(self._flags)} flags from {self.config_path}")
        except Exception as e:
            print(f"[ERROR] Failed to load flags: {e}")
    
    def is_enabled(self, flag_name: str, default: bool = False) -> bool:
        """
        Check if a feature flag is enabled.
        Hot-reloads config if file changed.
        """
        self._load_flags()  # Check for file changes
        
        flag = self._flags.get(flag_name, {})
        return flag.get("enabled", default)
    
    def get(self, flag_name: str, default: Any = None) -> Any:
        """Get flag value with default"""
        self._load_flags()
        
        flag = self._flags.get(flag_name, {})
        return flag.get("value", default)
    
    def is_killed(self, feature: str) -> bool:
        """Check if feature is killed (emergency off switch)"""
        self._load_flags()
        
        kill_switches = self._flags.get("_kill_switches", {})
        return kill_switches.get(feature, False)

# Global instance
_flags_instance: Optional[RuntimeFlags] = None

def get_flags() -> RuntimeFlags:
    """Get global flags instance"""
    global _flags_instance
    if _flags_instance is None:
        _flags_instance = RuntimeFlags()
    return _flags_instance
