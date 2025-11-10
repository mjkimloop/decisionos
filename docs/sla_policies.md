# SLA Policies Guide

## 목적
이 문서는 HITL (Human-in-the-Loop) 운영의 Service Level Agreement (SLA) 정책을 정의하고, 측정 방법과 관리 절차를 제시합니다.

---

## SLA 개요

### SLA란?
Service Level Agreement (서비스 수준 협약)는 서비스 제공자와 고객 간의 약속으로,
HITL 운영에서는 **케이스 검토 및 처리 시간**에 대한 보장입니다.

### SLA의 중요성
- **고객 경험**: 빠른 응답은 고객 만족도 직결
- **운영 효율**: 명확한 목표로 리소스 최적화
- **품질 보장**: 시간 압박 속에서도 품질 유지
- **책임성**: 팀 및 개인 성과 측정 기준

---

## SLA 구조

### SLA 구성 요소

#### 1. 측정 지표 (SLI - Service Level Indicator)
실제로 측정 가능한 메트릭:
- First Pick Time (첫 할당 시간)
- Resolution Time (해결 시간)
- Total Time (총 소요 시간)

#### 2. 목표 (SLO - Service Level Objective)
내부적으로 달성하려는 목표:
- 예: Resolution Time p95 < 20시간

#### 3. 약속 (SLA - Service Level Agreement)
고객에게 약속하는 수준:
- 예: Resolution Time p95 < 24시간 (SLO보다 여유 있게 설정)

---

## 우선순위별 SLA

### P0 (Critical) - 긴급

#### SLA 정의
| 메트릭 | 목표 (SLO) | 약속 (SLA) |
|--------|-----------|----------|
| First Pick Time | p95 < 15분 | p95 < 30분 |
| Resolution Time | p95 < 3시간 | p95 < 4시간 |
| Total Time | p95 < 3.5시간 | p95 < 4시간 |

#### 적용 대상
- VIP 고객
- 고액 거래 (예: 1억원 이상)
- 법적 기한 임박
- 사기 의심 (긴급 확인)
- 시스템 오류로 인한 잘못된 결정

#### 위반 시 조치
- **경고 (80% 소진)**: Slack 알림
- **임박 (90% 소진)**: PagerDuty, 자동 에스컬레이션
- **위반 (100% 초과)**: Senior Reviewer 즉시 배정, 고객 사과 통지

### P1 (High) - 높음

#### SLA 정의
| 메트릭 | 목표 (SLO) | 약속 (SLA) |
|--------|-----------|----------|
| First Pick Time | p95 < 2시간 | p95 < 4시간 |
| Resolution Time | p95 < 20시간 | p95 < 24시간 |
| Total Time | p95 < 22시간 | p95 < 24시간 |

#### 적용 대상
- 경계선 케이스 (스코어 0.45-0.55)
- 중요 고객 (거래 이력 우수)
- 복잡한 사례 (여러 요인 검토 필요)
- 정책 예외 요청

#### 위반 시 조치
- **경고 (80% 소진)**: 이메일 알림
- **임박 (90% 소진)**: Slack 알림, 우선순위 상향
- **위반 (100% 초과)**: Senior Reviewer 에스컬레이션 옵션, 고객 진행 상황 안내

### P2 (Medium) - 보통

#### SLA 정의
| 메트릭 | 목표 (SLO) | 약속 (SLA) |
|--------|-----------|----------|
| First Pick Time | p95 < 8시간 | p95 < 12시간 |
| Resolution Time | p95 < 40시간 | p95 < 48시간 |
| Total Time | p95 < 44시간 | p95 < 48시간 |

#### 적용 대상
- 표준 검토 케이스
- 일부 정보 부족 (보완 가능)
- 정책 확인 필요

#### 위반 시 조치
- **경고 (90% 소진)**: 이메일 알림
- **위반 (100% 초과)**: 팀 리더에게 보고, 지연 사유 기록

### P3 (Low) - 낮음

