# Go 기준 - 48시간 우선 과제 (v0.5.11t+2 → v0.5.11t+3)

**작성일**: 2025-11-18
**목표**: 실전 전환 직전 마지막 안정화 및 관측성 강화

---

## ✅ Go 기준 점검 완료 (10분 컷)

모든 필수 점검 항목 통과:

1. ✅ RBAC 강제 (X-Scopes 없이 403, ops:read로 200/304)
2. ✅ Vary/304 캐시 안전성 (Vary 헤더 + Content-Length: 0)
3. ✅ Strong ETag 유효성 (tenant + catalog SHA + 데이터)
4. ✅ 테넌트 분리 (ETag/캐시 키 분리)
5. ✅ Delta 협상 (X-Delta-Base-ETag 검증)
6. ✅ 메트릭 카운터 (hit/miss 추적)
7. ✅ HTTP 재시도 정책 (401/403/422 즉시 실패, 429/5xx 재시도)
8. ✅ 민감정보 마스킹 (헤더/필드)
9. ✅ HMAC 서명 (키 ID + 서명 + 타임스탬프)
10. ✅ CI gate_go_readiness (9개 테스트 Green)

---

## 🔥 48시간 우선 과제 (짧고 굵게)

### 1. 대시보드 신뢰도 마무리

**목표**: Cards 집계와 Evidence 인덱스 1:1 정합성 확보

**작업**:
- [ ] `compute_reason_trends()` 가중치·버킷 합산 최종 검증
- [ ] 라벨 카탈로그 SHA를 ETag seed에 반영 완료 (이미 적용됨 ✅)
- [ ] 인덱스 변경 시 자동 무효화 테스트 (catalog SHA 변경 시)

**검증**:
```bash
# 인덱스 직접 수정 후 ETag 변경 확인
python -m pytest -xvs tests/e2e/test_go_readiness_checklist_v1.py::test_go_3_strong_etag_validity
```

**리스크**: 집계 불일치 시 잘못된 의사결정 유도
**완료 기준**: 인덱스 fingerprint 변경 → ETag miss 100%

---

### 2. 경계 테스트 추가 (회귀 방지)

**목표**: ETag 충돌 방지 및 Delta 협상 엣지 케이스 커버

**작업**:
- [x] **ETag seed 충돌 방지 테스트** ✅
  - 동일 `generated_at`이더라도 상위 reason 변경 시 miss
  - Property-based test로 무작위 데이터 1000회 검증
  - 테넌트/catalog SHA/query hash 분리 검증

- [x] **Delta 협상 3케이스** ✅
  - 헤더 없음 → delta=null, X-Delta-Accepted: 0
  - 불일치 Base ETag → X-Delta-Accepted: 0, delta=null
  - 강제 풀 페이로드 프로브 → X-Delta-Probe: 1

**파일**:
```
tests/ops/test_cards_etag_collision_v1.py (property-based)
tests/ops/test_cards_delta_negotiation_edge_v1.py
```

**검증**:
```bash
python -m pytest -q tests/ops/test_cards_etag_collision_v1.py
python -m pytest -q tests/ops/test_cards_delta_negotiation_edge_v1.py
```

**리스크**: ETag 충돌 시 잘못된 304 → 오래된 데이터 제공
**완료 기준**: 충돌 케이스 0건, Delta 협상 3케이스 모두 Green ✅

**검증 결과** (v0.5.11u-2):
```bash
$ pytest -q tests/ops/test_cards_etag_collision_v1.py
...  [100%]  # 3 passed

$ pytest -q tests/ops/test_cards_delta_negotiation_edge_v1.py
...  [100%]  # 3 passed
```

---

### 3. 슬로퀘리/에러 예산 알람

**목표**: 캐시/재시도 이상 징후 즉시 감지

**작업**:
- [x] **알람 규칙 작성 (Prometheus AlertManager)** ✅

```yaml
# configs/alerts/cards_cache.yaml
groups:
  - name: cards_cache
    interval: 1m
    rules:
      - alert: CardsETagHitRateDropped
        expr: |
          rate(decisionos_cards_etag_total{result="hit"}[5m])
          /
          rate(decisionos_cards_etag_total[5m]) < 0.6
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Cards ETag hit rate below 60%"
          description: "Hit rate: {{ $value | humanizePercentage }}"

      - alert: HTTPRetryRateSpiked
        expr: |
          rate(decisionos_exec_http_retries_total[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "HTTP retry rate above 5%"

      - alert: CardsP95LatencySpiked
        expr: |
          histogram_quantile(0.95,
            rate(decisionos_cards_latency_bucket[5m])
          ) > 0.5
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "Cards P95 latency > 500ms"
```

