# v0.5.11u-5 보안 핫픽스 배포 런북

**버전**: v0.5.11u-5
**날짜**: 2025-11-19
**우선순위**: Critical
**담당**: Security Team, Ops Team

---

## 개요

3가지 보안 취약점을 패치하는 긴급 핫픽스:

1. **SEC-001 (Critical)**: RBAC 테스트모드 우회 → 프로덕션에서 권한 탈취 가능
2. **SEC-002 (High)**: CORS 와일드카드 → CSRF 공격, 세션 탈취
3. **SEC-003 (Medium)**: 서명 검증 에러 누출 → 키 추론 공격

---

## 배포 절차

### 1. 사전 준비 (T-30분)

#### 1.1 환경변수 검증

```bash
# 프로덕션 환경변수 확인
cat .env.prod | grep -E "DECISIONOS_ENV|RBAC_TEST_MODE|CORS_ALLOWLIST"

# 필수 확인사항:
# - DECISIONOS_ENV=prod
# - DECISIONOS_RBAC_TEST_MODE=0 (또는 미설정)
# - DECISIONOS_CORS_ALLOWLIST=https://app.example.com,... (명시적 화이트리스트)
```

#### 1.2 백업

```bash
# 현재 배포 버전 확인
git tag --points-at HEAD

# 현재 설정 백업
cp .env.prod .env.prod.backup.$(date +%Y%m%d_%H%M%S)
```

#### 1.3 릴리즈 프리즈 선언

- Slack: `#decisionos-ops`
  ```
  🔒 릴리즈 프리즈 시작 (24시간)
  버전: v0.5.11u-5
  사유: 보안 핫픽스 (RBAC/CORS/서명 검증)
  기간: 2025-11-19 10:00 ~ 2025-11-20 10:00
  담당: @security-team @ops-team
  ```

---

### 2. 코드 배포 (T+0)

#### 2.1 Git 체크아웃

```bash
# 저장소 업데이트
git fetch --tags

# 핫픽스 태그 체크아웃
git checkout v0.5.11u-5

# 변경사항 확인
git diff v0.5.11t+3..v0.5.11u-5 --stat
```

#### 2.2 의존성 설치

```bash
# Python 패키지 업데이트 (변경사항 없음)
pip install -r requirements.txt
```

#### 2.3 환경변수 설정

**프로덕션 `.env.prod` 업데이트:**

```bash
# 1. RBAC 테스트모드 OFF (필수)
DECISIONOS_RBAC_TEST_MODE=0

# 2. CORS 화이트리스트 명시 (필수)
DECISIONOS_CORS_ALLOWLIST=https://app.example.com,https://console.example.com

# 3. 환경 확인
DECISIONOS_ENV=prod
```

**검증:**

```bash
# 부팅 테스트 (dry-run)
python -c "
import os
os.environ['DECISIONOS_ENV'] = 'prod'
os.environ['DECISIONOS_RBAC_TEST_MODE'] = '0'
os.environ['DECISIONOS_CORS_ALLOWLIST'] = 'https://app.example.com'
from apps.gateway.main import app
print('✓ 부팅 성공')
"
```

---

### 3. Canary 배포 (단계적)

#### 3.1 단계 1: 5% 트래픽 (30분)

```bash
# Canary 환경에 배포
kubectl set image deployment/decisionos-gateway \
  gateway=decisionos/gateway:v0.5.11u-5 \
  --namespace=decisionos-canary

# 트래픽 라우팅 (5%)
kubectl apply -f configs/canary/5pct-30min.yaml
```

**메트릭 모니터링:**

```bash
# 1. 401 에러율
curl -s http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=rate(decisionos_http_requests_total{status="401"}[5m])'

# 2. RBAC 거부율
curl -s http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=rate(decisionos_rbac_denied_total[5m])'

# 3. CORS 위반율
curl -s http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=rate(decisionos_cors_violation_total[5m])'
```

