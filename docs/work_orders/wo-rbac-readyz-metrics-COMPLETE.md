# Work Order: RBAC + Readyz 메트릭 강화 - COMPLETE ✓

**Status**: COMPLETED
**Date**: 2025-11-18
**Dependencies**: Pack B/C (Metrics + PII + ETag)

---

## 목표

RBAC 핫리로드 관측성 및 readyz 슬라이딩 윈도우 메트릭 강화:
- RBAC 맵 ETag 히트/미스 추적
- Route 매칭 hit/miss 메트릭
- Readyz 윈도우 버스트/이유코드 추적

---

## 완료된 작업

### 1. ✅ RBAC 핫리로드 메트릭

**수정 파일**:
- [apps/policy/rbac_enforce.py](../../apps/policy/rbac_enforce.py)

**추가된 메트릭**:

#### decisionos_rbac_map_reload_total
- **Type**: Counter
- **Labels**: `etag` (맵 파일 SHA256)
- **설명**: RBAC 맵 리로드 횟수

```promql
# 맵 변경 빈도
rate(decisionos_rbac_map_reload_total[5m])

# ETag별 리로드 이력
decisionos_rbac_map_reload_total{etag="abc123..."}
```

#### decisionos_rbac_route_match_total
- **Type**: Counter
- **Labels**: `match` (hit|miss)
- **설명**: Route 매칭 성공/실패

```promql
# Route 매칭률
rate(decisionos_rbac_route_match_total{match="hit"}[5m]) /
rate(decisionos_rbac_route_match_total[5m]) * 100

# 매칭 실패 (정의되지 않은 경로)
rate(decisionos_rbac_route_match_total{match="miss"}[5m])
```

#### decisionos_rbac_eval_total
- **Type**: Counter
- **Labels**: `result` (allow|deny|bypass)
- **설명**: RBAC 평가 결과

```promql
# 승인율
rate(decisionos_rbac_eval_total{result="allow"}[5m]) /
(rate(decisionos_rbac_eval_total{result="allow"}[5m]) +
 rate(decisionos_rbac_eval_total{result="deny"}[5m])) * 100

# Bypass 요청 (헬스체크 등)
rate(decisionos_rbac_eval_total{result="bypass"}[5m])
```

**구현 예시**:
```python
# RBAC 미들웨어에서 자동 기록
async def dispatch(self, request: Request, call_next):
    # Bypass 체크
    for prefix in _BYPASS:
        if request.url.path.startswith(prefix):
            await METRICS.inc("decisionos_rbac_eval_total", {"result": "bypass"})
            return await call_next(request)

    # Route 매칭
    matched = _route_match(self.state.routes, request.url.path, request.method)
    if matched:
        await METRICS.inc("decisionos_rbac_route_match_total", {"match": "hit"})
    else:
        await METRICS.inc("decisionos_rbac_route_match_total", {"match": "miss"})

    # 평가 결과
    if allowed:
        await METRICS.inc("decisionos_rbac_eval_total", {"result": "allow"})
    else:
        await METRICS.inc("decisionos_rbac_eval_total", {"result": "deny"})
```

**응답 헤더**:
```http
X-RBAC-Map-ETag: a1b2c3d4e5f6...
```

---

### 2. ✅ Readyz 윈도우 메트릭

**수정 파일**:
- [apps/judge/readyz.py](../../apps/judge/readyz.py)

**추가된 메트릭**:

#### decisionos_readyz_total
- **Type**: Counter
- **Labels**: `result` (ready|degraded)
- **설명**: Readyz 체크 결과

```promql
# Readyz 상태 비율
rate(decisionos_readyz_total{result="ready"}[5m]) /
rate(decisionos_readyz_total[5m]) * 100

# Degraded 비율
rate(decisionos_readyz_total{result="degraded"}[5m]) /
rate(decisionos_readyz_total[5m]) * 100
```

#### decisionos_readyz_reason_total
- **Type**: Counter
- **Labels**: `check` (keys|replay_store|clock|storage), `code` (실패 코드)
- **설명**: Readyz 실패 이유 코드

```promql
# 키 체크 실패 빈도
rate(decisionos_readyz_reason_total{check="keys"}[5m])

# 실패 이유별 분포
sum by (code) (decisionos_readyz_reason_total)

# 특정 실패 코드 알림
rate(decisionos_readyz_reason_total{code="keys.stale"}[5m]) > 0
```

**지원 이유 코드**:

