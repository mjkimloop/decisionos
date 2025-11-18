# 실행 체크리스트 - v0.5.11t+2 안정화 패키지

**버전**: v0.5.11t+2
**작성일**: 2025-11-18
**실행 소요**: 15분 (스모크 테스트 포함)

---

## 📋 사전 준비

### 필수 확인 사항
- [ ] Go 기준 점검 9/9 통과 (tests/e2e/test_go_readiness_checklist_v1.py)
- [ ] v0.5.11t+2 커밋 완료 (489290c)
- [ ] 로컬 개발 환경 Python 3.11+

---

## 🚀 실행 단계

### 1. 구성 파일 배치

#### configs/cards/weights.yaml
```bash
cat > configs/cards/weights.yaml <<'EOF'
# Cards 집계 가중치 설정
default_weight: 1.0
label_weights:
  perf: 1.5
  latency: 1.5
  error: 2.0
  security: 2.5
  compliance: 2.0
  availability: 1.8
EOF
```

#### configs/cards/catalog_sha.lock
```bash
# 라벨 카탈로그 SHA 생성
sha256sum configs/labels/label_catalog_v2.json | awk '{print $1}' > configs/cards/catalog_sha.lock

# Windows
certutil -hashfile configs\labels\label_catalog_v2.json SHA256 | findstr /v "hash" | findstr /v "CertUtil" > configs\cards\catalog_sha.lock
```

#### configs/alerts/cards_alerts.yml
```bash
cat > configs/alerts/cards_alerts.yml <<'EOF'
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
          rate(decisionos_http_retry_total[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "HTTP retry rate above 5%"

      - alert: CardsP95LatencySpiked
        expr: |
          histogram_quantile(0.95,
            rate(decisionos_cards_latency_ms_bucket[5m])
          ) > 250
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "Cards P95 latency > 250ms"
EOF
```

**검증**:
```bash
# 파일 생성 확인
ls -l configs/cards/weights.yaml configs/cards/catalog_sha.lock configs/alerts/cards_alerts.yml

# 알람 규칙 검증 (Prometheus 있는 경우)
promtool check rules configs/alerts/cards_alerts.yml
```

---

### 2. 환경키 설정

#### .env 추가 (로컬/스테이징)
```bash
# Cards 설정
DECISIONOS_EVIDENCE_INDEX=var/evidence/index.json
DECISIONOS_CARDS_TTL=60
DECISIONOS_DELTA_FORCE_FULL_PROBE_PCT=1  # 1% 강제 풀 페이로드

# 알람 임계값
DECISIONOS_ALERT_P95_MS=250
DECISIONOS_ALERT_RETRY_RATE=0.05
DECISIONOS_ALERT_ETAG_HIT_MIN=0.60

# 라벨 카탈로그 SHA (자동 생성)
DECISIONOS_LABEL_CATALOG_SHA=$(cat configs/cards/catalog_sha.lock)
```

#### CI 환경변수 설정 (GitHub Actions)
```bash
# GitHub Secrets에 추가
gh secret set DECISIONOS_LABEL_CATALOG_SHA < configs/cards/catalog_sha.lock
gh secret set DECISIONOS_DELTA_FORCE_FULL_PROBE_PCT --body "1"
```

---

### 3. 로컬 스모크 테스트

```bash
# 1. Cards 가중치/버킷 테스트
python -m pytest -xvs tests/ops/test_cards_weights_and_buckets_v1.py

# 2. Delta 협상 테스트
python -m pytest -xvs tests/ops/test_cards_delta_negotiation_v1.py

# 3. ETag seed property-based 테스트
python -m pytest -xvs tests/property/test_etag_seed_property_v1.py

# 4. 알람 YAML 스키마 테스트
python -m pytest -xvs tests/alerts/test_alerts_yaml_schema_v1.py

# 5. 메트릭 노출 테스트
python -m pytest -xvs tests/metrics/test_cards_etag_metrics_v1.py

# 전체 통합 테스트 (5분 소요)
python -m pytest -q \
  tests/ops/test_cards_weights_and_buckets_v1.py \
  tests/ops/test_cards_delta_negotiation_v1.py \
  tests/property/test_etag_seed_property_v1.py \
  tests/alerts/test_alerts_yaml_schema_v1.py \
  tests/metrics/test_cards_etag_metrics_v1.py
```

