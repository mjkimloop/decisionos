# Changelog

## [v0.5.11t+2] 2025-11-18 — 48h 안정화(ETag/Delta/알람/런북)

### Added
- Cards 집계 가중/버킷 정의(`configs/cards/weights.yaml`)와 카탈로그 SHA 잠금(`configs/cards/catalog_sha.lock`).
- Delta 협상/ETag 시드 보강(`apps/ops/api/cards_delta.py`) 및 무작위 풀페이로드 프로브 옵션.
- PrometheusRule 3종(`configs/alerts/cards_alerts.yml`)과 RUNBOOK-OPS 업데이트.
- 신규 테스트 스위트: weights/buckets, delta 협상, ETag seed property, alerts yaml, metrics, runbook 링크체크.

### Changed
- `apps/ops/api/cards_data.py`가 Evidence 버킷/라벨 가중 집계와 그룹 점수를 계산하도록 확정.
- HTTP 실행기 재시도 제어에 `idempotent` 플래그 반영(비멱등 재시도 기본 차단 유지).
- CI에 48h 안정화 게이트(`gate_r_48h`) 추가.

### Notes
- 환경키: `DECISIONOS_DELTA_FORCE_FULL_PROBE_PCT`, `DECISIONOS_ALERT_P95_MS`, `DECISIONOS_ALERT_RETRY_RATE`, `DECISIONOS_ALERT_ETAG_HIT_MIN`을 필요 시 조정.
- 라벨 카탈로그 SHA 변경 시 `configs/cards/catalog_sha.lock` 및 `DECISIONOS_LABEL_CATALOG_SHA`를 동기화.

---

## [v0.5.11t] 2025-11-18 — Cards 데이터 연동 · RBAC/ETag 정리 · readyz 점검

### Added
- **Cards API 실제 데이터 연동**: `apps/ops/api/cards.py`가 Evidence 인덱스 + 라벨 카탈로그(가중치)로 상위 그룹/스코어를 집계.
- **gate_q 테스트** 3종:
  - `test_cards_reads_evidence_v1.py`
  - `test_rbac_env_unify_v1.py`
  - `test_readyz_shape_v1.py`

### Changed
- **RBAC 맵 일원화**: `DECISIONOS_RBAC_MAP`(인라인 YAML) 우선, 없으면 `DECISIONOS_RBAC_MAP_PATH` 사용. 핫리로드 유지.
- **ETagStore 경로 수렴**: 표준 `apps/ops/cache/etag_store.py`. 레거시 경로(`apps/ops/etag_store.py`, `apps/storage/etag_store.py`)는 shim으로 대체.
- **/readyz 응답/지표 스모크 강화**: window/ratios/eta 키 존재 확인, `/metrics` 스크레이핑 스모크 추가.

### CI
- `gate_q` 스텝 추가(ETag/Delta, RBAC 핫리로드, Cards↔Evidence 연동).

### Migration Notes
- 새 ENV 확인:
  - `DECISIONOS_EVIDENCE_INDEX`, `DECISIONOS_LABEL_CATALOG`, `DECISIONOS_CARDS_TTL`, `DECISIONOS_TOP_IMPACT_N`
  - 운영은 `DECISIONOS_RBAC_TEST_MODE=0` 유지.
- 레거시 ETagStore 임포트는 **동작하나** 추후 제거 예정. 표준 경로로 전환 권장.

### Security
- RBAC 기본 거부 정책에 맞춰 맵/테스트 모드 재점검.
- Evidence 경로/카탈로그 파일 권한 최소화 권고.

---
