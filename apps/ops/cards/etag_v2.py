from __future__ import annotations
import os
from typing import Dict, Any, Optional
from apps.ops.cache.etag import sha256_file, make_etag

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if v else default

def build_cards_etag_key(
    period_start: str, period_end: str, *,
    bucket: str, seasonality: str,
    delta_enabled: bool, delta_require_same_window: bool,
    continuity_token: Optional[str],
    label_catalog_path: Optional[str] = None,
    group_weights_path: Optional[str] = None,
    seasonal_thresholds_path: Optional[str] = None,
    data_revision_token: Optional[str] = None
) -> Dict[str, Any]:
    # 파일 경로 기본값(존재하지 않으면 None)
    label_catalog_path = label_catalog_path or _env("LABEL_CATALOG_PATH", "configs/ops/label_catalog.json")
    group_weights_path = group_weights_path or _env("GROUP_WEIGHTS_PATH", "var/cards/group_weights.json")
    seasonal_thresholds_path = seasonal_thresholds_path or _env("CARDS_THRESHOLDS_SEASONAL_PATH", "var/cards/thresholds_seasonal.json")

    return {
        "v": 2,
        "period": {"start": period_start, "end": period_end},
        "bucket": bucket,
        "seasonality": seasonality,
        "delta": {"enabled": bool(delta_enabled), "require_same_window": bool(delta_require_same_window)},
        "continuity_token": continuity_token or "",  # secret-scan: ignore (identifier only)
        "hashes": {
            "label_catalog": sha256_file(label_catalog_path) if label_catalog_path else None,
            "group_weights": sha256_file(group_weights_path),
            "seasonal_thresholds": sha256_file(seasonal_thresholds_path),
            "data_revision": data_revision_token or _env("CARDS_DATA_REV", ""),
        },
    }

def compute_cards_etag(etag_key: Dict[str, Any]) -> str:
    return make_etag(etag_key)
