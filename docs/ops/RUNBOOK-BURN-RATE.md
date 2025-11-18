# RUNBOOK — SLO Burn Rate Gate

## 정책
- 파일: `configs/slo/burn_policy.yaml`
- 윈도우: 5m / 30m / 1h / 6h
- 임계: Fast 2×, Slow 4× (둘 중 하나라도 초과 시 게이트 실패)
- 메트릭: Error Rate(가용성), p95/p99 지연

## 절차
1. 드라이런
   ```bash
   python -m jobs.burn_alert_gate --dry-run --report var/ci/burn_report.json
   ```
2. 게이트 실행
   ```bash
   python -m jobs.burn_alert_gate \
     --policy configs/slo/burn_policy.yaml \
     --samples var/metrics/burn_samples.json \
     --report var/ci/burn_report.json \
     --reasons-json var/gate/reasons.json
   ```
3. 실패 시
   - `var/release/freeze.flag` 자동 생성 → 카나리/프로모션 차단
   - Slack(Webhook)으로 `:fire: Burn rate ...` 알림
   - `var/gate/reasons.json` 에 `reason:budget-burn` 축적

## 모니터링 & 카드
- Ops API: `GET /ops/cards/burn-trends?window=5m`
- Prometheus 텍스트: `burn_rate_error_rate_5m` 등 Gauge 노출
- CI Step Summary: Burn report 업로드

## 대응
- Root cause 분석 → Error/Latency 감소
- Freeze 해제 후 재실행
- GameDay 리허설에서 동일 시나리오 반복

## 참고
- 샘플 데이터: `configs/slo/burn_samples_stub.json`
- Slack Webhook: `SLACK_WEBHOOK_URL`
- 환경변수: `BURN_WINDOWS`, `DECISIONOS_FREEZE_FILE`
