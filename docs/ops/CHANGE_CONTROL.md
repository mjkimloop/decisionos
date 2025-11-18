# Change Control Notes

- prod 배포에서 정책 파일(`configs/policy/*.signed.json`)은 HMAC 서명본만 허용되며, CI가 `--verify-signed-policy`로 서명 유효성을 검증합니다.
- 기본 키는 `DECISIONOS_POLICY_KEYS`(없으면 `DECISIONOS_JUDGE_KEYS`)에서 적재되며, 정책 수정 시 payload와 signature를 함께 갱신해야 합니다.
