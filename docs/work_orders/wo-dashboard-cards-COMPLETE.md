# Work Order: 대시보드 카드 API - COMPLETE ✓

**Status**: COMPLETED
**Date**: 2025-11-18
**Dependencies**: RBAC + Readyz 메트릭

---

## 목표

운영 대시보드용 실시간 판단 카드 API 구현:
- **RBAC ETag 히스토리 카드**: 맵 리로드 이력 및 변경 추적
- **Readyz 윈도우 버스트 카드**: 헬스 윈도우 및 버스트 감지

---

## 완료된 작업

### 1. ✅ RBAC ETag 히스토리 카드

**구현 파일**:
- [apps/ops/cards/rbac_history.py](../../apps/ops/cards/rbac_history.py) (170줄)

**주요 기능**:

#### RBACHistoryTracker
- RBAC 맵 리로드 이력 추적 (최근 50개)
- ETag 변경 감지 및 기록
- 리로드 통계 계산

```python
from apps.ops.cards.rbac_history import get_rbac_history_card

card = get_rbac_history_card(limit=20)
# {
#   "card_type": "rbac_history",
#   "health": "healthy",
#   "health_message": "Normal reload activity",
#   "stats": {
#     "total_reloads": 5,
#     "unique_etags": 3,
#     "reload_rate_per_hour": 1.2,
#     "current_etag": "a1b2c3d4...",
#   },
#   "history": [
#     {"etag": "a1b2...", "timestamp": 1700000000, "event": "reload", "age_seconds": 120},
#     ...
#   ]
# }
```

**Health 판단 기준**:
- `healthy`: 정상 리로드 활동 (< 10회/시간)
- `warning`: 높은 리로드 빈도 (≥ 10회/시간)
- `error`: RBAC 맵 미로드 (ETag=EMPTY)
- `unknown`: 리로드 이력 없음

**API 엔드포인트**:
```http
GET /cards/rbac-history?limit=20&tenant=t1
```

**응답 예시**:
```json
{
  "tenant": "t1",
  "card_type": "rbac_history",
  "timestamp": 1700000000,
  "health": "healthy",
  "health_message": "Normal reload activity",
  "stats": {
    "total_reloads": 15,
    "unique_etags": 5,
    "reload_rate_per_hour": 0.75,
    "current_etag": "a1b2c3d4e5f6...",
    "current_etag_full": "a1b2c3d4e5f6789...full hash..."
  },
  "history": [
    {
      "etag": "a1b2c3d4e5f6...",
      "etag_full": "full hash",
      "timestamp": 1700000000,
      "event": "reload",
      "age_seconds": 300
    }
  ],
  "metrics": {
    "route_match": {
      "hit": 1250,
      "miss": 50,
      "total": 1300,
      "hit_rate": 96.15
    },
    "eval": {
      "allow": 1200,
      "deny": 50,
      "bypass": 500,
      "total": 1250,
      "approval_rate": 96.0
    }
  }
}
```

---

### 2. ✅ Readyz 윈도우 버스트 카드

**구현 파일**:
- [apps/ops/cards/readyz_window.py](../../apps/ops/cards/readyz_window.py) (180줄)

**주요 기능**:

#### ReadyzWindowTracker
- Readyz 체크 결과를 슬라이딩 윈도우로 추적 (기본 5분, 300 샘플)
- 버스트 감지 (연속 실패 카운트)
- 실패 이유 분포 분석

```python
from apps.ops.cards.readyz_window import get_readyz_window_card

card = get_readyz_window_card()
# {
#   "card_type": "readyz_window",
#   "health": "healthy",
#   "alerts": [],
#   "window": {
#     "samples": 150,
#     "ok": 148,
#     "fail": 2,
#     "fail_ratio": 0.0133,
#     "burst_current": 0,
#     "burst_max": 2,
#     "window_sec": 300
#   },
#   "recent_failures": [...],
#   "top_reasons": [...]
# }
```

