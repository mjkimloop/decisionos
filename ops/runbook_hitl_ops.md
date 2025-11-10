# HITL Operations Runbook

## 목적
이 런북은 Human-in-the-Loop (HITL) 운영팀의 케이스 검토, 태스크 처리, 이의 제기(Appeals) 대응 절차를 정의합니다. DecisionOS의 자동화 의사결정에 사람의 판단이 필요한 상황을 안전하고 신속하게 처리하는 것이 목표입니다.

## 개요

### HITL Ops v2 핵심 개념

#### 주요 객체
- **Case**: 검토가 필요한 결정/신청의 컨테이너
- **Task**: Case 내 수행해야 할 구체적 작업 단위
- **Queue**: 우선순위와 스킬 기준의 작업 대기열
- **Action**: 검토자가 취할 수 있는 조치
- **Appeal**: 최초 결정에 대한 이의 제기 프로세스

#### 역할 (RBAC)
- **reviewer**: 일반 검토자 (Case 검토 및 처리)
- **senior_reviewer**: 선임 검토자 (복잡한 케이스, Appeals 처리)
- **qa**: 품질 관리 (샘플링 검토, 품질 감사)
- **ops_admin**: 운영 관리자 (큐 관리, 재할당, 정책 조정)
- **auditor**: 감사자 (읽기 전용, 감사 추적 확인)

---

## 케이스 우선순위

### 우선순위 정의

#### P0 (Critical) - 긴급
**SLA**: 4시간 이내 해결
**특징**:
- 고액 거래 (예: 1억원 이상)
- VIP 고객
- 법적 기한 임박
- 사기 의심 (긴급 확인 필요)
- 시스템 오류로 인한 잘못된 거부

**예시**:
- "VIP 고객의 5억원 대출 신청이 시스템 오류로 거부됨"
- "사기 패턴 탐지되었으나 정상 고객일 가능성 있음 (긴급 확인)"

**처리 원칙**:
- 즉시 할당 (대기열 우선)
- 필요시 senior_reviewer 즉시 에스컬레이션
- 모든 조치는 실시간 로깅

#### P1 (High) - 높음
**SLA**: 24시간 이내 해결
**특징**:
- 경계선 케이스 (스코어 0.45-0.55)
- 중요 고객 (거래 이력 우수)
- 복잡한 사례 (여러 요인 검토 필요)
- 정책 예외 요청

**예시**:
- "신용점수 598점 (기준 600), 기타 조건 우수"
- "자영업자 소득 증빙 추가 확인 필요"

**처리 원칙**:
- 당일 내 할당
- 필요한 추가 서류 요청
- 충분한 시간 들여 검토

#### P2 (Medium) - 보통
**SLA**: 48시간 이내 해결
**특징**:
- 표준 검토 케이스
- 일부 정보 부족 (보완 가능)
- 정책 확인 필요

**예시**:
- "소득 증빙 서류 추가 필요"
- "최근 이직으로 재직 증명 확인 필요"

**처리 원칙**:
- 순차 처리
- 서류 요청 시 고객에게 3-5일 여유 제공
- 표준 프로세스 준수

#### P3 (Low) - 낮음
**SLA**: 72시간 이내 해결
**특징**:
- 단순 확인 사항
- 비긴급 문의
- 정보 제공 요청

**예시**:
- "대출 조건 문의"
- "서류 제출 방법 안내"

**처리 원칙**:
- 표준 처리 순서
- 템플릿 활용
- 고객 셀프 서비스 유도

---

## 케이스 라이프사이클

### 상태 전환 다이어그램

```
[open] → [pending] → [awaiting_docs] → [escalated] → [closed]
   ↓         ↓              ↓              ↓            ↓
[rejected] [approved]   [rejected]    [approved]   [archived]
```

### 상태 정의

#### open (열림)
- 케이스가 생성되고 큐에 적재됨
- 할당 대기 중
- **Action**: 자동 라우팅에 따라 assignee 배정

#### pending (보류)
- 검토자에게 할당되어 검토 중
- **Action**: 검토자가 조사 및 판단 수행

#### awaiting_docs (서류 대기)
- 추가 서류/정보 요청됨
- 고객 응답 대기 중
- **Action**: 서류 도착 시 pending 으로 복귀