#### SLA 정의
| 메트릭 | 목표 (SLO) | 약속 (SLA) |
|--------|-----------|----------|
| First Pick Time | p95 < 16시간 | p95 < 24시간 |
| Resolution Time | p95 < 60시간 | p95 < 72시간 |
| Total Time | p95 < 68시간 | p95 < 72시간 |

#### 적용 대상
- 단순 확인 사항
- 비긴급 문의
- 정보 제공 요청

#### 위반 시 조치
- **위반 (100% 초과)**: 로그 기록, 주간 리뷰

---

## Appeals (이의 제기) SLA

### 표준 Appeals SLA
| 메트릭 | 목표 (SLO) | 약속 (SLA) |
|--------|-----------|----------|
| Acknowledgment (접수 확인) | p95 < 4시간 | p95 < 8시간 |
| First Review (첫 검토) | p95 < 24시간 | p95 < 48시간 |
| Resolution Time (해결) | p95 < 60시간 | p95 < 72시간 |

### 복잡한 Appeals
복잡도가 높은 경우 (예: 다수 증빙, 복잡한 사정) SLA 연장 가능:
- 표준 + 48시간까지
- 고객에게 사전 안내 필수

---

## 서류 요청 (Awaiting Docs) 시 SLA

### 기본 원칙
- 서류 요청 후 고객 대기 시간은 SLA에서 제외
- 고객 제출 기한: 일반적으로 5-7일
- 서류 제출 후 SLA 재시작

### 케이스별 처리
| 상황 | SLA 처리 |
|------|---------|
| 서류 요청 발송 | SLA 일시 정지 (Paused) |
| 서류 제출 | SLA 재시작 (Resumed) |
| 기한 초과 | 케이스 종료, 재신청 안내 |
| 서류 불충분 | 추가 요청, SLA 연장 가능 |

### 측정 방법
```
실제 검토 시간 = 총 소요 시간 - 서류 대기 시간
```

예시:
- 케이스 오픈: Day 1 10:00
- 서류 요청: Day 1 14:00 (4시간 경과)
- 서류 제출: Day 6 10:00 (5일 대기)
- 최종 결정: Day 6 16:00 (6시간 경과)
- **실제 검토 시간**: 4시간 + 6시간 = 10시간 (SLA 준수)

---

## SLA 측정 방법

### 측정 지표 정의

#### First Pick Time (첫 할당 시간)
**정의**: 케이스 생성 시점부터 검토자에게 할당될 때까지의 시간

**시작 시점**: `case.created_at`
**종료 시점**: `task.assigned_at` (첫 번째 Task 할당 시점)

**계산**:
```sql
SELECT
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY first_pick_time)
FROM (
    SELECT
        c.id AS case_id,
        EXTRACT(EPOCH FROM (MIN(t.assigned_at) - c.created_at)) / 3600 AS first_pick_time
    FROM cases c
    JOIN tasks t ON t.case_id = c.id
    WHERE c.created_at >= NOW() - INTERVAL '7 days'
        AND c.priority = 'p1'
    GROUP BY c.id
) subquery;
```

#### Resolution Time (해결 시간)
**정의**: 케이스 생성부터 최종 결정(close)까지의 시간 (서류 대기 시간 제외)

**시작 시점**: `case.created_at`
**종료 시점**: `case.closed_at`
**제외**: `awaiting_docs` 상태 기간

**계산**:
```sql
SELECT
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY resolution_time)
FROM (
    SELECT
        c.id,
        (EXTRACT(EPOCH FROM (c.closed_at - c.created_at)) -
         COALESCE(SUM(EXTRACT(EPOCH FROM (ce.ended_at - ce.started_at))), 0)
        ) / 3600 AS resolution_time
    FROM cases c
    LEFT JOIN (
        SELECT
            case_id,
            started_at,
            COALESCE(ended_at, NOW()) AS ended_at
        FROM case_events
        WHERE status = 'awaiting_docs'
    ) ce ON ce.case_id = c.id
    WHERE c.closed_at IS NOT NULL
        AND c.created_at >= NOW() - INTERVAL '7 days'
        AND c.priority = 'p1'
    GROUP BY c.id, c.created_at, c.closed_at
) subquery;
```

