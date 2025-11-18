# Policy Signing Key Rotation

**Owner**: Platform Security
**Updated**: 2025-11-16
**Version**: v0.5.11t

---

## 개요

DecisionOS의 서명 정책(Signed Policy)은 HMAC 기반 MultiKey 시스템으로 검증됩니다. 키 로테이션은 보안 컴플라이언스의 핵심 요구사항이며, 본 문서는 키 라이프사이클 관리 및 CI 자동 감시 절차를 정의합니다.

---

## 키 형식

### 환경 변수

```bash
DECISIONOS_POLICY_KEYS='[
  {
    "key_id": "k1",
    "secret": "base64-encoded-secret",
    "state": "active",
    "not_before": "2025-10-01T00:00:00Z",
    "not_after": "2026-01-01T00:00:00Z"
  },
  {
    "key_id": "k2",
    "secret": "base64-encoded-secret",
    "state": "grace",
    "not_before": "2025-12-01T00:00:00Z",
    "not_after": "2026-03-01T00:00:00Z"
  }
]'
```

**Fallback**: `DECISIONOS_JUDGE_KEYS` (Judge 서버와 동일한 키셋 사용 가능)

### 필드 정의

| 필드 | 타입 | 설명 |
|------|------|------|
| `key_id` | string | 키 식별자 (헤더 `X-Key-Id`로 전달) |
| `secret` | string | Base64 인코딩된 HMAC 시크릿 |
| `state` | enum | `active` / `grace` / `retired` |
| `not_before` | ISO8601 | 키 활성화 시작 시각 (UTC) |
| `not_after` | ISO8601 | 키 만료 시각 (UTC) |

### 상태 정의

- **active**: 현재 서명에 사용 중인 키
- **grace**: 로테이션 준비 중 (검증만 가능, 새 서명 불가)
- **retired**: 만료됨 (검증 거부)

---

## 로테이션 기준

### 시간 임계값

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `ROTATION_SOON_DAYS` | 14 | 만료 임박 경고 임계 (일) |
| `GRACE_OVERLAP_DAYS` | 7 | active/grace 최소 겹침 보장 (일) |

### 감지 조건

**경고 (WARN)**:
1. Active 키가 `ROTATION_SOON_DAYS` 이내에 만료 예정
2. Active/Grace 키 간 겹침이 `GRACE_OVERLAP_DAYS` 미만

**오류 (FAIL)**:
- Active 키가 이미 만료됨 (`not_after` < now)

---

## CI 통합

### Pre-Gate: 정책 변경 감시

**스크립트**: `scripts/ci/policy_diff_guard.py`

```bash
# 정책 파일 변경 시 2인 승인 강제
python -m scripts.ci.policy_diff_guard
```

**통과 조건** (둘 중 하나):
1. PR에 `review/2-approvers` 라벨 존재 (기본)
2. GitHub Reviews ≥2 (REQUIRE_APPROVALS=1 설정 시)

**스킵 조건**:
- GITHUB_TOKEN 미설정
- PR 컨텍스트 없음 (CI_PR_NUMBER 미설정)
- 정책 파일 변경 없음

### Post-Gate: 키 로테이션 알림

**스크립트**: `scripts/ci/key_rotation_alert.py`

```bash
# 키 상태 분석 및 JSON 리포트 생성
python -m scripts.ci.key_rotation_alert > var/gate/key_rotation_report.json
```

**출력 예시**:
```json
{
  "now": "2025-11-16T10:30:00Z",
  "soon_days": 14,
  "min_overlap_days": 7,
  "findings": [
    {
      "code": "key.expiry_soon",
      "key_id": "k1",
      "days_left": 10.5
    },
    {
      "code": "key.overlap_insufficient",
      "a": "k1",
      "b": "k2",
      "overlap_days": 3.2
    }
  ],
  "summary": {
    "status": "warn",
    "warnings": 2,
    "errors": 0
  }
}
```

**종료 코드**:
- `0`: OK (문제 없음)
- `8`: WARN (경고 존재, CI 통과하지만 PR 코멘트에 노출)

---

## 운영 절차

### 1. 새 키 생성

```bash
# OpenSSL로 256비트 시크릿 생성
openssl rand -base64 32 > k2.secret
```

### 2. Grace 기간 설정

새 키를 `grace` 상태로 추가:
- `not_before`: 현재 active 키 만료 7일 전
- `not_after`: 현재 active 키 만료 + 60일
- `state`: `grace`

### 3. Active 키 전환

Grace 기간 동안 모니터링 후:
1. 새 키를 `active`로 변경
2. 기존 active 키를 `grace`로 변경
3. 7일 후 기존 키를 `retired`로 변경

### 4. CI 검증

```bash
# 로컬 테스트
DECISIONOS_POLICY_KEYS='[...]' python -m scripts.ci.key_rotation_alert

# 정책 변경 시뮬레이션
CI_BASE_SHA=main CI_HEAD_SHA=HEAD python -m scripts.ci.policy_diff_guard
```

---

## 치트시트

### 키 상태 확인

```bash
# 현재 키 리스트 확인
echo $DECISIONOS_POLICY_KEYS | jq '.[] | {key_id, state, not_after}'

# 만료 임박 키 필터링
echo $DECISIONOS_POLICY_KEYS | jq '.[] | select(.not_after < (now + 86400*14 | strftime("%Y-%m-%dT%H:%M:%SZ")))'
```

### CI 강제 실행

```bash
# Pre-gate (정책 변경 감시)
CI_PR_NUMBER=123 \
GITHUB_TOKEN=$TOKEN \
CI_REPO=org/repo \
python -m scripts.ci.policy_diff_guard

# Post-gate (키 로테이션 알림)
DECISIONOS_POLICY_KEYS='[...]' \
ROTATION_SOON_DAYS=30 \
python -m scripts.ci.key_rotation_alert
```

