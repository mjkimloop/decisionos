# RUNBOOK — GameDay Drill

## 개요
- 시나리오: `latency_spike`, `error_spike`, `judge_unavailable`
- 목적: 게이트/롤백/DR 절차를 실제로 검증하고 보고서를 PR에 첨부

## 실행
1. 로컬/CI에서 시나리오 실행
   ```bash
   python -m scripts.gameday.run_scenario --scenario latency_spike --out var/ci/gameday_latency.json
   python -m scripts.gameday.run_scenario --scenario error_spike --out var/ci/gameday_error.json
   python -m scripts.gameday.run_scenario --scenario judge_unavailable --out var/ci/gameday_judge.json
   ```
2. 리포트 생성
   ```bash
   python -m scripts.gameday.report_md \
     --inputs var/ci/gameday_latency.json var/ci/gameday_error.json var/ci/gameday_judge.json \
     --out var/ci/gameday_report.md
   ```
3. CI 연결
   - `.github/workflows/ci.yml` post_gate 스텝에서 자동 실행
   - 결과는 `$GITHUB_STEP_SUMMARY`와 PR 코멘트(GameDay 섹션)에 첨부

## 체크리스트
- [ ] 각 시나리오별 `checks` 필드(Pass/Fail) 기록
- [ ] 발견된 GAP은 Jira/OPS 티켓으로 추적
- [ ] GameDay 종료 후 freeze 상태/라인업 복구 확인

## 일정 관리
- 캘린더는 `ops/gameday_playbook.md` 참고
- 기본 주기: 월 1회 (릴리스 직전), DR Runbook과 연동

## 산출물
- JSON: `var/ci/gameday_*.json`
- Markdown: `var/ci/gameday_report.md`
- PR 라벨: `sev:*` (향후 자동화 예정)
