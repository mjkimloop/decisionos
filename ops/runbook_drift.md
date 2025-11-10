# Drift Monitoring Runbook

## 목적
이 런북은 DecisionOS의 모델 및 데이터 드리프트(Drift) 감지, 모니터링, 대응 절차를 정의합니다. 드리프트는 프로덕션 환경에서 모델 성능 저하의 주요 원인이며, 조기 탐지와 신속한 대응이 필수적입니다.

## 개요

### 드리프트 유형

#### 1. Feature Drift (특성 드리프트)
**정의**: 입력 데이터 분포의 변화
**원인**:
- 사용자 행동 변화
- 계절적 패턴
- 시장/경제 상황 변화
- 데이터 수집 방식 변경

**예시**: 대출 신청자의 평균 소득 분포가 변경됨

#### 2. Prediction Drift (예측 드리프트)
**정의**: 모델 출력 분포의 변화
**원인**:
- Feature drift 영향
- 모델 자체 문제
- 타겟 분포 변화

**예시**: 승인율이 70%에서 50%로 급감

#### 3. Concept Drift (개념 드리프트)
**정의**: 입력과 타겟 간 관계의 변화
**원인**:
- 외부 환경 변화
- 규제/정책 변경
- 경쟁 구도 변화

**예시**: 신용점수 700점의 연체율이 과거와 달라짐

#### 4. Data Quality Drift (데이터 품질 드리프트)
**정의**: 데이터 품질 지표의 저하
**원인**:
- 업스트림 시스템 변경
- ETL 파이프라인 버그
- 데이터 소스 장애

**예시**: 결측치 비율이 5%에서 30%로 증가

---

## 드리프트 탐지 방법

### 1. Statistical Tests

#### Population Stability Index (PSI)
```python
def calculate_psi(expected, actual, bins=10):
    """
    PSI 계산
    - PSI < 0.1: 변화 없음 (No significant drift)
    - 0.1 ≤ PSI < 0.25: 경미한 변화 (Monitor)
    - PSI ≥ 0.25: 유의한 변화 (Action required)
    """
    pass
```

**임계값**:
- PSI < 0.1: 정상 (GREEN)
- 0.1 ≤ PSI < 0.25: 주의 (YELLOW)
- PSI ≥ 0.25: 경고 (RED)

#### Jensen-Shannon Divergence (JSD)
```python
def calculate_jsd(p, q):
    """
    JSD 계산 (0~1 범위)
    - JSD < 0.1: 변화 없음
    - 0.1 ≤ JSD < 0.3: 경미한 변화
    - JSD ≥ 0.3: 유의한 변화
    """
    pass
```

**임계값**:
- JSD < 0.1: 정상 (GREEN)
- 0.1 ≤ JSD < 0.3: 주의 (YELLOW)
- JSD ≥ 0.3: 경고 (RED)

#### Kolmogorov-Smirnov Test
```python
from scipy.stats import ks_2samp

def detect_drift_ks(reference, current):
    """
    KS 테스트
    - p-value > 0.05: 분포 동일 (정상)
    - p-value ≤ 0.05: 분포 다름 (드리프트)
    """
    statistic, p_value = ks_2samp(reference, current)
    return p_value < 0.05  # True면 드리프트
```

### 2. Performance-Based Detection

#### 모델 성능 메트릭 추적
```yaml
metrics:
  classification:
    - accuracy
    - precision
    - recall
    - f1_score
    - auc_roc
    - log_loss

  regression:
    - mse
    - rmse
    - mae
    - r2_score

  business:
    - approval_rate
    - denial_rate
    - average_decision_score
    - revenue_per_decision
```

**성능 저하 임계값**:
- Accuracy drop > 5%: WARNING
- Accuracy drop > 10%: CRITICAL
- AUC drop > 0.05: CRITICAL

---

## 모니터링

### 핵심 메트릭

#### 1. Feature Drift Metrics
```yaml
feature_metrics:
  - feature_psi: 각 피처별 PSI
  - feature_jsd: 각 피처별 JSD
  - missing_rate: 결측치 비율 변화
  - outlier_rate: 이상치 비율 변화
  - value_range: 값 범위 변화
  - categorical_distribution: 범주형 분포 변화
```

**모니터링 주기**:
- 고위험 피처: 1시간마다
- 일반 피처: 일일
- 저위험 피처: 주간