### PR 라벨 추가

```bash
# GitHub CLI 사용
gh pr edit 123 --add-label "review/2-approvers"

# API 직접 호출
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/org/repo/issues/123/labels \
  -d '{"labels":["review/2-approvers"]}'
```

---

## 문제 해결

### Q: CI에서 "policy changed but PR context missing" 경고

**A**: 로컬 실행 또는 CI 환경 변수 미설정. 프로덕션 환경에서만 체크하므로 무시 가능.

### Q: 정책 파일이 아닌데 gate 실패

**A**: `POLICY_GLOB` 환경 변수로 패턴 조정:
```bash
POLICY_GLOB="configs/policy/*.signed.json,configs/rbac/*.yaml"
```

### Q: 키 겹침 경고 무시하고 싶음

**A**: `GRACE_OVERLAP_DAYS=0` 설정 (권장하지 않음)

---

## 자동화: Rotation Bot

### 개요

**Rotation Bot**은 매일 02:10 UTC에 자동으로 만료 임박 키를 감지하고 드래프트 PR (또는 Issue)을 생성합니다.

### 동작 방식

1. **스케줄 실행**: GitHub Actions cron (`rotation-bot.yml`)
2. **키 분석**: `DECISIONOS_POLICY_KEYS`에서 14일 내 만료 예정 키 검색
3. **라벨 동기화**: `rotation:soon-{14,7,3}` 라벨 생성/업데이트
4. **PR 생성**:
   - 브랜치: `chore/rotate-keys-YYYYMMDD`
   - 커밋: 로테이션 공지 문서 (`docs/ops/ROTATION-NOTICE-YYYYMMDD.md`)
   - 상태: Draft PR
   - 라벨: 만료 일수에 따라 자동 부여
5. **Fallback**: PR 생성 실패 시 Issue 자동 생성

### 카운트다운 라벨

| 라벨 | 색상 | 조건 |
|------|------|------|
| `rotation:soon-14` | 🟠 오렌지 (#e67e22) | 만료 ≤14일 |
| `rotation:soon-7` | 🟠 진한 오렌지 (#d35400) | 만료 ≤7일 |
| `rotation:soon-3` | 🔴 빨강 (#c0392b) | 만료 ≤3일 |

### 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ROTATION_PR_ENABLE` | 1 | 0이면 봇 비활성화 |
| `ROTATION_SOON_DAYS` | 14 | 감지 임계값 (일) |
| `ROTATION_BRANCH_PREFIX` | `chore/rotate-keys` | 브랜치 프리픽스 |
| `ALLOW_ISSUE_FALLBACK` | 1 | PR 실패 시 Issue 생성 |

### 수동 실행

```bash
# GitHub Actions UI에서 workflow_dispatch 트리거
# 또는 로컬에서:
GITHUB_TOKEN=$TOKEN \
DECISIONOS_POLICY_KEYS='[...]' \
python -m scripts.ci.key_rotation_bot
```

### PR 생성 예시

**제목**: `[Rotation] Keys expiring within 14d`

**본문**:
```markdown
# Key Rotation Notice

|key_id|state|not_after|days_left|
|---|---|---|---|
|k1|active|2025-12-01T00:00:00Z|10.5|
|k2|grace|2025-12-05T00:00:00Z|14.2|

> 자동 생성: key_rotation_bot
```

**라벨**: `rotation:soon-14`, `rotation:soon-7`

---

## 정책 Diff 요약

### 개요

정책 파일 변경 시 **핵심 필드**만 추출하여 리뷰어가 빠르게 영향 범위를 파악할 수 있도록 MD/JSON 요약을 생성합니다.

### 추적 필드

- `budget.allow_levels` - 예산 허용 레벨
- `budget.max_spent` - 최대 지출
- `quota.forbid_actions` - 금지 액션
- `latency.max_p95_ms` - P95 지연 임계값
- `latency.max_p99_ms` - P99 지연 임계값
- `error.max_error_rate` - 최대 오류율
- `min_samples` - 최소 샘플 수
- `window_sec` - 윈도 크기 (초)
- `grace_burst` - Grace burst 허용량

### 출력 형식

**Markdown** (`var/gate/policy-diff-*.md`):
```markdown
### Policy Diff (critical fields)

|field|before|after|
|---|---:|---:|
|`budget.max_spent`|`1000`|`2000`|
|`latency.max_p95_ms`|`500`|`300`|
```

**JSON** (`var/gate/policy-diff-*.json`):
```json
{
  "file": "configs/policy/slo.signed.json",
  "changes": [
    {"field": "budget.max_spent", "before": 1000, "after": 2000},
    {"field": "latency.max_p95_ms", "before": 500, "after": 300}
  ]
}
```

### CI 통합

```yaml
- name: Policy diff summary
  run: python -m scripts.ci.policy_diff_summarize

- name: Attach to PR
  run: |
    python -m scripts.ci.annotate_release_gate \
      --extras var/gate/policy-diff-*.json
```

---

## 참고 자료

- [Judge Crypto Documentation](../../apps/judge/crypto.py)
- [KMS Key Loader](../../apps/judge/keyloader_kms.py)
- [CI Annotation Script](../../scripts/ci/annotate_release_gate.py)
- [Rotation Bot Workflow](../../.github/workflows/rotation-bot.yml)
- [Policy Diff Summarizer](../../scripts/ci/policy_diff_summarize.py)

---

**Last Review**: 2025-11-16
**Next Review**: 2026-01-01 (또는 다음 메이저 키 로테이션 시)
