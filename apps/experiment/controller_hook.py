"""
컨트롤러-통합 훅:
- stage 변경 시 로컬 로그/마커 기록
- 선택적으로 외부 배포 명령 실행(ENV)
- 선택적으로 Evidence 재서명/주석 라인 남김
"""
from __future__ import annotations
import argparse, os, json, subprocess, time, hashlib, sys
from pathlib import Path

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def log(line: str) -> None:
    Path("var/rollout").mkdir(parents=True, exist_ok=True)
    with open("var/rollout/hooks.log", "a", encoding="utf-8") as f:
        f.write(line.rstrip()+"\n")
    print(line)

def run_cmd(cmd: str) -> int:
    try:
        return subprocess.run(cmd, shell=True, check=False).returncode
    except Exception as e:
        log(f"[hook] 외부 명령 실패: {e}")
        return 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--source", default="controller")
    args = ap.parse_args()

    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    marker = {"ts": ts, "stage": args.stage, "source": args.source}
    Path("var/rollout").mkdir(parents=True, exist_ok=True)
    Path("var/rollout/last_hook.json").write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[hook] stage={args.stage} source={args.source} at {ts}")

    # 1) 선택: 외부 배포 명령
    # 예) DECISIONOS_ON_PROMOTE_CMD="kubectl argo rollouts promote myapp"
    cmd = os.getenv("DECISIONOS_ON_PROMOTE_CMD","").strip()
    if cmd:
        rc = run_cmd(cmd)
        log(f"[hook] DECISIONOS_ON_PROMOTE_CMD rc={rc}")

    # 2) 선택: Evidence 재서명(변경된 perf/perf_judge/canary 병합 후)
    ev_path = Path("var/evidence/latest.json")
    if ev_path.exists():
        try:
            # SHA-256 재계산 (간단 버전)
            data = json.loads(ev_path.read_text(encoding="utf-8"))
            core_keys = ["meta","witness","usage","rating","quota","budget","anomaly"]
            core = {k: data[k] for k in core_keys if k in data}
            core_json = json.dumps(core, ensure_ascii=False, sort_keys=True)
            sig = sha256_text(core_json)
            data.setdefault("integrity", {})["signature_sha256"] = sig
            ev_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"[hook] Evidence re-sign 완료: sha256={sig[:16]}...")
        except Exception as e:
            log(f"[hook] Evidence re-sign 스킵: {e}")

    # 3) GitHub Actions 주석(선택)
    summ = os.getenv("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write(f"- controller hook: stage **{args.stage}** at {ts}\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
