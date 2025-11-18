# AUTODOC RUNBOOK

## 사용
- 워크오더 작성: `docs/work_orders/wo-*.yaml` (템플릿: `wo-template.yaml`)
- 적용: `python scripts/wo_apply.py docs/work_orders/wo-*.yaml --all`
- 검증: `python scripts/doc_guard.py --strict`
- VSCode: `wo:apply-all`, `wo:check`, `docs:guard` 태스크 사용

## 트러블슈팅
- DOC001: BEGIN/END 마커 짝 불일치 → 문서에서 손상된 마커를 복구 후 재실행
- DOC002: Out-of-sync → `wo_apply.py --all`로 적용 후 커밋
- DOC003: 헤더 누락/불일치 → techspec/plan 헤더 블록 확인
- WOS001/2: Work Order 스키마/모드 오류 → `scripts/schemas/work_order.schema.json` 확인

## 원복
- `git checkout -- docs/techspec.md docs/plan.md docs/index.md CHANGELOG.md`
- 필요 시 문제 워크오더를 수정/삭제 후 `wo_apply.py --all` 재실행
