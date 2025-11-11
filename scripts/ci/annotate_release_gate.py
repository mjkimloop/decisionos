#!/usr/bin/env python3
import argparse, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

MARKER = "<!--DECISIONOS:PR:RELEASE_GATE-->"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def render_template(tpl: str, ctx: dict) -> str:
    out = tpl
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out

def build_reasons_rows(reasons):
    rows = []
    for r in reasons or []:
        rows.append(f"| `{r.get('code','')}` | {str(r.get('message','')).replace('|','\\|')} | {r.get('count',0)} |")
    return "\n".join(rows) if rows else "| — | — | 0 |"

def build_topimpact_block(path: str) -> str:
    if not path or not Path(path).exists():
        return ""
    data = load_json(path)
    lst = data.get("top_impact") or []
    if not lst:
        return ""
    lines = ["\n#### Top-Impact Modules (weighted)\n| module | score | events |\n|---|---:|---:|"]
    for it in lst:
        lines.append(f"| `{it.get('module')}` | {it.get('score')} | {it.get('events')} |")
    return "\n".join(lines) + "\n"

def gh_api(args_list, token):
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    return subprocess.check_output(["gh","api",*args_list], env=env).decode("utf-8")

def upsert_comment(repo: str, pr: str, body: str, token: str):
    # list comments and find marker
    raw = gh_api([f"repos/{repo}/issues/{pr}/comments"], token)
    comments = json.loads(raw)
    target_id = None
    for c in comments:
        if isinstance(c.get("body"), str) and MARKER in c["body"]:
            target_id = c.get("id")
            break
    if target_id:
        gh_api(["-X","PATCH", f"repos/{repo}/issues/comments/{target_id}", "-f", f"body={body}"], token)
        print(f"[annotate] updated comment #{target_id}")
    else:
        gh_api([f"repos/{repo}/issues/{pr}/comments","-f", f"body={body}"], token)
        print("[annotate] created new comment")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--status-json", required=True)
    ap.add_argument("--reasons-json", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--top-impact", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default="")
    ap.add_argument("--pr", default="")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN missing", file=sys.stderr)
        sys.exit(3)

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

    # optional Top-Impact block injection
    block = build_topimpact_block(args.top_impact)
    if block:
        # inject before Artifacts section or append at end
        insert_at = body.find("#### Artifacts")
        body = (body[:insert_at] + block + body[insert_at:]) if insert_at != -1 else (body + "\n" + block)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(body)

    if args.repo and args.pr:
        try:
            upsert_comment(args.repo, args.pr, body, token)
        except subprocess.CalledProcessError as e:
            print(f"[annotate] gh api failed: {e}", file=sys.stderr)
            sys.exit(3)
    else:
        print("[annotate] GH context missing; wrote file only.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