**성공 기준**: 모든 테스트 Green (0 failed)

---

### 4. 서버 경로 점검

```bash
# 라우트 등록 확인
grep -r "reason-trends" apps/ops/api/

# RBAC 스코프 확인
grep "require_scopes" apps/ops/api/cards_delta.py

# 예상 출력:
# apps/ops/api/cards_delta.py:    dependencies=[require_scopes("ops:read")],
# apps/ops/api/cards_delta.py:@router.get("/reason-trends")
```

**검증**:
```bash
# 로컬 서버 실행
uvicorn apps.ops.api.server:app --reload

# 별도 터미널에서 엔드포인트 테스트
curl -i http://localhost:8000/ops/cards/reason-trends \
  -H "X-Scopes: ops:read" \
  | grep -E "ETag|Vary|Cache-Control"

# 예상 출력:
# ETag: "..."
# Vary: Authorization, X-Scopes, X-Tenant, ...
# Cache-Control: private, max-age=60
```

---

### 5. CI 배선 확인

```bash
# CI 워크플로우에 gate_go_readiness 존재 확인
grep "gate_go_readiness" .github/workflows/ci.yml

# 예상 출력:
#   gate_go_readiness:
#     name: gate_go — Go 기준 점검 (실전 전환)
```

**CI에서 실행될 테스트**:
- `gate_core_executor_storage_delta`
- `gate_q_cards_delta_and_http_exec`
- `gate_r_hardening_sweep`
- `gate_go_readiness` ← **NEW**

---

### 6. 알람 룰 드라이런 (스테이징)

```bash
# Prometheus에 알람 룰 로드 (dry-run)
promtool check rules configs/alerts/cards_alerts.yml

# 메트릭 스크레이프 확인
curl -s http://localhost:8000/metrics | grep decisionos_cards

# 예상 출력:
# decisionos_cards_etag_total{result="hit"} 0
# decisionos_cards_etag_total{result="miss"} 0
# decisionos_cards_latency_ms_bucket{le="50"} 0
# ...
```

**Prometheus AlertManager 설정** (스테이징):
```yaml
# prometheus.yml
rule_files:
  - "configs/alerts/cards_alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093
```

---

### 7. 릴리스 컷

```bash
# 변경사항 커밋
git add configs/cards/ configs/alerts/ tests/ docs/ops/
git commit -m "chore(t2): cards weights/buckets + delta negotiation + alerts + runbook"

# 태그 생성
git tag -a v0.5.11t+2 -m "feat: Cards 집계 안정화 + Delta 협상 + 알람 (Go 기준 통과)"
git push --follow-tags

# 릴리즈 프리즈 선언 (24시간)
echo "🔒 Release Freeze: v0.5.11t+2 - 24h monitoring period" | \
  gh pr comment <PR_NUMBER> --body-file -
```

#### 24시간 모니터링 체크리스트

**메트릭 대시보드**:
- [ ] ETag hit rate: 60-80% 유지
- [ ] HTTP retry rate: < 1% 유지
- [ ] Cards P95 latency: < 250ms 유지
- [ ] Delta accepted rate: 20-40% 유지

**로그 검증**:
```bash
# 에러 로그 모니터링
tail -f var/logs/decisionos.log | grep -E "ERROR|CRITICAL"

# 재시도 로그 확인
tail -f var/logs/decisionos.log | grep "http_call.*retry"

# ETag 로그 확인
tail -f var/logs/decisionos.log | grep "decisionos_cards_etag"
```

**알람 트리거 확인**:
```bash
# AlertManager 알람 목록
curl -s http://alertmanager:9093/api/v2/alerts | jq '.[] | select(.labels.alertname | startswith("Cards"))'
```

---

## ✅ 성공 판정

### 필수 조건 (모두 만족 시 승인)

1. **테스트 통과**
   - [ ] test_cards_weights_and_buckets_v1.py: Green
   - [ ] test_cards_delta_negotiation_v1.py: Green
   - [ ] test_etag_seed_property_v1.py: Green (1000회 무작위 검증)
   - [ ] test_alerts_yaml_schema_v1.py: Green
   - [ ] test_cards_etag_metrics_v1.py: Green