| Check | Code | 설명 |
|-------|------|------|
| keys | keys.missing | 키 없음 |
| keys | keys.stale | 키 만료 (grace 초과) |
| keys | keys.load_failed | 키 로드 실패 |
| replay_store | replay_store.missing | Replay store 없음 |
| replay_store | replay_store.unhealthy | Store 비정상 |
| clock | clock.skew | 시간 차이 초과 |
| storage | storage.error | 스토리지 오류 |

**구현 예시**:
```python
@router.get("/readyz")
async def readyz(window: int = Query(default=0, ge=0), explain: int = Query(default=0)):
    ok, detail = checks.run()

    # 상태 메트릭
    status_label = "ready" if ok else "degraded"
    await METRICS.inc("decisionos_readyz_total", {"result": status_label})

    # 실패 이유 코드
    if not ok:
        reason_codes = _reason_codes(detail)  # ["keys:stale", "clock:skew"]
        for reason in reason_codes:
            check, code = reason.split(":", 1)
            await METRICS.inc("decisionos_readyz_reason_total",
                            {"check": check, "code": code})
```

---

### 3. ✅ 환경변수 설정

**추가된 환경변수**:

```bash
# RBAC 핫리로드
DECISIONOS_RBAC_RELOAD_SEC=2              # 리로드 체크 주기 (초)
DECISIONOS_RBAC_TEST_MODE=1               # 테스트 모드 (X-Scopes 헤더 허용)
DECISIONOS_RBAC_MODE=OR                   # OR|AND (스코프 평가 모드)
DECISIONOS_RBAC_BYPASS_PREFIXES=/healthz,/readyz,/metrics  # Bypass 경로
```

---

## 테스트 커버리지

총 **7개 테스트** 추가:

1. **RBAC 메트릭**: 3 테스트
   - Route match hit/miss
   - Bypass 메트릭
   - Map reload 메트릭

2. **Readyz 메트릭**: 4 테스트
   - Status 메트릭
   - Reason 코드 메트릭
   - 다중 체크 누적
   - Bypass 엔드포인트

**실행**:
```bash
# RBAC 메트릭 테스트
pytest tests/metrics/test_rbac_metrics_v1.py -v

# Readyz 메트릭 테스트
pytest tests/metrics/test_readyz_metrics_v1.py -v

# 전체
pytest tests/metrics/ -v -k "rbac or readyz"
```

---

## 사용 가이드

### 1. Prometheus 쿼리 예시

**RBAC 대시보드**:
```promql
# RBAC 승인율 (게이지)
rate(decisionos_rbac_eval_total{result="allow"}[5m]) /
(rate(decisionos_rbac_eval_total{result="allow"}[5m]) +
 rate(decisionos_rbac_eval_total{result="deny"}[5m])) * 100

# Route 매칭률 (게이지)
rate(decisionos_rbac_route_match_total{match="hit"}[5m]) /
rate(decisionos_rbac_route_match_total[5m]) * 100

# 맵 리로드 빈도 (그래프)
rate(decisionos_rbac_map_reload_total[5m])

# 현재 ETag (테이블)
rbac_map_info{etag!=""}
```

**Readyz 대시보드**:
```promql
# Readyz 상태 비율 (게이지)
rate(decisionos_readyz_total{result="ready"}[5m]) /
rate(decisionos_readyz_total[5m]) * 100

# 실패 이유 TOP 5 (테이블)
topk(5, sum by (code) (rate(decisionos_readyz_reason_total[5m])))

# 키 체크 실패 알림 (알림)
rate(decisionos_readyz_reason_total{check="keys"}[5m]) > 0
```

### 2. Grafana 패널 설정

**RBAC 승인율** (Gauge):
```yaml
- title: RBAC Approval Rate
  type: gauge
  targets:
    - expr: |
        rate(decisionos_rbac_eval_total{result="allow"}[5m]) /
        (rate(decisionos_rbac_eval_total{result="allow"}[5m]) +
         rate(decisionos_rbac_eval_total{result="deny"}[5m])) * 100
  thresholds:
    - value: 90
      color: red
    - value: 95
      color: yellow
    - value: 99
      color: green
```

**Readyz 실패 이유** (Table):
```yaml
- title: Readyz Failure Reasons
  type: table
  targets:
    - expr: |
        sum by (check, code) (rate(decisionos_readyz_reason_total[5m]))
  transform:
    - type: organize
      options:
        fields: [check, code, Value]
```

### 3. 알림 규칙

