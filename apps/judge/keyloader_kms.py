from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


def _coerce_entry(value: str, name: str) -> List[Dict[str, Any]]:
    base_id = name.split("/")[-1] or "key"
    result: List[Dict[str, Any]] = []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        parsed.setdefault("key_id", base_id)
        parsed.setdefault("state", "active")
        result.append(parsed)
    elif isinstance(parsed, list):
        for idx, item in enumerate(parsed):
            if not isinstance(item, dict):
                continue
            item.setdefault("key_id", item.get("key_id") or f"{base_id}-{idx}")
            item.setdefault("state", "active")
            result.append(item)
    else:
        result.append({"key_id": base_id, "secret": value, "state": "active"})
    return result


def load_from_ssm(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    KMS/SSM Key Loader
    ------------------
    - Path: /decisionos/${env}/keys/*
    - Return: [{"key_id":"k1","secret":"...","state":"active"}, ...]
    - Gracefully handles missing boto3/env.
    """
    path = path or os.getenv("DECISIONOS_KMS_SSM_PATH")
    if not path:
        return []
    try:
        import boto3  # type: ignore
    except Exception:
        return []

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-northeast-2"
    client = boto3.client("ssm", region_name=region)
    params: List[Dict[str, Any]] = []
    next_token: Optional[str] = None
    try:
        while True:
            request = {
                "Path": path,
                "Recursive": True,
                "WithDecryption": True,
                "MaxResults": 10,
            }
            if next_token:
                request["NextToken"] = next_token
            resp = client.get_parameters_by_path(**request)
            params.extend(resp.get("Parameters", []))
            next_token = resp.get("NextToken")
            if not next_token:
                break
    except Exception:
        return []

    keys: List[Dict[str, Any]] = []
    for param in params:
        name = param.get("Name", "key")
        value = param.get("Value", "")
        keys.extend(_coerce_entry(value, name))
    return keys


__all__ = ["load_from_ssm"]