#### 2. Prediction Drift Metrics
```yaml
prediction_metrics:
  - prediction_mean: 예측값 평균
  - prediction_std: 예측값 표준편차
  - prediction_distribution: 예측값 분포
  - approval_rate: 승인율
  - denial_rate: 거부율
  - review_rate: 검토율
```

#### 3. Performance Metrics
```yaml
performance_metrics:
  - accuracy_rolling_7d: 최근 7일 정확도
  - precision_rolling_7d: 최근 7일 정밀도
  - recall_rolling_7d: 최근 7일 재현율
  - performance_delta: 훈련 시점 대비 성능 변화
```

#### 4. Business Metrics
```yaml
business_metrics:
  - revenue_per_decision: 결정당 수익
  - bad_rate: 불량률 (승인 후 연체/사기)
  - customer_complaints: 고객 불만 건수
  - manual_override_rate: 수동 오버라이드 비율
```

### 대시보드

#### 메인 드리프트 대시보드
- **URL**: `https://grafana.company.com/d/drift-main`
- **패널**:
  - Feature PSI 히트맵 (피처 × 시간)
  - 모델 성능 추이 (7일/30일)
  - 예측 분포 변화
  - 비즈니스 메트릭 추이
  - 드리프트 알림 이력

#### 피처별 상세 대시보드
- **URL**: `https://grafana.company.com/d/drift-features`
- **패널**:
  - 각 피처의 분포 비교 (참조 vs 현재)
  - PSI/JSD 시계열
  - 결측치/이상치 추이
  - 상관관계 변화

---

## 알림 규칙

### P0 (Critical) - 즉시 대응 필요

#### P0-DRIFT-001: 급격한 성능 저하
**조건**: `accuracy_drop > 10%` or `auc_drop > 0.1` for 2시간
**영향**: 모델 신뢰성 심각하게 손상
**알림 채널**: PagerDuty, Slack #ml-critical
**대응 SLA**: 30분

**조사 체크리스트**:
- [ ] 성능 저하 시작 시점 파악
- [ ] 동시기 데이터/시스템 변경 확인
- [ ] 피처 드리프트 확인
- [ ] 데이터 품질 문제 확인
- [ ] 최근 배포 영향 확인

**완화 조치**:
```bash
# 1. 즉시 모델 롤백 (이전 안정 버전)
dosctl model rollback --model {model_id}

# 2. 문제 기간 데이터 격리
dosctl data quarantine --from {start_time} --to {end_time}

# 3. 수동 검토 모드 활성화
dosctl decisions manual-review --all --until-investigation
```

#### P0-DRIFT-002: 데이터 품질 급격한 악화
**조건**: `missing_rate > 30%` or `data_quality_score < 0.5`
**영향**: 모델 입력 데이터 신뢰 불가
**알림 채널**: PagerDuty, Slack #data-quality
**대응 SLA**: 15분

**조사 체크리스트**:
- [ ] 업스트림 데이터 소스 상태 확인
- [ ] ETL 파이프라인 로그 확인
- [ ] 데이터 스키마 변경 여부 확인
- [ ] 데이터 계약 위반 사항 확인

**완화 조치**:
```bash
# 1. 영향받은 피처 비활성화
dosctl model disable-features --features {affected_features}

# 2. 대체 데이터 소스 활성화 (있는 경우)
dosctl data switch-source --to backup

# 3. 페일세이프 모드 (데이터 복구 시까지)
dosctl model failsafe --use-last-known-good-data
```

#### P0-DRIFT-003: 비정상적 예측 분포
**조건**: `approval_rate` 변화 > 30% for 1시간
**영향**: 비즈니스 영향 심각 (매출/리스크)
**알림 채널**: PagerDuty, Slack #ml-critical, #business
**대응 SLA**: 30분

**조사 체크리스트**:
- [ ] 입력 데이터 분포 확인
- [ ] 모델 로직 변경 여부 확인
- [ ] 정책 변경 여부 확인
- [ ] 외부 요인 (시장 변화 등) 확인

**완화 조치**:
```bash
# 1. 임시 정책 적용 (이전 승인율 유지)
dosctl policy apply --temporary --target-approval-rate {previous_rate}

# 2. 모델 롤백
dosctl model rollback

# 3. 비즈니스 팀에 즉시 알림
```

### P1 (High) - 2시간 내 대응

