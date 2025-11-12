# GitHub Actions CI/CD

DecisionOS는 3단계 게이트 구조의 CI/CD 파이프라인을 제공합니다.

## 워크플로우

### 1. Smoke Tests (`smoke-tests.yml`)
- **트리거**: Push/PR to main, develop
- **목적**: 빠른 스모크 테스트 (외부 의존성 없음)
- **실행 시간**: ~30초
- **테스트**: gate_q (8 tests)
  - Risk Governor 기본 동작
  - Burn Rate 레벨 구분
  - Shadow Sampler 히스테리시스
  - Alerts Dispatcher dry-run
  - Jobs 통합 테스트
  - Metrics no-op

### 2. Full CI (`decisionos-ci.yml`)
- **트리거**: Push/PR to main, workflow_dispatch
- **목적**: 전체 게이트 검증
- **실행 시간**: ~5분
- **단계**:
  1. **Pre-Gate**: Clock guard, Evidence index, gate_t tests
  2. **Gate**: SLO 저지, Quorum 검증
  3. **Post-Gate**: PR annotation, Labels sync, API smoke

## Pre-Gate 단계

Clock/Evidence/Unit 검증:
- Clock skew 확인 (±2초)
- Evidence 인덱싱
- gate_t 타겟 테스트 (non-fatal)

```yaml
- name: Clock Guard
  run: python -m jobs.clock_guard --max-skew-sec 2 --out var/log/clock_guard.json
```

## Gate 단계

SLO 저지 + Quorum:

### Evidence 빌드
```python
# reqlog → perf.json
python -m apps.cli.dosctl.witness_perf --csv var/log/reqlog.csv --out var/evidence/perf.json

# judgelog → perf_judge.json
python -m apps.cli.dosctl.witness_judge_perf --csv var/log/judgelog.csv --out var/evidence/perf_judge.json

# Evidence 병합 및 서명
python - <<'PY'
from apps.obs.evidence.snapshot import Evidence
from apps.obs.evidence.ops import recompute_signature
# ... merge perf/perf_judge/canary
ev = Evidence.from_dict(base)
ev_json = ev.to_json()
(p / "latest.json").write_text(ev_json)
recompute_signature(p / "latest.json")
PY
```

### SLO 저지
```bash
# Infra SLO (Judge 성능)
python -m apps.cli.dosctl.slo_judge --slo configs/slo/slo-judge-infra.json --evidence var/evidence/latest.json

# Canary SLO (엄격 버전)
python -m apps.cli.dosctl.slo_judge --slo configs/slo/slo-billing-strict-v2.json --evidence var/evidence/latest.json
```

### Quorum
```bash
# 2/3 쿼럼 (로컬 + HTTP judges)
python -m apps.cli.dosctl.judge_quorum \
  --slo configs/slo/slo-billing-strict-v2.json \
  --evidence var/evidence/latest.json \
  --providers configs/judge/providers.yaml \
  --quorum 2/3 \
  --attach-evidence
```

## Post-Gate 단계

PR Annotation + Labels + API Smoke:

### PR 코멘트
```bash
DIFF_LINK="https://github.com/${{ github.repository }}/compare/base...head"
python -m scripts.annotate_release_gate \
  --evidence gate-artifacts/var/evidence/latest.json \
  --artifacts-url "https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}" \
  --diff-link "$DIFF_LINK" \
  --reason-summary top-3 \
  --label-catalog configs/labels/label_catalog_v2.json
```

### Labels 동기화
```bash
python -m scripts.ensure_labels \
  --catalog configs/labels/label_catalog_v2.json \
  --repo ${{ github.repository }}
```

### Ops API Smoke
```python
# ETag/304 검증
import threading, time, requests
from apps.ops.api import create_app
import uvicorn

def run():
    uvicorn.run(create_app(), host="127.0.0.1", port=8081, log_level="warning")

t = threading.Thread(target=run, daemon=True)
t.start(); time.sleep(1.2)

s = requests.Session()
r1 = s.get("http://127.0.0.1:8081/ops/cards/reason-trends", timeout=3)
etag = r1.headers.get("ETag")
assert r1.status_code == 200 and etag

r2 = s.get("http://127.0.0.1:8081/ops/cards/reason-trends",
           headers={"If-None-Match": etag}, timeout=3)
assert r2.status_code == 304  # Not Modified
```

## 환경 변수

### 필수
- `GITHUB_TOKEN`: PR 코멘트/라벨 자동 생성

### 선택적
- `REDIS_URL`: 캐시 (없으면 no-op)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: SSM/KMS (없으면 no-op)
- `DECISIONOS_ALLOW_SCOPES`: RBAC 스코프 (기본: 읽기 전용)

## Secrets 설정

Repository → Settings → Secrets and variables → Actions:

```
REDIS_URL (optional)
AWS_REGION (optional, default: ap-northeast-2)
AWS_ACCESS_KEY_ID (optional)
AWS_SECRET_ACCESS_KEY (optional)
```

## 로컬 테스트

CI 실행 전 로컬 검증:

```bash
# Smoke tests (빠른 검증)
pytest tests/gates/gate_q/ -v

# Full gate_u tests
pytest tests/gates/gate_u/ -v

# 전체 게이트 시뮬레이션
./pipeline/release/pre_gate_risk.sh
./pipeline/release/gate_burn_and_risk.sh
./pipeline/release/post_alerts.sh
```

## 트러블슈팅

### Clock Guard 실패
```
Error: Clock skew > 2 seconds
```
→ CI 서버 시간 동기화 확인

### SLO Judge 실패
```
Error: SLO violation - p95_ms > threshold
```
→ Evidence 확인: `var/evidence/latest.json`
→ 임계값 조정: `configs/slo/*.json`

### Quorum 실패
```
Error: Only 1/3 judges passed (need 2/3)
```
→ Judge providers 확인: `configs/judge/providers.yaml`
→ HTTP judges 가용성 확인

### PR Annotation 실패
```
Error: GITHUB_TOKEN permission denied
```
→ Workflow permissions 확인: Settings → Actions → General → Workflow permissions
→ "Read and write permissions" 체크

## 모범 사례

1. **PR마다 Smoke Tests 실행** - 빠른 피드백
2. **Main merge 전에 Full CI 실행** - 완전한 검증
3. **Evidence 아티팩트 보관** - 사후 분석 가능
4. **SLO 임계값 점진적 강화** - warn → strict 단계적 적용
5. **Quorum 설정 상황별 조정** - 개발: 1/2, 프로덕션: 2/3
