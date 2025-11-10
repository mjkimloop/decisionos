#!/usr/bin/env bash
set -euo pipefail

# --- 입력 ---
STAGE="${1:-promote}"                 # 기본 promote
STAGE_FILE="${STAGE_FILE:-var/rollout/desired_stage.txt}"
RBAC_SCOPE="${RBAC_SCOPE:-deploy:promote}"
HOOK_CMD="${DECISIONOS_CONTROLLER_HOOK:-}"  # 예: "python -m apps.experiment.controller_hook"

# --- RBAC 확인 ---
python - <<'PY'
import os, sys
# RBAC 체크 비활성화 옵션
if os.getenv("DECISIONOS_ENFORCE_RBAC", "1") == "0":
    print("[promote] RBAC 비활성화 (테스트 모드)")
    sys.exit(0)

try:
    from apps.policy.pep import PEP
    pep = PEP()
except Exception as e:
    print(f"[promote] RBAC 모듈 로드 실패: {e}", file=sys.stderr)
    sys.exit(1)

scope = os.environ.get("RBAC_SCOPE", "deploy:promote")
if not pep.enforce(scope):
    print(f"[promote] RBAC 거부: '{scope}' 필요", file=sys.stderr)
    sys.exit(3)
print("[promote] RBAC ok")
PY

# --- stage 파일 원자적 갱신 ---
python - "$STAGE" "$STAGE_FILE" <<'PY'
import sys, os, hashlib, time
stage, path = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(path), exist_ok=True)
tmp = f"{path}.tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(stage.strip()+"\n")
os.replace(tmp, path)
data=open(path,"rb").read()
sha=hashlib.sha256(data).hexdigest()
print(f"[promote] stage={stage} sha256={sha} file={path}")
# GitHub Actions 주석/출력
summ=os.environ.get("GITHUB_STEP_SUMMARY")
out=os.environ.get("GITHUB_OUTPUT")
line=f"- stage set to **{stage}** (`{path}`) — sha256 `{sha}` at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
if summ:
    with open(summ,"a",encoding="utf-8") as f:
        f.write(line)
if out:
    with open(out,"a",encoding="utf-8") as f:
        f.write(f"stage={stage}\nsha256={sha}\n")
PY

# --- 선택: 컨트롤러 훅 호출 (비차단) ---
if [[ -n "${HOOK_CMD}" ]]; then
  echo "[promote] controller hook 실행: ${HOOK_CMD} --stage ${STAGE} --source promote.sh"
  set +e
  ${HOOK_CMD} --stage "${STAGE}" --source "promote.sh"
  hook_rc=$?
  set -e
  echo "[promote] controller hook rc=${hook_rc}"
fi

echo "[promote] 완료"