**파일**: [configs/alerts/cards_alerts.yml](../../configs/alerts/cards_alerts.yml)

**알람 규칙** (5개):
1. **CardsETagHitRateDropped** (warning): Hit rate < 60%, 5분 지속
2. **HTTPRetryRateSpiked** (warning): Retry rate > 5%, 2분 지속
3. **CardsP95LatencySpiked** (critical): P95 > 250ms, 3분 지속
4. **DeltaAcceptedRateDropped** (info): Delta 수락률 < 20%, 5분 지속
5. **CardsErrorRateSpiked** (critical): 에러율 > 1%, 2분 지속

**검증**:
```bash
# YAML 스키마 검증
pytest -xvs tests/alerts/test_alerts_yaml_schema_v1.py
# 5 passed
```

**리스크**: 이상 징후 감지 지연 → 장애 확산
**완료 기준**: 5개 알람 규칙 등록 + 스키마 검증 통과 ✅

**검증 결과** (v0.5.11u-3):
```bash
$ pytest -xvs tests/alerts/test_alerts_yaml_schema_v1.py
.....  [100%]  # 5 passed
- YAML 구조 유효성 ✅
- 필수 필드 검증 ✅
- PromQL 표현식 구문 ✅
- 필수 알람 커버리지 ✅
- 심각도 분포 적절성 ✅
```

---

### 4. 운영 문서 마지막 정리

**목표**: /ops/cards 캐시·ETag 정책 표준화

**작업**:
- [ ] **RUNBOOK-OPS-CARDS.md 작성**

```markdown
# Cards API 운영 가이드

## 캐시 정책

### ETag 구조
- **Strong ETag**: `SHA256(tenant + catalog_SHA + generated_at + top_reasons_fingerprint + query)`
- **TTL**: 60초 (DECISIONOS_CARDS_TTL)
- **Vary 헤더**: `Authorization, X-Scopes, X-Tenant, Accept, If-None-Match, If-Modified-Since`

### 304 Not Modified
- **조건**: `If-None-Match` == ETag
- **응답**: `304 + Content-Length: 0 + ETag + Vary + Cache-Control`
- **대역폭 절감**: 98% (50 KB → < 1 KB)

### Delta 협상
- **헤더**: `X-Delta-Base-ETag` (클라이언트가 가진 이전 ETag)
- **불일치**: `X-Delta-Accepted: 0` + 풀 페이로드
- **일치**: `X-Delta-Accepted: 1` + delta 객체 (added/removed/changed)
- **Base ETag 갱신**: `X-Delta-Base-ETag` 응답 헤더

## 트러블슈팅

### ETag Hit Rate 저하
1. 인덱스 갱신 주기 확인 (`generated_at` 변동)
2. 라벨 카탈로그 변경 여부 (`DECISIONOS_LABEL_CATALOG_SHA`)
3. 테넌트 분리 설정 확인 (`DECISIONOS_TENANT`)

### 304 응답 안 옴
1. 클라이언트가 `If-None-Match` 헤더 전송하는지 확인
2. ETag 값이 정확한지 확인 (따옴표 포함)
3. Vary 헤더의 필드가 동일한지 확인 (Authorization 등)

### Delta 협상 실패
1. `X-Delta-Base-ETag`가 현재 ETag와 일치하는지 확인
2. Delta가 없는 경우 (데이터 불변) → `X-Delta-Accepted: 1` + delta=null
3. Base ETag 불일치 → `X-Delta-Accepted: 0` + 풀 페이로드
```

**검증**:
```bash
# 문서 링크 검증
markdown-link-check docs/ops/RUNBOOK-OPS-CARDS.md
```

**리스크**: 운영자가 캐시 정책 오해 → 장애 대응 지연
**완료 기준**: RUNBOOK 작성 + 링크 체크 통과

---

### 5. 릴리즈 컷

**목표**: v0.5.11t+2 태그 고정 + 24시간 프리즈

**작업**:
- [ ] **Git 태그 생성**
```bash
git tag -a v0.5.11t+2 -m "feat(hardening): Cards Delta-ETag + HTTP retry policy (Go 기준 통과)"
git push origin v0.5.11t+2
```

- [ ] **릴리즈 프리즈 선언** (24시간)
  - CHANGELOG.md 업데이트
  - PR 라벨: `release-freeze` (머지 차단)
  - Slack 공지: "v0.5.11t+2 릴리즈 프리즈 24h"

