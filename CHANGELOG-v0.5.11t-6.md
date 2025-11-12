# v0.5.11t-6 Release Notes

## 개요
Risk Governor, Burn-rate Gate, Shadow Sampler, Alerts/Playbook 시스템 추가 + 스켈레톤 코드 정비 + gate_q 스모크 테스트 + GitHub Actions CI 파이프라인 구축

## 커밋 히스토리 (5 commits)

### 1. feat(ops): Risk Governor + Burn-rate Gate + Shadow Sampler + Alerts (98a3a12)
**핵심 기능 구현** (23 files, 1728 insertions)

#### Risk Governor
- 6개 신호 퓨전: drift_z, anomaly_score, infra_p95_ms, error_rate, quota_denies, budget_level
- 정규화 타입: zscore, linear, minmax, enum
- Score [0..10) → Action 매핑 (promote/canary/freeze/abort)
- 파일: `apps/rollout/risk/governor.py`, `apps/rollout/risk/mapping.py`
- 설정: `configs/rollout/risk_governor.json`

#### Burn-rate Gate
- SLO error budget 소모율 모니터링
- 공식: `actual_error_rate / expected_error_rate`
- 레벨: ok / warn / critical
- critical → exit(2) fail-closed pattern
- 파일: `apps/sre/burnrate.py`
- Job: `jobs/burnrate_gate.py`
- 설정: `configs/rollout/burn_rate.json`

#### Shadow Sampler
- 적응형 샘플링 (1-50%)
- 히스테리시스: up_ms=900, down_ms=300 (증가는 느리게, 감소는 빠르게)
- 부하 기반 자동 조정 (cpu, queue_depth)
- 파일: `apps/experiment/shadow_sampler.py`
- Job: `jobs/shadow_autotune.py`
- 설정: `configs/shadow/sampler.json`

#### Alerts & Playbook
- Slack/Webhook 라우팅 (dry-run 지원)
- Reason code → Action 매핑
- PR 코멘트 자동 주입
- 파일: `apps/alerts/dispatcher.py`
- 설정: `configs/alerts/routes.json`, `configs/playbooks/actions.json`

#### Prometheus Metrics
- `decisionos_risk_score` [0..10)
- `decisionos_burn_rate` [0..∞)
- `decisionos_shadow_pct` %
- `decisionos_alerts_total{level}`
- 파일: `apps/ops/metrics.py`
- Optional import + Mock fallback

---

### 2. refactor(core): 스켈레톤 코드로 정비 (e00a68a)
**타입 안전성 강화 및 의존성 최소화** (-399 lines: 807 deletions, 408 insertions)

#### Dataclass 기반 설정
- `GovernorConfig`, `BurnRateConfig`, `SamplerConfig`
- `Hysteresis`, `RangeAction`
- 타입 안전성 및 IDE 지원 개선

#### 타입 힌트 강화
- `from __future__ import annotations` 전면 적용
- Python 3.10+ style type hints
- Literal types for enum-like values

#### 버그 수정
1. **zscore 정규화**: `abs(x)` 사용으로 음수 z-score 올바르게 처리
2. **burn_rate 공식**: `actual_error_rate / expected_error_rate`로 수정
3. **enum 타입 처리**: budget_level 같은 문자열 값 float 변환 오류 수정

#### 의존성 최소화
- `requests` → `urllib.request` 대체 (외부 의존성 제거)
- `prometheus_client` 선택적 import + 모듈 수준 mock
- 환경변수 기반 설정 + CLI args 병행 지원

#### 테스트 업데이트
- 새로운 API에 맞춰 gate_u 테스트 수정
- playbook helpers 추가 (load_playbooks, get_playbook_actions)
- **12/12 tests passing** (gate_u + playbook)

---

### 3. test(gate_q): 스모크 테스트 추가 (0c81ba6)
**외부 의존성 없는 빠른 검증** (6 files, 8 tests, 0.2초)

#### 테스트 파일
1. `test_risk_governor_decide_smoke_v1.py` - RiskGovernor 기본 동작
2. `test_burnrate_levels_smoke_v1.py` - Burn rate 레벨 구분 (ok/warn/critical)
3. `test_shadow_sampler_smoke_v1.py` - Hysteresis 동작 검증
4. `test_alerts_dispatcher_dryrun_v1.py` - Dry-run 모드 + 빈 이벤트 처리
5. `test_jobs_integration_smoke_v1.py` - Jobs 통합 (risk/burn/shadow)
6. `test_ops_metrics_noop_v1.py` - prometheus_client 미설치 환경 no-op

#### 특징
- 외부 의존성 없음 (네트워크, DB, 서비스 불필요)
- 환경변수 기반 설정 + 모듈 reload 패턴
- 격리된 테스트 (tmp_path + monkeypatch)

#### pytest 마커
- `gate_q`: Quick smoke tests
- `gate_u`: Unit tests for core logic
- 실행: `pytest tests/gates/gate_q/ -q`

---

### 4. ci(workflows): GitHub Actions 3단계 게이트 파이프라인 (145dbf9)
**PreGate → Gate → PostGate** (3 files, 508 insertions)

#### smoke-tests.yml
- **트리거**: Push/PR to main, develop
- **실행 시간**: ~30초
- **테스트**: gate_q (8 tests)
- 외부 의존성 없음

#### decisionos-ci.yml
- **트리거**: Push/PR to main, workflow_dispatch
- **실행 시간**: ~5분
- **3단계 게이트**:

