# Queue Routing Guide

## 목적
이 문서는 HITL 케이스를 적절한 검토자에게 효율적으로 라우팅하는 방법을 정의합니다.

---

## 라우팅 개요

### 라우팅 목표
1. **정확성**: 올바른 스킬의 검토자에게 할당
2. **공정성**: 작업량을 균등하게 분배
3. **효율성**: 빠른 할당으로 SLA 준수
4. **유연성**: 우선순위와 용량에 따라 동적 조정

### 라우팅 프로세스
```
[케이스 생성]
    ↓
[라우팅 규칙 평가]
    ↓
[큐 선택]
    ↓
[검토자 선택]
    ↓
[할당]
```

---

## 큐 (Queue) 구조

### 큐 유형

#### 1. 제품/도메인별 큐

##### credit_personal (개인 신용 대출)
**담당 제품**:
- 신용 대출
- 마이너스 통장
- 신용카드 한도

**필요 스킬**:
- `credit_scoring`
- `personal_lending`

**검토자 수**: 10-15명

##### credit_business (기업 신용 대출)
**담당 제품**:
- 기업 대출
- 사업자 대출

**필요 스킬**:
- `credit_scoring`
- `business_lending`
- `financial_analysis`

**검토자 수**: 5-8명

##### mortgage (주택담보대출)
**담당 제품**:
- 주택담보대출
- 주택담보대출 전환

**필요 스킬**:
- `mortgage_lending`
- `collateral_valuation`
- `real_estate`

**검토자 수**: 8-10명

#### 2. 우선순위별 큐

##### p0_critical (긴급)
**특징**:
- 모든 제품의 P0 케이스
- Senior Reviewer 우선 할당
- 실시간 모니터링

**검토자**: Senior Reviewer 전원

##### p1_high (높음)
**특징**:
- 복잡하거나 중요한 케이스
- 경험 많은 검토자 할당

**검토자**: Reviewer (3년+ 경력) + Senior Reviewer

#### 3. 특수 큐

##### appeals (이의 제기)
**특징**:
- 모든 Appeals 케이스
- 원래 검토자와 다른 Senior Reviewer 배정

**검토자**: Senior Reviewer 전용

##### qa_review (품질 검토)
**특징**:
- QA 샘플링 케이스
- 이중 검토

**검토자**: QA Team 전용

##### escalated (에스컬레이션)
**특징**:
- 검토자가 에스컬레이션한 케이스
- 복잡하거나 정책 예외 필요

**검토자**: Senior Reviewer + Ops Admin

##### burst (버스트/오버플로우)
**특징**:
- 일시적 케이스 폭증 시 사용
- 임시 인력 또는 타 팀 지원

**검토자**: 교차 훈련된 검토자, 임시 인력

---

## 라우팅 규칙

### 규칙 우선순위

#### 1순위: 우선순위 (Priority)
```yaml
if case.priority == 'p0':
    queue = 'p0_critical'
elif case.priority == 'p1' and case.complexity == 'high':
    queue = 'p1_high'
else:
    # 제품/도메인별 큐로 진행
```

#### 2순위: 케이스 유형 (Type)
```yaml
if case.type == 'appeal':
    queue = 'appeals'
elif case.type == 'qa_review':
    queue = 'qa_review'
elif case.status == 'escalated':
    queue = 'escalated'
else:
    # 제품/도메인별 큐로 진행
```

#### 3순위: 제품/도메인 (Product/Domain)
```yaml
if case.product in ['credit_loan', 'credit_card', 'overdraft']:
    queue = 'credit_personal'
elif case.product in ['business_loan', 'business_credit']:
    queue = 'credit_business'
elif case.product in ['mortgage', 'mortgage_refinance']:
    queue = 'mortgage'
else:
    queue = 'general'
```

#### 4순위: 지역 (Region) - 해당 시
```yaml
if case.region == 'seoul':
    queue = queue + '_seoul'
elif case.region == 'busan':
    queue = queue + '_busan'
```

