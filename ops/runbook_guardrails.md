# Guardrails Runbook

## 목적
이 런북은 DecisionOS Guardrails v2의 운영, 모니터링, 사고 대응 절차를 정의합니다. Guardrails는 입출력 검증, 보안 정책 시행, 자동 롤백을 담당하는 핵심 안전장치입니다.

## 개요

### Guardrails 구성요소
1. **Input Validators**: 입력 데이터 검증 (스키마, PII, 인젝션 공격)
2. **Output Validators**: 출력 데이터 검증 (타입, 민감정보, 정책 위반)
3. **Policy Enforcer**: 정책 시행 및 의사결정 라우팅
4. **Canary & Shadow**: 점진적 배포 및 병렬 평가
5. **Auto Rollback**: 자동 롤백 메커니즘

### SLO (Service Level Objectives)
- **공격 차단율**: ≥ 99.5%
- **오탐률**: ≤ 1.0%
- **처리 오버헤드**: p95 ≤ 120ms
- **가용성**: ≥ 99.9%

---

## 아키텍처 다이어그램

```
[요청] → [Input Validators] → [Policy Enforcer] → [Decision Engine] → [Output Validators] → [응답]
              ↓                      ↓                                         ↓
          [Block]              [HITL Queue]                               [Block/Review]
              ↓                      ↓                                         ↓
      [로그/알림]             [수동 검토]                              [로그/알림]

                              [Canary/Shadow]
                                     ↓
                            [성능 비교/자동 롤백]
```

---

## 모니터링

### 핵심 메트릭

#### 1. 보안 메트릭
```yaml
metrics:
  security:
    - injection_attempts_blocked: 인젝션 공격 차단 건수
    - pii_redactions: PII 마스킹 건수
    - api_key_leaks_prevented: API 키 유출 방지 건수
    - toxicity_blocks: 유해 콘텐츠 차단 건수
    - rate_limit_violations: 속도 제한 위반 건수
```

**대시보드 위치**: Grafana > Security > Guardrails Overview

**알림 임계값**:
- `injection_attempts_blocked > 10/분`: WARNING
- `injection_attempts_blocked > 50/분`: CRITICAL
- `api_key_leaks_prevented > 0`: CRITICAL

#### 2. 성능 메트릭
```yaml
metrics:
  performance:
    - guardrails_latency_p50: 중앙값 지연시간
    - guardrails_latency_p95: 95 백분위 지연시간
    - guardrails_latency_p99: 99 백분위 지연시간
    - overhead_percent: 전체 요청 대비 오버헤드 비율
```

**SLO**:
- p95 latency ≤ 120ms
- overhead ≤ 15%

**알림 임계값**:
- `guardrails_latency_p95 > 120ms` for 5분: WARNING
- `guardrails_latency_p95 > 200ms` for 2분: CRITICAL

#### 3. 정확도 메트릭
```yaml
metrics:
  accuracy:
    - true_positives: 정탐 (실제 위협 차단)
    - false_positives: 오탐 (정상 요청 차단)
    - false_negatives: 미탐 (위협 놓침)
    - precision: 정밀도 = TP / (TP + FP)
    - recall: 재현율 = TP / (TP + FN)
```

**SLO**:
- Precision ≥ 99.0% (오탐률 ≤ 1.0%)
- Recall ≥ 99.5% (차단율 ≥ 99.5%)

**알림 임계값**:
- `false_positive_rate > 1.0%`: WARNING
- `false_positive_rate > 2.0%`: CRITICAL
- `false_negative_rate > 0.5%`: CRITICAL

#### 4. 운영 메트릭
```yaml
metrics:
  operations:
    - total_requests: 전체 요청 수
    - blocked_requests: 차단된 요청 수
    - reviewed_requests: 수동 검토로 라우팅된 수
    - bypassed_requests: Guardrails 우회 요청 수 (admin)
    - policy_updates: 정책 업데이트 횟수
```

### 대시보드

