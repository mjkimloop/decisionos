"""
Rule-Based Reason Summary
규칙 기반 reason 요약 (Top-N + 압축)
"""
from typing import List, Dict, Any
from collections import Counter


def summarize_reasons(
    items: List[Dict[str, Any]],
    top_n: int = 5,
    compress_threshold: int = 3
) -> Dict[str, Any]:
    """
    규칙 기반 reason 요약

    Args:
        items: 아이템 목록 (각 아이템은 label, group, value 필드 포함)
        top_n: Top-N 라벨/그룹 개수
        compress_threshold: 나머지 압축 임계값 (이 값 이상일 때 [+others] 추가)

    Returns:
        요약 결과 딕셔너리
        {
            "top_labels": [{"label": "...", "count": N}, ...],
            "top_groups": [{"group": "...", "count": N}, ...],
            "total_items": N,
            "unique_labels": N,
            "unique_groups": N
        }
    """
    # 1. 라벨별/그룹별 집계
    label_counts = Counter()
    group_counts = Counter()

    for item in items:
        label = item.get("label", "")
        group = item.get("group", "")
        value = item.get("value", 1)

        if label:
            label_counts[label] += value
        if group:
            group_counts[group] += value

    # 2. Top-N 추출
    top_labels = [
        {"label": label, "count": count}
        for label, count in label_counts.most_common(top_n)
    ]
    top_groups = [
        {"group": group, "count": count}
        for group, count in group_counts.most_common(top_n)
    ]

    # 3. 나머지 압축
    top_label_set = {item["label"] for item in top_labels}
    top_group_set = {item["group"] for item in top_groups}

    other_labels_count = sum(
        count for label, count in label_counts.items()
        if label not in top_label_set
    )
    other_groups_count = sum(
        count for group, count in group_counts.items()
        if group not in top_group_set
    )

    if other_labels_count >= compress_threshold:
        top_labels.append({"label": "[+others]", "count": other_labels_count})

    if other_groups_count >= compress_threshold:
        top_groups.append({"group": "[+others]", "count": other_groups_count})

    # 4. 결과 반환
    return {
        "top_labels": top_labels,
        "top_groups": top_groups,
        "total_items": len(items),
        "unique_labels": len(label_counts),
        "unique_groups": len(group_counts)
    }
