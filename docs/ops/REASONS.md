# Reasons Namespace v1

## 주 사유 (`reasons[0].code`)
- `infra.samples_insufficient`
- `infra.availability_breach`
- `perf.p95_over`
- `perf.p99_over`
- `error.rate_over`
- `budget.exceeded`
- `quota.forbidden_action`
- `integrity.signature_mismatch`
- `witness.csv_missing`
- `canary.delta_exceeds`

## 규칙
1. 주 사유(main_code)는 최대 1개만 `reasons` 배열에 기록한다.
2. 추가 신호 및 부가 정보는 `meta.reason_detail[]` 배열에 기록한다.
3. 파이프라인/대시보드는 주 사유만으로 상태를 분류하고, reason_detail은 상세 근거로만 사용한다.
4. JSON 컨트랙트 예시:

```json
{
  "decision": "fail",
  "reasons": [
    { "code": "infra.samples_insufficient", "message": "not enough judge samples" }
  ],
  "meta": {
    "reason_detail": [
      { "code": "perf.p95_over", "at_ms": 1234 },
      { "code": "error.rate_over", "value": 0.012 }
    ]
  }
}
```

5. 사유 코드 네임스페이스는 `infra.*`, `perf.*`, `error.*`, `budget.*`, `quota.*`, `integrity.*`, `witness.*`, `canary.*` 범위를 사용한다.
