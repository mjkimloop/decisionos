# Privacy Controls

- `DECISIONOS_PII_ENABLE` 기본값은 0이지만, prod 모드(`DECISIONOS_MODE=prod`)에서는 CI가 강제로 1을 요구합니다.
- 배포 파이프라인에서 PII 토글이 OFF인 상태로는 게이트를 통과할 수 없으며, 필요 시 `scripts/ci/validate_artifacts.py --require-pii-on-when-prod` 로컬 검증이 가능합니다.
