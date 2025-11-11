#!/usr/bin/env python3
import argparse, json, os, subprocess, sys, hashlib
from datetime import datetime, timezone
from pathlib import Path

MARKER = "<!--DECISIONOS:PR:RELEASE_GATE-->"

def load_json(p): return json.load(open(p,"r",encoding="utf-8"))

def sha256_json(path: str) -> str:
    try:
        obj = load_json(path)
        return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()
    except Exception:
        return "n/a"

def render_template(tpl: str, ctx: dict) -> str:
    out = tpl
    for k, v in ctx.items(): out = out.replace("{{"+k+"}}", str(v))
    return out

def build_rows(reasons):
    rows = []
    for r in reasons or []:
        rows.append(f"| `{r.get('code','')}` | {str(r.get('message','')).replace('|','\\|')} | {r.get('count',0)} |")
    return "\n".join(rows) if rows else "| — | — | 0 |"

def build_topimpact(path):
    if not path or not Path(path).exists(): return ""
    data = load_json(path); lst = data.get("top_impact") or []
    if not lst: return ""
    lines = ["\n#### Top-Impact Modules (weighted)\n| module | score | events |\n|---|---:|---:|"]
    for it in lst: lines.append(f"| `{it.get('module')}` | {it.get('score')} | {it.get('events')} |")
    return "\n".join(lines) + "\n"

def gh_api(args, token):
    env = os.environ.copy(); env["GH_TOKEN"] = token
    return subprocess.check_output(["gh","api",*args], env=env).decode("utf-8")

def upsert_comment(repo: str, pr: str, body: str, token: str):
    raw = gh_api([f"repos/{repo}/issues/{pr}/comments"], token)
    comments = json.loads(raw)
    target = next((c for c in comments if isinstance(c.get("body"),str) and MARKER in c["body"]), None)
    if target:
        gh_api(["-X","PATCH", f"repos/{repo}/issues/comments/{target['id']}", "-f", f"body={body}"], token)
        print(f"[annotate] updated #{target['id']}")
    else:
        gh_api([f"repos/{repo}/issues/{pr}/comments","-f", f"body={body}"], token)
        print("[annotate] created comment")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--status-json", required=True)
    ap.add_argument("--reasons-json", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--top-impact", default="")
    ap.add_argument("--diff-link", default="")
    ap.add_argument("--label-cat", default="configs/ops/label_catalog.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default="")
    ap.add_argument("--pr", default="")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token: print("GITHUB_TOKEN missing", file=sys.stderr); return 3

    tpl = open(args.template,"r",encoding="utf-8").read()
    status  = load_json(args.status_json)
    reasons = load_json(args.reasons_json)
    manifest= load_json(args.manifest)

    ctx = {
      "STATUS": status.get("status","UNKNOWN").upper(),
      "STATUS_EMOJI": "✅" if status.get("status")=="pass" else "❌",
      "INFRA_STATUS": status.get("infra_status","n/a"),
      "CANARY_STATUS": status.get("canary_status","n/a"),
      "RUN_URL": status.get("run_url","(run url)"),
      "REASONS_ROWS": build_rows(reasons),
      "EVIDENCE_URL": manifest.get("EVIDENCE_URL",""),
      "REPORT_URL": manifest.get("REPORT_URL",""),
      "OPS_TRENDS_URL": manifest.get("OPS_TRENDS_URL",""),
      "OPS_IMPACT_URL": manifest.get("OPS_IMPACT_URL",""),
      "DIFF_LINK": args.diff_link or "(n/a)",
      "LABEL_CATALOG_SHA": sha256_json(args.label_cat),
      "INSPECTOR": os.environ.get("GITHUB_ACTOR","ci"),
      "GENERATED_AT": datetime.now(timezone.utc).isoformat()
    }
    body = render_template(tpl, ctx)

    block = build_topimpact(args.top_impact)
    if block:
        insert = body.find("#### Artifacts")
        body = (body[:insert] + block + body[insert:]) if insert!=-1 else (body + "\n" + block)

    with open(args.out,"w",encoding="utf-8") as f: f.write(body)
    if args.repo and args.pr: upsert_comment(args.repo, args.pr, body, token)
    else: print("[annotate] wrote file only")
    return 0

if __name__=="__main__": sys.exit(main())
