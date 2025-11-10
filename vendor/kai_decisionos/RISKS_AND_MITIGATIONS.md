# 위험 및 대응 전략

**프로젝트**: DecisionOS
**버전**: Sprint 1 ~ Sprint 2
**최종 업데이트**: 2025-11-02

---

## 🎯 식별된 위험 및 대응책

### 1. 📚 규칙 부채 (Rule Debt)

**위험 레벨**: 🔴 HIGH

#### 문제
- 규칙이 누적되면서 충돌/음영 발생 가능성 증가
- 수동 검토만으로는 규칙 간 상호작용 파악 어려움
- 규칙 변경 시 예상치 못한 부작용 발생 가능

#### 영향
- 비즈니스 로직 불일치
- 의도하지 않은 거부/승인 결정
- 디버깅 시간 증가

#### 대응책

**1단계: 자동화된 린트 검증 (✅ 구현 완료)**
```yaml
# .github/workflows/lint-rules.yml
name: Lint Rules

on:
  pull_request:
    paths:
      - 'packages/rules/**/*.yaml'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run linter
        run: |
          python -m apps.rule_engine.linter packages/rules/triage --fail-on=conflict
      - name: Check for shadows
        run: |
          python -m apps.rule_engine.linter packages/rules/triage --json > lint_report.json
          python -c "
          import json
          with open('lint_report.json') as f:
              data = json.load(f)
          shadows = [i for i in data['issues'] if i['kind'] == 'shadow']
          if shadows:
              print(f'WARNING: {len(shadows)} shadowed rules found')
              for s in shadows:
                  print(f\"  - {s['rule']}: {s['message']}\")
          "
```

**2단계: 시뮬레이션 강제화 (✅ 구현 완료)**
```yaml
# .github/workflows/simulate-rules.yml
name: Simulate Rules

on:
  pull_request:
    paths:
      - 'packages/rules/**/*.yaml'

jobs:
  simulate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run offline evaluation
        run: |
          python cli/dosctl/main.py simulate lead_triage \
            --csv packages/samples/offline_eval.sample.csv \
            --label label \
            --json-out simulation_result.json
      - name: Check metrics
        run: |
          python -c "
          import json
          with open('simulation_result.json') as f:
              metrics = json.load(f)['metrics']

          # 성능 하락 검증
          assert metrics['reject_precision'] >= 0.8, 'Precision too low'
          assert metrics['review_rate'] <= 0.6, 'Review rate too high'
          print('✅ Metrics within acceptable range')
          "
      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: simulation-report
          path: simulation_result.json
```

**3단계: PR 체크리스트 템플릿**
```markdown
## Rule Change Checklist

- [ ] Linter passed with 0 conflicts
- [ ] Simulation shows acceptable metrics
- [ ] No new shadowed rules (or justified)
- [ ] Reviewed rule priority ordering
- [ ] Updated rule documentation
```

#### 모니터링
- PR마다 자동 린트/시뮬 실행
- 주간 규칙 부채 리포트 생성
- 분기별 규칙 리팩토링 세션

---

### 2. 💰 비용 폭주 (Cost Explosion)

**위험 레벨**: 🟡 MEDIUM

#### 문제
- AI 모델 호출 시 비용 예측 어려움
- 트래픽 급증 시 비용 폭발 가능성
- 고가 모델(GPT-4) 무분별 사용

#### 영향
- 예산 초과
- 서비스 중단 필요
- ROI 악화

#### 대응책

**1단계: Switchboard 비용 상한 (✅ 구현 완료)**
```python
# apps/switchboard/switch.py
async def route_request(
    self,
    prompt: str,
    cost_budget: float = 0.5,  # 기본 $0.50
    timeout: float = 3.0
) -> Dict[str, Any]:

    # 비용 기반 폴백
    estimated_cost = primary_adapter.estimate_cost(prompt, model)
    if estimated_cost > cost_budget:
        adapter_to_use = self.fallback_adapter  # 저렴한 로컬 모델
        reason = f"cost_exceeded (est: {estimated_cost:.4f} > budget: {cost_budget})"
    else:
        adapter_to_use = primary_adapter
```

**2단계: 캐싱 전략**
```python
# 동일 페이로드 캐싱 (Sprint 2 구현 예정)
from functools import lru_cache
import hashlib

def get_cache_key(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()

@lru_cache(maxsize=1000)
def cached_decide(payload_hash: str, payload: dict):
    return decide("lead_triage", payload["org_id"], payload)
```

**3단계: 비용 모니터링**
```python
# apps/switchboard/cost_tracker.py (Sprint 2 구현 예정)
class CostTracker:
    def __init__(self):
        self.daily_budget = 100.0  # $100/day
        self.current_spend = 0.0
        self.call_count = 0

    def track_call(self, model: str, tokens: int, cost: float):
        self.current_spend += cost
        self.call_count += 1

        if self.current_spend > self.daily_budget:
            raise BudgetExceededError(
                f"Daily budget exceeded: ${self.current_spend:.2f}"
            )
```

