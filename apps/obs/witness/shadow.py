from __future__ import annotations

import csv
import random
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Optional


class ShadowRecorder:
    """간단한 섀도 트래픽 CSV 레코더 (control/canary)."""

    def __init__(self, control_path: str | Path, canary_path: str | Path):
        self.control_path = Path(control_path)
        self.canary_path = Path(canary_path)
        self.control_path.parent.mkdir(parents=True, exist_ok=True)
        self.canary_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_file(self.control_path)
        self._init_file(self.canary_path)
        self._lock = threading.Lock()

    def _init_file(self, path: Path) -> None:
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["ts", "status", "latency_ms", "signature_error", "payload_size"])

    def record(self, bucket: str, status: int, latency_ms: float, signature_error: bool, payload_size: int) -> None:
        path = self.control_path if bucket == "control" else self.canary_path
        with self._lock, path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                status,
                round(latency_ms, 2),
                1 if signature_error else 0,
                payload_size,
            ])


def default_redactor(payload: str) -> str:
    # placeholder: 실제 PII 마스킹은 정규식 기반으로 확장 가능.
    return payload.replace("@", "[at]")


def mirror_request(
    bucket: str,
    status_code: int,
    latency_ms: float,
    *,
    recorder: ShadowRecorder,
    sample_rate: float = 0.1,
    signature_error: bool = False,
    payload: Optional[str] = None,
    redactor: Optional[Callable[[str], str]] = None,
) -> None:
    if random.random() > sample_rate:
        return
    payload_size = len((redactor or default_redactor)(payload or "")) if payload else 0
    recorder.record(bucket, status_code, latency_ms, signature_error, payload_size)


__all__ = ["ShadowRecorder", "mirror_request"]
