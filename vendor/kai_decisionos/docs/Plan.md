<!--
version: v0.4.3
date: 2025-11-05
status: locked
summary: Gate-W: Policies & ABAC · Data Boundaries · Masking/Tokenization · Residency (No-Gemini)
-->













































# DecisionOS‑Lite 실행플랜 (SSoT)

본 파일은 실행플랜의 단일 진실원본(SSoT)입니다. 실행 세부는 상위 문서 `docs/Plan.md`와 동치이며, 버전/날짜/상태는 본 헤더를 기준으로 운영합니다.

- 참조: docs/Plan.md




<!-- AUTOGEN:BEGIN:Milestones -->
- PDP/PEP/정책저장소·언어(v1) · 정책 번들 서명/배포
- 카탈로그 태깅 + 경계/거주지 강제 · Export 통제
- DB RLS/CLS/마스킹/토큰화 · API 후처리 PEP
- Consent/Purpose Binding · 감사 라벨/리포트
- 테스트/런북/증빙 번들(보안/정책)
<!-- AUTOGEN:END:Milestones -->

<!-- AUTOGEN:BEGIN:Next Actions -->
Day 116: abac_eval(PDP) · cedar-lite parser · policy_store + dosctl policy lint|eval
Day 117: PEP 미들웨어(API/Gateway/SQL) · deny-by-default 적용 · 오버헤드 측정
Day 118: 카탈로그 태깅·경계/거주지 검사 · export 통제(목적/티켓/만료토큰)
Day 119: RLS/CLS/Masking/Tokenization 구현 · 단위/회귀 테스트 60+
Day 120: Consent/Purpose Binding · 롤아웃/롤백·증빙/런북·SLO 검수
<!-- AUTOGEN:END:Next Actions -->