#### Active Review Time (실제 검토 시간)
**정의**: 검토자가 실제로 작업한 시간

**계산**:
```sql
SELECT
    AVG(review_time) AS avg_review_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY review_time) AS p95_review_time
FROM (
    SELECT
        t.id,
        SUM(EXTRACT(EPOCH FROM (te.ended_at - te.started_at))) / 3600 AS review_time
    FROM tasks t
    JOIN task_events te ON te.task_id = t.id
    WHERE te.event_type = 'in_progress'
        AND te.ended_at IS NOT NULL
        AND t.created_at >= NOW() - INTERVAL '7 days'
    GROUP BY t.id
) subquery;
```

### 측정 주기
- **실시간**: SLA 위반 알림용
- **일일**: 운영 대시보드
- **주간**: 팀 리뷰 및 리포트
- **월간**: 경영진 리포트

---

## SLA 리포트

### 일일 리포트

#### 구조
```markdown
# HITL SLA 일일 리포트 - {날짜}

## 전체 요약
- 총 케이스: {건수}
- SLA 준수율: {비율}% (목표: 95%)
- SLA 위반: {건수}

## 우선순위별

### P0 (Critical)
- 케이스: {건수}
- SLA 준수: {건수} / {총 건수} ({비율}%)
- p95 Resolution Time: {시간}시간 (SLA: 4시간)
- 위반 케이스: {케이스 ID 목록}

### P1 (High)
{위와 동일}

### P2 (Medium)
{위와 동일}

### P3 (Low)
{위와 동일}

## 위반 케이스 상세
| 케이스 ID | 우선순위 | 할당자 | 소요 시간 | SLA | 위반 시간 | 상태 | 사유 |
|----------|----------|--------|-----------|-----|-----------|------|------|
| {id} | P0 | {user} | 5.2h | 4h | +1.2h | closed | {사유} |

## 액션 아이템
- [ ] {액션 1}
- [ ] {액션 2}
```

### 주간 리포트

#### 추가 섹션
- **트렌드 분석**: 지난주 대비 변화
- **검토자별 성과**: 개인별 SLA 준수율
- **병목 구간 분석**: 어느 단계에서 지연 발생?
- **개선 제안**: 프로세스 개선 아이디어

### 월간 리포트

#### 추가 섹션
- **월간 종합 요약**: 전체 성과 및 하이라이트
- **우선순위 재조정 제안**: 케이스 분류 개선
- **용량 계획**: 인력 필요 예측
- **정책 변경 제안**: SLA 조정 필요성 검토

---

## SLA 거버넌스

### SLA 설정 및 변경

#### 신규 SLA 설정
1. **데이터 수집**: 최소 1개월 간 현재 성과 측정
2. **목표 설정**: 현실적이면서 도전적인 목표
3. **이해관계자 협의**: 운영팀, 고객지원팀, 경영진
4. **승인**: Ops Admin 승인
5. **공지 및 교육**: 팀 공지 및 교육 (1주일 전)
6. **시행**: 정식 시행
7. **모니터링**: 첫 1개월 집중 모니터링

#### SLA 변경
- **완화 (더 느슨하게)**: 신중히 검토, 고객 영향 고려
- **강화 (더 엄격하게)**: 팀 역량 확인, 점진적 적용
- **변경 주기**: 분기 단위 권장

### SLA 예외 처리

#### 예외 승인 케이스
- 고객 요청 (서류 제출 지연 등)
- 외부 요인 (공휴일, 시스템 장애)
- 복잡도 높음 (복잡한 케이스, 다수 이해관계자)

#### 예외 승인 절차
1. 검토자가 예외 요청 (사유 기재)
2. Senior Reviewer 또는 Ops Admin 승인
3. 승인 시 연장된 SLA 적용
4. 고객에게 예상 시간 안내
5. 예외 사유 기록 (통계 및 분석용)

---

## SLA 최적화

### 베스트 프랙티스

#### 1. 적절한 우선순위 분류
- 자동 분류 규칙 정기 검토
- 오분류 케이스 분석 및 조정

