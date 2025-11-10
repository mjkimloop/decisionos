from __future__ import annotations

from typing import Dict


def compare_versions(base: str, target: str) -> Dict[str, bool]:
    def split(ver: str) -> tuple[int, int, int]:
        parts = ver.strip("v").split(".")
        parts += ["0"] * (3 - len(parts))
        return tuple(int(p) for p in parts[:3])

    b = split(base)
    t = split(target)
    return {
        "base": base,
        "target": target,
        "compatible": t[0] == b[0] and t >= b,
        "upgrade_required": t[0] > b[0],
    }


__all__ = ["compare_versions"]