#### 5순위: 큐 용량 (Capacity)
```yaml
if queue.current_load > queue.max_capacity:
    # 오버플로우 처리
    if case.priority in ['p0', 'p1']:
        queue = 'escalated'  # 즉시 에스컬레이션
    else:
        queue = 'burst'  # 버스트 큐로
```

### 라우팅 알고리즘

#### Weighted Round-Robin
기본 할당 알고리즘:

```python
def route_to_reviewer(case, queue):
    # 1. 큐에서 가용 검토자 목록
    available_reviewers = get_available_reviewers(queue)

    # 2. 스킬 매칭
    skilled_reviewers = [
        r for r in available_reviewers
        if has_required_skills(r, case)
    ]

    # 3. 현재 작업량 기반 가중치 계산
    weights = []
    for reviewer in skilled_reviewers:
        current_load = get_current_case_count(reviewer)
        max_load = reviewer.max_concurrent_cases
        weight = max(0, max_load - current_load)
        weights.append(weight)

    # 4. 가중 랜덤 선택
    if sum(weights) == 0:
        # 모두 만석이면 가장 적게 가진 사람에게
        reviewer = min(skilled_reviewers, key=lambda r: get_current_case_count(r))
    else:
        reviewer = random.choices(skilled_reviewers, weights=weights)[0]

    return reviewer
```

#### Skill-Based Routing
스킬 매칭:

```python
def has_required_skills(reviewer, case):
    required_skills = get_required_skills(case)
    reviewer_skills = reviewer.skills

    # 모든 필수 스킬 보유 확인
    return all(skill in reviewer_skills for skill in required_skills)

def get_required_skills(case):
    skills = []

    # 제품별 스킬
    if case.product in ['credit_loan', 'credit_card']:
        skills.append('credit_scoring')
        skills.append('personal_lending')
    elif case.product in ['business_loan']:
        skills.append('credit_scoring')
        skills.append('business_lending')
        skills.append('financial_analysis')
    elif case.product in ['mortgage']:
        skills.append('mortgage_lending')
        skills.append('collateral_valuation')

    # 복잡도별 스킬
    if case.complexity == 'high':
        skills.append('complex_analysis')

    # 특수 상황
    if case.has_fraud_suspicion:
        skills.append('fraud_detection')

    return skills
```

#### Fairness Algorithm (공정성)
작업량 균등 분배:

```python
def calculate_fairness_score(reviewer):
    # 현재 작업량
    current_cases = get_current_case_count(reviewer)

    # 오늘 처리한 케이스 수
    today_completed = get_today_completed_count(reviewer)

    # 평균 대비 편차
    team_avg_current = get_team_avg_current_cases()
    team_avg_completed = get_team_avg_completed_today()

    # 공정성 점수 (낮을수록 더 할당받아야 함)
    fairness_score = (
        (current_cases / team_avg_current) * 0.6 +
        (today_completed / team_avg_completed) * 0.4
    )

    return fairness_score

# 라우팅 시 fairness_score가 낮은 검토자 우선
```

---

## 검토자 스킬 관리

### 스킬 정의

#### 제품 지식 스킬
| 스킬 코드 | 스킬 이름 | 설명 |
|----------|----------|------|
| `credit_scoring` | 신용 평가 | 신용점수, 신용 이력 분석 |
| `personal_lending` | 개인 대출 | 개인 신용 대출 심사 |
| `business_lending` | 기업 대출 | 기업/사업자 대출 심사 |
| `mortgage_lending` | 주택담보대출 | 주택담보대출 심사 |
| `collateral_valuation` | 담보 평가 | 부동산, 차량 등 담보 가치 평가 |
| `financial_analysis` | 재무 분석 | 재무제표, 사업 계획 분석 |

