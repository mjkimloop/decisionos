## 변경 요약
- [ ] docs/techspec.md / docs/plan.md 버전·날짜 동기화
- [ ] docs/index.md 갱신, CHANGELOG.md 항목 추가
- [ ] 영향범위/릴리스 노트 기재
- [ ] wo:apply 실행됨(해당 워크오더 내용 자동 반영)

## 확인 체크리스트
- [ ] `python scripts/doc_guard.py` = OK
- [ ] 버전 태그(예: v0.1.1)가 두 문서에 동일
- [ ] 한 줄 summary가 헤더와 PR 본문에 일치
- [ ] (옵션) `python scripts/wo_apply.py <wo.yaml> --scaffold`로 디렉토리 스캐폴딩 완료