#### escalated (에스컬레이션)
- senior_reviewer 또는 상위 관리자에게 전달
- 복잡하거나 정책 예외 필요
- **Action**: 상위 검토자가 최종 결정

#### closed (종료)
- 최종 결정 완료 (승인/거부)
- 고객에게 통지 완료
- **Action**: 일정 기간 후 archived

#### rejected (거부)
- 신청 거부 결정
- Reason Codes 포함
- **Action**: Appeal 가능

#### approved (승인)
- 신청 승인 결정
- 조건 명시 (한도, 금리 등)
- **Action**: 계약 진행

---

## 케이스 처리 절차

### 1. 케이스 수령 (Pick)

#### 자동 할당
시스템이 스킬/우선순위/가용성에 따라 자동 할당:
```bash
# 시스템이 자동으로 할당
# 검토자는 Inbox에서 확인
```

#### 수동 픽업
검토자가 큐에서 직접 선택:
```bash
# CLI
dosctl tasks next --queue credit_review

# 또는 UI에서 "다음 케이스 가져오기" 클릭
```

**체크리스트**:
- [ ] 할당된 케이스를 Inbox에서 확인
- [ ] 우선순위 확인 (P0는 즉시 처리)
- [ ] SLA 남은 시간 확인
- [ ] 본인의 스킬/권한으로 처리 가능한지 확인

### 2. 케이스 검토 (Review)

#### 정보 수집
**확인 사항**:
1. **의사결정 컨텍스트**
   - 원래 자동 결정 결과
   - 스코어 및 Reason Codes
   - 사용된 모델 버전 및 정책

2. **고객 정보**
   - 신청 내용 (금액, 용도, 기간)
   - 신용 정보 (점수, 이력, 연체)
   - 소득 정보 (금액, 안정성, 증빙)
   - 거래 이력 (기존 고객 여부, 성과)

3. **추가 자료**
   - 첨부 서류 (신분증, 소득 증빙, 재직 증명)
   - 이전 노트 및 커뮤니케이션
   - 유사 케이스 참고

#### 판단 기준
**승인 고려 요소**:
- ✅ 신용 점수가 기준에 근접하지만 기타 요소 우수
- ✅ 일시적 어려움이나 오류로 인한 부정적 요인
- ✅ 담보/보증으로 리스크 완화 가능
- ✅ 기존 거래 이력 우수
- ✅ 소득 안정성 높음

**거부 고려 요소**:
- ❌ 최근 연체 이력 (90일 이상)
- ❌ 부채 비율 과도하게 높음 (DTI > 50%)
- ❌ 소득 증빙 불가 또는 의심스러움
- ❌ 사기 징후 발견
- ❌ 정책/규제 위반

**체크리스트** ([ops/checklists/review.md](checklists/review.md) 참조):
- [ ] 신청 정보 완전성 확인
- [ ] 신용 정보 최신성 확인
- [ ] 소득 증빙 적절성 확인
- [ ] 부채 수준 평가
- [ ] 사기 징후 확인
- [ ] 정책/규제 준수 확인
- [ ] 유사 케이스 일관성 확인

### 3. 조치 수행 (Action)

#### approve (승인)
```bash
dosctl tasks do approve --id {task_id} \
  --limit 30000000 \
  --rate 4.5 \
  --conditions "보증인 필요" \
  --note "소득 안정성 우수, 기존 거래 이력 양호"
```

**필수 입력**:
- 승인 조건 (한도, 금리, 기간, 담보/보증 요구사항)
- 승인 사유 (간략히)
- Reason Codes (승인 근거)

**사후 조치**:
- 고객에게 승인 통지 자동 발송
- 계약 프로세스 시작
- 케이스 상태 → closed

#### deny (거부)
```bash
dosctl tasks do deny --id {task_id} \
  --reason-codes CREDIT-DENY-SCORE-001,CREDIT-DENY-DTI-001 \
  --note "신용점수 580 (기준 600 미만), DTI 48% (기준 40% 초과)" \
  --improvement-advice "6개월 후 재신청 권장"
```

**필수 입력**:
- Reason Codes (거부 사유 코드)
- 상세 설명
- 개선 방안 (재신청 조건)

**사후 조치**:
- 고객에게 거부 통지 및 설명서 발송
- Appeal 가능 안내
- 케이스 상태 → closed

