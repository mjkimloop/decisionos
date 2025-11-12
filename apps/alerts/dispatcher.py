"""
Alert Dispatcher
Slack/Webhook 라우팅 및 발행
"""
import json
import os
import requests
from typing import Dict, Any, List, Optional


def load_routes(path: str = "configs/alerts/routes.json") -> Dict[str, Any]:
    """라우팅 설정 로드"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Routes config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_playbooks(path: str = "configs/playbooks/actions.json") -> Dict[str, List[str]]:
    """플레이북 액션 로드"""
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_playbook_actions(reason: str, playbooks: Dict[str, List[str]]) -> List[str]:
    """reason 코드에 해당하는 플레이북 액션 가져오기"""
    # 정확한 매치 시도
    if reason in playbooks:
        return playbooks[reason]

    # 부분 매치 시도 (reason이 키를 포함하는 경우)
    for key in playbooks:
        if key in reason or reason in key:
            return playbooks[key]

    # 기본값
    return playbooks.get("default", ["Open incident ticket", "Notify on-call"])


def dispatch_alert(
    level: str,
    reason: str,
    message: str,
    routes: Dict[str, Any],
    dry_run: bool = False
) -> bool:
    """
    Slack/Webhook으로 알림 발행

    Args:
        level: 심각도 (info/warn/critical)
        reason: 이유 코드
        message: 메시지 본문
        routes: 라우팅 설정
        dry_run: True이면 실제 발송 안함

    Returns:
        성공 여부
    """
    # 필터 적용
    filters = routes.get("filters", {})
    min_severity = filters.get("min_severity", "info")
    severity_order = {"info": 0, "warn": 1, "critical": 2}

    if severity_order.get(level, 0) < severity_order.get(min_severity, 0):
        print(f"[SKIP] Alert level '{level}' below min_severity '{min_severity}'")
        return True

    # 플레이북 액션 추가
    playbooks = load_playbooks()
    actions = get_playbook_actions(reason, playbooks)

    full_message = f"[{level.upper()}] {reason}\n{message}\n\n**Playbook Actions:**\n"
    for i, action in enumerate(actions, 1):
        full_message += f"{i}. {action}\n"

    # Slack 발송
    slack_config = routes.get("slack", {})
    if slack_config:
        webhook_url = os.getenv(slack_config.get("webhook_env", ""), "")
        channel = slack_config.get("channel", "#decisionos-alerts")

        if webhook_url and not dry_run:
            try:
                payload = {
                    "channel": channel,
                    "username": "DecisionOS Alert",
                    "text": full_message,
                    "icon_emoji": ":warning:" if level == "warn" else ":rotating_light:"
                }
                resp = requests.post(webhook_url, json=payload, timeout=5)
                resp.raise_for_status()
                print(f"[OK] Slack alert sent to {channel}")
            except Exception as e:
                print(f"[ERROR] Failed to send Slack alert: {e}")
                return False
        else:
            print(f"[DRY-RUN] Would send Slack alert to {channel}")

    # Webhook 발송
    webhooks = routes.get("webhook", [])
    for wh in webhooks:
        wh_name = wh.get("name", "unknown")
        wh_url = os.getenv(wh.get("url_env", ""), "")

        if wh_url and not dry_run:
            try:
                payload = {
                    "level": level,
                    "reason": reason,
                    "message": message,
                    "actions": actions
                }
                resp = requests.post(wh_url, json=payload, timeout=5)
                resp.raise_for_status()
                print(f"[OK] Webhook alert sent to {wh_name}")
            except Exception as e:
                print(f"[ERROR] Failed to send webhook alert to {wh_name}: {e}")
                return False
        else:
            print(f"[DRY-RUN] Would send webhook alert to {wh_name}")

    return True


def main():
    """CLI 엔트리포인트"""
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="warn", choices=["info", "warn", "critical"])
    ap.add_argument("--reason", default="test:alert")
    ap.add_argument("--message", default="Test alert message")
    ap.add_argument("--dry-run", default="true", choices=["true", "false"])
    args = ap.parse_args()

    dry_run = args.dry_run == "true"

    routes = load_routes()
    success = dispatch_alert(args.level, args.reason, args.message, routes, dry_run)

    if not success:
        exit(1)


if __name__ == "__main__":
    main()