#### 메인 대시보드 (Grafana)
- URL: `https://grafana.company.com/d/guardrails-main`
- 새로고침: 30초
- 패널:
  - 실시간 요청 처리량
  - 차단률 추이 (1시간/24시간/7일)
  - 지연시간 분포
  - 오탐/미탐 추이
  - 공격 유형별 차단 건수

#### 보안 대시보드
- URL: `https://grafana.company.com/d/guardrails-security`
- 패널:
  - 공격 히트맵 (시간/유형)
  - 공격 출처 IP/지역
  - PII/민감정보 탐지 패턴
  - 정책 위반 상위 10개

---

## 알림 규칙

### P0 (Critical) - 즉시 대응 필요

#### P0-GUARDRAILS-001: 높은 미탐률
**조건**: `false_negative_rate > 0.5%` for 5분
**영향**: 위협 요청이 시스템을 통과하고 있음
**알림 채널**: PagerDuty, Slack #security-critical, SMS (on-call)
**대응 SLA**: 15분

**조사 단계**:
1. 대시보드에서 미탐 패턴 확인
2. 최근 정책 변경 사항 검토
3. 로그에서 미탐 사례 샘플링
4. Guardrails 우회 여부 확인

**완화 조치**:
```bash
# 1. 긴급 정책 강화
dosctl guardrails update --policy strict --emergency

# 2. 의심 요청 임시 차단
dosctl guardrails block-pattern --pattern "{observed_pattern}" --duration 1h

# 3. 수동 검토 활성화
dosctl guardrails enable-review --all-suspicious
```

#### P0-GUARDRAILS-002: Guardrails 서비스 다운
**조건**: `guardrails_availability < 99%` for 2분
**영향**: 안전장치 없이 요청 처리 중 (고위험)
**알림 채널**: PagerDuty, Slack #incidents
**대응 SLA**: 5분

**조사 단계**:
1. 서비스 상태 확인: `kubectl get pods -n decisionos | grep guardrails`
2. 로그 확인: `kubectl logs -n decisionos guardrails-xxx --tail=100`
3. 리소스 확인: CPU/메모리/네트워크

**완화 조치**:
```bash
# 1. 자동 재시작 트리거
kubectl rollout restart deployment/guardrails -n decisionos

# 2. 트래픽 차단 (서비스 복구 시까지)
dosctl traffic block --except-whitelist

# 3. 페일세이프 모드 활성화 (모든 요청 차단)
dosctl guardrails failsafe --mode block-all
```

#### P0-GUARDRAILS-003: 대량 공격 진행 중
**조건**: `injection_attempts_blocked > 100/분` for 5분
**영향**: DDoS 또는 조직적 공격 시도
**알림 채널**: PagerDuty, Slack #security-critical
**대응 SLA**: 10분

**조사 단계**:
1. 공격 패턴 및 출처 분석
2. 공격 유형 식별 (SQL Injection, XSS, RCE 등)
3. 영향 범위 평가

**완화 조치**:
```bash
# 1. 출처 IP 차단
dosctl guardrails block-ip --cidr {attacker_cidr}

# 2. Rate limiting 강화
dosctl guardrails rate-limit --requests 10 --window 1m --per-ip

# 3. WAF 규칙 업데이트 (있는 경우)
# 외부 WAF/CDN에 패턴 추가
```

### P1 (High) - 1시간 내 대응

#### P1-GUARDRAILS-001: 높은 오탐률
**조건**: `false_positive_rate > 1.0%` for 10분
**영향**: 정상 사용자 차단, UX 저하
**알림 채널**: Slack #guardrails-alerts
**대응 SLA**: 1시간

**조사 단계**:
1. 오탐 사례 샘플 추출 및 분석
2. 최근 정책 변경 확인
3. 특정 사용자/패턴에 집중되었는지 확인