#### 역량 스킬
| 스킬 코드 | 스킬 이름 | 설명 |
|----------|----------|------|
| `complex_analysis` | 복잡 분석 | 복잡한 케이스 분석 능력 |
| `fraud_detection` | 사기 탐지 | 사기 징후 식별 |
| `policy_exception` | 정책 예외 | 정책 예외 판단 권한 |
| `senior_approval` | 선임 승인 | 고액/복잡 케이스 최종 승인 |

#### 프로세스 스킬
| 스킬 코드 | 스킬 이름 | 설명 |
|----------|----------|------|
| `appeals_review` | 이의 검토 | Appeals 케이스 검토 |
| `qa_audit` | 품질 감사 | QA 감사 수행 |
| `escalation_handling` | 에스컬레이션 처리 | 에스컬레이션 케이스 처리 |

### 스킬 레벨

#### Level 1 (Junior): 기본
- 표준 케이스 검토 가능
- 지도 감독 필요
- 복잡한 케이스는 에스컬레이션

#### Level 2 (Mid): 숙련
- 대부분 케이스 독립 검토
- 일부 복잡한 케이스 처리
- 경계선 케이스 판단

#### Level 3 (Senior): 전문가
- 모든 케이스 검토 가능
- 복잡한 케이스 전문
- 정책 예외 승인 권한
- Appeals 검토

#### Level 4 (Expert): 마스터
- 최고 난이도 케이스
- 정책 개발 참여
- 교육 및 멘토링
- 프로세스 개선 주도

### 스킬 획득 및 인증

#### 신규 스킬 습득 과정
1. **교육** (1-2주)
   - 이론 교육
   - 사례 연구
   - 시뮬레이션

2. **실습** (2-4주)
   - Shadow 검토 (선임 검토자 관찰)
   - 지도 검토 (선임 검토자 지도하에 검토)
   - 이중 검토 (독립 검토 후 선임 검토자 확인)

3. **평가** (1주)
   - 테스트 케이스 검토
   - 선임 검토자 평가
   - QA 평가

4. **인증**
   - 합격 시 스킬 부여
   - 프로필 업데이트
   - 해당 큐 접근 권한

#### 스킬 유지 및 갱신
- **정기 교육**: 분기 1회
- **재인증**: 연 1회 (QA 샘플 평가)
- **스킬 레벨 업그레이드**: 경력 및 성과 기반

---

## 오버플로우 관리

### 오버플로우 정의
큐의 케이스 대기 수가 임계값을 초과한 상태:

```yaml
overflow_thresholds:
  p0_critical:
    warning: 3
    critical: 5

  p1_high:
    warning: 10
    critical: 20

  credit_personal:
    warning: 30
    critical: 50

  mortgage:
    warning: 20
    critical: 35
```

### 오버플로우 대응

#### Level 1: Warning (경고)
**조치**:
- 팀 리더에게 알림
- 다음 근무조에 사전 알림
- 자발적 잔업 요청

#### Level 2: Critical (위험)
**조치**:
1. **버스트 큐 활성화**
   - 타 팀 검토자 차출 (교차 훈련된 인력)
   - 임시 인력 투입

2. **우선순위 재조정**
   - P2/P3 케이스 일시 보류
   - P0/P1 집중 처리

3. **라우팅 재분배**
   - 여유 있는 큐로 일부 케이스 이동
   - 지역 간 재분배 (가능 시)

4. **에스컬레이션 간소화**
   - 에스컬레이션 임계값 완화
   - 빠른 의사결정 지원

#### Level 3: Emergency (비상)
**조치**:
1. **자동화 확대**
   - 자동 승인 임계값 조정 (일시적)
   - 단순 케이스 자동 처리

2. **외부 지원**
   - 외주 검토팀 투입
   - 타 지역/국가 팀 지원

3. **SLA 재조정**
   - 임시 SLA 연장 (고객 사전 안내)

4. **경영진 보고**
   - 상황 보고 및 자원 요청

### 오버플로우 예방

