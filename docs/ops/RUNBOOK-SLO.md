# RUNBOOK — Judge/Canary SLO 대응

## 1. 알람 채널
- Slack `#decisionos-slo` (PagerDuty 연계)
- 이메일 `sre@decisionos.io`

## 2. 체크리스트
1. 최근 배포 중인지 확인: `pipeline/release/canary_step.sh <stage>` 실행 이력 및 Argo Rollout 상태
2. Evidence S3 객체 확인: `s3://decisionos-evidence/YYYY/MM/DD/<commit>/evidence-latest.json`
3. 알람 유형별 Runbook

### 2.1 Judge Infra (latency / availability / signature_error)
- `dosctl witness_judge_perf --csv <judgelog>` 로 현황 재계산
- `python jobs/evidence_harvest_judgelog.py --judgelog ... --evidence var/evidence/latest.json`
- `dosctl judge quorum --slo configs/slo/slo-judge-infra.json --evidence var/evidence/latest.json --providers configs/judge/providers.yaml --quorum 2/3`
- Fail 시 `pipeline/release/abort.sh` 실행 후 Evidence 링크를 알람 스레드에 첨부

### 2.2 Canary Regression
- `python -m apps.cli.dosctl.shadow_capture --out var/shadow --samples 2000`
- `python -m apps.cli.dosctl.canary_compare --control var/shadow/control.csv --canary var/shadow/canary.csv --out var/evidence/canary-latest.json`
- `dosctl judge quorum --slo configs/slo/slo-canary.json ...`
- Fail 시 stage 0%로 롤백 후 `RUNBOOK-ROLLBACK.md` 절차 수행

## 3. 자동화 확인
- `jobs/cron/evidence_harvest.cron` 이 적용돼 있는지 확인 (`systemctl status decisionos-harvest.service`)
- S3 업로드 실패 알람(CloudWatch Event) 처리: IAM 키/네트워크 상태 확인 후 재시도

## 4. 해제 조건
- 2회 연속 그린 + Evidence SHA 검증 성공 + Error budget 남은 비율 > 95%
- `pipeline/release/promote.sh` 실행으로 다음 stage 이동

## 5. 참고
- SLO 정의: `configs/slo/slo-judge-infra.json`, `configs/slo/slo-canary.json`
- Providers: `configs/judge/providers.yaml`
