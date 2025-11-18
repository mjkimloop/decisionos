from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
import traceback
import time

@dataclass
class ExecResult:
    ok: bool
    started_at: float
    ended_at: float
    elapsed_ms: int
    output: Optional[Any] = None
    error: Optional[str] = None
    reason: Optional[str] = None  # 'exec.error', 'exec.ok'
    meta: Dict[str, Any] = field(default_factory=dict)

class ExecutorRunner:
    """
    MVP 동기 실행기.
    decision = {
      "action": "python.call",
      "fn": "myfunc",
      "args": [1,2], "kwargs": {"x":3},
      "trace": {"tenant":"t1","evidence_id":"..."}
    }
    """
    def __init__(self, registry: "PluginRegistry"):
        self.registry = registry

    def execute(self, decision: Dict[str, Any]) -> ExecResult:
        started = time.time()
        try:
            action = decision.get("action")
            if not action:
                raise ValueError("missing action")

            handler = self.registry.resolve(action)
            output = handler(decision)
            ended = time.time()
            return ExecResult(
                ok=True,
                started_at=started,
                ended_at=ended,
                elapsed_ms=int((ended-started)*1000),
                output=output,
                reason="exec.ok",
                meta={"trace": decision.get("trace")}
            )
        except Exception as ex:
            ended = time.time()
            return ExecResult(
                ok=False,
                started_at=started,
                ended_at=ended,
                elapsed_ms=int((ended-started)*1000),
                error=f"{type(ex).__name__}: {ex}",
                reason="exec.error",
                meta={
                    "trace": decision.get("trace"),
                    "tb": traceback.format_exc(limit=3)
                }
            )

class PluginRegistry:
    def __init__(self):
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register(self, action: str, fn: Callable[[Dict[str, Any]], Any]) -> None:
        self._handlers[action] = fn

    def resolve(self, action: str) -> Callable[[Dict[str, Any]], Any]:
        if action not in self._handlers:
            raise KeyError(f"no handler for action={action}")
        return self._handlers[action]
