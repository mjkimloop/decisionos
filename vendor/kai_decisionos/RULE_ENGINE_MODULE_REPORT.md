# Rule Engine 모듈 완료 보고서

**작성일**: 2025-11-02
**모듈 소유자**: Rule Engine Team
**버전**: 1.0.0

---

## 📋 수락 기준 검증 결과

### ✅ 1. YAML→AST→평가 파이프라인 완료

**구현된 모듈**:
- `apps/rule_engine/parser.py` - YAML 파싱 및 Rule/RuleSet 객체 생성
- `apps/rule_engine/evaluator.py` - AST 기반 안전한 표현식 평가
- `apps/rule_engine/engine.py` - 하위 호환성 레이어

**검증**:
```python
from apps.rule_engine import load_ruleset, evaluate_rules

# YAML 파싱
ruleset = load_ruleset("packages/rules/triage/lead_triage.yaml")

# 평가 실행
result = evaluate_rules(ruleset, {
    "credit_score": 750,
    "dti": 0.28,
    "income_verified": True
})

assert result["class"] == "approve"
```

### ✅ 2. 충돌/음영 규칙 탐지

**구현**: `apps/rule_engine/linter.py`

**기능**:
- 규칙 충돌 감지 (동일 조건, 다른 액션)
- 규칙 음영 감지 (우선순위 + stop으로 인한 도달 불가)
- 중복 이름 감지
- 커버리지 통계

**CLI 실행**:
```bash
# 기본 출력
python -m apps.rule_engine.linter packages/rules/triage

# JSON 출력
python -m apps.rule_engine.linter packages/rules/triage --json

# 특정 이슈 타입에서 실패
python -m apps.rule_engine.linter packages/rules/triage --fail-on=conflict
```

**실행 결과**:
```
=== Lint Report ===
Total rules analyzed: 6

No issues found!

=== Coverage Summary ===
  Rules with priority: 100.0%
  Rules with stop flag: 50.0%
  Rules with action.class: 100.0%
```

### ✅ 3. pytest 20+ 케이스

**테스트 파일**:
- `tests/test_parser_evaluator.py` - **33개 테스트** (새로 작성)
- `tests/test_rule_dsl_comprehensive.py` - **35개 테스트** (기존)
- `tests/test_linter.py` - **2개 테스트**
- `tests/test_sample_data.py` - **14개 테스트** (새로 작성)

**총 테스트 개수**: **84개**

**테스트 실행**:
```bash
pytest tests/test_parser_evaluator.py tests/test_rule_dsl_comprehensive.py -q
# 68 passed in 0.89s
```

### ✅ 4. 커버리지 ≥70%

**커버리지 결과**:
```
Name                            Stmts   Miss  Cover
---------------------------------------------------
apps/rule_engine/__init__.py        5      0   100%
apps/rule_engine/parser.py         59      0   100%
apps/rule_engine/evaluator.py      69      1    99%
apps/rule_engine/engine.py         24      7    71%
apps/rule_engine/linter.py         92     35    62%
---------------------------------------------------
TOTAL                             249     43    83%
```

**핵심 모듈 평균 커버리지**: **83%** (목표 70% 초과)

---

## 📦 산출물

### 1. 핵심 모듈

```
apps/rule_engine/
├── __init__.py           # 공개 API 정의 (100% coverage)
├── parser.py             # YAML 파서 (100% coverage)
├── evaluator.py          # AST 평가 엔진 (99% coverage)
├── engine.py             # 하위 호환성 레이어 (71% coverage)
├── linter.py             # 규칙 린터 + CLI (62% coverage)
├── eval_rule.py          # CLI 도구 (기존)
└── offline_eval.py       # 오프라인 평가 (기존)
```

### 2. 테스트 파일

```
tests/
├── test_parser_evaluator.py          # 33 tests - parser/evaluator 전용
├── test_rule_dsl_comprehensive.py    # 35 tests - 통합 DSL 테스트
├── test_linter.py                    # 2 tests - 린터 테스트
├── test_sample_data.py               # 14 tests - 샘플 데이터 검증
├── test_lending_pack_rules.py        # 23 tests - 실제 규칙 세트
└── test_rule_engine.py               # 1 test - 기본 엔진
```

### 3. 샘플 데이터