#### 2. 효율적인 라우팅
- 스킬 기반 할당 최적화
- 작업량 균등 분배

#### 3. 병목 구간 제거
- 서류 요청 템플릿 개선 (명확한 안내)
- 자주 묻는 질문 자동화
- 에스컬레이션 프로세스 간소화

#### 4. 예방적 에스컬레이션
- SLA 80% 소진 시 자동 알림
- 복잡한 케이스 조기 에스컬레이션

#### 5. 지속적 개선
- 주간 회고 (retrospective)
- 위반 케이스 root cause 분석
- 프로세스 개선 제안 및 시행

### 용량 계획

#### 검토자 수요 예측
```
필요 검토자 수 = (예상 케이스 수 × 평균 검토 시간) / (검토자 가용 시간 × SLA 준수 목표)
```

예시:
- 예상 케이스: 100건/일
- 평균 검토 시간: 1시간
- 검토자 가용 시간: 6시간/일 (실제 작업 시간, 회의 등 제외)
- SLA 준수 목표: 95%

```
필요 검토자 수 = (100 × 1) / (6 × 0.95) = 17.5 → 18명
```

버퍼 고려: 18명 × 1.2 = 21.6 → 22명 (휴가, 병가, 교육 등 고려)

---

## SLA 모니터링 대시보드

### 실시간 대시보드 (Grafana)

#### 패널 구성
1. **SLA 준수율** (Gauge)
   - 현재: {비율}%
   - 목표: 95%
   - 색상: 녹색(≥95%), 노랑(90-95%), 빨강(<90%)

2. **현재 케이스 현황** (Table)
   - 우선순위별 대기 케이스
   - SLA 남은 시간
   - 위반 임박 케이스 강조

3. **p95 Resolution Time** (Time Series)
   - 우선순위별 추이 (1시간 단위)
   - SLA 기준선 표시

4. **SLA 위반 알림** (Alert List)
   - 최근 위반 케이스 목록
   - 조치 상태

5. **검토자별 작업량** (Bar Chart)
   - 현재 할당된 케이스 수
   - 오늘 처리한 케이스 수

### 알림 설정
```yaml
alerts:
  - name: "P0 SLA 위반 임박"
    condition: "P0 케이스 SLA 90% 소진"
    severity: critical
    channels:
      - pagerduty
      - slack: #hitl-critical

  - name: "P1 SLA 위반 임박"
    condition: "P1 케이스 SLA 90% 소진"
    severity: warning
    channels:
      - slack: #hitl-ops

  - name: "전체 SLA 준수율 저하"
    condition: "지난 1시간 SLA 준수율 < 90%"
    severity: warning
    channels:
      - slack: #hitl-ops
      - email: ops-admin@company.com
```

---

## FAQ

### Q1: SLA를 준수하지 못한 케이스는 어떻게 되나요?
**A**: SLA 위반 자체가 서비스 중단을 의미하지는 않습니다. 그러나:
- 위반 사유 기록 및 분석
- 반복적 위반 시 프로세스 개선
- 심각한 위반(P0)은 고객 사과 및 보상 검토

### Q2: 서류 요청 시 SLA는 어떻게 되나요?
**A**: 서류 요청 기간은 SLA에서 제외됩니다. 고객 제출 후 SLA 재시작.

### Q3: 복잡한 케이스로 SLA 준수가 어려운 경우?
**A**: Senior Reviewer 또는 Ops Admin에게 예외 승인 요청. 승인 시 연장된 SLA 적용.

### Q4: SLA와 SLO의 차이는?
**A**:
- **SLO** (목표): 내부 목표 (예: 20시간)
- **SLA** (약속): 고객 약속 (예: 24시간)
- SLO를 더 엄격하게 설정하여 SLA 위반 방지

### Q5: SLA 변경은 얼마나 자주 하나요?
**A**: 분기 단위로 검토, 필요 시 조정. 급격한 변경은 피하고 점진적으로.

---

## 관련 문서
- [HITL Ops Runbook](../ops/runbook_hitl_ops.md)
- [Queue Routing Guide](queue_routing.md)
- [Review Checklist](../ops/checklists/review.md)
