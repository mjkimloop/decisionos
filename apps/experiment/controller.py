from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml

from apps.experiment.stage_file import Stage, StageState, guard_and_repair, write_stage_atomic
from apps.judge.metrics import JudgeMetrics


@dataclass
class RolloutPolicy:
    stages: list[int]
    hold_minutes: int = 10
    max_parallel: int = 1
    rollback_on_fail: bool = True
    hash_key: str = "header:X-Canary-Key"

    @classmethod
    def load(cls, path: str | Path) -> "RolloutPolicy":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(
            stages=data.get("stages", [1, 5, 10, 25, 50, 100]),
            hold_minutes=int(data.get("hold_minutes", 10)),
            max_parallel=int(data.get("max_parallel", 1)),
            rollback_on_fail=bool(data.get("rollback_on_fail", True)),
            hash_key=str(data.get("hash_key", "header:X-Canary-Key")),
        )


class TrafficController:
    """
    Sticky hash 기반 카나리/블루-그린 트래픽 컨트롤러.
    단순하게 현재 단계의 퍼센트를 기준으로 라우팅한다.
    """

    def __init__(
        self,
        policy_path: str = "configs/rollout/policy.yaml",
        stage_file: str | Path | None = "var/rollout/desired_stage.txt",
    ) -> None:
        self.policy_path = policy_path
        self.policy = RolloutPolicy.load(policy_path)
        self.stage_index = 0
        self.stage_changed_at = time.time()
        self.kill_switch = False
        self._lock = threading.Lock()
        self.metrics = JudgeMetrics(window_seconds=600)
        self.stage_file = Path(stage_file) if stage_file else None
        self._stage_file_mtime = 0.0
        self._stage_hash: str = ""
        self._sync_stage_from_file(initial=True)

    def current_percentage(self) -> int:
        if self.kill_switch:
            return 0
        try:
            return int(self.policy.stages[self.stage_index])
        except IndexError:
            return 0

    def route(self, headers: Optional[Dict[str, str]] = None, context: Optional[Dict[str, str]] = None) -> str:
        self._sync_stage_from_file()
        percent = self.current_percentage()
        if percent <= 0:
            return "control"
        key = self._extract_key(headers or {}, context or {})
        if not key:
            return "control"
        bucket = self._hash_to_percentage(key)
        return "canary" if bucket < percent else "control"

    def _extract_key(self, headers: Dict[str, str], context: Dict[str, str]) -> Optional[str]:
        source = (self.policy.hash_key or "").lower()
        if source.startswith("header:"):
            header_name = source.split(":", 1)[1]
            return headers.get(header_name) or headers.get(header_name.lower())
        if source.startswith("context:"):
            field = source.split(":", 1)[1]
            return context.get(field)
        # default sticky: tenant|user|path if present
        parts: Iterable[str] = (
            headers.get("X-Tenant", ""),
            headers.get("X-User", ""),
            headers.get(":path", context.get("path", "")),
        )
        combined = "|".join(filter(None, parts))
        return combined or headers.get("X-Canary-Key")

    @staticmethod
    def _hash_to_percentage(key: str) -> int:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        # take first 8 bytes as integer
        value = int.from_bytes(digest[:8], byteorder="big")
        return value % 100

    def set_stage(self, percentage: int, *, _from_file: bool = False) -> None:
        with self._lock:
            self._apply_percentage(percentage)
            if not _from_file:
                desired_state: StageState = "stable" if percentage <= 0 else "canary"
                self._write_stage_file(
                    desired_state,
                    {"percentage": percentage, "source": "controller"},
                )

    def advance_stage(self) -> None:
        with self._lock:
            if self.stage_index < len(self.policy.stages) - 1:
                if self._hold_elapsed():
                    self.stage_index += 1
                    self.stage_changed_at = time.time()
                    self._write_stage_file(
                        "canary",
                        {
                            "percentage": self.policy.stages[self.stage_index],
                            "source": "controller",
                        },
                    )

    def rollback(self, reason: str = "") -> None:
        if not self.policy.rollback_on_fail:
            return
        with self._lock:
            self.stage_index = 0
            self.kill_switch = True
            self.stage_changed_at = time.time()
            self._write_stage_file("stable", {"source": "controller", "reason": reason})

    def _hold_elapsed(self) -> bool:
        hold_seconds = self.policy.hold_minutes * 60
        return (time.time() - self.stage_changed_at) >= hold_seconds

    def register_result(self, success: bool) -> None:
        if success:
            self.advance_stage()
        else:
            self.rollback("failure")

    def kill(self) -> None:
        self.set_stage(0)

    def _sync_stage_from_file(self, *, initial: bool = False) -> None:
        if not self.stage_file:
            return
        record = guard_and_repair(str(self.stage_file))
        if not initial and record.sha256 == self._stage_hash and record.mtime <= self._stage_file_mtime:
            return
        self._stage_file_mtime = record.mtime
        self._stage_hash = record.sha256
        self._apply_stage_state(record.stage)

    def _apply_stage_state(self, state: StageState) -> None:
        token = state.stage
        if token == "stable":
            self.set_stage(0, _from_file=True)
        elif token == "canary":
            target = self.policy.stages[0] if self.stage_index == 0 else self.policy.stages[self.stage_index]
            self.set_stage(target, _from_file=True)
        elif token == "promote":
            self.advance_stage()
        elif token == "abort":
            self.rollback("abort command")

    def _apply_percentage(self, percentage: int) -> None:
        if percentage <= 0:
            self.stage_index = 0
            self.kill_switch = True
        else:
            if percentage not in self.policy.stages:
                self.policy.stages.append(percentage)
                self.policy.stages.sort()
            self.stage_index = self.policy.stages.index(percentage)
            self.kill_switch = False
        self.stage_changed_at = time.time()

    def _write_stage_file(self, state: Stage, meta: Optional[Dict[str, Any]] = None) -> None:
        if not self.stage_file:
            return
        try:
            record = write_stage_atomic(state, str(self.stage_file))
            self._stage_file_mtime = record.mtime
            self._stage_hash = record.sha256
        except OSError:
            pass


__all__ = ["TrafficController", "RolloutPolicy"]
