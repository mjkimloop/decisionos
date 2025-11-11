# 30분 온콜 드릴 - Release Hardening 런북 (v0.5.11r-10)

**목표**: 주요 장애 시나리오에 대한 30분 내 대응 완료

이 런북은 v0.5.11r 라운드에서 구현된 모든 Release Hardening 항목을 통합합니다.

---

## 📋 사전 체크리스트 (5분)

### 1. 시스템 상태 확인

```bash
# ETag 저장소 헬스체크
curl http://localhost:8080/ops/health/etag-store

# Redis 연결 확인 (Redis 백엔드 사용 시)
curl http://localhost:8080/ops/health/redis

# Judge 준비 상태 (쿼럼 포함)
curl http://localhost:8080/readyz

# Ops Cards 상한선 확인
curl "http://localhost:8080/ops/cards/reason-trends/summary?start=2025-01-11T00:00:00Z&end=2025-01-11T23:59:59Z"
```

**기대 결과**:
- ETag hit_rate ≥ 80%
- Redis healthy=true (사용 시)
- Judge readyz 200 OK
- Cards thresholds.exceeded=false

---

## 🚨 시나리오 1: Judge 쿼럼 퇴화 (10분)

**증상**: 3대 Judge 중 2대 다운, 쿼럼 미달

### 1. 쿼럼 상태 확인 (2분)

```bash
# SLO 쿼럼 설정 확인
cat configs/slo/slo-billing-baseline-v2.json | grep -A5 quorum
```

**기대**: `k=2, n=3, fail_closed_on_degrade=true`

### 2. Judge 노드 상태 (3분)

```bash
# 각 Judge 노드 readyz 체크
curl http://judge-1:8080/readyz
curl http://judge-2:8080/readyz
curl http://judge-3:8080/readyz
```

### 3. Fail-Closed 검증 (3분)

```bash
# 카나리 배포 차단 확인
python jobs/canary_auto_promote.py
# 기대: exit 2 (abort)
```

### 4. 복구 액션 (2분)

```bash
# 다운된 노드 재시작
systemctl restart judge-2
systemctl restart judge-3

# 쿼럼 회복 확인
curl http://judge-2:8080/readyz && curl http://judge-3:8080/readyz
```

---

## 🚨 시나리오 2: ETag 캐시 히트율 급락 (8분)

**증상**: hit_rate < 50%, API 응답 느림

### 1. 메트릭 확인 (2분)

```bash
curl http://localhost:8080/ops/health/etag-store | jq '.metrics'
```

### 2. Redis 백엔드 상태 (3분)

```bash
# Redis 연결 확인
redis-cli ping

# 메모리 사용량
redis-cli info memory

# 키 개수
redis-cli dbsize
```

### 3. 폴백 동작 확인 (2분)

```bash
# Redis 다운 시 InMemory 자동 폴백
curl http://localhost:8080/ops/health/etag-store | jq '.backend'
# 기대: backend="memory" (Redis 실패 시)
```

### 4. 복구 액션 (1분)

```bash
# Redis 재시작 또는 캐시 워밍
redis-cli FLUSHDB
systemctl restart redis

# 히트율 재확인
curl http://localhost:8080/ops/health/etag-store | jq '.metrics.hit_rate_pct'
```

---

## 🚨 시나리오 3: 키 만료 임박 (7분)

**증상**: 키 만료 7일 전 경고

### 1. 키 만료 체크 (2분)

```bash
python scripts/ops/key_rotation.py --check-expiry --warn-days=7
```

**기대**: ⚠️ 만료 임박 키 리스트 출력

### 2. 키 로테이션 준비 (3분)

```bash
# 새 키 생성 (예시)
openssl rand -hex 32 > new_key.txt

# 키 설정 파일 업데이트
cat > keys.json <<EOF
[
  {"key_id": "k1", "secret": "$(cat old_key.txt)", "state": "active"},
  {"key_id": "k2", "secret": "$(cat new_key.txt)", "state": "pending"}
]
EOF
```

### 3. 무중단 로테이션 실행 (2min)

```bash
# active → grace, pending → active
python scripts/ops/key_rotation.py \
  --rotate \
  --old-key-id=k1 \
  --new-key-id=k2 \
  --grace-days=7 \
  --keys-file=keys.json \
  --out=keys-rotated.json

# 적용
export DECISIONOS_JUDGE_KEYS="$(cat keys-rotated.json)"
systemctl reload judge
```

---

## 🚨 시나리오 4: Evidence 변조 감지 (6min)

**증상**: 무결성 체크 실패

### 1. Evidence 스캔 (2min)