**PreGate**: Clock/Evidence/Unit
- Clock skew 검증 (±2초)
- Evidence 인덱싱
- gate_t 타겟 테스트 (non-fatal)

**Gate**: SLO 저지 + Quorum
- reqlog/judgelog 수확 → perf.json/perf_judge.json
- Evidence 병합 및 서명 (integrity.signature_sha256)
- Infra SLO 저지 (Judge 성능)
- Canary SLO 저지 (엄격 버전)
- 2/3 Quorum 검증 (로컬 + HTTP judges)

**PostGate**: Annotation + Labels + API Smoke
- Labels 동기화 (label_catalog_v2.json)
- PR 코멘트 (사유 top-3 + diff link + artifacts URL)
- Ops API smoke (ETag/304 검증)
- GitHub Step Summary 생성

#### 환경 변수
- `DECISIONOS_ALLOW_SCOPES`: ops:read,judge:run,deploy:promote,deploy:abort
- `REDIS_URL`, `AWS_*` (optional, no-op fallback)
- `GITHUB_TOKEN` (PR 코멘트/라벨)

#### 문서
- `.github/README.md` 추가
- 워크플로우 상세 설명
- Evidence 빌드 가이드
- SLO 저지/Quorum 설정
- 트러블슈팅 가이드

---

### 5. chore(samples): CI 워크플로우용 샘플 데이터 (f189925)
**바로 붙여넣어 돌아가는 샘플** (5 files, 65 insertions)

#### Judge Providers
- `configs/judge/providers.yaml`
- local-0 (weight: 1.0)
- judge-http-a (HTTP + retry + circuit breaker + HMAC)

#### Label Catalog v2
- `configs/labels/label_catalog_v2.json`
- 7개 그룹: infra/perf/canary/quota/budget/anomaly/security
- 10개 라벨 (reason:* 코드)
- GitHub 라벨 자동 동기화용

#### 샘플 로그
1. `data/reqlog_sample.csv` (10 rows)
   - Request 성능 로그
   - 정상 요청 + 429 throttle + 500 error

2. `data/judgelog_sample.csv` (7 rows)
   - Judge 성능 로그
   - Judge infra SLO 검증용

3. `data/witness_sample.csv` (3 rows)
   - Witness 사용량 데이터
   - tokens(130) + storage_gb(8)

---

## 전체 통계

### 코드 변경
- **5 commits**
- **Net changes**: +1,500 lines (코드 품질 개선으로 -399 lines)
- **파일 수**: 37 files changed

### 테스트 커버리지
- **gate_u**: 10 tests (Risk Governor 4, Burn Rate 3, Shadow Sampler 3)
- **gate_q**: 8 tests (스모크 테스트)
- **전체**: 18/18 passing (0.3초)

### 주요 파일
```
apps/
├── rollout/risk/        # Risk Governor
├── sre/                 # Burn-rate Gate
├── experiment/          # Shadow Sampler
├── alerts/              # Alerts & Playbook
└── ops/                 # Prometheus Metrics

jobs/
├── risk_decide_and_stage.py
├── burnrate_gate.py
└── shadow_autotune.py

configs/
├── rollout/             # risk_governor.json, burn_rate.json
├── shadow/              # sampler.json
├── alerts/              # routes.json
├── playbooks/           # actions.json
├── judge/               # providers.yaml
└── labels/              # label_catalog_v2.json

tests/gates/
├── gate_u/              # Unit tests
└── gate_q/              # Smoke tests

.github/workflows/
├── smoke-tests.yml      # 빠른 검증
└── decisionos-ci.yml    # 전체 게이트
```

---

## 실행 방법

### 로컬 테스트
```bash
# 스모크 테스트
pytest tests/gates/gate_q/ -v

# 유닛 테스트
pytest tests/gates/gate_u/ -v

# 전체 게이트 시뮬레이션
./pipeline/release/pre_gate_risk.sh
./pipeline/release/gate_burn_and_risk.sh
./pipeline/release/post_alerts.sh
```

### CI 워크플로우
```bash
# GitHub에 push하면 자동 실행
git push origin main

# 또는 수동 트리거
gh workflow run smoke-tests.yml
gh workflow run decisionos-ci.yml
```

### Jobs 실행
```bash
# Risk Governor
python -m jobs.risk_decide_and_stage

# Burn-rate Gate
python -m jobs.burnrate_gate

# Shadow Sampler
python -m jobs.shadow_autotune
```

---

## Breaking Changes
없음 (모두 신규 기능 추가)

---

## Migration Guide
기존 코드에 영향 없음. 새로운 기능을 사용하려면:

1. **Risk Governor 활성화**:
   ```bash
   export DECISIONOS_RISK_CFG=configs/rollout/risk_governor.json
   python -m jobs.risk_decide_and_stage
   ```

2. **Burn-rate Gate 추가**:
   ```bash
   export DECISIONOS_BURN_CFG=configs/rollout/burn_rate.json
   python -m jobs.burnrate_gate
   ```

3. **Shadow Sampler 활성화**:
   ```bash
   export DECISIONOS_SHADOW_CFG=configs/shadow/sampler.json
   python -m jobs.shadow_autotune
   ```

---

## Contributors
- @claude-code (Claude Code Assistant)

---

## Next Steps (v0.5.11t-7 후보)
- [ ] Canary step 자동 조정 (slew rate 기반)
- [ ] Drift SLO 게이트 추가
- [ ] Explain API (reason 분석)
- [ ] Evidence 자동 압축 (retention policy)
- [ ] Real-time alerting (webhook → Slack)
