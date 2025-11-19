from __future__ import annotations

import time


def generate_local(prompt: str, **kwargs):
    """간단한 로컬 폴백 응답."""
    return {
        "provider": "local",
        "prompt": prompt,
        "generated": f"[local-fallback]{prompt[:50]}",
        "latency_ms": int(time.time() * 0 % 5),
    }
