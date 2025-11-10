# CLI — Deploy + Evidence Gate

## 1. Stage 별 명령
| 단계 | 명령 |
| --- | --- |
| 25% | `pipeline/release/canary_step.sh 25 && pipeline/release/promote.sh` |
| 50% | `pipeline/release/canary_step.sh 50 && pipeline/release/promote.sh` |
| 100% | `pipeline/release/canary_step.sh 100` |

- `canary_step.sh` 는 Shadow capture → canary compare → evidence harvest(reqlog/judgelog) → infra/canary judge gate 순으로 실행
- 성공(exit 0) 시에만 `promote.sh` 로 다음 단계 진입
- 실패(exit 2) 시 즉시 `abort.sh`

## 2. 필수 환경 변수
```
export ROLLOUT_NAME=judge-api
export ROLLOUT_NAMESPACE=decisionos
export PROVIDERS_PATH=configs/judge/providers.yaml
export EVIDENCE_PATH=/var/lib/decisionos/evidence/latest.json
```

## 3. Evidence 자동화 파이프라인
1. Reqlog 수집 → `jobs/evidence_harvest_reqlog.py --reqlog /var/log/ingress/reqlog.csv --evidence $EVIDENCE_PATH`
2. Judgelog 수집 → `jobs/evidence_harvest_judgelog.py --judgelog /var/log/judge/judgelog.csv --canary-json var/evidence/canary-latest.json --evidence $EVIDENCE_PATH`
3. 결과 JSON 업로드: `aws s3 cp $EVIDENCE_PATH s3://decisionos-evidence/$RELEASE_TAG/evidence.json`

cron 예시는 `jobs/cron/evidence_harvest.cron` 참고.

## 4. Validation Checklist
- `dosctl judge quorum --slo configs/slo/slo-judge-infra.json --quorum 2/3`
- `dosctl judge quorum --slo configs/slo/slo-canary.json --quorum 2/3`
- Evidence integrity SHA=`jq -r .integrity.signature_sha256 var/evidence/latest.json`

## 5. Exit Codes

| Code | 의미            | 파이프라인 동작                |
|-----:|-----------------|--------------------------------|
| 0    | pass            | 다음 단계로 승격               |
| 2    | policy_fail     | `abort_on_gate_fail.sh` 실행   |
| 3    | rbac_denied     | 즉시 실패(권한 확인)           |
| 4    | invalid_input   | 즉시 실패(증빙/설정 검토)      |
| 5    | infra_error     | 즉시 실패(장애/재시도 판단)    |

## 5. Troubleshooting
- reqlog/judgelog 누락 → harvest 스크립트 exit 1 → 파이프라인 중지
- boto3 미설치 → `pip install boto3` 후 재실행
- stage mismatch → `cat var/rollout/desired_stage.txt` 와 Argo step 비교