#### P1-DRIFT-001: 유의한 Feature Drift
**조건**: `feature_psi > 0.25` for 3개 이상 주요 피처, 지속 시간 > 6시간
**영향**: 모델 성능 저하 가능성
**알림 채널**: Slack #ml-alerts
**대응 SLA**: 2시간

**조사 체크리스트**:
- [ ] 드리프트 발생 피처 식별
- [ ] 드리프트 원인 분석 (계절성? 트렌드? 데이터 이슈?)
- [ ] 모델 성능에 미치는 영향 평가
- [ ] 다른 모델도 영향받는지 확인

**완화 조치**:
```bash
# 1. 드리프트 보고서 생성
dosctl drift report --features {drifted_features} --output report.pdf

# 2. 재훈련 필요 여부 평가
dosctl model evaluate-retrain --baseline {training_data} --current {recent_data}

# 3. 모니터링 강화
dosctl monitor increase-frequency --features {drifted_features} --to 15min
```

#### P1-DRIFT-002: 개념 드리프트 의심
**조건**: `feature_drift low` but `performance_degradation > 5%`
**영향**: 모델 재훈련 필요
**알림 채널**: Slack #ml-alerts
**대응 SLA**: 2시간

**조사 체크리스트**:
- [ ] 입력-출력 관계 변화 확인
- [ ] 최근 외부 환경 변화 조사
- [ ] 타겟 레이블 분포 확인 (가능한 경우)
- [ ] 비즈니스 팀에 인사이트 요청

**완화 조치**:
```bash
# 1. 긴급 재훈련 일정 수립
# (개념 드리프트는 재훈련 외 해결 방법 제한적)

# 2. 임시 규칙 추가로 성능 보완
dosctl rules add --temporary --to-compensate-drift

# 3. Shadow 모델로 재훈련 모델 테스트 준비
dosctl model shadow-deploy --new-model {retrained_model}
```

### P2 (Medium) - 8시간 내 대응

#### P2-DRIFT-001: 경미한 Feature Drift
**조건**: `0.1 ≤ feature_psi < 0.25`, 지속 시간 > 24시간
**영향**: 모니터링 필요, 즉각 조치 불필요
**알림 채널**: Slack #ml-monitoring
**대응 SLA**: 8시간

**조사 및 조치**:
- [ ] 드리프트 트렌드 분석
- [ ] 계절성/주기성 여부 판단
- [ ] 다음 재훈련 일정에 반영
- [ ] 문서화

#### P2-DRIFT-002: 비즈니스 메트릭 변화
**조건**: `revenue_per_decision` 변화 > 10%
**영향**: 비즈니스 영향 평가 필요
**알림 채널**: Slack #business-metrics
**대응 SLA**: 8시간

**조사 및 조치**:
- [ ] 비즈니스 팀과 협의
- [ ] 모델 vs 시장 요인 구분
- [ ] 전략 조정 필요성 평가

---

## 사고 대응 절차

### 드리프트 조사 체크리스트

#### 1단계: 문제 확인 및 범위 파악
- [ ] 드리프트 유형 식별 (Feature/Prediction/Concept/Data Quality)
- [ ] 영향받은 모델/파이프라인 목록 작성
- [ ] 시작 시점 파악
- [ ] 심각도 평가 (P0/P1/P2)

#### 2단계: 근본 원인 분석
- [ ] **데이터 소스 확인**
  - 업스트림 시스템 변경
  - 데이터 수집 로직 변경
  - 스키마 변경
- [ ] **파이프라인 확인**
  - ETL 로그 확인
  - 데이터 변환 로직 확인
  - 피처 엔지니어링 변경
- [ ] **모델 확인**
  - 최근 모델 배포
  - 하이퍼파라미터 변경
  - 훈련 데이터 변경
- [ ] **외부 요인 확인**
  - 시장/경제 상황 변화
  - 계절적 패턴
  - 규제/정책 변경
  - 경쟁 상황 변화

#### 3단계: 영향 평가
- [ ] 모델 성능 영향 정량화
- [ ] 비즈니스 영향 추정 (매출/리스크)
- [ ] 고객 영향 평가
- [ ] 규제/컴플라이언스 영향

#### 4단계: 완화 조치
- [ ] 즉시 조치 (롤백/수동 검토 등)
- [ ] 단기 조치 (규칙 조정/피처 비활성화)
- [ ] 장기 조치 (재훈련/파이프라인 수정)

