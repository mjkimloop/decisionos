#!/usr/bin/env python3
import argparse, json, os, subprocess, sys, time
from datetime import datetime, timezone

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def render_template(tpl: str, ctx: dict) -> str:
    out = tpl
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out

def build_reasons_rows(reasons):
    # reasons: list of {code, message, count}
    lines = []
    for r in reasons:
        lines.append(f"| `{r.get('code','')}` | {r.get('message','').replace('|','\|')} | {r.get('count',0)} |")
    return "\n".join(lines) if lines else "| — | — | 0 |"

def gh_post_comment(repo: str, pr: str, body: str):
    token = os.environ.get("GITHUB_TOKEN")
    if not token or not repo or not pr:
        print("[annotate] Missing GH context; writing file only.")
        return False
    cmd = [
        "gh", "api",
        f"repos/{repo}/issues/{pr}/comments",
        "-f", f"body={body}"
    ]
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    subprocess.check_call(cmd, env=env)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--status-json", required=True)
    ap.add_argument("--reasons-json", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default="")
    ap.add_argument("--pr", default="")
    args = ap.parse_args()

    with open(args.template, "r", encoding="utf-8") as f:
        tpl = f.read()

    status = load_json(args.status_json)
    reasons = load_json(args.reasons_json)
    manifest = load_json(args.manifest)

    ctx = {
        "STATUS": status.get("status","UNKNOWN").upper(),
        "STATUS_EMOJI": "✅" if status.get("status") == "pass" else "❌",
        "INFRA_STATUS": status.get("infra_status","n/a"),
        "CANARY_STATUS": status.get("canary_status","n/a"),
        "RUN_URL": status.get("run_url","(run url)"),
        "REASONS_ROWS": build_reasons_rows(reasons),
        "EVIDENCE_URL": manifest.get("EVIDENCE_URL",""),
        "REPORT_URL": manifest.get("REPORT_URL",""),
        "OPS_TRENDS_URL": manifest.get("OPS_TRENDS_URL",""),
        "OPS_IMPACT_URL": manifest.get("OPS_IMPACT_URL",""),
        "INSPECTOR": os.environ.get("GITHUB_ACTOR","ci"),
        "GENERATED_AT": datetime.now(timezone.utc).isoformat(),
    }

    body = render_template(tpl, ctx)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(body)

    # try posting to PR
    try:
        posted = gh_post_comment(args.repo, args.pr, body)
        print(f"[annotate] posted={posted}")
    except subprocess.CalledProcessError as e:
        print(f"[annotate] gh api failed: {e}", file=sys.stderr)
        sys.exit(3)

    return 0

if __name__ == "__main__":
    sys.exit(main())
