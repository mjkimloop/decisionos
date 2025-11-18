# RUNBOOK — Prod Cutover 리허설

## 목표
- 10→25→50% 단계로 카나리 전환을 리허설하고 연속 Green 시 자동 프로모션을 확인한다.
- 버스트/실패 시 자동 abort와 stage 복구가 동작하는지 검증한다.

## 준비
- Stage 서명 키 설정: `DECISIONOS_STAGE_KEY` / `DECISIONOS_STAGE_KEY_ID`
- Evidence 경로: `var/evidence/latest.json` (pre_gate에서 생성)
- 자동 프로모션: `DECISIONOS_AUTOPROMOTE_ENABLE=1`

## 실행
### 리허설 1 (10→25%)
```bash
bash pipeline/release/cutover_rehearsal.sh --steps "10,25" --evidence var/evidence/latest.json
```

### 리허설 2 (25→50%, 버스트 주입)
```bash
bash pipeline/release/cutover_rehearsal.sh --steps "25,50" --inject-burst yes --evidence var/evidence/latest.json
```
- `--inject-burst yes`는 Evidence의 `canary.windows`에 burst 기록을 추가해 auto-abort 경로를 강제한다.

## 확인
- Evidence 최신본(`integrity.signature_sha256`)에 `canary/windows`가 누적되었는지 확인
- `jobs/canary_auto_promote` 로그에서 `stage=promote` 혹은 `abort` 출력
- 필요 시 Stage 토큰 강제로 복구: `python -m apps.experiment.stage_file guard_and_repair`

## 실패 대응
- 즉시 `write_stage_atomic("abort")` 호출 또는 `stage_file.guard_and_repair()`로 stage=stable 복원
- CI에서 `DECISIONOS_AUTOPROMOTE_ENABLE=0`, `DECISIONOS_BURST_DETECT=1`로 안전하게 다운시프트