**정상 기준:**
- 401 에러율: 베이스라인 ± 3σ
- RBAC 거부율: 증가 < 5%
- CORS 위반율: 0 (기존 클라이언트는 화이트리스트에 포함)

**이상 감지 시:**
```bash
# 즉시 롤백
kubectl set image deployment/decisionos-gateway \
  gateway=decisionos/gateway:v0.5.11t+3 \
  --namespace=decisionos-canary
```

#### 3.2 단계 2: 25% 트래픽 (30분)

```bash
kubectl apply -f configs/canary/25pct-30min.yaml
```

**추가 검증:**
- 로그 샘플링: `RBAC 테스트모드 비활성화`, `CORS 허용 Origin` 확인
- 서명 검증 실패 로그: 상세 사유 내부 로깅만 (외부 노출 없음)

#### 3.3 단계 3: 100% 트래픽 (안정화)

```bash
# 프로덕션 전환
kubectl set image deployment/decisionos-gateway \
  gateway=decisionos/gateway:v0.5.11u-5 \
  --namespace=decisionos-prod

# Canary 정리
kubectl delete -f configs/canary/25pct-30min.yaml
```

---

### 4. 검증 (T+2h)

#### 4.1 보안 검증

```bash
# 1. RBAC 테스트모드 우회 시도 (실패해야 함)
curl -i https://api.decisionos.com/ops/cards/reason-trends \
  -H "X-Scopes: ops:read"
# → 403 Forbidden (X-Scopes 헤더 무시됨)

# 2. CORS 비인가 Origin (차단 확인)
curl -i https://api.decisionos.com/healthz \
  -H "Origin: https://evil.com"
# → Access-Control-Allow-Origin 헤더 없음

# 3. 서명 검증 실패 (일반 메시지 확인)
curl -X POST https://api.decisionos.com/judge \
  -H "X-DecisionOS-Signature: invalid" \
  -H "X-DecisionOS-Nonce: test" \
  -H "X-DecisionOS-Timestamp: $(date +%s)" \
  -d '{"evidence":{}, "slo":{}}'
# → 401 {"detail": "invalid signature"} (상세 사유 없음)
```

#### 4.2 기능 검증

```bash
# 정상 요청 (토큰 인증)
curl -i https://api.decisionos.com/ops/cards/reason-trends \
  -H "Authorization: Bearer $VALID_TOKEN"
# → 200 OK

# 정상 CORS (화이트리스트 Origin)
curl -i https://api.decisionos.com/healthz \
  -H "Origin: https://app.example.com"
# → Access-Control-Allow-Origin: https://app.example.com
```

---

### 5. 모니터링 (24시간)

#### 5.1 대시보드

