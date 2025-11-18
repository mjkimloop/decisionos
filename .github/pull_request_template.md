# [v0.5.11t] Cards·RBAC·ETag·readyz 안정화

## 개요
- Work Order: `wo-v0.5.11t-stabilize-cards-rbac-etag-readyz`
- 목적: Cards API를 Evidence 인덱스/라벨 가중 집계에 연결하고, RBAC 맵/ETag 스토어/readyz 지표를 일원화 및 점검

## 변경 요약
- [ ] **Cards API**: Evidence 인덱스 연동(ETag v2 + Delta 유지)
- [ ] **RBAC 맵 일원화**: `DECISIONOS_RBAC_MAP`(인라인) > `DECISIONOS_RBAC_MAP_PATH`(파일)
- [ ] **ETagStore 수렴**: `apps/ops/cache/etag_store.py` 표준화 + 레거시 shim 제공
- [ ] **/readyz**: window/ratios/eta 형태/지표 스모크 보강
- [ ] **테스트**: `gate_q` 3종(카드 집계, RBAC env, readyz shape)
- [ ] **CI**: gate_q 스텝 추가

## 환경 변수
- `DECISIONOS_EVIDENCE_INDEX=var/evidence/index.json`
- `DECISIONOS_LABEL_CATALOG=configs/labels/label_catalog_v2.json`
- `DECISIONOS_CARDS_TTL=60`
- `DECISIONOS_TOP_IMPACT_N=5`
- `DECISIONOS_RBAC_MAP` (인라인 YAML · 선택)
- `DECISIONOS_RBAC_MAP_PATH=configs/policy/rbac_map.yaml`
- `DECISIONOS_RBAC_TEST_MODE=0` (운영 기본값)
- `DECISIONOS_REDIS_URL` (없으면 In-Memory)

## 확인 항목
- [ ] 단위/통합/E2E 테스트 Green
- [ ] CI `gate_q — Cards/RBAC/readyz` 통과
- [ ] RBAC TEST_MODE 운영에서 비활성(=0)
- [ ] Evidence 인덱스/라벨 카탈로그 경로 유효
- [ ] Redis 미구성 환경에서도 정상(ETag In-Memory 동작)
- [ ] 롤백 시 Cards는 예시 페이로드로 복귀 가능

## 리스크 & 롤백
- 리스크: 카탈로그/인덱스 포맷 상이, RBAC 맵 미적용 시 403/401 변동
- 롤백: Cards 집계 연결 해제(예시 페이로드), shim 유지로 ETagStore 경로 복귀

## 테스트 노트
- 로컬 스모크:
  ```bash
  export DECISIONOS_RBAC_TEST_MODE=1
  python -m pytest -q tests/gates/gate_q/
  ```
- API 스모크:
  ```python
  from starlette.testclient import TestClient
  from apps.ops.api.server import app
  c=TestClient(app)
  print(c.get("/ops/cards/reason-trends", headers={"X-Scopes":"ops:read"}).json())
  ```

---

<!-- decisionos:gate -->Gate Status: (CI가 자동 갱신)
Artifacts: (CI가 검증/링크)
Diff: {{DIFF_LINK}}

> 주: 위 마커 블록은 CI가 PR 코멘트를 업서트하고 배지/아티팩트를 채웁니다.
