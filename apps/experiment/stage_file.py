from __future__ import annotations
import os, io, json, hashlib, time
from dataclasses import dataclass
from typing import Literal, Tuple

Stage = Literal["stable","canary","promote","abort"]

@dataclass(frozen=True)
class StageState:
    stage: Stage
    sha256: str
    mtime: float

def _fsync_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path)) or "."
    if os.name == "nt":
        return
    fd = os.open(d, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def read_stage_with_hash(path: str = "var/rollout/desired_stage.txt") -> StageState:
    with open(path, "r", encoding="utf-8") as f:
        data = f.read().strip()  # no trailing newline
    st = os.stat(path)
    return StageState(stage=data, sha256=_sha256_text(data), mtime=st.st_mtime)

def write_stage_atomic(stage: Stage, path: str = "var/rollout/desired_stage.txt") -> StageState:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = stage  # single-line, no newline
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)  # atomic on same FS (Windows/Posix)
    _fsync_dir(path)
    return read_stage_with_hash(path)

def guard_and_repair(path: str = "var/rollout/desired_stage.txt") -> StageState:
    """손상/부분쓰기 탐지 시 마지막 유효 상태로 복구(기본값 stable)."""
    try:
        st = read_stage_with_hash(path)
        if st.stage not in ("stable","canary","promote","abort"):
            raise ValueError("invalid stage token")
        return st
    except Exception:
        repaired = write_stage_atomic("stable", path)
        return repaired