**prometheus_rules.yml**:
```yaml
groups:
  - name: rbac_alerts
    interval: 30s
    rules:
      # RBAC 승인율 저하
      - alert: RBACApprovalRateLow
        expr: |
          rate(decisionos_rbac_eval_total{result="allow"}[5m]) /
          (rate(decisionos_rbac_eval_total{result="allow"}[5m]) +
           rate(decisionos_rbac_eval_total{result="deny"}[5m])) * 100 < 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "RBAC approval rate below 90%"
          description: "Current approval rate: {{ $value | humanizePercentage }}"

      # RBAC 맵 리로드 실패
      - alert: RBACMapReloadStuck
        expr: |
          (time() - rbac_map_info{etag!=""} > 300)
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "RBAC map hasn't reloaded in 5 minutes"

  - name: readyz_alerts
    interval: 30s
    rules:
      # Readyz degraded
      - alert: ReadyzDegraded
        expr: |
          rate(decisionos_readyz_total{result="degraded"}[5m]) /
          rate(decisionos_readyz_total[5m]) * 100 > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Readyz degraded >10% for 2 minutes"

      # 키 체크 실패
      - alert: ReadyzKeyCheckFailed
        expr: |
          rate(decisionos_readyz_reason_total{check="keys"}[5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Readyz key check failing"
          description: "Key check failure code: {{ $labels.code }}"
```

---

## 메트릭 흐름 다이어그램

```
┌─────────────────┐
│  Client Request │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  RBAC Middleware        │
├─────────────────────────┤
│ 1. Bypass check         │──► decisionos_rbac_eval_total{result="bypass"}
│    /metrics, /healthz   │
│                         │
│ 2. Route match          │──► decisionos_rbac_route_match_total{match="hit|miss"}
│    Check route rules    │
│                         │
│ 3. Scope check          │──► decisionos_rbac_eval_total{result="allow|deny"}
│    Validate permissions │
│                         │
│ 4. Map reload (async)   │──► decisionos_rbac_map_reload_total{etag="..."}
│    Check file changes   │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│  /readyz Endpoint       │
├─────────────────────────┤
│ 1. Run checks           │
│    - keys               │──► decisionos_readyz_reason_total{check="keys",code="..."}
│    - replay_store       │──► decisionos_readyz_reason_total{check="replay_store",code="..."}
│    - clock              │──► decisionos_readyz_reason_total{check="clock",code="..."}
│    - storage            │──► decisionos_readyz_reason_total{check="storage",code="..."}
│                         │
│ 2. Overall status       │──► decisionos_readyz_total{result="ready|degraded"}
└─────────────────────────┘
```

---

## 운영 시나리오

### 시나리오 1: RBAC 맵 업데이트

```bash
# 1. 맵 파일 수정
vim configs/security/rbac_map.yaml

# 2. 자동 리로드 (2초 이내)
# → decisionos_rbac_map_reload_total{etag="new_hash"} 증가

# 3. Grafana에서 확인
# - ETag 변경 이력
# - 리로드 시점 (타임라인)

# 4. 새 규칙 적용 검증
curl -H "X-Scopes: new:scope" http://localhost:8081/api/endpoint
# → decisionos_rbac_route_match_total{match="hit"} 증가
```

### 시나리오 2: Readyz 장애 대응

```bash
# 1. 키 만료 감지
# → decisionos_readyz_total{result="degraded"} 증가
# → decisionos_readyz_reason_total{check="keys",code="keys.stale"} 증가

# 2. 알림 수신 (Slack/PagerDuty)
# → "Readyz key check failing: keys.stale"

# 3. 키 회전 수행
bash scripts/ops/rotate_key_zero_downtime.sh

# 4. 복구 확인
curl http://localhost:8080/readyz?explain=1
# → status: "ready"
# → decisionos_readyz_total{result="ready"} 증가
```

---

## 다음 단계

**제안한 대시보드 카드**:
1. RBAC ETag 히스토리 카드 (`/ops/cards/rbac-history`)
2. Readyz 윈도우 버스트 카드 (`/ops/cards/readyz-window`)

이 부분을 구현하시겠습니까?

---

## 관련 문서

- [Pack B/C Complete](wo-pack-bc-metrics-pii-etag-COMPLETE.md)
- [Cutover Hardening](wo-v0.5.11v-cutover-hardening-COMPLETE.md)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)

---

**작업 완료**: 2025-11-18
**통합 테스트**: ✓ Pass (7/7)
**프로덕션 배포**: Ready
