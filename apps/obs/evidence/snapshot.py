"""
apps/obs/evidence/snapshot.py

Evidence 스냅샷 생성 — Witness → Metering → Rating/Quota → Cost-Guard 전체 체인의
판정 근거를 JSON 형태로 직렬화하고 무결성 서명 추가.
"""
from __future__ import annotations
import json
import hashlib
import os
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

from apps.common.timeutil import time_utcnow
from apps.rating.engine import RatingResult
from apps.limits.quota import QuotaDecision


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return _sha256_bytes(f.read())


@dataclass
class Evidence:
    """Evidence 스냅샷 데이터 구조"""

    meta: Dict[str, Any]
    witness: Dict[str, Any]
    usage: Dict[str, Any]
    rating: Dict[str, Any]
    quota: Dict[str, Any]
    budget: Dict[str, Any]
    anomaly: Dict[str, Any]
    perf: Dict[str, Any] | None
    perf_judge: Dict[str, Any] | None
    judges: Dict[str, Any] | None
    canary: Dict[str, Any] | None
    integrity: Dict[str, Any]

    def to_json(self, indent: int = 2) -> str:
        """JSON 문자열로 직렬화 (정렬된 키)"""
        return json.dumps(
            asdict(self), ensure_ascii=False, indent=indent, sort_keys=True
        )

    def save(self, dirpath: str = "var/evidence") -> str:
        """파일 시스템에 저장 (타임스탬프 기반 파일명)"""
        os.makedirs(dirpath, exist_ok=True)
        ts = time_utcnow().strftime("%Y%m%dT%H%M%SZ")
        path = os.path.join(dirpath, f"evidence-{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        return path


def build_snapshot(
    *,
    version: str,
    tenant: str,
    witness_csv_path: str | None,
    witness_rows: int,
    witness_csv_sha256: str | None,
    buckets: Dict[str, Any],
    deltas_by_metric: Dict[str, float],
    rating: RatingResult,
    quota: List[QuotaDecision],
    budget_level: str,
    budget_spent: float,
    budget_limit: float,
    anomaly_is_spike: bool,
    anomaly_ewma: float,
    anomaly_ratio: float,
    perf: Dict[str, Any] | None = None,
    judges: Dict[str, Any] | None = None,
    perf_judge: Dict[str, Any] | None = None,
    canary: Dict[str, Any] | None = None,
) -> Evidence:
    """
    전체 체인 실행 결과를 Evidence 스냅샷으로 빌드.

    Parameters:
        version: Evidence 스키마 버전
        tenant: 테넌트 ID
        witness_csv_path: Witness CSV 파일 경로 (nullable)
        witness_rows: 이벤트 행 수
        witness_csv_sha256: CSV 파일 SHA-256 해시 (nullable)
        buckets: Metering 집계 결과 (Dict[bucket_key, MeterBucket])
        deltas_by_metric: Metric별 사용량 합계
        rating: RatingResult 객체
        quota: QuotaDecision 리스트
        budget_level: 예산 판정 레벨 (ok/warn/exceeded)
        budget_spent: 실제 지출액
        budget_limit: 예산 한도
        anomaly_is_spike: 급증 탐지 여부
        anomaly_ewma: EWMA 값
        anomaly_ratio: Spike 판정 비율

    Returns:
        Evidence 객체 (to_json()으로 직렬화 가능)
    """
    now_ts = time_utcnow()
    meta = {
        "version": version,
        "generated_at": now_ts.isoformat().replace("+00:00", "Z"),
        "tenant": tenant,
    }
    witness = {
        "csv_path": witness_csv_path,
        "csv_sha256": witness_csv_sha256,
        "rows": witness_rows,
    }
    rating_dict = {
        "subtotal": rating.subtotal,
        "items": [
            {
                "metric": it.metric,
                "included": getattr(it, "included", None),
                "overage": getattr(it, "overage_units", None),
                "amount": it.amount,
            }
            for it in rating.items
        ],
    }
    quota_dict = {
        "decisions": {
            d.metric: {
                "action": d.action,
                "used": d.used,
                "soft": getattr(d, "soft", None),
                "hard": getattr(d, "hard", None),
            }
            for d in quota
        }
    }
    budget_dict = {
        "level": budget_level,
        "spent": budget_spent,
        "limit": budget_limit,
    }
    anomaly_dict = {
        "is_spike": anomaly_is_spike,
        "ewma": anomaly_ewma,
        "ratio": anomaly_ratio,
    }
    usage = {"buckets": buckets, "deltas_by_metric": deltas_by_metric}

    # 서명: 핵심 필드만 정렬 JSON → SHA-256
    core = {
        "meta": meta,
        "witness": witness,
        "usage": usage,
        "rating": rating_dict,
        "quota": quota_dict,
        "budget": budget_dict,
        "anomaly": anomaly_dict,
    }
    if perf is not None:
        core["perf"] = perf
    if perf_judge is not None:
        core["perf_judge"] = perf_judge
    if judges is not None:
        core["judges"] = judges
    if canary is not None:
        core["canary"] = canary
    core_json = json.dumps(core, ensure_ascii=False, sort_keys=True)
    integrity = {"signature_sha256": sha256_text(core_json)}

    return Evidence(
        meta=meta,
        witness=witness,
        usage=usage,
        rating=rating_dict,
        quota=quota_dict,
        budget=budget_dict,
        anomaly=anomaly_dict,
        perf=perf,
        perf_judge=perf_judge,
        judges=judges,
        canary=canary,
        integrity=integrity,
    )
