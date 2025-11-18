# RUNBOOK — Key Rotation (Dummy Plan)

## 목적
- 서명 키 회전을 무중단으로 리허설하고 readyz 상태를 확인한다.

## 준비
- `configs/keys/key_rotation_plan.json`에 예고/교체/검증/정리 단계 정의
- 현재 활성 키: `DECISIONOS_POLICY_KEYS` 또는 `DECISIONOS_JUDGE_KEYS`

## 절차
1. 플랜 실행
   ```bash
   python -m scripts.keys.rotate_keys --plan configs/keys/key_rotation_plan.json --out var/keys/rotation_manifest.json
   ```
2. readyz 확인
   ```bash
   curl -fsS http://localhost:8080/readyz | jq .status
   ```
3. manifest 검증
   - `var/keys/rotation_manifest.json`에 `manifest` + `signature`가 포함되는지 확인
   - TODO: 실제 키 교체는 운영 KMS/SSM로 대체

## 롤백
- 기존 active 키로 환경 변수를 되돌리고 readyz 재확인
- manifest 삭제: `rm -f var/keys/rotation_manifest.json`