#### 5단계: 검증 및 모니터링
- [ ] 조치 효과 확인
- [ ] 메트릭 정상화 확인
- [ ] 모니터링 강화
- [ ] 재발 방지 대책 수립

#### 6단계: 사후 분석
- [ ] Post-mortem 작성
- [ ] 타임라인 정리
- [ ] 교훈 및 개선사항 도출
- [ ] 알림 규칙 조정 (필요시)

---

## 대응 시나리오

### 시나리오 1: 급격한 Feature Drift (예: COVID-19)

**상황**: 팬데믹으로 인해 대출 신청 패턴이 급변

**증상**:
- 소득 분포 PSI > 0.4
- 고용 상태 분포 PSI > 0.5
- 승인율 70% → 40%

**대응**:
```bash
# 1. 현황 파악
dosctl drift analyze --window 7d

# 2. 긴급 비즈니스 리뷰 회의
# → 새로운 리스크 정책 합의

# 3. 임시 규칙 추가
dosctl rules add \
  --name covid_income_adjustment \
  --condition "employment_status == 'furloughed'" \
  --action "increase_scrutiny"

# 4. 재훈련 데이터 수집 시작
dosctl data collect --tag covid_period --for-retraining

# 5. 빠른 재훈련 (2주 이내)
dosctl model retrain --expedited --with-recent-data
```

### 시나리오 2: 데이터 파이프라인 버그

**상황**: ETL 버그로 일부 피처 값이 잘못 계산됨

**증상**:
- debt_to_income_ratio 값이 모두 0
- missing_rate 30% 증가
- 승인율 70% → 90% (잘못된 승인)

**대응**:
```bash
# 1. 즉시 모델 중단
dosctl model pause --model credit_risk_v2

# 2. 영향 범위 파악
dosctl decisions list --model credit_risk_v2 --since {bug_start_time}

# 3. 잘못된 결정 재평가
dosctl decisions reevaluate --decision-ids {affected_ids}

# 4. 파이프라인 수정 및 검증
# (데이터 엔지니어링 팀)

# 5. 데이터 재처리
dosctl data reprocess --from {bug_start_time} --fix-pipeline

# 6. 모델 재개 (검증 후)
dosctl model resume --model credit_risk_v2 --after-verification
```

### 시나리오 3: 계절적 드리프트

**상황**: 매년 12월 대출 신청 패턴 변화

**증상**:
- 신청액 분포 PSI = 0.15 (주의)
- 성능 저하 없음 (예상된 패턴)

**대응**:
```bash
# 1. 계절성 확인
dosctl drift seasonal-analysis --feature loan_amount --years 3

# 2. 계절별 모델 고려 (장기)
# 또는 계절 피처 추가

# 3. 모니터링 기준 조정
dosctl monitor set-baseline --seasonal --feature loan_amount

# 4. 문서화
# "12월 대출액 증가는 정상 (연말 소비 증가)"
```

---

## 재훈련 의사결정 프레임워크

### 재훈련이 필요한 경우

#### 즉시 재훈련 (긴급)
- Accuracy drop > 10%
- AUC drop > 0.1
- Critical business metric 악화 > 20%
- 규제 위반 가능성

#### 계획된 재훈련 (1-2주 내)
- Accuracy drop 5-10%
- Feature PSI > 0.25 (3개 이상 주요 피처)
- Concept drift 확인
- 비즈니스 전략 변경

#### 정기 재훈련 (월간/분기)
- 경미한 드리프트 누적
- 새로운 데이터 충분히 수집됨
- 모델 개선 기회 (새 피처 등)

### 재훈련 프로세스

#### 1. 데이터 준비
```bash
# 1. 재훈련 데이터셋 생성
dosctl data prepare-retrain \
  --train-window 12M \
  --val-window 2M \
  --test-window 1M \
  --exclude-drifted-data {optional}

# 2. 데이터 품질 검증
dosctl data validate --dataset retrain_2025q4

# 3. 피처 엔지니어링 업데이트 (필요시)
```

#### 2. 모델 훈련
```bash
# 1. 훈련 실행
dosctl model train \
  --config configs/credit_risk_v3.yaml \
  --data retrain_2025q4 \
  --experiment-name retrain_drift_response

# 2. 성능 평가
dosctl model evaluate \
  --model credit_risk_v3 \
  --test-set retrain_2025q4_test

# 3. 드리프트 테스트 (재훈련 효과 확인)
dosctl drift test \
  --old-model credit_risk_v2 \
  --new-model credit_risk_v3 \
  --on-data recent_production_data
```

