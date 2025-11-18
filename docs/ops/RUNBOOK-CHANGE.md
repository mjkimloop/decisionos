# RUNBOOK — Change Governance & CAB 절차

## 1. 프리즈 확인
- 정책 위치: `configs/change/freeze_windows.yaml` (서명본 `.sig`)
- CLI:
  ```bash
  python -m scripts.change.verify_freeze_window --service ops-api --labels "hotfix"
  ```
- 프리즈에 걸리면 기본 차단, `hotfix/urgent` 라벨 또는 break-glass 토큰이 있어야 진행 가능

## 2. CAB 멀티-시그
- 정책: `configs/policy/approval_policies.yaml`
- 서비스 소유자/온콜: `configs/change/ownership.yaml`
- 필수 조건(ops-api 예시):
  - 최소 2명 서명
  - `cab` 그룹 중 2명 이상 포함
  - 특정 승인자(alice/bob/carol) 포함
- 검증:
  ```bash
  python -m scripts.change.require_cab_multisig --service ops-api --signers "alice,bob"
  ```

## 3. 온콜 확인
- 온콜 목록: `ownership.yaml`의 `oncall` 필드
- 최소 1명의 온콜 사용자가 `ack`(라벨/코멘트/Slack) 해야 함
- 검증:
  ```bash
  python -m scripts.change.require_oncall_ack --service ops-api --ack-users "ops-primary"
  ```

## 4. Break-Glass 절차
- 목적: P1/P0 등 비상시 일시적으로 프리즈 우회
- 발급:
  ```bash
  python -m scripts.change.break_glass issue --reason "incident-123" --approved-by "director"
  ```
  - TTL 기본 30분(`DECISIONOS_BREAK_GLASS_TTL_SEC`)
  - 서명된 매니페스트(`var/change/breakglass.json`)와 TOKEN 출력
- 검증/사용:
  ```bash
  python -m scripts.change.break_glass verify --token "$TOKEN"
  ```
  - Stage 전환 스크립트(`promote.sh`, `abort.sh`)가 자동 호출
- 종료: `python -m scripts.change.break_glass revoke`

## 5. 컨트롤러 연동
- `apps/experiment/controller.py`는 프리즈 상태를 감지해 `promote/abort` 호출을 차단
- Break-glass가 유효하면 차단 해제

## 6. CI & 가시화
- `.github/workflows/ci.yml`
  - Pre-gate: freeze 검증
  - Gate: CAB/On-call 검증
  - Post-gate: `var/ci/change_status.json` → PR 코멘트/Checks 표시
- Step Summary/PR 코멘트에 배지로 노출 (`scripts/ci/annotate_release_gate.py`)

## 7. 비상 연락망
- CAB/온콜 그룹은 `configs/change/ownership.yaml` 유지보수
- Slack 채널: 각 서비스 `slack_channel` 필드 참고

## 8. 로그/감사
- `var/gate/reasons.json`: 실패 사유 (freeze/cab/oncall/breakglass)
- `var/change/breakglass.json`: 사용 내역(서명, 사유, TTL)
- 모든 변경 기록은 incident/PR 링크로 묶어 Change Board에 보고