**Health 및 알림 기준**:
- `critical`: 현재 버스트 ≥ 5 (연속 5회 이상 실패)
- `warning`: 현재 버스트 ≥ 3
- `degraded`: 실패율 > 10%
- `healthy`: 정상
- `unknown`: 윈도우 내 샘플 없음

**API 엔드포인트**:
```http
GET /cards/readyz-window?tenant=t1
```

**응답 예시**:
```json
{
  "tenant": "t1",
  "card_type": "readyz_window",
  "timestamp": 1700000000,
  "health": "warning",
  "alerts": [
    "Burst: 3 consecutive failures"
  ],
  "window": {
    "samples": 200,
    "ok": 195,
    "fail": 5,
    "fail_ratio": 0.025,
    "burst_current": 3,
    "burst_max": 3,
    "window_sec": 300
  },
  "recent_failures": [
    {
      "timestamp": 1699999900,
      "age_seconds": 100,
      "reasons": ["keys:stale", "clock:skew"]
    }
  ],
  "top_reasons": [
    {"reason": "keys:stale", "count": 3},
    {"reason": "clock:skew", "count": 2}
  ],
  "metrics": {
    "checks": {
      "ready": 1200,
      "degraded": 50,
      "total": 1250,
      "ready_ratio": 96.0
    },
    "reason_distribution": {
      "check=\"keys\",code=\"stale\"": 30,
      "check=\"clock\",code=\"skew\"": 20
    }
  }
}
```

---

### 3. ✅ 자동 이력 기록 통합

**RBAC 연동**:
- `apps/policy/rbac_enforce.py`에서 맵 리로드 시 자동 기록
- 초기 로드: `event="initial"`
- 리로드: `event="reload"`

```python
def _force_reload_unlocked(self):
    # ...
    _record_rbac_history(self.sha, "initial")

def ensure_fresh(self):
    # ...
    if current and current != self.sha:
        # ...
        _record_rbac_history(current, "reload")
```

**Readyz 연동**:
- `apps/judge/readyz.py`에서 체크 시 자동 기록
- OK/degraded 상태 및 실패 이유 코드 저장

```python
@router.get("/readyz")
async def readyz(...):
    # ...
    _record_readyz_window(ok, reason_codes if not ok else None)
```

---

## 사용 시나리오

### 시나리오 1: RBAC 맵 변경 추적

```bash
# 1. 맵 파일 수정
vim configs/security/rbac_map.yaml

# 2. 자동 리로드 (2초 이내)
# → History tracker에 기록

# 3. 대시보드 확인
curl "http://localhost:8081/cards/rbac-history?tenant=t1&limit=10" | jq .

# 출력:
# {
#   "health": "healthy",
#   "stats": {
#     "total_reloads": 6,  # ← 증가
#     "current_etag": "new hash"
#   },
#   "history": [
#     {"etag": "new hash", "event": "reload", "age_seconds": 5},
#     {"etag": "old hash", "event": "reload", "age_seconds": 305},
#     ...
#   ]
# }
```

### 시나리오 2: Readyz 버스트 감지

```bash
# 1. 키 만료로 인한 연속 실패 발생
# → Readyz checks fail 3 times in a row

# 2. 대시보드 확인
curl "http://localhost:8080/cards/readyz-window?tenant=t1" | jq .

# 출력:
# {
#   "health": "warning",
#   "alerts": ["Burst: 3 consecutive failures"],
#   "window": {
#     "burst_current": 3,  # ← 현재 버스트
#     "burst_max": 3,
#     "fail_ratio": 0.015
#   },
#   "top_reasons": [
#     {"reason": "keys:stale", "count": 3}
#   ]
# }

# 3. 키 회전 수행
bash scripts/ops/rotate_key_zero_downtime.sh --auto-generate

# 4. 복구 확인
curl "http://localhost:8080/cards/readyz-window?tenant=t1" | jq .health
# → "healthy"
```

### 시나리오 3: Grafana 대시보드 통합