#### request_docs (서류 요청)
```bash
dosctl tasks do request_docs --id {task_id} \
  --docs "원천징수영수증,재직증명서,통장사본(최근3개월)" \
  --deadline "2025-11-10" \
  --note "소득 확인을 위해 추가 서류 필요"
```

**필수 입력**:
- 필요한 서류 목록
- 제출 기한 (일반적으로 3-7일)
- 요청 사유

**사후 조치**:
- 고객에게 서류 요청 발송 (템플릿 사용)
- 케이스 상태 → awaiting_docs
- 기한 내 미제출 시 자동 알림 또는 거부

#### escalate (에스컬레이션)
```bash
dosctl tasks do escalate --id {task_id} \
  --to senior_reviewer \
  --reason "정책 예외 검토 필요: 신용점수 598점, 기타 조건 우수" \
  --note "승인 권장하나 senior_reviewer 승인 필요"
```

**에스컬레이션 사유**:
- 정책 예외 필요
- 고액 거래 (권한 초과)
- 복잡한 사례 (판단 어려움)
- 법적/규제 이슈
- 품질 의심 (재검토 필요)

**사후 조치**:
- senior_reviewer 큐로 이동
- SLA 리셋 (새로운 SLA 적용)
- 에스컬레이션 사유 기록

#### comment (코멘트)
```bash
dosctl tasks do comment --id {task_id} \
  --body "고객과 통화 완료. 최근 이직 확인. 재직증명서 3일 내 제출 예정."
```

**용도**:
- 진행 상황 기록
- 다른 검토자와 정보 공유
- 감사 추적

#### close (종료)
```bash
dosctl cases close --id {case_id} \
  --resolution "승인 완료, 계약 진행 중" \
  --final-decision approve
```

**종료 조건**:
- 최종 결정 완료 (approve/deny)
- 고객 통지 완료
- 모든 Task 완료

---

## 우선순위별 처리 시나리오

### P0 시나리오: VIP 고객 고액 대출

**상황**:
- VIP 고객 (거래 3년, 연체 0회)
- 신청액: 5억원
- 자동 시스템이 고액으로 인해 수동 검토 라우팅

**절차**:
1. **즉시 픽업** (P0 알림 수신 즉시)
   ```bash
   dosctl cases show --id case_vip_001
   ```

2. **긴급 검토** (30분 이내)
   - ✅ 신용점수: 850 (우수)
   - ✅ 소득: 연 5억원 (증빙 확인)
   - ✅ 거래 이력: 3년, 성실 상환
   - ✅ 담보: 부동산 15억원 (감정가)
   - ⚠️ 대출액: 5억원 (고액, 정책 확인 필요)

3. **senior_reviewer 즉시 에스컬레이션**
   ```bash
   dosctl tasks do escalate --id task_001 \
     --to senior_reviewer \
     --reason "VIP 고객 고액 대출 (5억원), 모든 조건 우수, 정책 승인 필요" \
     --priority p0
   ```

4. **senior_reviewer 승인** (1시간 이내)
   ```bash
   dosctl tasks do approve --id task_001 \
     --limit 500000000 \
     --rate 3.8 \
     --conditions "부동산 담보 설정" \
     --note "VIP 고객, 신용 우수, 담보 충분"
   ```

5. **완료** (총 소요 시간: 2시간)
   - SLA: 4시간 (준수 ✅)
   - 고객 만족도: 높음 (신속 처리)

### P1 시나리오: 경계선 케이스

**상황**:
- 일반 고객
- 신청액: 3,000만원
- 신용점수: 598점 (기준 600점 미달)
- 기타 조건: 양호

**절차**:
1. **당일 내 픽업** (8시간 이내)
   ```bash
   dosctl tasks next --queue credit_review
   ```

2. **상세 검토** (2-3시간)
   - ⚠️ 신용점수: 598 (기준 600 미달, 차이 2점)
   - ✅ 소득: 연 6,000만원 (안정적)
   - ✅ DTI: 25% (양호)
   - ✅ 연체 이력: 없음
   - ✅ 재직: 정규직 5년

3. **판단**: 승인 (정책 예외 적용)
   - 신용점수 차이 미미 (2점)
   - 기타 모든 조건 우수
   - 리스크 낮음

