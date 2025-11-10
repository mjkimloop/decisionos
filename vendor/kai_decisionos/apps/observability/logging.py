from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict

from pkg.context import corr as corr_ctx
from pkg.context import trace as trace_ctx


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        obj: Dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        try:
            obj["corr_id"] = corr_ctx.get_corr_id()
        except Exception:
            pass
        try:
            obj["trace_id"] = trace_ctx.get_trace_id()
        except Exception:
            pass
        return json.dumps(obj, ensure_ascii=False)


def setup_json_logging(level: int = logging.INFO):
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [h]
    root.setLevel(level)
