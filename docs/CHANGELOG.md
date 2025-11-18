# Changelog

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
