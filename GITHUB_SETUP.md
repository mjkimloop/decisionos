# GitHub Repository 설정 가이드

## 현재 상태

```bash
✅ Git 초기화 완료
✅ 2개 커밋 완료
   - 428b099: feat(release): Add promote pipeline with controller hook integration
   - dff0de2: refactor(release): Simplify promote.sh and add full DecisionOS codebase
✅ 787개 파일 (63,458줄 추가)
⏳ GitHub remote 설정 대기
```

---

## 1. GitHub에서 새 레포지토리 생성

### 방법 1: GitHub 웹사이트
1. https://github.com/new 접속
2. 레포지토리 이름: `DecisionOS`
3. 설명: `SLO-as-Code platform with Evidence-provable execution`
4. Public/Private 선택
5. **❗ 중요**: `Initialize this repository with:` 모두 **체크 해제**
   - ❌ Add a README file
   - ❌ Add .gitignore
   - ❌ Choose a license
6. `Create repository` 클릭

### 방법 2: GitHub CLI
```bash
gh repo create DecisionOS --public --source=. --remote=origin --push
```

---

## 2. Git Remote 설정

### GitHub 레포 생성 후 표시되는 URL 사용

```bash
# HTTPS (추천)
git remote add origin https://github.com/YOUR-USERNAME/DecisionOS.git

# SSH (SSH 키 설정 필요)
git remote add origin git@github.com:YOUR-USERNAME/DecisionOS.git
```

**예시**:
```bash
git remote add origin https://github.com/johndoe/DecisionOS.git
```

---

## 3. Push

### 첫 Push (branch 설정 포함)
```bash
git branch -M main
git push -u origin main
```

**성공 메시지**:
```
Enumerating objects: 1234, done.
Counting objects: 100% (1234/1234), done.
Delta compression using up to 8 threads
Compressing objects: 100% (567/567), done.
Writing objects: 100% (1234/1234), 3.45 MiB | 2.34 MiB/s, done.
Total 1234 (delta 456), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (456/456), done.
To https://github.com/YOUR-USERNAME/DecisionOS.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

---

## 4. GitHub Actions 자동 실행 확인

Push 후 **자동으로** 다음이 실행됨:

### CI 워크플로우
```
GitHub 레포 → Actions 탭 → CI 워크플로우
```

### 실행되는 Jobs:
1. **tests** (5개 게이트 매트릭스)
   - gate_t (Observability)
   - gate_aj (Judge)
   - gate_s (Billing)
   - gate_p
   - gate_o

2. **release_gate** (SLO 판정)
   - Evidence 생성
   - Shadow/Canary 비교
   - SLO 판정 (judge_quorum)

3. **e2e_promote** (배포 통합)
   - promote.sh 실행
   - E2E 테스트
   - 아티팩트 업로드

### 예상 실행 시간:
- tests: ~3분
- release_gate: ~5분
- e2e_promote: ~2분
- **총 ~10분**

---

## 5. GitHub Actions 결과 확인

### 성공 시:
```
✅ tests (5/5 passed)
✅ release_gate (SLO passed)
✅ e2e_promote (2 tests passed)
```

### 아티팩트 다운로드:
```
Actions → 워크플로우 실행 → Artifacts 섹션
→ decisionos-rollout-{run_id}.zip 다운로드
```

**포함 내용**:
- var/rollout/desired_stage.txt
- var/rollout/hooks.log
- var/rollout/last_hook.json
- var/evidence/*.json

---

## 6. 트러블슈팅

### 문제 1: `remote origin already exists`
```bash
git remote remove origin
git remote add origin https://github.com/YOUR-USERNAME/DecisionOS.git
```

### 문제 2: `! [rejected] main -> main (fetch first)`
```bash
# 원인: GitHub에서 README 등을 자동 생성한 경우
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### 문제 3: GitHub Actions 실패
```bash
# 로컬에서 먼저 테스트
export DECISIONOS_ENFORCE_RBAC="0"
export DECISIONOS_CONTROLLER_HOOK="python -m apps.experiment.controller_hook"

# 테스트 실행
pytest -m e2e tests/e2e/

# promote.sh 실행
bash pipeline/release/promote.sh
```

---

## 7. 다음 단계

### Push 완료 후:
1. ✅ GitHub Actions 그린 확인
2. ✅ 아티팩트 다운로드
3. ✅ README.md 추가 (선택)
4. ✅ About 섹션 수정 (설명, 태그 추가)

### README.md 추가 (선택):
```bash
cat > README.md << 'EOF'
# DecisionOS

SLO-as-Code platform with Evidence-provable execution.

## Features

- ✅ SLO-based release gates
- ✅ Evidence snapshots (SHA-256 signed)
- ✅ Multi-judge quorum (k-of-n)
- ✅ Performance witness (p50/p95/p99)
- ✅ CI/CD integration

## Quick Start

\`\`\`bash
# Run promote
export DECISIONOS_CONTROLLER_HOOK="python -m apps.experiment.controller_hook"
bash pipeline/release/promote.sh

# Run tests
pytest -m e2e tests/e2e/
\`\`\`

## Documentation

- [pipeline/release/README.md](pipeline/release/README.md) - Promote pipeline guide
- [docs/](docs/) - Full documentation
EOF

git add README.md
git commit -m "docs: Add README.md"
git push
```

---

## 빠른 명령어 모음

```bash
# 1. GitHub 레포 생성 (웹사이트)
# → https://github.com/new

# 2. Remote 추가
git remote add origin https://github.com/YOUR-USERNAME/DecisionOS.git

# 3. Push
git branch -M main
git push -u origin main

# 4. Actions 확인
# → https://github.com/YOUR-USERNAME/DecisionOS/actions

# 5. 로컬 테스트 (선택)
pytest -m e2e tests/e2e/
bash pipeline/release/promote.sh
```

---

## 체크리스트

```
설정:
□ GitHub 레포 생성
□ git remote add origin 실행
□ git push 성공

확인:
□ GitHub Actions 그린
□ 아티팩트 다운로드 가능
□ 레포 About 섹션 업데이트

선택:
□ README.md 추가
□ LICENSE 파일 추가
□ GitHub Topics 태그 추가
```

---

**준비 완료!** 위 1-3단계만 실행하면 GitHub Actions가 자동으로 돌아갑니다. 🚀