**완화 조치**:
```bash
# 1. 정책 롤백 (최근 변경이 원인인 경우)
dosctl guardrails rollback --to-version {previous_version}

# 2. 화이트리스트 추가 (특정 패턴이 오탐인 경우)
dosctl guardrails whitelist-pattern --pattern "{pattern}" --reason "False positive"

# 3. 임계값 조정
dosctl guardrails tune --rule {rule_id} --threshold {new_threshold}
```

#### P1-GUARDRAILS-002: 높은 지연시간
**조건**: `guardrails_latency_p95 > 200ms` for 5분
**영향**: 전체 응답 시간 증가, SLA 위반 가능
**알림 채널**: Slack #performance
**대응 SLA**: 1시간

**조사 단계**:
1. 느린 Validator 식별
2. 리소스 사용률 확인
3. 동시 요청 수 확인

**완화 조치**:
```bash
# 1. 스케일 아웃
kubectl scale deployment/guardrails -n decisionos --replicas={current+2}

# 2. 무거운 검증 비활성화 (일시적)
dosctl guardrails disable --validator {slow_validator} --duration 30m

# 3. 캐싱 활성화
dosctl guardrails cache --enable --ttl 5m
```

### P2 (Medium) - 4시간 내 대응

#### P2-GUARDRAILS-001: Canary 성능 저하
**조건**: `canary_performance_delta > 20%` for 15분
**영향**: 신규 정책/모델 품질 문제
**알림 채널**: Slack #guardrails-alerts
**대응 SLA**: 4시간

**조사 단계**:
1. Canary vs Production 메트릭 비교
2. Canary 로그 확인
3. 변경 사항 검토

**완화 조치**:
```bash
# 1. Canary 롤백
dosctl guardrails canary rollback

# 2. Canary 트래픽 비율 축소
dosctl guardrails canary --traffic-percent 1

# 3. Shadow 모드로 전환 (실제 영향 없음)
dosctl guardrails canary --shadow-only
```

---

## 사고 대응 매트릭스

| 사고 유형 | 우선순위 | 초기 대응 SLA | 해결 목표 | 에스컬레이션 |
|----------|----------|---------------|-----------|-------------|
| Guardrails 서비스 다운 | P0 | 5분 | 15분 | 즉시 → CTO |
| 높은 미탐률 (>0.5%) | P0 | 15분 | 1시간 | 30분 → Security Lead |
| 대량 공격 진행 중 | P0 | 10분 | 1시간 | 즉시 → Security Lead |
| 높은 오탐률 (>1%) | P1 | 1시간 | 4시간 | 2시간 → Eng Lead |
| 높은 지연시간 (>200ms p95) | P1 | 1시간 | 4시간 | 2시간 → Eng Lead |
| Canary 성능 저하 | P2 | 4시간 | 1일 | 8시간 → Product Owner |
| 정책 업데이트 실패 | P2 | 4시간 | 1일 | 8시간 → DevOps |

---

## 운영 절차

### 정책 업데이트 절차

#### 1. 정책 검증 (개발 환경)
```bash
# 1. 정책 파일 작성
vi policies/new_policy_v2.yaml

# 2. 로컬 검증
dosctl guardrails validate --policy policies/new_policy_v2.yaml

# 3. 테스트 셋 실행
dosctl guardrails test --policy policies/new_policy_v2.yaml --test-set tests/guardrails_tests.json
```

**통과 기준**:
- 모든 테스트 케이스 통과
- False positive rate < 1%
- False negative rate < 0.5%

#### 2. Canary 배포
```bash
# 1. Canary 배포 (1% 트래픽)
dosctl guardrails deploy --policy policies/new_policy_v2.yaml --canary --traffic-percent 1

# 2. 모니터링 (30분)
dosctl guardrails canary status --watch

# 3. 트래픽 점진 증가
dosctl guardrails canary --traffic-percent 5   # 30분 후
dosctl guardrails canary --traffic-percent 25  # 2시간 후
dosctl guardrails canary --traffic-percent 50  # 4시간 후
```

**각 단계 통과 기준**:
- False positive rate < 1%
- False negative rate < 0.5%
- p95 latency < 120ms
- No critical errors