**Panel 1: RBAC 히스토리**
```json
{
  "title": "RBAC Map Reload History",
  "type": "table",
  "targets": [{
    "url": "http://ops:8081/cards/rbac-history?tenant=t1&limit=20",
    "format": "json"
  }],
  "transformations": [
    {"id": "organize", "options": {
      "excludeByName": {"tenant": true},
      "indexByName": {"etag": 0, "event": 1, "age_seconds": 2}
    }}
  ]
}
```

**Panel 2: Readyz 버스트 게이지**
```json
{
  "title": "Readyz Burst Current",
  "type": "gauge",
  "targets": [{
    "url": "http://ops:8081/cards/readyz-window?tenant=t1",
    "jsonPath": "$.window.burst_current"
  }],
  "thresholds": [
    {"value": 0, "color": "green"},
    {"value": 3, "color": "yellow"},
    {"value": 5, "color": "red"}
  ]
}
```

---

## API 통합

**apps/ops/api_cards.py** 라우터에 추가:

```python
@router.get("/cards/rbac-history")
async def get_rbac_history(
    limit: int = Query(default=20, ge=1, le=100),
    tenant_id: str = Depends(require_tenant),
    _=Depends(require_scope("ops:read"))
):
    """Get RBAC map reload history and metrics."""
    from .cards.rbac_history import get_rbac_history_card, get_rbac_metrics_summary

    card = get_rbac_history_card(limit)
    metrics = await get_rbac_metrics_summary()

    return {
        "tenant": tenant_id,
        **card,
        "metrics": metrics,
    }

@router.get("/cards/readyz-window")
async def get_readyz_window(
    tenant_id: str = Depends(require_tenant),
    _=Depends(require_scope("ops:read"))
):
    """Get readyz health window with burst detection."""
    from .cards.readyz_window import get_readyz_window_card, get_readyz_metrics_summary

    card = get_readyz_window_card()
    metrics = await get_readyz_metrics_summary()

    return {
        "tenant": tenant_id,
        **card,
        "metrics": metrics,
    }
```

---

## 알림 규칙

**prometheus_alerts.yml**:
```yaml
groups:
  - name: dashboard_cards_alerts
    interval: 30s
    rules:
      # RBAC 리로드 과도
      - alert: RBACReloadRateHigh
        expr: |
          rbac_reload_rate_per_hour > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "RBAC map reloading too frequently"
          dashboard: "http://ops:8081/cards/rbac-history?tenant=t1"

      # Readyz 버스트 감지
      - alert: ReadyzBurstDetected
        expr: |
          readyz_burst_current >= 5
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Readyz burst: 5+ consecutive failures"
          dashboard: "http://ops:8081/cards/readyz-window?tenant=t1"

      # Readyz 실패율 높음
      - alert: ReadyzFailRateHigh
        expr: |
          readyz_fail_ratio > 0.1
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Readyz failure rate >10% for 3 minutes"
          dashboard: "http://ops:8081/cards/readyz-window?tenant=t1"
```

---

## 다음 단계

### 추가 카드 제안
1. **Canary Health Card**: 카나리 배포 건강도 (green windows, burst)
2. **PII Circuit Breaker Card**: PII 마스킹 상태 및 에러율
3. **ETag Delta Efficiency Card**: Delta 히트율 및 대역폭 절감
4. **Key Rotation Countdown Card**: 키 만료 카운트다운 및 알림

### 개선 포인트
1. **WebSocket 스트리밍**: 실시간 카드 업데이트
2. **히스토리 영속화**: Redis/DB에 장기 보관
3. **카드 구독 API**: 특정 카드 변경 시 푸시 알림
4. **멀티테넌트 집계**: 테넌트별 통계 비교

---

## 관련 문서

- [RBAC + Readyz 메트릭](wo-rbac-readyz-metrics-COMPLETE.md)
- [Pack B/C (Metrics + PII + ETag)](wo-pack-bc-metrics-pii-etag-COMPLETE.md)
- [Cutover Hardening](wo-v0.5.11v-cutover-hardening-COMPLETE.md)

---

**작업 완료**: 2025-11-18
**프로덕션 배포**: Ready
**대시보드 통합**: Grafana/자체 UI
