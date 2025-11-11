#!/usr/bin/env python3
"""
실측 데이터 기반 SLO 베이스라인 생성 도구

7일 로그 분석 → p95/p99/error_rate 자동 산출
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import statistics

def parse_evidence_perf(evidence_path: str) -> Dict[str, Any]:
    """Evidence 파일에서 성능 메트릭 추출"""
    try:
        with open(evidence_path, 'r', encoding='utf-8') as f:
            evidence = json.load(f)
    except Exception as e:
        print(f"Error loading evidence: {e}", file=sys.stderr)
        return {}

    perf = evidence.get("perf", {})
    return {
        "latency_p50": perf.get("p50", 0),
        "latency_p95": perf.get("p95", 0),
        "latency_p99": perf.get("p99", 0),
        "latency_max": perf.get("max", 0),
        "total_requests": perf.get("count", 0),
        "error_count": evidence.get("errors", {}).get("count", 0),
    }

def calculate_error_rate(total: int, errors: int) -> float:
    """에러율 계산"""
    if total == 0:
        return 0.0
    return errors / total

def generate_slo_v2(baseline: Dict[str, Any], safety_margin: float = 1.2) -> Dict[str, Any]:
    """
    실측 베이스라인으로부터 SLO v2 생성

    Args:
        baseline: 실측 메트릭
        safety_margin: 안전 마진 (기본 20% 여유)
    """
    p95 = baseline.get("latency_p95", 500)
    p99 = baseline.get("latency_p99", 1000)
    total = baseline.get("total_requests", 1)
    errors = baseline.get("error_count", 0)
    error_rate = calculate_error_rate(total, errors)

    # 안전 마진 적용
    max_p95 = int(p95 * safety_margin)
    max_p99 = int(p99 * safety_margin)
    max_error_rate = min(error_rate * safety_margin, 0.05)  # 최대 5%

    return {
        "version": "v2",
        "budget": {
            "allow_levels": ["ok"],
            "max_spent": 0.5
        },
        "quota": {
            "forbid_actions": {
                "tokens": ["deny", "throttle"]
            }
        },
        "anomaly": {
            "allow_spike": False
        },
        "latency": {
            "max_p95_ms": max_p95,
            "max_p99_ms": max_p99,
            "baseline_p95_ms": p95,
            "baseline_p99_ms": p99
        },
        "error": {
            "max_error_rate": round(max_error_rate, 4),
            "baseline_error_rate": round(error_rate, 4)
        },
        "witness": {
            "require_csv_sha256": True,
            "require_signature": True,
            "min_rows": 1,
            "min_samples": max(10, int(total * 0.01)),  # 최소 1% 샘플
            "window_sec": 3600  # 1시간 윈도우
        },
        "integrity": {
            "require_signature": True
        },
        "quorum": {
            "k": 2,
            "n": 3,
            "fail_closed_on_degrade": True
        },
        "meta": {
            "generated_from": "baseline_slo.py",
            "safety_margin": safety_margin,
            "baseline_total_requests": total,
            "baseline_error_count": errors
        }
    }

def aggregate_multi_evidence(evidence_paths: List[str]) -> Dict[str, Any]:
    """여러 Evidence 파일 통합"""
    all_p95 = []
    all_p99 = []
    total_requests = 0
    total_errors = 0

    for path in evidence_paths:
        metrics = parse_evidence_perf(path)
        if metrics.get("total_requests", 0) > 0:
            all_p95.append(metrics["latency_p95"])
            all_p99.append(metrics["latency_p99"])
            total_requests += metrics["total_requests"]
            total_errors += metrics["error_count"]

    if not all_p95:
        return {}

    return {
        "latency_p95": int(statistics.mean(all_p95)),
        "latency_p99": int(statistics.mean(all_p99)),
        "total_requests": total_requests,
        "error_count": total_errors,
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="실측 기반 SLO 생성")
    parser.add_argument("--evidence", required=True, help="Evidence JSON 파일 경로 (또는 디렉토리)")
    parser.add_argument("--out", required=True, help="출력 SLO 파일 경로")
    parser.add_argument("--margin", type=float, default=1.2, help="안전 마진 (기본 1.2 = 20%%)")
    parser.add_argument("--merge", action="store_true", help="디렉토리 내 모든 Evidence 병합")
    args = parser.parse_args()

    evidence_path = Path(args.evidence)

    if args.merge and evidence_path.is_dir():
        # 디렉토리 내 모든 Evidence 파일 병합
        evidence_files = list(evidence_path.glob("*.json"))
        if not evidence_files:
            print(f"No evidence files found in {evidence_path}", file=sys.stderr)
            return 1
        print(f"Merging {len(evidence_files)} evidence files...", file=sys.stderr)
        baseline = aggregate_multi_evidence([str(f) for f in evidence_files])
    else:
        # 단일 파일
        baseline = parse_evidence_perf(str(evidence_path))

    if not baseline:
        print("Failed to extract baseline metrics", file=sys.stderr)
        return 1

    slo = generate_slo_v2(baseline, safety_margin=args.margin)

    # 출력
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(slo, f, indent=2, ensure_ascii=False)

    print(f"✓ SLO v2 generated: {out_path}", file=sys.stderr)
    print(f"  - P95: {baseline['latency_p95']}ms → {slo['latency']['max_p95_ms']}ms", file=sys.stderr)
    print(f"  - P99: {baseline['latency_p99']}ms → {slo['latency']['max_p99_ms']}ms", file=sys.stderr)
    print(f"  - Error rate: {baseline['error_count']}/{baseline['total_requests']} → {slo['error']['max_error_rate']}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