#### 3. 전체 배포
```bash
# 1. 100% 롤아웃
dosctl guardrails deploy --policy policies/new_policy_v2.yaml --promote

# 2. 이전 버전 유지 (롤백 대비)
# 자동으로 24시간 유지됨

# 3. 모니터링 강화 (24시간)
# 대시보드 확인, 알림 민감도 증가
```

### 롤백 절차

#### 자동 롤백
자동 롤백 조건 (자동 트리거):
- False positive rate > 2%
- False negative rate > 1%
- Error rate > 5%
- p95 latency > 300ms

#### 수동 롤백
```bash
# 1. 즉시 롤백 (이전 버전으로)
dosctl guardrails rollback

# 2. 특정 버전으로 롤백
dosctl guardrails rollback --to-version v1.2.3

# 3. 롤백 확인
dosctl guardrails status
dosctl guardrails version
```

**롤백 후 조치**:
1. 사고 보고서 작성
2. 실패 원인 분석
3. 테스트 케이스 추가
4. 정책 수정 및 재배포

### Validator 활성화/비활성화

#### Validator 목록 확인
```bash
dosctl guardrails validators list

# 출력 예시:
# NAME                    STATUS    LATENCY_P95  FALSE_POSITIVE_RATE
# input-schema-validator  ENABLED   5ms          0.1%
# pii-detector           ENABLED   45ms         0.3%
# injection-detector     ENABLED   30ms         0.2%
# output-toxicity        ENABLED   60ms         0.5%
```

#### Validator 비활성화 (긴급)
```bash
# 일시 비활성화 (1시간)
dosctl guardrails disable --validator pii-detector --duration 1h --reason "High latency emergency"

# 영구 비활성화
dosctl guardrails disable --validator {validator_name} --permanent
```

#### Validator 재활성화
```bash
dosctl guardrails enable --validator pii-detector
```

### 화이트리스트/블랙리스트 관리

#### IP 블랙리스트
```bash
# IP 차단
dosctl guardrails block-ip --ip 1.2.3.4 --reason "Malicious activity" --duration 24h

# CIDR 차단
dosctl guardrails block-ip --cidr 1.2.3.0/24 --permanent

# 차단 목록 확인
dosctl guardrails block-list

# 차단 해제
dosctl guardrails unblock-ip --ip 1.2.3.4
```

#### 패턴 화이트리스트
```bash
# 패턴 화이트리스트 추가 (오탐 방지)
dosctl guardrails whitelist-pattern \
  --pattern "SELECT.*FROM.*users.*WHERE.*user_id = ?" \
  --reason "Legitimate parameterized query" \
  --reviewer security@company.com

# 화이트리스트 확인
dosctl guardrails whitelist show

# 화이트리스트 제거
dosctl guardrails whitelist-remove --id {whitelist_id}
```

---

## 정기 유지보수

### 일일 점검
- [ ] 대시보드 확인 (오탐/미탐률, 지연시간)
- [ ] 알림 로그 검토
- [ ] 차단된 요청 샘플 검토 (정당성 확인)

### 주간 점검
- [ ] 정책 효과성 분석
- [ ] 오탐 패턴 분석 및 화이트리스트 업데이트
- [ ] 성능 트렌드 분석
- [ ] 테스트 셋 업데이트

### 월간 점검
- [ ] Guardrails 정책 전체 검토
- [ ] 공격 패턴 변화 분석
- [ ] SLO 달성률 보고
- [ ] Validator 최적화

---

## 로그 및 감사

### 로그 위치
```yaml
logs:
  guardrails_decisions: /var/log/decisionos/guardrails/decisions.log
  blocked_requests: /var/log/decisionos/guardrails/blocked.log
  policy_updates: /var/log/decisionos/guardrails/policy_changes.log
  performance: /var/log/decisionos/guardrails/performance.log
```