- **Grafana**: [DecisionOS Security Dashboard](https://grafana.example.com/d/security)
- **패널**:
  1. RBAC 거부율 (test_mode_disabled, scope_missing)
  2. CORS 위반율 (origin별)
  3. 서명 검증 실패율 (key_missing, sig_mismatch, clock_skew)
  4. 401 에러율 (전체)

#### 5.2 알람

```yaml
# Prometheus Alert 규칙 자동 로드됨
groups:
  - name: security_u5
    rules:
      - alert: RBACDeniedSpiked
        expr: rate(decisionos_rbac_denied_total[5m]) > baseline * 1.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "RBAC 거부율 급증 (u-5 배포 후)"

      - alert: CORSViolationDetected
        expr: rate(decisionos_cors_violation_total[5m]) > 0.01
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "CORS 위반 감지 (비인가 Origin)"

      - alert: SignatureFailRateSpiked
        expr: rate(decisionos_signature_fail_total[5m]) > baseline * 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "서명 검증 실패율 급증"
```

---

### 6. 릴리즈 프리즈 해제 (T+24h)

```bash
# 메트릭 최종 확인
python scripts/ops/check_metrics_baseline.py --since="24h ago" --baseline=v0.5.11t+3

# 이상 없을 시:
# Slack 공지
```
🔓 릴리즈 프리즈 해제
버전: v0.5.11u-5
결과: 정상 (메트릭 안정화)
다음 배포: 승인 대기
```
```

---

## 롤백 절차

### 긴급 롤백 (< 5분)

```bash
# 1. 이전 버전으로 롤백
git checkout v0.5.11t+3
kubectl set image deployment/decisionos-gateway \
  gateway=decisionos/gateway:v0.5.11t+3

# 2. 환경변수 복원
cp .env.prod.backup.YYYYMMDD_HHMMSS .env.prod

# 3. 재시작
kubectl rollout restart deployment/decisionos-gateway

# 4. 확인
kubectl rollout status deployment/decisionos-gateway
```

### 롤백 트리거

| 지표 | 임계값 | 조치 |
|------|--------|------|
| 401 에러율 | 베이스라인 + 5σ | 즉시 롤백 |
| CORS 위반율 | > 1% 정상 요청 차단 | 즉시 롤백 |
| 서명 검증 실패율 | > 10% | 검토 → 롤백 |
| RBAC 거부율 | 베이스라인 + 3σ | 검토 → 롤백 |

---

## 트러블슈팅

### 문제 1: 부팅 실패 (RBAC test-mode)

**증상**:
```
RuntimeError: FATAL: RBAC test-mode must be OFF in production.
```

**해결**:
```bash
# .env.prod 확인
grep RBAC_TEST_MODE .env.prod

# 수정
sed -i 's/DECISIONOS_RBAC_TEST_MODE=1/DECISIONOS_RBAC_TEST_MODE=0/' .env.prod

# 재시작
systemctl restart decisionos-gateway
```

### 문제 2: 부팅 실패 (CORS wildcard)

**증상**:
```
RuntimeError: FATAL: CORS allowlist must be explicit in production (no wildcard).
```

**해결**:
```bash
# .env.prod 확인
grep CORS_ALLOWLIST .env.prod

# 수정 (명시적 화이트리스트)
echo "DECISIONOS_CORS_ALLOWLIST=https://app.example.com,https://console.example.com" >> .env.prod

# 재시작
systemctl restart decisionos-gateway
```

### 문제 3: 정상 요청 403 (RBAC 거부)

**증상**: 정상 토큰으로도 403 Forbidden

**진단**:
```bash
# 로그 확인
tail -f /var/log/decisionos/gateway.log | grep rbac_deny

# 예시:
# {"event":"rbac_deny_scope", "path":"/ops/cards", "need":["ops:read"], "have":[], "test_mode":false}
```

**해결**:
- 인증 미들웨어가 `req.state.scopes` 설정하는지 확인
- 레거시 헤더 `X-DecisionOS-Scopes` 사용 중인지 확인
- 토큰 페이로드에 `scopes` 클레임 포함 여부 확인

### 문제 4: CORS 정상 클라이언트 차단

**증상**: 기존 클라이언트에서 CORS 에러

**진단**:
```bash
# 클라이언트 Origin 확인
curl -i https://api.decisionos.com/healthz \
  -H "Origin: https://client.example.com" | grep Access-Control

# 허용 리스트 확인
echo $DECISIONOS_CORS_ALLOWLIST
```

**해결**:
```bash
# 화이트리스트에 Origin 추가
export DECISIONOS_CORS_ALLOWLIST="$DECISIONOS_CORS_ALLOWLIST,https://client.example.com"

# 재시작
systemctl restart decisionos-gateway
```

---

## 참고 문서

- [워크오더: wo-v0.5.11u-5-security-hotfix.yaml](../../docs/work_orders/wo-v0.5.11u-5-security-hotfix.yaml)
- [GO-READINESS-48H.md](GO-READINESS-48H.md)
- [RUNBOOK-OPS-CARDS.md](RUNBOOK-OPS-CARDS.md)
- [RBAC 맵: configs/security/rbac_map.yaml](../../configs/security/rbac_map.yaml)

---

## 변경 이력

| 날짜 | 버전 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 2025-11-19 | v1.0 | Security Team | 초기 작성 (v0.5.11u-5 배포) |