2. **메트릭 정상**
   - [ ] ETag hit rate: 60-80%
   - [ ] HTTP retry rate: < 1%
   - [ ] Cards P95 latency: < 250ms
   - [ ] 에러율: < 0.1%

3. **알람 검증**
   - [ ] 알람 룰 문법 검증 통과
   - [ ] 메트릭 스크레이프 정상
   - [ ] False positive 0건 (24h)

4. **문서 완성**
   - [ ] RUNBOOK-OPS-CARDS.md 작성
   - [ ] 링크 체크 통과
   - [ ] 트러블슈팅 가이드 포함

---

## 🔙 롤백 스위치

### 즉시 완화 (문제 발생 시)

```bash
# 1. Delta 강제 풀 페이로드 비활성화
export DECISIONOS_DELTA_FORCE_FULL_PROBE_PCT=0

# 2. 알람 일시 중단
kubectl annotate namespace default prometheus.io/alerts=disabled

# 3. 가중치 초기화 (필요 시)
cat > configs/cards/weights.yaml <<'EOF'
default_weight: 1.0
label_weights: {}
EOF

# 4. 서버 재시작
systemctl restart decisionos-ops-api
```

### 완전 롤백 (이전 버전으로)

```bash
# 1. 이전 태그로 체크아웃
git checkout v0.5.11t+1

# 2. 설정 파일 복원
git restore configs/cards/ configs/alerts/

# 3. 재배포
docker-compose down && docker-compose up -d

# 4. 헬스 체크
curl -i http://localhost:8000/healthz
```

---

## 📊 성공 메트릭 예시

### 정상 운영 중 메트릭 (24h 후)

```
# ETag hit rate: 72%
decisionos_cards_etag_total{result="hit"} 7200
decisionos_cards_etag_total{result="miss"} 2800

# HTTP retry rate: 0.3%
decisionos_http_retry_total 30
decisionos_http_attempts_total 10000

# Cards latency (P50/P95/P99)
decisionos_cards_latency_ms{quantile="0.5"} 45
decisionos_cards_latency_ms{quantile="0.95"} 180
decisionos_cards_latency_ms{quantile="0.99"} 350

# Delta accepted rate: 35%
decisionos_cards_delta_accepted_total 3500
decisionos_cards_200_total 10000
```

---

## 🚨 트러블슈팅

### ETag Hit Rate < 60%

**원인**:
- 인덱스 파일 갱신 주기가 너무 짧음 (< 60초)
- 라벨 카탈로그 SHA가 자주 변경됨
- 테넌트 분리 설정 오류

**해결**:
```bash
# 1. 인덱스 갱신 주기 확인
stat -c %Y var/evidence/index.json | \
  awk '{print systime() - $1 " seconds ago"}'

# 2. 카탈로그 SHA 변경 이력
git log --oneline configs/labels/label_catalog_v2.json | head -5

# 3. 테넌트 설정 확인
echo $DECISIONOS_TENANT
```

### HTTP Retry Rate > 5%

**원인**:
- 다운스트림 서비스 불안정
- 타임아웃 설정이 너무 짧음
- 일시적 네트워크 장애

**해결**:
```bash
# 1. 다운스트림 헬스 체크
curl -i http://downstream-service/healthz

# 2. 타임아웃 증가 (임시)
export DECISIONOS_EXEC_HTTP_TIMEOUT=10

# 3. 재시도 제한 (장애 확산 방지)
export DECISIONOS_EXEC_HTTP_RETRIES=1
```

### Cards P95 Latency > 500ms

**원인**:
- 인덱스 파일이 너무 큼 (> 5 MB)
- 집계 로직 병목
- 디스크 I/O 지연

**해결**:
```bash
# 1. 인덱스 파일 크기 확인
du -h var/evidence/index.json

# 2. 집계 캐시 활성화
export DECISIONOS_CARDS_TTL=120

# 3. 인덱스 압축 (배치)
gzip var/evidence/index.json
mv var/evidence/index.json.gz var/evidence/index.json
```

---

**다음 단계**: 24시간 프리즈 후 v0.5.11t+3 착수 → 실전 전환 승인