### 로그 조회 예시
```bash
# 최근 차단된 요청 확인
tail -f /var/log/decisionos/guardrails/blocked.log | jq .

# 특정 IP에서 차단된 요청
grep "1.2.3.4" /var/log/decisionos/guardrails/blocked.log

# 오탐 가능성 있는 차단 (수동 검토 필요)
grep '"confidence": "LOW"' /var/log/decisionos/guardrails/blocked.log
```

### 감사 추적
모든 정책 변경은 감사 로그에 기록됨:
```json
{
  "timestamp": "2025-11-03T10:30:00Z",
  "action": "POLICY_UPDATE",
  "policy_id": "guardrails-v2.3",
  "actor": "admin@company.com",
  "changes": {
    "validator": "pii-detector",
    "field": "threshold",
    "old_value": 0.8,
    "new_value": 0.9
  },
  "approval": "HITL-12345",
  "reason": "Reduce false positives"
}
```

---

## 도구 및 명령어 참조

### dosctl guardrails 명령어
```bash
# 상태 확인
dosctl guardrails status
dosctl guardrails version
dosctl guardrails metrics

# 정책 관리
dosctl guardrails validate --policy {file}
dosctl guardrails test --policy {file} --test-set {file}
dosctl guardrails deploy --policy {file} [--canary]
dosctl guardrails rollback [--to-version {version}]

# Canary 관리
dosctl guardrails canary --traffic-percent {percent}
dosctl guardrails canary status
dosctl guardrails canary rollback

# Validator 관리
dosctl guardrails validators list
dosctl guardrails enable --validator {name}
dosctl guardrails disable --validator {name} [--duration {time}]

# 차단/허용 관리
dosctl guardrails block-ip --ip {ip} [--duration {time}]
dosctl guardrails unblock-ip --ip {ip}
dosctl guardrails whitelist-pattern --pattern {regex}
dosctl guardrails block-list

# 긴급 조치
dosctl guardrails failsafe --mode {block-all|allow-all}
dosctl guardrails update --policy strict --emergency
```

---

## 에스컬레이션 체인

1. **Level 1 (On-call Engineer)**
   - 초기 대응 및 조사
   - 표준 완화 조치 실행
   - 30분 내 해결 실패 시 Level 2로 에스컬레이션

2. **Level 2 (Security Lead / Engineering Lead)**
   - 복잡한 문제 해결
   - 정책 조정 승인
   - 1시간 내 해결 실패 또는 사업 영향 크면 Level 3로

3. **Level 3 (CTO / VP Engineering)**
   - 중대 사고 의사결정
   - 외부 커뮤니케이션 승인
   - 리소스 추가 할당

---

## 체크리스트

### 사고 대응 체크리스트
- [ ] 사고 심각도 평가 (P0/P1/P2)
- [ ] 알림 채널에 사고 알림
- [ ] 초기 조사 수행
- [ ] 완화 조치 실행
- [ ] 모니터링 강화
- [ ] 이해관계자 업데이트
- [ ] 사고 해결 확인
- [ ] 사후 분석(Post-mortem) 작성
- [ ] 재발 방지 조치 수립

### 정책 배포 체크리스트
- [ ] 정책 파일 검증
- [ ] 테스트 셋 통과 확인
- [ ] 변경 승인 획득 (HITL)
- [ ] Canary 배포 (1% → 5% → 25% → 50%)
- [ ] 각 단계별 메트릭 확인
- [ ] 100% 롤아웃
- [ ] 24시간 집중 모니터링
- [ ] 배포 완료 보고

---

## 연락처

- **On-call Engineer**: PagerDuty 자동 호출
- **Security Lead**: security-lead@company.com / +82-10-XXXX-XXXX
- **Engineering Lead**: eng-lead@company.com / +82-10-XXXX-XXXX
- **DevOps Team**: #devops Slack 채널
- **Guardrails Squad**: #guardrails Slack 채널

---

## 관련 문서
- [Drift Monitoring Runbook](runbook_drift.md)
- [Guardrails Architecture](../docs/guardrails_architecture.md)
- [Security Policies](../docs/security_policies.md)
- [Incident Response Plan](incident_response.md)
