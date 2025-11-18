#!/usr/bin/env python3
"""Display cutover readiness dashboard in CLI.

Usage:
    python scripts/ops/show_cutover_dashboard.py
    python scripts/ops/show_cutover_dashboard.py --watch
    python scripts/ops/show_cutover_dashboard.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from apps.ops.cards.cutover_readiness import (
    format_card_text,
    get_cutover_readiness_card,
)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Show cutover readiness dashboard")
    parser.add_argument("--watch", action="store_true", help="Watch mode (refresh every 10s)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--interval", type=int, default=10, help="Watch interval (seconds)")
    args = parser.parse_args()

    try:
        if args.watch:
            print("[Cutover Dashboard - Watch Mode]")
            print(f"[Refresh interval: {args.interval}s, Press Ctrl+C to exit]\n")

            while True:
                # Clear screen (ANSI escape code)
                print("\033[2J\033[H", end="")

                # Get card
                card = get_cutover_readiness_card()

                if args.json:
                    output = {
                        "overall_state": card.overall_state,
                        "go_no_go": card.go_no_go,
                        "timestamp": card.timestamp,
                        "checks": [
                            {
                                "name": c.name,
                                "state": c.state,
                                "message": c.message,
                                "details": c.details,
                            }
                            for c in card.checks
                        ],
                        "metrics": card.metrics,
                    }
                    print(json.dumps(output, indent=2))
                else:
                    print(format_card_text(card))

                # Sleep
                time.sleep(args.interval)

        else:
            # Single shot
            card = get_cutover_readiness_card()

            if args.json:
                output = {
                    "overall_state": card.overall_state,
                    "go_no_go": card.go_no_go,
                    "timestamp": card.timestamp,
                    "checks": [
                        {
                            "name": c.name,
                            "state": c.state,
                            "message": c.message,
                            "details": c.details,
                        }
                        for c in card.checks
                    ],
                    "metrics": card.metrics,
                }
                print(json.dumps(output, indent=2))
            else:
                print(format_card_text(card))

            # Exit code based on Go/No-Go
            if card.go_no_go == "GO":
                return 0
            elif card.go_no_go == "PENDING":
                return 1
            else:  # NO-GO
                return 2

    except KeyboardInterrupt:
        print("\n[Exiting...]")
        return 0
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