4. **senior_reviewer 에스컬레이션** (정책 예외 승인 필요)
   ```bash
   dosctl tasks do escalate --id task_002 \
     --to senior_reviewer \
     --reason "신용점수 598점 (기준 600), 기타 조건 우수, 예외 승인 권장" \
     --recommendation approve
   ```

5. **senior_reviewer 승인** (4시간 이내)
   ```bash
   dosctl tasks do approve --id task_002 \
     --limit 30000000 \
     --rate 5.5 \
     --note "정책 예외 적용: 신용점수 598점이나 기타 조건 우수, 리스크 낮음"
   ```

6. **완료** (총 소요 시간: 18시간)
   - SLA: 24시간 (준수 ✅)

### P2 시나리오: 서류 보완 필요

**상황**:
- 일반 고객
- 신청액: 2,000만원
- 자영업자 (소득 증빙 추가 필요)

**절차**:
1. **픽업** (24시간 이내)
   ```bash
   dosctl tasks next --queue credit_review
   ```

2. **초기 검토** (1시간)
   - ✅ 신용점수: 680 (양호)
   - ⚠️ 소득: 자영업자, 증빙 불충분
   - ✅ 연체 이력: 없음

3. **서류 요청**
   ```bash
   dosctl tasks do request_docs --id task_003 \
     --docs "소득금액증명원(최근2년),사업자등록증,부가가치세신고서" \
     --deadline "2025-11-08" \
     --note "자영업자 소득 확인을 위해 추가 서류 필요"
   ```

4. **대기** (고객 서류 제출 시까지)
   - 케이스 상태 → awaiting_docs
   - 기한: 5일

5. **서류 도착 후 재검토** (1시간)
   - ✅ 소득: 연 5,000만원 확인
   - ✅ 사업: 3년 운영, 안정적

6. **승인**
   ```bash
   dosctl tasks do approve --id task_003 \
     --limit 20000000 \
     --rate 6.5 \
     --note "소득 증빙 확인 완료, 승인"
   ```

7. **완료** (총 소요 시간: 6일)
   - SLA: 48시간 (초기 검토) + 고객 대기 시간 (SLA 제외)
   - 최종 SLA: 준수 ✅

### P3 시나리오: 단순 문의

**상황**:
- 고객 문의: "대출 한도 확인"
- 신청 아님

**절차**:
1. **픽업** (48시간 이내)
   ```bash
   dosctl tasks next --queue customer_service
   ```

2. **확인 및 안내** (15분)
   - 템플릿 사용
   - 자동 한도 계산 링크 제공

3. **종료**
   ```bash
   dosctl cases close --id case_004 \
     --resolution "한도 안내 완료" \
     --final-decision info_provided
   ```

---

## 에스컬레이션 프로세스

### 에스컬레이션 레벨

#### Level 1 → Level 2 (reviewer → senior_reviewer)
**사유**:
- 정책 예외 필요
- 경계선 케이스 (판단 어려움)
- 고액 거래 (권한 초과)
- 고객 특수 요청

**절차**:
```bash
dosctl tasks do escalate --id {task_id} \
  --to senior_reviewer \
  --reason "정책 예외 검토 필요" \
  --context "..."
```

#### Level 2 → Level 3 (senior_reviewer → ops_admin)
**사유**:
- 정책 변경 필요 검토
- 시스템 이슈 보고
- 매우 복잡한 사례
- 법적/규제 이슈

**절차**:
```bash
dosctl tasks do escalate --id {task_id} \
  --to ops_admin \
  --reason "정책 검토 필요: 유사 케이스 증가 추세" \
  --impact "월 50건 이상 발생"
```

### 에스컬레이션 SLA
- **Level 1 → Level 2**: 동일 우선순위 SLA 유지
- **Level 2 → Level 3**: P0로 격상

---

## Appeals (이의 제기) 처리

### Appeals 프로세스

#### 1. 이의 제기 접수
**고객 제출 경로**:
- 웹 포털
- 이메일
- 고객센터 (전화)

**시스템 처리**:
```bash
# 시스템이 자동으로 Appeal 생성
# senior_reviewer 큐로 자동 라우팅
```

**확인 사항**:
- [ ] 원래 케이스 ID
- [ ] 거부 사유 확인
- [ ] 고객 제출 사유 및 추가 증빙
- [ ] 제출 기한 (일반적으로 결정 후 30일 이내)

