# RUNBOOK — Canary/Blue-Green 롤백

## 0. 트리거
- Judge quorum fail (infra 혹은 canary)
- Shadow diff 에서 error_delta > 0.01
- 수동 판단(운영자)

## 1. 즉시 조치
1. `pipeline/release/abort.sh` 실행 (기본 ROLLOUT_MODE=argo)
2. `kubectl argo rollouts status judge-api -n decisionos` 로 안정화 확인
3. `apps/experiment/controller.py` stage 파일 초기화: `echo 0 > var/rollout/desired_stage.txt`

## 2. 증빙
- `jobs/evidence_harvest_reqlog.py --reqlog ... --evidence var/evidence/latest.json`
- `jobs/evidence_harvest_judgelog.py --judgelog ... --canary-json var/evidence/canary-latest.json --evidence var/evidence/latest.json`
- Evidence SHA → S3 업로드 (`s3://decisionos-evidence/<date>/<commit>/rollback.json`)

## 3. 커뮤니케이션
- Slack `#decisionos-release` : 롤백 이유, Evidence 링크, 다음 점검 시간 공유
- Incident ticket 생성(JIRA `REL-xxxx`)

## 4. 재시도 전 체크
- Judge remote 서버 `/healthz`, `/metrics` 정상
- 새 아티팩트 재검증(qa / staging)
- Runway 재작성 후 `pipeline/release/canary_step.sh 25` 부터 재시작

## 5. FAQ
- *Argo Rollouts가 설치되지 않았다면?* → `ROLLOUT_MODE=nginx pipeline/release/abort.sh`
- *Kill-switch 강제?* → `python - <<'PY' ... TrafficController().kill()` (but 일반적으로 stage 파일 0) 