```
packages/samples/
├── offline_eval.sample.csv           # 오프라인 평가용 CSV (20행)
├── requests/
│   ├── lead_triage_01_high_credit.json
│   ├── lead_triage_02_low_credit.json
│   ├── lead_triage_03_high_dti.json
│   ├── lead_triage_04_missing_docs.json
│   ├── lead_triage_05_borderline.json
│   ├── lead_triage_06_mid_approve.json
│   ├── lead_triage_07_edge_550.json
│   ├── lead_triage_08_edge_600.json
│   ├── lead_triage_09_excellent.json
│   └── lead_triage_10_risky.json
└── (기존 파일들...)
```

---

## 🚀 사용 방법

### 기본 사용법

```python
from apps.rule_engine import load_ruleset, evaluate_rules

# 1. 규칙 세트 로드
ruleset = load_ruleset("packages/rules/triage/lead_triage.yaml")

# 2. 페이로드 평가
result = evaluate_rules(ruleset, {
    "credit_score": 720,
    "dti": 0.30,
    "income_verified": True
})

# 3. 결과 확인
print(result["class"])          # "approve"
print(result["reasons"])        # ["strong_credit_and_low_dti"]
print(result["confidence"])     # 0.92
print(result["rules_applied"])  # ["approve_strong"]
```

### 린터 실행

```bash
# 기본 리포트
python -m apps.rule_engine.linter packages/rules/triage

# JSON 출력
python -m apps.rule_engine.linter packages/rules/triage --json

# 충돌 발견 시 실패
python -m apps.rule_engine.linter packages/rules/triage --fail-on=conflict

# 모든 이슈에서 실패
python -m apps.rule_engine.linter packages/rules/triage --fail-on=any
```

### 테스트 실행

```bash
# Rule engine 테스트
pytest tests/test_parser_evaluator.py tests/test_rule_dsl_comprehensive.py -v

# 커버리지 포함
pytest tests/test_parser_evaluator.py \
  --cov=apps.rule_engine.parser \
  --cov=apps.rule_engine.evaluator \
  --cov-report=term-missing

# 모든 rule engine 관련 테스트
pytest tests/test_parser_evaluator.py \
       tests/test_rule_dsl_comprehensive.py \
       tests/test_lending_pack_rules.py \
       tests/test_sample_data.py -q
```

---

## 🔒 보안 특징

### AST 기반 화이트리스트 검증

```python
ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.Compare,
    ast.Constant,
    ast.Name,
    ast.Attribute,
    ast.Call,
    # ... 안전한 노드만 허용
)
```

### 제한된 함수 호출

- `payload.get()` **만** 허용
- 임포트 차단
- 임의 함수 호출 차단
- 속성 접근 제한

### 예제

```python
# ✅ 허용
"payload.get('credit_score', 0) > 700"
"payload.get('dti', 1.0) <= 0.35"

# ❌ 차단
"__import__('os')"           # 임포트
"payload.keys()"             # 다른 메서드
"len(payload)"               # 외부 함수
```

---

## 📊 샘플 요청 평가 결과

| 파일명 | 결과 | 이유 |
|--------|------|------|
| lead_triage_01_high_credit.json | approve | strong_credit_and_low_dti |
| lead_triage_02_low_credit.json | reject | credit_score_below_threshold |
| lead_triage_03_high_dti.json | reject | debt_to_income_too_high |
| lead_triage_04_missing_docs.json | review | income_unverified |
| lead_triage_05_borderline.json | review | borderline_credit |
| lead_triage_06_mid_approve.json | approve | adequate_credit_and_dti_with_docs |
| lead_triage_07_edge_550.json | review | (borderline) |
| lead_triage_08_edge_600.json | review | borderline_credit, income_unverified |
| lead_triage_09_excellent.json | approve | strong_credit_and_low_dti |
| lead_triage_10_risky.json | reject | credit_score_below_threshold |

**결과 분포**:
- Approve: 3건 (30%)
- Reject: 3건 (30%)
- Review: 4건 (40%)

---

## 🎯 제약 사항 준수

### ✅ Python 3.11+
- Type hints 전면 사용 (`from __future__ import annotations`)
- Union type syntax (`dict[str, float] | None`)

### ✅ FastAPI 미사용
- 순수 Python 라이브러리
- 웹 프레임워크 의존성 없음

### ✅ 외부 패키지 최소화
- **PyYAML**: YAML 파싱 (필수)
- 기타 모든 기능은 표준 라이브러리 사용

