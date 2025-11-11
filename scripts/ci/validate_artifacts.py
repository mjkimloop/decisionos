#!/usr/bin/env python3
import argparse, json, sys, urllib.request, urllib.error

OK_CODES = {200, 201, 202, 204, 302, 304}

def is_url_ok(url: str, timeout: float = 5.0) -> bool:
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode() in OK_CODES
    except urllib.error.HTTPError as e:
        if e.code in OK_CODES:
            return True
        return False
    except Exception:
        # fallback GET once
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.getcode() in OK_CODES
        except Exception:
            return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="JSON file containing artifact URLs")
    args = ap.parse_args()

    with open(args.manifest, "r", encoding="utf-8") as f:
        data = json.load(f)

    urls = []
    # support both dict of {name:url} and list of urls
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, str):
                urls.append((k, v))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            if isinstance(v, str):
                urls.append((str(i), v))

    bad = []
    for name, url in urls:
        ok = is_url_ok(url)
        print(f"[validate] {name}: {url} -> {'OK' if ok else 'FAIL'}")
        if not ok:
            bad.append((name, url))

    if bad:
        print("Artifact link validation failed:", file=sys.stderr)
        for n, u in bad:
            print(f" - {n}: {u}", file=sys.stderr)
        sys.exit(2)
    print("All artifact links valid.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
