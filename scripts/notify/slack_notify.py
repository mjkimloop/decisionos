"""
Slack Notification
게이트 결과/톱임팩트/증빙 링크 알림
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.request
from typing import Dict, Any, List


def load_config(config_path: str = "configs/alerts/slack.json") -> Dict[str, Any]:
    """Load Slack config"""
    if not os.path.exists(config_path):
        return {
            "webhook": "",
            "channel": "",
            "mention": "@here",
            "severity_map": {
                "fail": ":rotating_light:",
                "warn": ":warning:",
                "pass": ":white_check_mark:"
            }
        }

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def send_slack_message(webhook_url: str, payload: Dict[str, Any]) -> bool:
    """Send message to Slack webhook"""
    if not webhook_url:
        print("[SKIP] Slack webhook not configured")
        return False

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception as e:
        print(f"[ERROR] Slack notification failed: {e}")
        return False


def format_gate_result(
    status: str,
    summary: str,
    artifacts_url: str = "",
    evidence_link: str = "",
    reasons: List[str] = None
) -> Dict[str, Any]:
    """
    Format gate result message

    Args:
        status: "pass", "warn", "fail"
        summary: Summary message
        artifacts_url: CI artifacts URL
        evidence_link: Evidence file URL
        reasons: List of reason codes

    Returns:
        Slack message payload
    """
    config = load_config()
    severity_map = config.get("severity_map", {})
    icon = severity_map.get(status, ":question:")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{icon} Gate {status.upper()}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": summary
            }
        }
    ]

    # Add reasons if any
    if reasons:
        reason_text = "\n".join(f"• `{r}`" for r in reasons[:3])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Top Reasons:*\n{reason_text}"
            }
        })

    # Add links
    if artifacts_url or evidence_link:
        links = []
        if artifacts_url:
            links.append(f"<{artifacts_url}|CI Artifacts>")
        if evidence_link:
            links.append(f"<{evidence_link}|Evidence>")

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": " | ".join(links)
                }
            ]
        })

    return {"blocks": blocks}


def main(argv: List[str] = None) -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True, choices=["pass", "warn", "fail"])
    parser.add_argument("--summary", required=True)
    parser.add_argument("--artifacts-url", default="")
    parser.add_argument("--evidence-link", default="")
    parser.add_argument("--reasons", nargs="*", default=[])
    parser.add_argument("--config", default="configs/alerts/slack.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    webhook = os.environ.get("SLACK_WEBHOOK_URL", config.get("webhook", ""))

    if not webhook:
        print("[SKIP] No Slack webhook configured")
        return 0

    payload = format_gate_result(
        status=args.status,
        summary=args.summary,
        artifacts_url=args.artifacts_url,
        evidence_link=args.evidence_link,
        reasons=args.reasons
    )

    if args.dry_run:
        print("[DRY-RUN] Would send to Slack:")
        print(json.dumps(payload, indent=2))
        return 0

    success = send_slack_message(webhook, payload)
    if success:
        print("[OK] Slack notification sent")
        return 0
    else:
        print("[ERROR] Slack notification failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
