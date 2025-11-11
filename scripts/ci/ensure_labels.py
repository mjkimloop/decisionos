#!/usr/bin/env python3
import argparse, json, os, subprocess, sys

def gh_api(args, token):
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    return subprocess.check_output(["gh","api",*args], env=env).decode("utf-8")

def upsert_label(repo, name, color, description, token):
    # 목록 조회 후 존재 여부 판단
    try:
        data = gh_api([f"repos/{repo}/labels/{name}"], token)
        exists = True
    except subprocess.CalledProcessError:
        exists = False

    if exists:
        gh_api([
            "-X","PATCH",
            f"repos/{repo}/labels/{name}",
            "-f", f"new_name={name}",
            "-f", f"color={color}",
            "-f", f"description={description}"
        ], token)
        print(f"[labels] updated {name}")
    else:
        gh_api([
            f"repos/{repo}/labels",
            "-f", f"name={name}",
            "-f", f"color={color}",
            "-f", f"description={description}"
        ], token)
        print(f"[labels] created {name}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--repo", required=True)
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN missing", file=sys.stderr); return 3

    with open(args.catalog, "r", encoding="utf-8") as f:
        cat = json.load(f)

    default_color = cat.get("default_color","95a5a6")
    default_desc  = cat.get("default_description","DecisionOS auto-label")

    for item in cat.get("labels", []):
        upsert_label(
            args.repo,
            item["name"],
            item.get("color", default_color),
            item.get("description", default_desc),
            token
        )
    return 0

if __name__ == "__main__":
    sys.exit(main())