#### 예측 모델
과거 데이터 기반 케이스 수요 예측:

```python
def predict_daily_cases(date, product):
    # 요일, 계절성, 이벤트, 트렌드 고려
    base_volume = historical_avg_volume(product)

    # 요일 보정 (월요일 +20%, 금요일 -10% 등)
    day_of_week_factor = get_day_of_week_factor(date)

    # 계절성 (연말 +30%, 여름휴가 -15% 등)
    seasonal_factor = get_seasonal_factor(date)

    # 이벤트 (마케팅 캠페인, 금리 변동 등)
    event_factor = get_event_factor(date)

    predicted = base_volume * day_of_week_factor * seasonal_factor * event_factor

    return predicted
```

#### 용량 계획
```python
def capacity_plan(predicted_cases, target_sla_compliance=0.95):
    avg_review_time = 1.0  # hours
    reviewer_daily_capacity = 6  # cases/day

    required_reviewers = (
        predicted_cases * avg_review_time / reviewer_daily_capacity
    ) / target_sla_compliance

    # 버퍼 추가 (20%)
    required_reviewers *= 1.2

    return math.ceil(required_reviewers)
```

#### 선제적 조치
- **예측 > 용량**: 사전 지원 인력 확보
- **휴가 조정**: 피크 시즌 휴가 제한
- **교육 강화**: 교차 훈련으로 유연성 확보

---

## 라우팅 정확도 측정

### 정확도 메트릭

#### Skill Match Accuracy (스킬 매칭 정확도)
케이스가 적절한 스킬의 검토자에게 할당되었는가?

**측정 방법**:
```sql
SELECT
    COUNT(CASE WHEN skill_mismatch = false THEN 1 END) * 100.0 / COUNT(*) AS skill_match_accuracy
FROM (
    SELECT
        c.id,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM case_required_skills crs
                WHERE crs.case_id = c.id
                    AND crs.skill NOT IN (
                        SELECT skill FROM reviewer_skills WHERE reviewer_id = c.assigned_to
                    )
            ) THEN true
            ELSE false
        END AS skill_mismatch
    FROM cases c
    WHERE c.assigned_to IS NOT NULL
        AND c.created_at >= NOW() - INTERVAL '7 days'
) subquery;
```

**목표**: ≥ 98%

#### Re-routing Rate (재라우팅 비율)
검토자가 스킬 부족으로 케이스를 반환하는 비율

**측정 방법**:
```sql
SELECT
    COUNT(CASE WHEN re_routed = true THEN 1 END) * 100.0 / COUNT(*) AS re_routing_rate
FROM cases
WHERE created_at >= NOW() - INTERVAL '7 days';
```

**목표**: ≤ 2%

#### Load Balance Fairness (작업량 공정성)
검토자 간 작업량 분산 정도

**측정 방법** (Gini Coefficient):
```python
def calculate_gini_coefficient(case_counts):
    """
    Gini Coefficient: 0 (완전 평등) ~ 1 (완전 불평등)
    """
    n = len(case_counts)
    sorted_counts = sorted(case_counts)

    cumsum = sum((i + 1) * count for i, count in enumerate(sorted_counts))

    gini = (2 * cumsum) / (n * sum(sorted_counts)) - (n + 1) / n

    return gini
```

**목표**: Gini ≤ 0.2 (공정한 분배)

#### Average Queue Wait Time (평균 큐 대기 시간)
케이스가 큐에서 할당되기까지의 시간

**측정 방법**:
```sql
SELECT
    queue_id,
    AVG(EXTRACT(EPOCH FROM (assigned_at - created_at)) / 60) AS avg_wait_minutes
FROM cases
WHERE created_at >= NOW() - INTERVAL '7 days'
    AND assigned_at IS NOT NULL
GROUP BY queue_id;
```

**목표**: 우선순위별 SLA의 First Pick Time 이내

---

## 라우팅 리포트

