from __future__ import annotations
from typing import Dict, Any, List
import os, json

def load_from_ssm() -> List[Dict[str, Any]]:
    """
    선택적 SSM 로더. boto3 미존재/환경 미설정 시 빈 배열.
    기대 포맷: [{"key_id":"k1","secret":"base64|hex|utf8", "state":"active"}, ...]
    """
    path = os.getenv("DECISIONOS_KMS_SSM_PATH")
    if not path:
        return []
    try:
        import boto3
    except Exception:
        return []
    ssm = boto3.client("ssm", region_name=os.getenv("AWS_REGION", "ap-northeast-2"))
    resp = ssm.get_parameter(Name=path, WithDecryption=True)
    txt = resp["Parameter"]["Value"]
    return json.loads(txt)

__all__ = ["load_from_ssm"]
