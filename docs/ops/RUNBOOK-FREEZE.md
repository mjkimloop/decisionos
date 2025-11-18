# RUNBOOK — Change Freeze

## 목적
- 릴리스 직전에 배포/카나리 단계를 일시 중지하여 사고면적을 최소화한다.
- 동결 기간 동안에는 `DECISIONOS_FREEZE=1` 또는 윈도우 캘린더 매치 여부를 기반으로 **fail-closed** 된다.

## 즉시 조치
1. 현재 상태 확인
   ```bash
   python -m apps.ops.freeze --action promote --echo
   ```
2. Freeze 강제(운영팀)
   ```bash
   pipeline/release/pause.sh "change-review"
   ```
   - 기본 플래그 파일: `var/release/freeze.flag`
   - 해제는 `pipeline/release/resume.sh`
3. 윈도우 스케줄 편집
   - `configs/freeze/windows.yaml`
   - 일회성: `start/end` ISO8601
   - 반복: `days` + `start_time` + `end_time` + `timezone`

## 예외 승인
- `deploy:override_freeze` 스코프를 부여 받은 계정만 override 가능
- `DECISIONOS_ALLOW_SCOPES="deploy:override_freeze"`
- 로그에 `[freeze] override scope detected`가 남으므로 후속 감사 필수

## 모니터링
- Freeze 상태는 Ops API `/ops/cards/burn-trends` 카드 하단에 함께 노출
- GitHub Actions 로그에서도 `freeze flag created` 메시지 확인

## 체크리스트
- [ ] Freeze 사유·기간을 PR/Slack에 공유
- [ ] 예외 부여 시 만료 시간 기록
- [ ] GameDay/Hotfix 등이 끝나면 반드시 resume

## 참고
- 정책 위치: `docs/ops/RUNBOOK-FREEZE.md` (본 문서)
- CI 적용: `.github/workflows/ci.yml` post_gate