### 일일 라우팅 리포트

```markdown
# 라우팅 일일 리포트 - {날짜}

## 전체 요약
- 총 케이스: {건수}
- 라우팅 정확도: {비율}% (목표: 98%)
- 재라우팅: {건수} ({비율}%)
- 작업량 공정성 (Gini): {값} (목표: ≤ 0.2)

## 큐별 현황
| 큐 | 처리 | 대기 | 평균 대기 | 재라우팅 | 오버플로우 |
|----|------|------|-----------|----------|-----------|
| p0_critical | {건수} | {건수} | {시간} | {건수} | {상태} |
| credit_personal | {건수} | {건수} | {시간} | {건수} | {상태} |
| mortgage | {건수} | {건수} | {시간} | {건수} | {상태} |

## 검토자별 작업량
| 검토자 | 할당 | 완료 | 진행 중 | 재라우팅 | 공정성 점수 |
|--------|------|------|---------|----------|------------|
| {이름} | {건수} | {건수} | {건수} | {건수} | {점수} |

## 이슈 및 조치
- {이슈 1}: {조치}
- {이슈 2}: {조치}
```

### 주간 라우팅 분석

추가 분석:
- **스킬 갭 분석**: 부족한 스킬 식별
- **큐 성능 비교**: 큐별 효율성
- **라우팅 규칙 효과성**: 규칙 조정 필요성
- **용량 계획**: 다음 주 예측 및 준비

---

## 라우팅 최적화

### 지속적 개선

#### 1. 데이터 기반 규칙 조정
- 재라우팅 사유 분석
- 스킬 미스매치 패턴 식별
- 규칙 업데이트

#### 2. 머신러닝 라우팅 (향후)
```python
def ml_route_prediction(case):
    """
    과거 데이터로 학습한 모델로 최적 검토자 예측
    """
    features = extract_features(case)  # 제품, 복잡도, 금액, 고객 프로필 등

    # 각 검토자의 성공률 예측
    reviewer_scores = []
    for reviewer in available_reviewers:
        score = model.predict_success_rate(case, reviewer)
        reviewer_scores.append((reviewer, score))

    # 상위 검토자 중 작업량 고려하여 선택
    top_reviewers = sorted(reviewer_scores, key=lambda x: x[1], reverse=True)[:5]

    # 공정성 점수로 최종 선택
    final_reviewer = min(top_reviewers, key=lambda x: calculate_fairness_score(x[0]))

    return final_reviewer
```

#### 3. A/B 테스트
- 새로운 라우팅 규칙을 일부 케이스에 시범 적용
- 성과 비교 (SLA 준수율, 품질, 공정성)
- 효과 확인 후 전면 적용

---

## FAQ

### Q1: 특정 검토자에게 케이스를 직접 할당할 수 있나요?
**A**: 예, 수동 할당 가능합니다 (Ops Admin 권한). 그러나 공정성을 위해 최소화해야 합니다.

### Q2: 검토자가 케이스를 거부할 수 있나요?
**A**: 정당한 사유 (스킬 부족, 이해 상충 등) 시 가능. 재라우팅되며 사유 기록됩니다.

### Q3: 큐가 가득 찬 경우 어떻게 되나요?
**A**: 버스트 큐로 오버플로우되거나, 우선순위에 따라 에스컬레이션됩니다.

### Q4: 라우팅 규칙을 변경하려면?
**A**: Ops Admin이 설정 파일 업데이트 후 배포. 중대한 변경은 A/B 테스트 권장.

### Q5: 스킬이 부족한 검토자에게 할당되면?
**A**: 검토자가 반환 요청 가능. 재라우팅되며 해당 검토자는 교육 필요 식별됩니다.

---

## 관련 문서
- [SLA Policies Guide](sla_policies.md)
- [HITL Ops Runbook](../ops/runbook_hitl_ops.md)
- [Review Checklist](../ops/checklists/review.md)