```bash
python scripts/ops/evidence_lockdown.py --verify
```

**경고 시**:
```
⚠️  변조된 Evidence 파일:
  - evidence-123.json: signature mismatch
```

### 2. 인덱스 재생성 (2min)

```bash
# 인덱스 및 manifest 재생성
python scripts/ops/evidence_lockdown.py \
  --index \
  --manifest=var/evidence/manifest.jsonl
```

### 3. S3 ObjectLock 적용 (2min)

```bash
# 변조 방지를 위한 S3 업로드
python scripts/ops/evidence_lockdown.py \
  --lock \
  --s3-bucket=decisionos-evidence \
  --s3-prefix=evidence/prod/ \
  --retain-days=7
```

---

## 🚨 시나리오 5: RBAC 위반 시도 (4min)

**증상**: 무허가 배포 시도

### 1. RBAC 로그 확인 (1min)

```bash
# stderr에서 RBAC deny 로그 검색
tail -f /var/log/judge.log | grep "\[RBAC\] deny"
```

### 2. 권한 검증 (2min)

```bash
# 현재 grants 확인
echo $DECISIONOS_ALLOW_SCOPES

# 배포 권한 테스트
python - <<'PY'
from apps.policy.pep import require
try:
    require("deploy:promote")
    print("✅ 권한 있음")
except PermissionError as e:
    print(f"❌ {e}")
PY
```

### 3. 복구 액션 (1min)

```bash
# 권한 부여 (승인 후)
export DECISIONOS_ALLOW_SCOPES="deploy:*,judge:run,ops:read"

# 또는 wildcard
export DECISIONOS_ALLOW_SCOPES="*"
```

---

## 📊 상한선 초과 대응 (추가)

### 레이턴시 초과

```bash
# Ops Cards에서 현재 지표 확인
curl "http://localhost:8080/ops/cards/reason-trends/summary?start=..." | \
  jq '.thresholds'

# 기대:
# {
#   "max_latency_ms": 780,
#   "baseline_latency_ms": 650,
#   "exceeded": false,
#   "utilization_pct": 85.0
# }
```

**초과 시 액션**:
1. 백프레셔 상태 확인: `curl /judge/backpressure/stats`
2. 서킷 브레이커 상태 확인
3. 필요 시 수평 확장

### 비용 초과

```bash
# 현재 비용 확인
curl http://localhost:8080/ops/cards/... | jq '.thresholds.max_cost_usd'
```

**초과 시 액션**:
1. 고비용 tenant 식별
2. quota 정책 강화
3. throttle 적용

---

## 🧪 DR 리허설 (선택 사항)

### 쿼럼 퇴화 시뮬레이션

```bash
# Judge 1대 강제 다운
systemctl stop judge-3

# 쿼럼 유지 확인 (2/3 가용)
python -c "from tests.chaos.test_quorum_degrade_v1 import decide_deployment; \
  cluster = {'judge-1': {'ready': True}, 'judge-2': {'ready': True}, 'judge-3': {'ready': False}}; \
  print(decide_deployment(cluster, k=2, n=3, fail_closed=True))"
# 기대: proceed

# 2대 다운 시뮬레이션
systemctl stop judge-2

# 쿼럼 미달 확인 (1/3 가용)
python -c "..."
# 기대: abort
```

---

## ✅ 드릴 완료 체크리스트

- [ ] 시나리오 1: Judge 쿼럼 퇴화 대응 완료 (10분)
- [ ] 시나리오 2: ETag 캐시 복구 완료 (8분)
- [ ] 시나리오 3: 키 로테이션 완료 (7분)
- [ ] 시나리오 4: Evidence 무결성 복구 완료 (6분)
- [ ] 시나리오 5: RBAC 위반 대응 완료 (4분)
- [ ] 상한선 모니터링 확인
- [ ] 모든 헬스체크 정상

**총 예상 시간**: 30분 + 버퍼 5분

---

## 📞 에스컬레이션

30분 내 해결 불가 시:

1. **#oncall** Slack 채널 알림
2. DevOps 리드 호출
3. 포스트모템 이슈 생성: [템플릿](../templates/postmortem.md)

---

## 📚 참고 문서

- [ETag 인프라 가이드](../ops/etag-infrastructure.md)
- [RBAC 정책 관리](../security/rbac-policy.md)
- [키 로테이션 가이드](../security/key-rotation.md)
- [Evidence 불변성](../observability/evidence-immutability.md)
- [카오스 엔지니어링](../chaos/quorum-degradation.md)

---

**버전**: v0.5.11r-10
**최종 업데이트**: 2025-01-11
**담당**: DecisionOS Release Hardening Team
