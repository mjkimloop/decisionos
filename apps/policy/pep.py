from __future__ import annotations
import os

class PEP:
    """ENV 기반 아주 단순한 PEP: DECISIONOS_ALLOW_SCOPES='judge:run,deploy:promote'"""
    def __init__(self, env="DECISIONOS_ALLOW_SCOPES"):
        self.env = env

    def enforce(self, scope: str) -> bool:
        allowed = os.getenv(self.env, "")
        scopes = {s.strip() for s in allowed.split(",") if s.strip()}
        if not scopes:
            return True
        return scope in scopes


__all__ = ["PEP"]
