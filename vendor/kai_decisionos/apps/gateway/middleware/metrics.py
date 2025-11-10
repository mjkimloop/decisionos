from __future__ import annotations

import time
from statistics import quantiles

_durations: list[float] = []
_errors: int = 0
_count: int = 0


def install(app):
    @app.middleware("http")
    async def _mw(request, call_next):  # type: ignore[override]
        global _durations, _errors, _count
        t0 = time.perf_counter()
        try:
            resp = await call_next(request)
            return resp
        except Exception:
            _errors += 1
            raise
        finally:
            _count += 1
            dt = (time.perf_counter() - t0) * 1000.0
            _durations.append(dt)
            if len(_durations) > 1000:
                _durations[:] = _durations[-1000:]


def snapshot() -> dict:
    if not _durations:
        p95 = 0.0
    else:
        try:
            p95 = quantiles(_durations, n=100)[94]
        except Exception:
            p95 = max(_durations)
    error_rate = 0.0 if _count == 0 else _errors / _count
    return {"p95_ms": round(p95, 2), "error_rate": round(error_rate, 4), "req_count": _count}