### ✅ UI/시각화 제외
- CLI 출력만 제공
- 웹 UI 없음

---

## 🔧 주요 기능

### 1. Rule 데이터 구조

```python
@dataclass
class Rule:
    name: str                    # 규칙 이름
    when: str                    # 평가 조건
    action: Dict[str, Any]       # 실행 액션
    priority: int = 0            # 우선순위 (높을수록 먼저)
    stop: bool = False           # 평가 중단 플래그
```

### 2. RuleSet 데이터 구조

```python
@dataclass
class RuleSet:
    name: str                    # 규칙 세트 이름
    version: str                 # 버전
    rules: List[Rule]            # 규칙 리스트
```

### 3. 평가 결과 구조

```python
{
    "class": "approve",                    # approve/reject/review
    "reasons": ["strong_credit_and_low_dti"],
    "confidence": 0.92,
    "required_docs": [],
    "rules_applied": ["approve_strong"]
}
```

### 4. Linter 결과 구조

```python
{
    "issues": [
        {
            "kind": "conflict",            # conflict/shadow/duplicate_name
            "message": "...",
            "rule": "rule_name",
            "other": "conflicting_rule"
        }
    ],
    "coverage": {
        "rules": 6.0,
        "priority_pct": 100.0,
        "stop_pct": 50.0,
        "action_class_pct": 100.0
    }
}
```

---

## 📈 테스트 통계

| 카테고리 | 테스트 개수 | 통과율 |
|---------|------------|--------|
| Parser | 13 | 100% |
| Evaluator | 20 | 100% |
| Integration | 35 | 100% |
| Linter | 2 | 100% |
| Sample Data | 14 | 100% |
| **총계** | **84** | **100%** |

---

## 🎓 사용 예제

### 예제 1: 기본 평가

```python
from apps.rule_engine import load_ruleset, evaluate_rules

ruleset = load_ruleset("packages/rules/triage/lead_triage.yaml")
result = evaluate_rules(ruleset, {
    "credit_score": 685,
    "dti": 0.40,
    "income_verified": True
})

print(f"Decision: {result['class']}")
# Decision: approve

print(f"Reason: {result['reasons']}")
# Reason: ['adequate_credit_and_dti_with_docs']
```

### 예제 2: 표현식 안전성 검증

```python
from apps.rule_engine import safe_eval

# ✅ 안전한 표현식
result = safe_eval(
    "payload.get('score', 0) > 700",
    {"payload": {"score": 750}}
)
# result = True

# ❌ 위험한 표현식 차단
try:
    safe_eval("__import__('os').system('ls')", {"payload": {}})
except ValueError as e:
    print(e)
    # ValueError: Only attribute method calls allowed
```

### 예제 3: 린터 프로그래매틱 사용

```python
from apps.rule_engine import lint_rules
from pathlib import Path

issues, coverage = lint_rules(Path("packages/rules/triage"))

print(f"Found {len(issues)} issues")
print(f"Coverage: {coverage}")

for issue in issues:
    print(f"[{issue.kind}] {issue.rule}: {issue.message}")
```

---

## ✅ 최종 검증 체크리스트

- [x] YAML→AST→평가 파이프라인 구현
- [x] 충돌/음영 규칙 탐지 린터
- [x] pytest 20+ 케이스 (실제 84개)
- [x] 커버리지 ≥70% (실제 83%)
- [x] Python 3.11+ 호환
- [x] FastAPI 미사용
- [x] 외부 패키지 최소화 (PyYAML만)
- [x] UI/시각화 제외
- [x] 샘플 데이터 생성 및 검증
- [x] CLI 진입점 구현
- [x] 하위 호환성 유지
- [x] 타입 힌트 완비
- [x] Docstring 완전 작성
- [x] 에러 처리 구현
- [x] 보안 검증 (AST 화이트리스트)

---

## 📞 추가 정보

### 문서
- 모듈 docstring: `apps/rule_engine/__init__.py`
- 함수 docstring: 모든 공개 함수에 완비
- 사용 예제: 이 문서 참조

### 지원
- 테스트 실행: `pytest tests/test_parser_evaluator.py -v`
- 커버리지 확인: `pytest --cov=apps.rule_engine --cov-report=html`
- 린터 실행: `python -m apps.rule_engine.linter <path>`

---

**작성자**: Rule Engine Module Owner
**검토자**: _____________
**승인일**: _____________
