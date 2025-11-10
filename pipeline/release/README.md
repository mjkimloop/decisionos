# DecisionOS Promote Pipeline

배포 단계(stage) 승급을 관리하는 자동화 스크립트.

## 파일 구조

```
pipeline/release/
├── promote.sh              # 메인 승급 스크립트
└── README.md              # 이 문서

apps/experiment/
└── controller_hook.py     # 컨트롤러 통합 훅

tests/e2e/
└── test_promote_controller_hook_v1.py  # E2E 테스트
```

## 빠른 시작

### 1. 로컬 테스트

```bash
# 환경 변수 설정
export DECISIONOS_CONTROLLER_HOOK="python -m apps.experiment.controller_hook"
export DECISIONOS_ENFORCE_RBAC="0"  # 테스트 모드

# 기본 promote 실행
bash pipeline/release/promote.sh

# 커스텀 stage 지정
bash pipeline/release/promote.sh canary
bash pipeline/release/promote.sh blue
```

### 2. 결과 확인

```bash
# stage 파일
cat var/rollout/desired_stage.txt

# 훅 로그
cat var/rollout/hooks.log

# 마지막 훅 실행 정보
cat var/rollout/last_hook.json
```

### 3. E2E 테스트 실행

```bash
pytest -m e2e tests/e2e/
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `STAGE` | `promote` | 승급할 단계 (promote, canary, blue 등) |
| `STAGE_FILE` | `var/rollout/desired_stage.txt` | stage 기록 파일 경로 |
| `RBAC_SCOPE` | `deploy:promote` | RBAC 검증 스코프 |
| `DECISIONOS_CONTROLLER_HOOK` | (없음) | 훅 실행 명령어 |
| `DECISIONOS_ENFORCE_RBAC` | `1` | RBAC 활성화 여부 (0=비활성화) |
| `DECISIONOS_ON_PROMOTE_CMD` | (없음) | 승급 시 실행할 외부 명령어 |

## 작동 방식

```
1. promote.sh 실행
   ↓
2. RBAC 검증 (선택적)
   ↓
3. stage 파일 원자적 업데이트
   ├─ var/rollout/desired_stage.txt 생성
   └─ SHA-256 서명 계산
   ↓
4. controller_hook 실행 (선택적)
   ├─ var/rollout/last_hook.json 생성
   ├─ var/rollout/hooks.log 기록
   ├─ Evidence 재서명 (있으면)
   └─ 외부 명령어 실행 (ENV 설정 시)
   ↓
5. 완료
```

## CI/CD 통합

### GitHub Actions

`.github/workflows/ci.yml`에 이미 통합되어 있음:

```yaml
- name: Promote smoke test
  env:
    DECISIONOS_ENFORCE_RBAC: "0"
    DECISIONOS_CONTROLLER_HOOK: "python -m apps.experiment.controller_hook"
  run: |
    bash pipeline/release/promote.sh

- name: Run E2E tests
  run: |
    pytest -q -m e2e tests/e2e/
```

### 아티팩트 업로드

```yaml
- name: Upload rollout artifacts
  uses: actions/upload-artifact@v4
  with:
    name: decisionos-rollout-${{ github.run_id }}
    path: |
      var/rollout/**
      var/evidence/**
```

## 실전 사용 예시

### Kubernetes/Argo Rollouts 연동

```bash
export DECISIONOS_ON_PROMOTE_CMD="kubectl argo rollouts promote myapp"
bash pipeline/release/promote.sh canary
```

### 다중 환경 배포

```bash
# dev → staging → production
bash pipeline/release/promote.sh staging
# SLO 판정 통과 후
bash pipeline/release/promote.sh production
```

## 트러블슈팅

### RBAC 거부

```
[promote] RBAC 거부: 'deploy:promote' 필요
```

**해결**:
```bash
export DECISIONOS_ENFORCE_RBAC="0"  # 테스트용
# 또는
export DECISIONOS_ALLOW_SCOPES="deploy:promote,judge:run"
```

### 훅 실행 실패

```
[promote] controller hook rc=1
```

**확인**:
```bash
cat var/rollout/hooks.log  # 에러 로그 확인
python -m apps.experiment.controller_hook --stage promote --source test  # 수동 실행
```

## 테스트 커버리지

```bash
# E2E 테스트
pytest -m e2e tests/e2e/

# 커버리지 포함
pytest --cov=apps.experiment --cov=pipeline -m e2e tests/e2e/
```

## 다음 단계

1. **RBAC 정책 설정**: `apps/policy/` 참고
2. **SLO 판정 연동**: `dosctl judge slo` 호출
3. **컨트롤러 루프 구현**: `apps/experiment/controller.py`에서 stage 변화 감지
4. **메트릭 수집**: Prometheus 연동

## 참고

- [SLO-as-Code 문서](../../docs/sli_slo_catalog.md)
- [Evidence 스키마](../../apps/obs/evidence/snapshot.py)
- [Judge 시스템](../../apps/judge/)
