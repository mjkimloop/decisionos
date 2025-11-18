# DR 복구 런북

## 개요

- Evidence는 ObjectLock으로 보호된 S3(또는 stub 저장소)에 보존됩니다.
- DR 상황에서는 지정된 정책에 따라 Evidence를 복구하고, SHA/Lock 검증 결과를 리포트로 남깁니다.

## 사전 준비

1. **환경 변수**
   - `DECISIONOS_S3_MODE=stub|aws`
   - `DECISIONOS_S3_BUCKET`, `DECISIONOS_S3_PREFIX`
   - `DECISIONOS_DR_POLICY_PATH` (기본 `configs/dr/sample_policy.json`)
   - `DECISIONOS_DR_DEST` (기본 `var/evidence/restore`)
2. **권한**
   - stub: `var/s3_stub/<bucket>/<prefix>` 경로에 접근 가능해야 함
   - aws: ObjectLock 활성화 버킷 + `boto3` + IAM 권한(Put/Get/ObjectLockRetention 등)

## 절차

1. **정책 확인**
   ```bash
   cat $DECISIONOS_DR_POLICY_PATH
   ```
   - `include_globs`, `exclude_globs`, `max_files`, `verify_lock`, `verify_sha`, `flatten` 필드를 검토합니다.

2. **복구 실행**
   ```bash
   pipeline/dr/restore_from_s3.sh
   ```

3. **결과 확인**
   - `var/dr/restore-report.json` 을 열어 `counts`, `restored[]` 항목의 `lock_ok`, `sha_ok` 플래그를 확인합니다.

4. **주의사항**
   - aws 모드에서 ObjectLock 미설정 시 `lock_ok` 가 `false` 일 수 있습니다. 버킷 정책/권한을 재확인합니다.
   - `verify_sha` 는 (있다면) `DECISIONOS_EVIDENCE_INDEX` 경로의 SHA와 대조합니다. 최신 인덱스를 유지하세요.
- `DECISIONOS_DR_DRY_RUN=1` 로 설정하면 경로와 선택 결과만 검토할 수 있습니다.

## CI 통합

- `.github/workflows/ci.yml`에서 `pre_gate → gate → post_gate` 순으로 자동 실행됩니다.
- `post_gate` 단계에서 `python -m jobs.dr_restore` 후 `scripts/ci/summary_postgate.py`가 요약을 Step Summary로 남깁니다.
- stub에서 Green을 확인한 뒤 `DECISIONOS_S3_MODE=aws` 로 전환하면 동일 워크플로가 실 S3 ObjectLock 버킷을 대상으로 실행됩니다.

## 복구 후

1. 복원된 Evidence 경로(`DECISIONOS_DR_DEST`)를 필요한 파이프라인/분석 스텝에 연결합니다.
2. 재색인이 필요한 경우 `python -m jobs.evidence_indexer --root $DECISIONOS_DR_DEST --out var/evidence/restore-index.json` 등을 실행합니다.
3. Incident/Change 로그에 DR 복구 실행과 리포트 링크를 기록합니다.

- PR 주석에는 post_gate 단계에서 생성된 DR 보고서(var/dr/restore-report.json) 링크가 자동 첨부되어 회귀 추적 시 참고할 수 있습니다.
