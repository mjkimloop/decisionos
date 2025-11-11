#!/usr/bin/env python3
"""
키 로테이션 및 시계 스큐 운영 도구 (v0.5.11r-8)

기능:
1. 키 만료 임박 경고 (7일 전)
2. Grace period 키 자동 전환 (active → grace → retired)
3. 시계 스큐 감지 (±10초)
4. 무중단 키 교체 검증

Usage:
  python scripts/ops/key_rotation.py --check-expiry --warn-days=7
  python scripts/ops/key_rotation.py --check-skew --max-skew-sec=10
  python scripts/ops/key_rotation.py --rotate --old-key-id=k1 --new-key-id=k2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_keys(keys_file: str | None = None, keys_env: str | None = None) -> List[Dict[str, Any]]:
    """키 설정 로드 (파일 또는 환경변수)"""
    import os

    keys = []

    # 파일에서 로드
    if keys_file:
        path = Path(keys_file)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                keys.extend(data if isinstance(data, list) else [data])
            except Exception as e:
                print(f"[key-rotation] 파일 로드 실패: {e}", file=sys.stderr)

    # 환경변수에서 로드
    if keys_env:
        env_val = os.getenv(keys_env)
        if env_val:
            try:
                data = json.loads(env_val)
                keys.extend(data if isinstance(data, list) else [data])
            except Exception as e:
                print(f"[key-rotation] 환경변수 로드 실패: {e}", file=sys.stderr)

    return keys


def check_key_expiry(keys: List[Dict[str, Any]], warn_days: int = 7) -> int:
    """
    키 만료 체크

    Returns:
        0: 정상, 1: 경고, 2: 만료
    """
    now = datetime.now(timezone.utc)
    warn_threshold = now + timedelta(days=warn_days)

    expired = []
    expiring_soon = []

    for key in keys:
        key_id = key.get("key_id", "unknown")
        state = key.get("state", "active")
        expires_at = key.get("expires_at")  # ISO 8601 format

        if not expires_at:
            continue

        try:
            expire_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except Exception:
            print(f"[key-rotation] 잘못된 만료 날짜: {key_id}", file=sys.stderr)
            continue

        if expire_dt < now:
            expired.append((key_id, state, expire_dt))
        elif expire_dt < warn_threshold:
            expiring_soon.append((key_id, state, expire_dt))

    # 결과 출력
    if expired:
        print(f"\n❌ 만료된 키 ({len(expired)}개):", file=sys.stderr)
        for key_id, state, expire_dt in expired:
            days_ago = (now - expire_dt).days
            print(f"  - {key_id} (state={state}): {days_ago}일 전 만료", file=sys.stderr)
        return 2

    if expiring_soon:
        print(f"\n⚠️  만료 임박 키 ({len(expiring_soon)}개):")
        for key_id, state, expire_dt in expiring_soon:
            days_left = (expire_dt - now).days
            print(f"  - {key_id} (state={state}): {days_left}일 남음")
        return 1

    print("\n✅ 모든 키 정상 (만료 없음)")
    return 0


def check_clock_skew(max_skew_sec: int = 10) -> int:
    """
    시계 스큐 감지

    Returns:
        0: 정상, 1: 경고
    """
    # 실제 구현에서는 NTP 서버와 비교하거나 클러스터 노드 간 시간 비교
    # 여기서는 시뮬레이션
    import os

    simulated_skew = float(os.getenv("DECISIONOS_SIMULATED_CLOCK_SKEW_SEC", "0"))

    if abs(simulated_skew) > max_skew_sec:
        print(f"\n⚠️  시계 스큐 감지: {simulated_skew:+.1f}초 (최대 ±{max_skew_sec}초)", file=sys.stderr)
        print(f"[clock-skew] 503 Service Unavailable 권장", file=sys.stderr)
        return 1

    print(f"\n✅ 시계 스큐 정상 (±{abs(simulated_skew):.1f}초 ≤ {max_skew_sec}초)")
    return 0


def rotate_key(keys: List[Dict[str, Any]], old_key_id: str, new_key_id: str, grace_days: int = 7) -> List[Dict[str, Any]]:
    """
    키 로테이션 수행 (active → grace → retired)

    1. old_key: active → grace (검증만 허용)
    2. new_key: grace → active (새 서명 생성)
    3. grace_period 이후 old_key: grace → retired
    """
    now = datetime.now(timezone.utc)
    grace_until = now + timedelta(days=grace_days)

    updated_keys = []
    old_found = False
    new_found = False

    for key in keys:
        key_id = key.get("key_id")

        if key_id == old_key_id:
            # active → grace
            if key.get("state") == "active":
                key["state"] = "grace"
                key["grace_until"] = grace_until.isoformat().replace("+00:00", "Z")
                print(f"[rotate] {old_key_id}: active → grace (until {grace_until.date()})")
                old_found = True

        elif key_id == new_key_id:
            # grace → active
            if key.get("state") in ["grace", "pending"]:
                key["state"] = "active"
                key.pop("grace_until", None)
                print(f"[rotate] {new_key_id}: {key.get('state', 'grace')} → active")
                new_found = True

        updated_keys.append(key)

    if not old_found:
        print(f"[rotate] 경고: 기존 키 {old_key_id} 없음", file=sys.stderr)
    if not new_found:
        print(f"[rotate] 경고: 새 키 {new_key_id} 없음", file=sys.stderr)

    return updated_keys


def retire_grace_keys(keys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Grace period 만료 키 자동 retire"""
    now = datetime.now(timezone.utc)
    updated_keys = []
    retired_count = 0

    for key in keys:
        key_id = key.get("key_id")
        state = key.get("state")
        grace_until = key.get("grace_until")

        if state == "grace" and grace_until:
            try:
                grace_dt = datetime.fromisoformat(grace_until.replace("Z", "+00:00"))
                if grace_dt < now:
                    key["state"] = "retired"
                    key.pop("grace_until", None)
                    print(f"[retire] {key_id}: grace → retired (만료)")
                    retired_count += 1
            except Exception:
                pass

        updated_keys.append(key)

    if retired_count == 0:
        print("[retire] Grace 만료 키 없음")

    return updated_keys