- [ ] **실트래픽 샘플 검증**
  - Canary 환경 1% 트래픽
  - ETag hit/miss 메트릭 확인
  - HTTP 재시도율 확인
  - 에러율 < 0.1%

**검증**:
```bash
# 태그 확인
git tag -l "v0.5.11t*"

# Canary 메트릭 확인
curl -s http://canary.decisionos.internal/metrics | grep decisionos_cards_etag_total
```

**리스크**: 프리즈 없이 머지 → 회귀 발생
**완료 기준**: 태그 생성 + 24h 프리즈 + Canary Green

---

## ⚠️ 잠재 리스크 (선제 차단)

### 1. 캐시 중독 (Cache Poisoning)

**시나리오**: 프록시/CDN가 Vary 헤더를 무시하고 첫 응답을 캐시
**영향**: 테넌트 A의 데이터를 테넌트 B에게 제공

**대책**:
- [ ] 엣지/Ingress에서 Vary 헤더 전달 강제
- [ ] 테넌트 ID를 URL 경로에 포함 (예: `/ops/cards/{tenant}/reason-trends`)
- [ ] Private Cache-Control 유지 (`private, max-age=60`)

**검증**:
```bash
# Vary 헤더가 Ingress를 통과하는지 확인
curl -i https://ops.decisionos.com/ops/cards/reason-trends \
  -H "Authorization: Bearer xxx" \
  -H "X-Scopes: ops:read" | grep Vary
```

---

### 2. Delta/304 과도 사용

**시나리오**: Hit rate 90% 이상 → 이상 탐지 민감도 저하
**영향**: 인덱스 조작 시 변화 감지 못함

**대책**:
- [ ] 주 1회 "풀 페이로드 강제" 헬스체크 (무작위 1%)
- [ ] Hit rate 90% 초과 시 경고 (정상: 60-80%)
- [ ] 인덱스 변조 탐지 (tampered 플래그)

**검증**:
```bash
# 강제 풀 페이로드 요청 (If-None-Match 생략)
curl -i https://ops.decisionos.com/ops/cards/reason-trends \
  -H "Authorization: Bearer xxx" \
  -H "X-Scopes: ops:read"
```

---

### 3. 재시도 폭풍 (Retry Storm)

**시나리오**: 다운스트림 장애 시 모든 요청이 재시도 → 플러드
**영향**: 장애 확산 + 복구 지연

**대책**:
- [ ] 재시도 상한 설정 (`DECISIONOS_EXEC_HTTP_RETRIES=2`)
- [ ] 동시성 제한 (httpx client pool size)
- [ ] 회로차단기 추가 (3회 연속 실패 시 5분 오픈)

**검증**:
```bash
# 재시도 제한 테스트
python -m pytest -xvs tests/executor/test_http_retry_storm_v1.py
```

---

## 📊 성공 지표

### 완료 기준

| 과제 | 지표 | 목표 |
|------|------|------|
| 대시보드 신뢰도 | 인덱스 변경 → ETag miss | 100% |
| 경계 테스트 | ETag 충돌 | 0건 |
| 알람 규칙 | Promtool 검증 | PASS |
| 운영 문서 | 링크 체크 | PASS |
| 릴리즈 컷 | Canary 에러율 | < 0.1% |

### 메트릭 벤치마크

| 메트릭 | 정상 범위 | 경고 임계값 | 위험 임계값 |
|--------|-----------|-------------|-------------|
| ETag hit rate | 60-80% | < 60% | < 40% |
| HTTP retry rate | < 1% | > 5% | > 10% |
| Cards P95 latency | < 200ms | > 500ms | > 1s |
| Delta accepted rate | 20-40% | < 10% | < 5% |

---

## 🚀 T+3 로드맵 (다음 라운드)

### 1. Cards 집계 고도화
- 버킷별 가중 점수 (시간대별 중요도)
- 상위 N 버스트 구간 (급증 감지)
- 집계·메트릭 정합성 체크 (일간 배치)

### 2. Executor 플러그인 확장
- httpx client 재사용 풀 (connection pooling)
- 멱등 키 자동 생성 (요청 본문 해시)
- Retry-After 헤더 존중

### 3. Connectors 착수
- S3/HTTP/DB 공통 인터페이스
- 헬스체크 표준화
- 재시도·지표 통합

---

**다음 단계**: 48시간 과제 완료 후 v0.5.11t+3 태그 생성 → 실전 전환 승인