**4단계: 로컬 폴백**
```python
# 비용 초과 시 rule-only 모드
route_meta = choose_route(contract, budgets)
chosen_model = route_meta.get("chosen_model")

if chosen_model and chosen_model != "rules-only":
    try:
        model_result = invoke_model(route_meta, payload)
    except (BudgetExceededError, TimeoutError):
        # 폴백: 규칙만 사용
        route_meta["degraded"] = True
        model_result = None
```

#### 모니터링
- 일일 비용 대시보드
- 모델별 호출 빈도/비용 추적
- 예산 80% 도달 시 알림

---

### 3. 📊 데이터 미존재 (Missing Data)

**위험 레벨**: 🟡 MEDIUM

#### 문제
- 초기 개발 시 실제 production 데이터 없음
- 샘플 데이터로만 개발 시 엣지 케이스 미발견
- 실제 배포 후 예상치 못한 데이터 패턴 발생

#### 영향
- 규칙 정확도 저하
- 예상치 못한 에러
- 고객 불만

#### 대응책

**1단계: 대표성 있는 샘플 CSV 생성 (✅ 완료)**
```csv
# packages/samples/offline_eval.sample.csv
# - 20행 다양한 시나리오
# - employment_type, income_monthly, property_type 등
# - label 포함 (1=승인, 0=거부)
```

**2단계: 합성 데이터 생성기 (Sprint 2 구현 예정)**
```python
# tools/generate_synthetic_data.py
import random
from faker import Faker

fake = Faker('ko_KR')

def generate_lead(label: int) -> dict:
    """레이블에 맞는 합성 리드 생성"""
    if label == 1:  # 승인될 프로필
        credit_score = random.randint(680, 850)
        dti = random.uniform(0.2, 0.45)
    else:  # 거부될 프로필
        credit_score = random.randint(300, 600)
        dti = random.uniform(0.5, 0.8)

    return {
        "org_id": fake.company(),
        "credit_score": credit_score,
        "dti": round(dti, 2),
        "income_verified": random.choice([True, False]),
        "converted": label
    }

# 1000행 생성
with open("synthetic_leads.csv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=[...])
    writer.writeheader()
    for i in range(1000):
        writer.writerow(generate_lead(label=random.choice([0, 1])))
```

**3단계: 실데이터 후치환 프로세스**
```markdown
## 실데이터 통합 체크리스트

1. [ ] 데이터 스키마 검증
   - Lead 모델과 호환성 확인
   - 필수 필드 존재 확인

2. [ ] 데이터 품질 체크
   - 결측치 비율 < 5%
   - 이상치 탐지 및 처리

3. [ ] 비교 평가
   - 샘플 데이터 vs 실데이터 시뮬레이션 결과 비교
   - 메트릭스 변화 분석

4. [ ] 점진적 롤아웃
   - 10% 트래픽으로 시작
   - 메트릭스 모니터링
   - 단계적 확대

5. [ ] 규칙 재튜닝
   - 실데이터 기반 임계값 조정
   - A/B 테스트 수행
```

**4단계: 데이터 품질 모니터링**
```python
# apps/monitor/data_quality.py (Sprint 2 구현 예정)
def validate_incoming_payload(payload: dict) -> List[str]:
    """페이로드 품질 검증"""
    issues = []

    # 필수 필드 체크
    if "credit_score" not in payload:
        issues.append("Missing credit_score")

    # 범위 체크
    if payload.get("credit_score", 0) < 300:
        issues.append("credit_score too low")

    # 타입 체크
    if not isinstance(payload.get("dti"), (int, float)):
        issues.append("dti must be numeric")

    return issues
```

#### 모니터링
- 일일 데이터 품질 리포트
- 이상 패턴 자동 감지
- 주간 규칙 성능 리뷰

---

## 📋 위험 요약 매트릭스

| 위험 | 레벨 | 확률 | 영향 | 대응 상태 | 담당자 |
|-----|------|------|------|----------|--------|
| 규칙 부채 | 🔴 HIGH | 높음 | 높음 | ✅ 완료 | Dev Team |
| 비용 폭주 | 🟡 MEDIUM | 중간 | 높음 | ✅ 완료 | Infra Team |
| 데이터 미존재 | 🟡 MEDIUM | 높음 | 중간 | ✅ 완료 | Data Team |

---

## 🔄 지속적 개선

### Sprint 2 개선 계획

1. **규칙 부채**
   - [ ] GitHub Actions CI/CD 통합
   - [ ] 규칙 버전 관리 시스템
   - [ ] 자동 롤백 메커니즘

2. **비용 폭주**
   - [ ] Redis 캐싱 레이어 추가
   - [ ] 비용 대시보드 구축
   - [ ] 동적 budget 조정 로직

3. **데이터 미존재**
   - [ ] 실데이터 파이프라인 구축
   - [ ] 데이터 품질 자동 모니터링
   - [ ] 드리프트 감지 시스템

---

**리뷰 주기**: 2주마다
**다음 리뷰**: Sprint 2 Week 1
**책임자**: Tech Lead
