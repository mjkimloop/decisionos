#!/usr/bin/env python3
"""Key rotation countdown checker with automated alerts.

Monitors key rotation deadlines and sends alerts when keys are approaching
retirement or grace period expiration.

Usage:
    python scripts/ops/check_key_rotation_countdown.py
    python scripts/ops/check_key_rotation_countdown.py --warn-days 7 --critical-days 3

Environment:
    DECISIONOS_POLICY_KEYS      Policy key configuration (JSON)
    SLACK_WEBHOOK_URL           Slack webhook for alerts
    ROTATION_WARN_DAYS          Warning threshold (default: 7)
    ROTATION_CRITICAL_DAYS      Critical threshold (default: 3)

Exit codes:
    0: All keys healthy
    1: Warning (keys approaching expiration)
    2: Critical (keys expiring soon, action required)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

# Key states
STATE_ACTIVE = "active"
STATE_GRACE = "grace"
STATE_RETIRED = "retired"

# Alert levels
LEVEL_OK = "ok"
LEVEL_WARNING = "warning"
LEVEL_CRITICAL = "critical"


def load_keys() -> list[dict[str, Any]]:
    """Load key configuration from environment."""
    keys_json = os.environ.get("DECISIONOS_POLICY_KEYS", "[]")
    try:
        keys = json.loads(keys_json)
        return keys if isinstance(keys, list) else []
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse DECISIONOS_POLICY_KEYS: {e}", file=sys.stderr)
        return []


def parse_iso_date(date_str: str | None) -> datetime | None:
    """Parse ISO date string to datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def check_key_expiration(key: dict[str, Any], warn_days: int, critical_days: int) -> dict[str, Any]:
    """Check if key is approaching expiration."""
    key_id = key.get("key_id", "unknown")
    state = key.get("state", "unknown")
    rotated_at = parse_iso_date(key.get("rotated_at"))
    expires_at = parse_iso_date(key.get("expires_at"))
    grace_until = parse_iso_date(key.get("grace_until"))

    now = datetime.now(timezone.utc)
    result = {
        "key_id": key_id,
        "state": state,
        "level": LEVEL_OK,
        "message": "OK",
        "days_remaining": None,
    }

    # Check expiration based on state
    if state == STATE_ACTIVE:
        if expires_at:
            days_remaining = (expires_at - now).days
            result["days_remaining"] = days_remaining

            if days_remaining <= critical_days:
                result["level"] = LEVEL_CRITICAL
                result["message"] = f"Active key expires in {days_remaining} days (CRITICAL)"
            elif days_remaining <= warn_days:
                result["level"] = LEVEL_WARNING
                result["message"] = f"Active key expires in {days_remaining} days"
            else:
                result["message"] = f"Active key expires in {days_remaining} days"

    elif state == STATE_GRACE:
        if grace_until:
            days_remaining = (grace_until - now).days
            result["days_remaining"] = days_remaining

            if days_remaining <= 0:
                result["level"] = LEVEL_CRITICAL
                result["message"] = f"Grace period EXPIRED ({abs(days_remaining)} days ago)"
            elif days_remaining <= critical_days:
                result["level"] = LEVEL_CRITICAL
                result["message"] = f"Grace period expires in {days_remaining} days (CRITICAL)"
            elif days_remaining <= warn_days:
                result["level"] = LEVEL_WARNING
                result["message"] = f"Grace period expires in {days_remaining} days"
            else:
                result["message"] = f"Grace period expires in {days_remaining} days"

    elif state == STATE_RETIRED:
        result["message"] = "Retired (no longer used)"

    return result


def send_slack_alert(checks: list[dict[str, Any]], level: str) -> None:
    """Send Slack alert for key rotation warnings."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("[WARN] SLACK_WEBHOOK_URL not set (skipping alert)")
        return

    # Build alert message
    emoji = "⚠️" if level == LEVEL_WARNING else "🚨"
    color = "warning" if level == LEVEL_WARNING else "danger"

    fields = []
    for check in checks:
        if check["level"] in (LEVEL_WARNING, LEVEL_CRITICAL):
            fields.append({
                "title": check["key_id"],
                "value": check["message"],
                "short": False
            })

    payload = {
        "attachments": [
            {
                "color": color,
                "title": f"{emoji} Key Rotation Alert",
                "text": "Keys approaching expiration - rotation required",
                "fields": fields,
                "footer": "DecisionOS Key Rotation Monitor",
                "ts": int(datetime.now(timezone.utc).timestamp())
            }
        ]
    }

    try:
        import urllib.request
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print("[INFO] Slack alert sent successfully")
            else:
                print(f"[WARN] Slack alert failed: HTTP {response.status}")
    except Exception as e:
        print(f"[ERROR] Failed to send Slack alert: {e}", file=sys.stderr)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check key rotation countdown")
    parser.add_argument("--warn-days", type=int, default=7, help="Warning threshold (days)")
    parser.add_argument("--critical-days", type=int, default=3, help="Critical threshold (days)")
    parser.add_argument("--send-alerts", action="store_true", help="Send Slack alerts")
    args = parser.parse_args()

    # Override from environment
    warn_days = int(os.environ.get("ROTATION_WARN_DAYS", args.warn_days))
    critical_days = int(os.environ.get("ROTATION_CRITICAL_DAYS", args.critical_days))

    print("=" * 60)
    print("  KEY ROTATION COUNTDOWN CHECK")
    print(f"  Warning threshold: {warn_days} days")
    print(f"  Critical threshold: {critical_days} days")
    print("=" * 60)

    # Load keys
    keys = load_keys()
    if not keys:
        print("[WARN] No keys found in DECISIONOS_POLICY_KEYS")
        return 0

    print(f"\nChecking {len(keys)} keys...\n")

    # Check each key
    checks = []
    for key in keys:
        check = check_key_expiration(key, warn_days, critical_days)
        checks.append(check)

        # Print status
        icon = {
            LEVEL_OK: "✓",
            LEVEL_WARNING: "⚠",
            LEVEL_CRITICAL: "✗"
        }.get(check["level"], "?")

        print(f"{icon} {check['key_id']:20s} [{check['state']:8s}] {check['message']}")

    # Determine overall status
    has_critical = any(c["level"] == LEVEL_CRITICAL for c in checks)
    has_warning = any(c["level"] == LEVEL_WARNING for c in checks)

    print("\n" + "=" * 60)

    if has_critical:
        print("  ✗✗✗ CRITICAL: Key rotation required immediately ✗✗✗")
        print("=" * 60)
        exit_code = 2

        # Send alert
        if args.send_alerts:
            send_slack_alert(checks, LEVEL_CRITICAL)

    elif has_warning:
        print("  ⚠⚠⚠ WARNING: Key rotation required soon ⚠⚠⚠")
        print("=" * 60)
        exit_code = 1

        # Send alert
        if args.send_alerts:
            send_slack_alert(checks, LEVEL_WARNING)

    else:
        print("  ✓✓✓ All keys healthy ✓✓✓")
        print("=" * 60)
        exit_code = 0

    # Print recommended actions
    if has_critical or has_warning:
        print("\nRecommended actions:")
        print("  1. Generate new key: python scripts/policy/generate_key.py")
        print("  2. Add to DECISIONOS_POLICY_KEYS with state=grace")
        print("  3. Sign new policies: python scripts/policy/sign.py --key-id new-key")
        print("  4. Promote to active: Update key state to 'active'")
        print("  5. Retire old key: Update key state to 'retired' after grace period")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
