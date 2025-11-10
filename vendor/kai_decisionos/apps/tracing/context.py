from __future__ import annotations

from pkg.context.corr import ensure_corr_id, get_corr_id as _get_corr_id, set_corr_id


def get_corr_id() -> str:
    """Backward-compatible alias for pkg.context.corr.get_corr_id."""
    return _get_corr_id()


__all__ = ["set_corr_id", "get_corr_id", "ensure_corr_id"]
