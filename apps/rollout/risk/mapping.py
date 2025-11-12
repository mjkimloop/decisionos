"""
Risk Score to Action Mapping Utility
score → action 맵핑 유틸리티
"""
from typing import Dict, Any, List, Optional


def find_action_for_score(score: float, mapping: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    맵핑 테이블에서 score에 해당하는 액션 찾기

    Args:
        score: 리스크 점수
        mapping: range와 action으로 구성된 맵핑 테이블
                 [{"range": [min, max], "action": {...}}, ...]

    Returns:
        해당하는 action 딕셔너리, 없으면 None
    """
    for entry in mapping:
        range_spec = entry.get("range", [0.0, 0.0])
        if len(range_spec) != 2:
            continue

        range_min, range_max = range_spec

        if range_min <= score < range_max:
            return entry.get("action")

    # 범위를 벗어나면 None
    return None
