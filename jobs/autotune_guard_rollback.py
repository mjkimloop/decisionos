#!/usr/bin/env python3
"""
Autotune Guard Rollback Job
수동으로 last_good 정책으로 롤백
"""
import json, shutil, os

def main():
    guard_path = "configs/optimizer/autotune_guard.json"
    guard = json.load(open(guard_path, "r", encoding="utf-8"))

    src = guard["rollback"]["last_good_path"]
    dst = "configs/canary/policy.autotuned.json"

    if not os.path.exists(src):
        print(f"[ERROR] last_good not found: {src}")
        exit(1)

    shutil.copyfile(src, dst)
    print(f"[OK] Restored {src} → {dst}")

if __name__ == "__main__":
    main()