#### 2. Appeals 검토
**검토 원칙**:
- **독립성**: 원래 검토자와 다른 senior_reviewer 배정
- **공정성**: 모든 증빙을 새롭게 검토
- **투명성**: 결정 근거 명확히 문서화

**체크리스트** ([ops/checklists/appeals.md](checklists/appeals.md) 참조):
- [ ] 원래 결정 검토
- [ ] 새로운 증빙 확인
- [ ] 정책 변경 여부 확인
- [ ] 오류 여부 확인
- [ ] 유사 케이스 일관성 확인

#### 3. Appeals 결정

**결과 유형**:

##### Uphold (유지)
원래 결정이 정당함
```bash
dosctl appeals resolve --id {appeal_id} \
  --resolution uphold \
  --message "원래 거부 사유(신용점수 부족, DTI 초과)가 여전히 유효합니다. 제출하신 추가 서류로도 기준 충족이 어렵습니다." \
  --reason-codes CREDIT-DENY-SCORE-001,CREDIT-DENY-DTI-001
```

**고객 통지**: 유지 사유 상세 설명, 개선 방안 제공

##### Overturn (번복)
원래 결정을 번복하여 승인
```bash
dosctl appeals resolve --id {appeal_id} \
  --resolution overturn \
  --message "제출하신 추가 소득 증빙을 확인한 결과, 승인 기준을 충족합니다." \
  --new-decision approve \
  --limit 25000000 \
  --rate 6.0
```

**고객 통지**: 승인 조건 안내, 계약 진행

##### Partial (조건부)
조건부 승인 또는 한도 조정
```bash
dosctl appeals resolve --id {appeal_id} \
  --resolution partial \
  --message "보증인 제공 조건으로 승인 가능합니다." \
  --new-decision approve_conditional \
  --limit 20000000 \
  --conditions "연대보증인 1인 필요"
```

**고객 통지**: 조건 설명, 조건 충족 시 진행 방법

#### 4. Appeals 통계 및 모니터링

**추적 메트릭**:
```yaml
appeals_metrics:
  - submission_rate: 전체 거부 중 이의 제기 비율
  - overturn_rate: 이의 제기 중 번복 비율
  - resolution_time_p95: 해결 시간 95 백분위
  - customer_satisfaction: 이의 제기 고객 만족도
```

**목표**:
- Appeals resolution time p95 ≤ 72시간
- Overturn rate: 10-20% (너무 높으면 원래 결정 품질 문제, 너무 낮으면 고객 불만)

---

## 품질 관리 (QA)

### QA 프로세스

#### 1. 샘플링
**샘플링 전략**:
- 무작위 샘플: 전체 케이스의 5%
- 타겟 샘플: 특정 조건 (새 검토자, 복잡한 케이스, 경계선)
- 리스크 기반: 고액, VIP, Appeals

**빈도**: 주간

#### 2. QA 검토
**평가 항목**:
- [ ] 절차 준수 (체크리스트 완료)
- [ ] 판단 적절성 (일관성, 정책 준수)
- [ ] 문서화 품질 (노트, Reason Codes)
- [ ] 타이밍 (SLA 준수)
- [ ] 고객 커뮤니케이션 품질

**점수**:
- Excellent (95-100점): 모든 항목 우수
- Good (85-94점): 대부분 적절
- Needs Improvement (70-84점): 일부 개선 필요
- Poor (< 70점): 재교육 필요

#### 3. 피드백 및 교육
- **개별 피드백**: QA 결과를 검토자에게 공유
- **집단 교육**: 공통 이슈에 대한 교육 세션
- **베스트 프랙티스**: 우수 사례 공유

#### 4. 연속 개선
- QA 결과 분석
- 정책/프로세스 개선 제안
- 자동화 기회 식별

---

## SLA 관리

### SLA 모니터링

#### 실시간 대시보드
**URL**: `https://grafana.company.com/d/hitl-sla`

**패널**:
- 현재 대기 중 케이스 (우선순위별)
- SLA 위반 임박 (1시간 이내)
- SLA 위반 발생
- 평균 처리 시간 (우선순위별)
- 검토자별 작업량 및 성과

#### 알림

**SLA 위반 임박** (Warning)
- **조건**: SLA 80% 소진
- **예**: P0 케이스 3.2시간 경과 (SLA 4시간)
- **알림**: Slack #hitl-ops
- **조치**: 우선순위 상향, 추가 검토자 할당 검토

