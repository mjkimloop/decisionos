from __future__ import annotations

import argparse
import random
from pathlib import Path

from apps.obs.witness.shadow import ShadowRecorder, mirror_request


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="dosctl shadow capture")
    parser.add_argument("--out", default="var/shadow", help="output directory for control/canary CSV")
    parser.add_argument("--samples", type=int, default=500, help="number of synthetic requests")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    recorder = ShadowRecorder(out_dir / "control.csv", out_dir / "canary.csv")

    random.seed(42)
    for i in range(args.samples):
        bucket = "canary" if random.random() < 0.2 else "control"
        if i % 400 == 0:
            status = 503
        elif i % 233 == 0:
            status = 429
        else:
            status = 200
        latency = random.gauss(100 if bucket == "control" else 108, 15)
        mirror_request(
            bucket,
            status,
            max(latency, 1),
            recorder=recorder,
            sample_rate=1.0,
            signature_error=False,
            payload="sample-payload",
        )

    print(f"[dosctl] shadow capture complete -> {out_dir}")


if __name__ == "__main__":
    main()
