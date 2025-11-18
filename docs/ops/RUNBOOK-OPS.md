# RUNBOOK — Ops Cards/ETag/Delta

## 캐시·ETag 기본
- Vary 헤더: `Authorization, X-Scopes, X-Tenant, Accept, If-None-Match, If-Modified-Since` 유지.
- ETag 시드: 테넌트 + 라벨 카탈로그 SHA + 인덱스 mtime + 쿼리 해시 + 상위 라벨 지문.
- Delta 협상: `X-Delta-Base-ETag` 일치 시 증분, 불일치 시 풀페이로드, 미제공 시 풀페이로드.
- 무작위 풀페이로드 프로브: `DECISIONOS_DELTA_FORCE_FULL_PROBE_PCT`(%)로 강제 풀 응답.

## 헬스체크
- `/readyz` 확인 후 `/metrics`에서 `decisionos_cards_etag_total`, `decisionos_http_retry_total` 지표 확인.
- ETag hit-rate 급락, HTTP 재시도율 급등, Cards p95 지연 급등 알람은 `configs/alerts/cards_alerts.yml` 규칙을 따른다.

## 장애 대응 요령
- ETag 충돌 의심: 라벨 카탈로그 SHA 변경 여부 확인 후 `DECISIONOS_LABEL_CATALOG_SHA` 재주입.
- Delta 불일치 반복: `X-Delta-Base-ETag` 값을 로깅해 비교하고, 필요 시 `DECISIONOS_DELTA_FORCE_FULL_PROBE_PCT=100`으로 강제 풀 응답.
- 재시도 폭증: 다운스트림 상태 확인 후 `DECISIONOS_EXEC_HTTP_RETRY_NON_IDEMPOTENT`는 0 유지, 타임아웃/백오프 환경 변수 재조정.

## 배포·릴리스 플로우
- 태그: `v0.5.11t+2` 배포 후 24시간 freeze.
- 샘플 실트래픽 검증: `/ops/cards/reason-trends`를 최소 2회 호출해 304/Delta 동작을 확인.
- 롤백: weights.yaml/ETag 시드 관련 변경을 원복하거나 Delta 프로브 비율을 0으로 낮춘다.