**SLA 위반** (Critical)
- **조건**: SLA 초과
- **알림**: PagerDuty, Slack #hitl-critical
- **조치**:
  1. 즉시 senior_reviewer에게 에스컬레이션
  2. 사유 기록
  3. 고객에게 지연 사과 및 예상 시간 안내

### SLA 위반 대응

#### 위반 시 액션
```bash
# 1. 케이스 확인
dosctl cases show --id {case_id}

# 2. 즉시 에스컬레이션
dosctl tasks do escalate --id {task_id} \
  --to senior_reviewer \
  --reason "SLA 위반 (P0, 4시간 초과)" \
  --urgent

# 3. 고객 통지
dosctl cases notify-customer --id {case_id} \
  --template sla_breach_apology \
  --eta "+2h"
```

#### 사후 분석
- **원인 파악**: 왜 SLA 위반 발생했는가?
  - 케이스 복잡도 과소평가
  - 검토자 부족
  - 시스템 이슈
  - 서류 지연
- **개선 조치**: 재발 방지 대책
- **문서화**: Post-mortem 작성

---

## 정기 유지보수

### 일일 점검
- [ ] SLA 대시보드 확인
- [ ] 위반 임박 케이스 조치
- [ ] 대기열 적체 확인 (burst 필요 여부)
- [ ] 긴급 케이스 (P0) 현황

### 주간 점검
- [ ] SLA 준수율 리포트 생성
- [ ] QA 샘플링 실시
- [ ] 검토자 작업량 균형 확인
- [ ] 정책 예외 케이스 분석

### 월간 점검
- [ ] 전체 운영 리포트 작성
- [ ] Appeals 통계 분석 (overturn rate)
- [ ] 검토자 성과 평가
- [ ] 프로세스 개선 워크샵

---

## 도구 및 명령어

### dosctl hitl 명령어
```bash
# Cases
dosctl cases open --decision {decision_id} --priority p1
dosctl cases show --id {case_id}
dosctl cases assign --id {case_id} --to {user_id}
dosctl cases close --id {case_id} --resolution "..."

# Tasks
dosctl tasks next --queue {queue_id}
dosctl tasks show --id {task_id}
dosctl tasks do {action} --id {task_id} [options]

# Appeals
dosctl appeals submit --case {case_id} --reason "..."
dosctl appeals show --id {appeal_id}
dosctl appeals resolve --id {appeal_id} --resolution {uphold|overturn|partial}

# Operations
dosctl ops queues ls
dosctl ops queues stats --queue {queue_id}
dosctl ops sla report --from 2025-11-01 --to 2025-11-03
dosctl ops reassign --from {user_id} --to {user_id}  # 휴가 등
```

---

## 비상 대응

### 시나리오: 대량 케이스 적체

**상황**: 시스템 변경으로 인해 케이스 급증 (평소 50건/일 → 500건/일)

**대응**:
1. **즉시 조치** (1시간 이내)
   - 상황 파악 및 원인 분석
   - Ops Admin에게 알림
   - P0/P1 케이스 우선 처리

2. **단기 조치** (당일)
   - Burst queue 활성화 (추가 검토자 투입)
   - 우선순위 재조정 (P3 → 일시 보류)
   - 자동화 확대 (단순 케이스 자동 승인 임계값 조정)

3. **중기 조치** (1주일)
   - 시스템 수정 (케이스 발생 원인 제거)
   - 백로그 처리 계획 수립
   - 추가 인력 배치

4. **장기 조치** (1개월)
   - 프로세스 개선 (유사 상황 재발 방지)
   - 자동화 강화 (AI 보조 도구)
   - 용량 계획 재검토

---

## 연락처

- **HITL Ops Team**: #hitl-ops Slack 채널
- **Ops Admin**: ops-admin@company.com
- **QA Team**: #qa Slack 채널
- **On-call**: PagerDuty (hitl-oncall)

---

## 관련 문서
- [Review Checklist](checklists/review.md)
- [Appeals Checklist](checklists/appeals.md)
- [Appeals Response Templates](../templates/appeal_response_ko.md)
- [SLA Policies Guide](../docs/sla_policies.md)
- [Queue Routing Guide](../docs/queue_routing.md)