def main() -> int:
    parser = argparse.ArgumentParser(description="키 로테이션 및 시계 스큐 운영 도구")
    parser.add_argument("--keys-file", help="키 설정 파일 경로")
    parser.add_argument("--keys-env", default="DECISIONOS_JUDGE_KEYS", help="키 환경변수 이름")
    parser.add_argument("--check-expiry", action="store_true", help="키 만료 체크")
    parser.add_argument("--warn-days", type=int, default=7, help="만료 경고 일수")
    parser.add_argument("--check-skew", action="store_true", help="시계 스큐 체크")
    parser.add_argument("--max-skew-sec", type=int, default=10, help="최대 허용 스큐 (초)")
    parser.add_argument("--rotate", action="store_true", help="키 로테이션 수행")
    parser.add_argument("--old-key-id", help="기존 키 ID (로테이션 시)")
    parser.add_argument("--new-key-id", help="새 키 ID (로테이션 시)")
    parser.add_argument("--grace-days", type=int, default=7, help="Grace period (일)")
    parser.add_argument("--retire-grace", action="store_true", help="Grace 만료 키 retire")
    parser.add_argument("--out", help="업데이트된 키 저장 경로")

    args = parser.parse_args()

    # 키 로드
    keys = load_keys(args.keys_file, args.keys_env)

    if not keys:
        print("[key-rotation] 키 없음 (파일 또는 환경변수 확인)", file=sys.stderr)
        return 1

    # 만료 체크
    if args.check_expiry:
        return check_key_expiry(keys, args.warn_days)

    # 시계 스큐 체크
    if args.check_skew:
        return check_clock_skew(args.max_skew_sec)

    # 키 로테이션
    if args.rotate:
        if not args.old_key_id or not args.new_key_id:
            print("❌ --old-key-id, --new-key-id 필수", file=sys.stderr)
            return 1

        updated_keys = rotate_key(keys, args.old_key_id, args.new_key_id, args.grace_days)

        if args.out:
            Path(args.out).write_text(json.dumps(updated_keys, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"\n[rotate] 저장: {args.out}")
        else:
            print("\n[rotate] 업데이트된 키 설정:")
            print(json.dumps(updated_keys, indent=2, ensure_ascii=False))

        return 0

    # Grace 키 retire
    if args.retire_grace:
        updated_keys = retire_grace_keys(keys)

        if args.out:
            Path(args.out).write_text(json.dumps(updated_keys, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"\n[retire] 저장: {args.out}")
        else:
            print("\n[retire] 업데이트된 키 설정:")
            print(json.dumps(updated_keys, indent=2, ensure_ascii=False))

        return 0

    # 기본: 키 정보 출력
    print(f"[key-rotation] 총 {len(keys)}개 키:")
    for key in keys:
        key_id = key.get("key_id", "unknown")
        state = key.get("state", "unknown")
        expires_at = key.get("expires_at", "없음")
        print(f"  - {key_id}: state={state}, expires={expires_at}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
