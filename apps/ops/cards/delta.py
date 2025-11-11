from __future__ import annotations
from typing import Any, Dict, List

def _index_buckets(buckets: List[dict]) -> dict:
    """버킷 리스트를 ts/bucket/id 키로 인덱싱"""
    idx = {}
    for b in buckets or []:
        k = b.get("ts") or b.get("bucket") or b.get("id") or b.get("end")
        if k is not None:
            idx[str(k)] = b
    return idx

def compute_delta_summary(prev: Dict[str, Any], curr: Dict[str, Any]) -> Dict[str, Any]:
    """
    이전 요약과 현재 요약 간의 증분(delta) 계산

    Args:
        prev: 이전 ETag의 스냅샷 페이로드
        curr: 현재 계산된 전체 요약

    Returns:
        delta 모드 응답 (변경분만 포함)
    """
    out: Dict[str, Any] = {"delta_mode": "shallow"}

    # 1) shallow 필드 변화만 추출
    changed = {}
    keys = set((prev or {}).keys()) | set((curr or {}).keys())
    for k in keys:
        if k == "buckets":  # 버킷은 별도 처리
            continue
        prev_val = (prev or {}).get(k)
        curr_val = (curr or {}).get(k)
        if prev_val != curr_val:
            changed[k] = curr_val

    out["changed_fields"] = changed

    # 2) buckets 변화 (추가/변경/삭제)
    pb = _index_buckets((prev or {}).get("buckets", []) or [])
    cb = _index_buckets((curr or {}).get("buckets", []) or [])
    added, changed_b, removed = [], [], []

    for k, v in cb.items():
        if k not in pb:
            added.append(v)
        elif pb[k] != v:
            changed_b.append(v)

    for k, v in pb.items():
        if k not in cb:
            removed.append({"bucket": k, "status": "removed"})

    out["buckets_delta"] = {
        "added": added,
        "changed": changed_b,
        "removed": removed,
    }

    # 3) 메타데이터 유지
    out["catalog_sha"] = curr.get("catalog_sha")
    out["window"] = curr.get("window")
    out["palette"] = curr.get("palette")

    return out

def same_window(prev: Dict[str, Any], curr: Dict[str, Any]) -> bool:
    """
    두 요약이 동일한 시간 윈도우를 사용하는지 확인

    Args:
        prev: 이전 요약
        curr: 현재 요약

    Returns:
        동일한 윈도우면 True, 아니면 False
    """
    try:
        prev_window = prev.get("window", {})
        curr_window = curr.get("window", {})
        ps, pe = prev_window.get("start"), prev_window.get("end")
        cs, ce = curr_window.get("start"), curr_window.get("end")
        return (ps, pe) == (cs, ce)
    except Exception:
        return False
