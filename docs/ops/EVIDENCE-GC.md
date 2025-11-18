# Evidence GC / Index / ObjectLock / DR

## 파이프라인 개요

1. **pre_gate** – Evidence 인덱스 작성 후 GC dry-run 리포트 생성.
2. **gate** – ObjectLock 업로드(stub 기본, aws 전환 가능) 및 선택적 Judge 게이트.
3. **post_gate** – stub/aws 경로에 따른 DR 복구 및 요약 리포트.

CI에서 세 단계가 자동으로 직렬 실행되며 각 단계는 아티팩트를 남깁니다.

| 단계     | 주요 스크립트                          | 산출물 예시                         |
|----------|----------------------------------------|-------------------------------------|
| pre_gate | `python -m apps.obs.evidence.indexer`  | `var/evidence/index.json`           |
|          | `python -m jobs.evidence_gc`           | `var/evidence/gc-report.json`       |
| gate     | `python -m jobs.evidence_objectlock`   | `var/evidence/upload-report.json`   |
| post_gate| `python -m jobs.dr_restore`            | `var/dr/restore-report.json`        |

## 로컬 재현 절차

```bash
# 1) Evidence 인덱스
python -m apps.obs.evidence.indexer

# 2) GC dry-run (환경: DECISIONOS_GC_DRY_RUN=1)
python -m jobs.evidence_gc

# 3) ObjectLock 업로드 (stub)
export DECISIONOS_S3_MODE=stub
python -m jobs.evidence_objectlock

# 4) DR 복구 (stub)
python -m jobs.dr_restore
```

각 단계는 `.env.example`에 정의된 기본값을 사용합니다. aws 전환 시 `DECISIONOS_S3_MODE=aws` 및 AWS 자격 증명을 셋업하세요.

## 운영 전환 체크리스트

1. GitHub Actions Secrets에 `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`(필요 시 Session Token) 등록.
2. 버킷 ObjectLock 활성화 확인 (`ObjectLockEnabledForBucket=true`).
3. CI 워크플로(job env)에서 `DECISIONOS_S3_MODE=aws`, 필요 시 `DECISIONOS_S3_DRY_RUN=0`으로 변경.
4. post_gate 리포트의 `lock_ok`, `sha_ok`가 `true`인지 점검하고 Slack/알림 시스템에 결과 공유.
