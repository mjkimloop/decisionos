from __future__ import annotations

from apps.ops.reports.reason_trend import aggregate_reason_trend, save_trend_reports


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Daily reason trend aggregation")
    parser.add_argument("--dir", default="var/evidence")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--topK", type=int, default=10)  # reserved for future use
    parser.add_argument("--out", default="var/reports")
    args = parser.parse_args()

    trend = aggregate_reason_trend(args.dir, args.days)
    save_trend_reports(
        trend,
        out_json=f"{args.out}/reason_trend.json",
        out_md=f"{args.out}/reason_trend.md",
    )


if __name__ == "__main__":
    main()
