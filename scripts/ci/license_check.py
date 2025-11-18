from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List

try:
    import pkg_resources
except ImportError:  # pragma: no cover
    pkg_resources = None


def parse_requirements(path: str) -> List[str]:
    reqs: List[str] = []
    file = Path(path)
    if not file.exists():
        return reqs
    for line in file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        reqs.append(line.split("==")[0])
    return reqs


def license_for(dist_name: str) -> str:
    if not pkg_resources:
        return "UNKNOWN"
    try:
        dist = pkg_resources.get_distribution(dist_name)
    except pkg_resources.DistributionNotFound:
        return "UNKNOWN"
    for metadata_name in ("METADATA", "PKG-INFO"):
        if dist.has_metadata(metadata_name):
            content = dist.get_metadata(metadata_name)
            for line in content.splitlines():
                if line.lower().startswith("license:"):
                    return line.split(":", 1)[1].strip()
    return "UNKNOWN"


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple license check")
    parser.add_argument("--requirements", default="requirements.txt")
    parser.add_argument("--allow", default="MIT,BSD,Apache-2.0")
    parser.add_argument("--out", default="var/ci/licenses.json")
    args = parser.parse_args()

    allow = {token.strip() for token in args.allow.split(",") if token.strip()}
    report: Dict[str, str] = {}
    for pkg in parse_requirements(args.requirements):
        report[pkg] = license_for(pkg)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        "{\n" + ",\n".join(f'  "{pkg}": "{lic}"' for pkg, lic in report.items()) + "\n}",
        encoding="utf-8",
    )
    print(f"[license_check] wrote {args.out}")

    for pkg, lic in report.items():
        normalized = lic.split()[0]
        if normalized not in allow:
            print(f"[license_check] disallowed license {lic} for {pkg}")
            sys.exit(1)


if __name__ == "__main__":
    main()
