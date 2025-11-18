from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Literal, Optional

import yaml

from apps.experiment import stage_file
from apps.ops import freeze as freeze_guard

Stage = Literal["blue", "green"]

DEFAULT_POLICY_PATH = "configs/canary/policy.v2.json"
DEFAULT_STATE_PATH = "var/rollout/canary_state.json"


def _parse_labels(raw: str) -> list[str]:
    if not raw:
        return []
    return [token.strip() for token in raw.replace(",", " ").split() if token.strip()]


def _change_guard(action: str) -> None:
    if os.getenv("DECISIONOS_CHANGE_GOV_ENABLE", "1") == "0":
        return
    labels = _parse_labels(os.getenv("CHANGE_LABELS", ""))
    blocked, reason = freeze_guard.is_freeze_active(service=os.getenv("DECISIONOS_SERVICE", "core"), labels=labels)
    if blocked and not freeze_guard.has_valid_break_glass():
        raise RuntimeError(f"change_guard:{action}:{reason}")


def _sha_bucket(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 100


class TrafficController:
    """Sticky canary router with stage FSM."""

    def __init__(
        self,
        stage_file_path: str = "var/rollout/desired_stage.txt",
        policy_path: Optional[str] = None,
        state_path: Optional[str] = None,
    ) -> None:
        self.stage_file = Path(stage_file_path)
        self.policy_path = policy_path or os.getenv("DECISIONOS_CANARY_POLICY", DEFAULT_POLICY_PATH)
        self.state_path = Path(state_path or os.getenv("DECISIONOS_CANARY_STATE", DEFAULT_STATE_PATH))
        self.policy = self._load_policy(self.policy_path)
        stages = sorted(set([0] + [int(p) for p in self.policy.get("stages", [10, 50, 100])]))
        self.stages = stages
        self._stage_pct = 0
        self._stage_index = 0
        self._load_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_policy(self, path: str) -> Dict[str, object]:
        try:
            data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = None
        return data or {"stages": [10, 50, 100], "hash_key": "header:X-Canary-Key"}

    def _write_stage(self, token: str) -> None:
        try:
            stage_file.write_stage_atomic(token, str(self.stage_file))
        except RuntimeError:
            self.stage_file.parent.mkdir(parents=True, exist_ok=True)
            self.stage_file.write_text(token + "\n", encoding="utf-8")

    def _load_state(self) -> None:
        if self.state_path.exists():
            try:
                payload = json.loads(self.state_path.read_text(encoding="utf-8"))
                pct = int(payload.get("pct", 0))
                self._stage_pct = max(0, min(100, pct))
            except Exception:
                self._stage_pct = 0
        else:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self._stage_pct = 0
            self._save_state()
        self._stage_index = self._closest_index(self._stage_pct)

    def _closest_index(self, pct: int) -> int:
        idx = 0
        for i, value in enumerate(self.stages):
            if pct >= value:
                idx = i
        return idx

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"pct": self._stage_pct}
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _hash_key_value(self, headers: Optional[Dict[str, str]]) -> str:
        headers = headers or {}
        spec = str(self.policy.get("hash_key", "header:X-Canary-Key"))
        if ":" in spec:
            kind, value = spec.split(":", 1)
        else:
            kind, value = "header", spec
        if kind == "header":
            lowered = {k.lower(): v for k, v in headers.items()}
            return lowered.get(value.lower(), f"header:{value}")
        if kind == "cookie":
            cookie_raw = headers.get("cookie") or headers.get("Cookie")
            if cookie_raw:
                for part in cookie_raw.split(";"):
                    if "=" in part:
                        name, val = part.strip().split("=", 1)
                        if name.strip() == value:
                            return val.strip()
        return value or "default"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_stage(self, percent: int) -> None:
        pct = max(0, min(100, int(percent)))
        self._stage_pct = pct
        self._stage_index = self._closest_index(pct)
        self._save_state()
        token = "canary" if pct > 0 else "stable"
        self._write_stage(token)

    def current_percentage(self) -> int:
        return self._stage_pct

    def register_result(self, success: bool) -> None:
        if success:
            for value in self.stages[self._stage_index + 1 :]:
                self.set_stage(value)
                return
            self.set_stage(self._stage_pct)
        else:
            self.set_stage(0)

    def route(self, headers: Optional[Dict[str, str]] = None) -> str:
        if self._stage_pct <= 0:
            return "stable"
        key = self._hash_key_value(headers)
        bucket = _sha_bucket(key)
        return "canary" if bucket < self._stage_pct else "stable"

    def promote(self) -> None:
        _change_guard("promote")
        self._write_stage("promote")

    def abort(self) -> None:
        _change_guard("abort")
        self._stage_pct = 0
        self._stage_index = 0
        self._save_state()
        self._write_stage("abort")


class BlueGreenController:
    """Minimal controller to satisfy existing tests."""

    def __init__(self) -> None:
        self.current_stage: Stage = "blue"

    def get_current_stage(self) -> Stage:
        return self.current_stage

    def check_health(self, stage: Stage) -> tuple[bool, str]:
        status = os.environ.get(f"HEALTH_{stage.upper()}", "ok")
        return status == "ok", status

    def cutover(self, target_stage: Stage, check_health: bool = True) -> tuple[bool, str]:
        try:
            _change_guard(f"cutover:{target_stage}")
        except RuntimeError as exc:
            return False, str(exc)
        if target_stage not in ("blue", "green"):
            return False, "invalid stage"
        if check_health:
            healthy, reason = self.check_health(target_stage)
            if not healthy:
                return False, f"{target_stage} unhealthy: {reason}"
        previous = self.current_stage
        self.current_stage = target_stage
        return True, f"Cutover from {previous} to {target_stage}"

    def rollback(self) -> tuple[bool, str]:
        new_stage: Stage = "green" if self.current_stage == "blue" else "blue"
        return self.cutover(new_stage, check_health=False)


def get_controller(**kwargs) -> TrafficController:
    return TrafficController(**kwargs)