#### 3. 배포
```bash
# 1. Shadow 배포 (1주일)
dosctl model deploy \
  --model credit_risk_v3 \
  --mode shadow \
  --duration 7d

# 2. Shadow 결과 분석
dosctl model shadow-report --model credit_risk_v3

# 3. Canary 배포
dosctl model deploy \
  --model credit_risk_v3 \
  --canary \
  --traffic-schedule "1%:2h,5%:6h,25%:12h,50%:24h,100%"

# 4. 전체 배포
dosctl model promote --model credit_risk_v3
```

---

## 정기 유지보수

### 일일 점검
- [ ] 드리프트 대시보드 확인
- [ ] 알림 로그 검토
- [ ] 성능 메트릭 확인
- [ ] 비정상 패턴 조사

### 주간 점검
- [ ] 피처별 드리프트 리포트 생성
- [ ] 성능 트렌드 분석
- [ ] 비즈니스 메트릭 리뷰
- [ ] 재훈련 필요성 평가

### 월간 점검
- [ ] 포괄적 드리프트 분석
- [ ] 모델 성능 대비 훈련 시점
- [ ] 알림 규칙 조정
- [ ] 재훈련 계획 수립

### 분기 점검
- [ ] 전체 모델 포트폴리오 리뷰
- [ ] 드리프트 대응 프로세스 개선
- [ ] 모니터링 인프라 최적화
- [ ] 교육 및 지식 공유

---

## 도구 및 명령어

### dosctl drift 명령어
```bash
# 드리프트 분석
dosctl drift analyze --model {model_id} --window {time_window}
dosctl drift report --features {features} --output {file}

# 통계 테스트
dosctl drift test-psi --feature {feature} --baseline {data} --current {data}
dosctl drift test-jsd --feature {feature} --baseline {data} --current {data}

# 모니터링 설정
dosctl drift monitor --features {features} --frequency {interval}
dosctl drift set-threshold --feature {feature} --psi {value}

# 알림 관리
dosctl drift alerts list
dosctl drift alerts acknowledge --alert-id {id}

# 시각화
dosctl drift visualize --feature {feature} --window 30d
dosctl drift dashboard --model {model_id}
```

### 프로그래밍 인터페이스
```python
from decisionos.monitoring import DriftDetector

# 드리프트 감지
detector = DriftDetector(model='credit_risk_v2')

# PSI 계산
psi_results = detector.calculate_psi(
    baseline_data=train_df,
    current_data=prod_df,
    features=['income', 'age', 'credit_score']
)

# 알림 설정
detector.add_alert(
    metric='feature_psi',
    feature='credit_score',
    threshold=0.25,
    action='notify_slack'
)

# 지속적 모니터링
detector.start_monitoring(interval='1h')
```

---

## 메트릭 및 KPI

### 드리프트 모니터링 KPI
```yaml
kpis:
  detection:
    - mean_time_to_detect: 드리프트 발생부터 탐지까지 시간 (목표: < 6시간)
    - false_alert_rate: 거짓 알림 비율 (목표: < 5%)
    - drift_coverage: 모니터링 피처 비율 (목표: 100% of critical features)

  response:
    - mean_time_to_respond: 탐지부터 조치까지 시간 (목표: < 2시간 for P1)
    - resolution_rate: 해결율 (목표: 100%)
    - retraining_frequency: 재훈련 주기 (목표: 분기 1회 이상)

  impact:
    - performance_recovery_time: 성능 회복 시간 (목표: < 24시간)
    - drift-related_incidents: 드리프트 관련 사고 건수 (목표: < 2/quarter)
```

---

## 연락처

- **ML Operations Team**: #ml-ops Slack 채널
- **Data Engineering**: #data-eng Slack 채널
- **ML Lead**: ml-lead@company.com
- **On-call ML Engineer**: PagerDuty 자동 호출

---

## 관련 문서
- [Guardrails Runbook](runbook_guardrails.md)
- [Model Retraining Guide](../docs/model_retraining.md)
- [Model Card Template](../docs/model_card_template.yaml)
- [Monitoring Architecture](../docs/monitoring_architecture.md)
