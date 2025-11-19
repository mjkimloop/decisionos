## v0.5.11u-7 — 2025-11-19 (성능 최적화)
- **압축/전송 최적화**: gzip 압축으로 응답 크기 ≥60% 감소, 저장 공간 ≥70% 절감
- `apps/common/compress.py`: 압축 유틸 (should_compress, gzip_bytes, negotiate_gzip, 임계값 체크)
- `apps/ops/api/cards_delta.py`: Accept-Encoding 협상, 4KB 이상 자동 압축, `Vary: Accept-Encoding` 헤더
- ETag 불변성: 압축 여부 무관 동일 ETag (RFC 7232 표현 무관 원칙)
- `apps/common/s3_adapter.py`: S3 업로드 압축 (.gz 확장자 + Content-Encoding 메타데이터, Stub/AWS 공통)
- `apps/ops/cache/snapshot_store.py`: Redis 스냅샷 압축 (4KB 이상, 메모리 절감)
- `apps/gateway/main.py`: Cards API 라우터 마운트
- **테스트 13개 모두 통과**:
  - `tests/common/test_compress_threshold_v1.py` (5/5): 압축 임계값/협상/roundtrip
  - `tests/ops/test_cards_gzip_and_etag_v1.py` (3/3): Cards API gzip 협상, ETag 불변성, 304 응답
  - `tests/s3/test_stub_upload_gzip_v1.py` (5/5): S3 stub 압축 업로드, 자동 압축 해제, 임계값
- `.github/workflows/ci.yml`: gate_u7_compress 추가 (13개 테스트 자동 실행)
- `.env.example`: 압축 환경변수 (COMPRESS_ENABLE=1, MIN_BYTES=4096, GZIP_LEVEL=6)

## v0.5.11u-5 — 2025-11-19 (보안 핫픽스)
- **SEC-001 (Critical)**: RBAC 테스트모드 기본 OFF, 프로덕션에서 test-mode=1 시 부팅 실패
- **SEC-002 (High)**: CORS 화이트리스트 강제, 프로덕션에서 wildcard(*) 금지
- **SEC-003 (Medium)**: 서명 검증 에러 메시지 일반화 ("invalid signature", 상세 사유 로그만)
- `apps/policy/rbac_enforce.py`: 테스트모드 기본값 0, prod 환경 검증
- `apps/gateway/security/cors.py`: 엄격 CORS 미들웨어 (화이트리스트 강제)
- `apps/judge/crypto.py`: SignatureInvalid 예외 + verify_signature_safe() 추가
- `tests/security/*`: 보안 테스트 3개 (15개 테스트 케이스)
- `.env.example`: 보안 기본값 업데이트 (RBAC_TEST_MODE=0, CORS_ALLOWLIST 주석)
- `docs/ops/RUNBOOK-u-5-security.md`: 배포 런북 (Canary 단계, 롤백 절차, 트러블슈팅)

## v0.5.11u-4 — 2025-11-19
- **운영 RUNBOOK**: Cards API 운영 가이드 (캐시 정책, 트러블슈팅, 메트릭, 환경변수)
- `docs/ops/RUNBOOK-OPS-CARDS.md` 추가 (ETag/304/Delta 프로토콜, 4가지 장애 시나리오, Prometheus 메트릭)
- 참고 문서 링크 (GO-READINESS, 배포 런북, 알람 규칙, 테스트)

## v0.5.11u-3 — 2025-11-19
- **Prometheus 알람**: 5개 알람 규칙 (ETag hit rate, HTTP retry, P95 latency, Delta, 에러율)
- `configs/alerts/cards_alerts.yml` 추가 (AlertManager 형식, PromQL 표현식, 심각도/임계값)
- 알람 YAML 스키마 검증 테스트 (5/5 passed)

## v0.5.11u-2 — 2025-11-19
- **경계 테스트**: ETag 충돌 방지 + Delta 협상 엣지 케이스 (회귀 방지)
- `tests/ops/test_cards_etag_collision_v1.py` (테넌트/카탈로그/쿼리 분리, 안정성 검증)
- `tests/ops/test_cards_delta_negotiation_edge_v1.py` (헤더 없음, 불일치, 강제 풀 페이로드 프로브)
- GO-READINESS-48H.md 작업 2 완료 (6/6 테스트 Green)

## v0.5.11u-1 — 2025-11-19
- **스켈레톤 위생**: NUL 제거 + 빈 __init__ 정리 + TODO 스윕 + CI 게이트
- `scripts/maintenance/apply_hygiene_patches.py` (멱등 자동 수정기)
- `scripts/ci/check_skeletons.py` (NUL/zero-byte 검출, 얼로우리스트 지원)
- `.gitignore`에 `nul`, `NUL` 추가 (Windows 호환성)
- CI pre-gate 추가 (자동 위생 체크)

## v0.5.11t-cutover-exec (진행 중)
- Cutover 리허설 스크립트(`pipeline/release/cutover_rehearsal.sh`) 추가, auto-promote/abort 경로 검증
- SLO v2 기본값 캘리브레이션(`configs/slo/slo-infra-v2.json`, `slo-canary-v2.json`)
- Key rotation 플랜/런북/도구 추가(`configs/keys/key_rotation_plan.json`, `scripts/keys/rotate_keys.py`)
# Changelog

## v0.5.11w — 2025-11-16
- Change Governance: freeze window registry + CAB 멀티-시그 + 온콜 확인 + break-glass
- scripts/change/* CI 스텝 및 pipeline enforcement, Ops API /ops/change/* 카드
- RUNBOOK-CHANGE.md 추가, PR 코멘트/Checks에 Change 배지 노출

## v0.5.11u — 2025-11-16
- Prod Readiness: Change Freeze 토글/윈도우 + override scope
- SLO Burn-Rate Gate: 다중 윈도, Slack/Freeze 연동, Ops 카드 + CI step
- GameDay Drill 자동화: latency/error/judge 시나리오 + 보고서/PR 코멘트 ## v0.3.8 — 2025-11-03 - Gate-R: HITL Ops v2 · Case Management · Dispute/Appeals (No-Gemini)  ## v0.3.9 — 2025-11-03 - Gate-S: Multi-Tenant · Billing · Usage Metering · Entitlements · Cost Guard (No-Gemini)  ## v0.1.6 — 2025-11-02 - PoV 드라이런(도커 패키징·커넥터 v1·관측성·Runbook·롤백). No‑Gemini 유지  ## v0.1.2 — 2025-11-02 - Gate-A 통과용 작업지시 + 문서 자동기입 도입  ## v0.1.3 — 2025-11-02 - Gate-B 준비: 조기신호 2/3·보안 문서화·PoV Runbook·실벤더 라우팅  ## v0.1.7 — 2025-11-02 - Gate-D: Client PoV — 싱글 테넌트 배포/관측성/보안 증빙/현장 리허설 (No-Gemini)  ## v0.1.8 — 2025-11-02 - Gate-E: SOW 승인·Paid PoV 계약·계량/청구 개통 (No-Gemini)  ## v0.1.9 — 2025-11-02 - Gate-F: 멀티테넌트·멀티리전 Lite 초기화(Active-Passive, RLS, DR/Failover, 관측성 통합)  ## v0.2.0 — 2025-11-02 - Gate-G: Auto-Failover·Health Probes·Error-Budget SLO·Canary·Chaos (No-Gemini)  ## v0.4.2 — 2025-11-04 - Gate-V: Partner SDK & Extensibility · Plugins/Webhooks/Embeds · Sandbox/Signing · Marketplace Beta (No-Gemini)  ## v0.2.1 — 2025-11-02 - Gate-H: Observability·Tracing·Cost Sentry·Vendor v2 (No-Gemini)  ## v0.2.2 — 2025-11-02 - Gate-I: Policy Engine·PII Vault·HITL(승인/오버라이드) — No-Gemini  ## v0.2.3 — 2025-11-02 - Gate-J: Playbooks·Decision Templates·Domain Packs — 표준·레지스트리·스캐폴딩·시뮬레이션  ## v0.3.0 — 2025-11-02 - Gate-K: Launch Readiness — Docs·Trials·Pricing·Support·Status (No-Gemini)  ## v0.3.1 — 2025-11-02 - Gate-L: Adoption Analytics·NPS·Feedback·Roadmap Backlog (No-Gemini)  ## v0.3.2 — 2025-11-02 - Gate-M: Usage-Based Pricing v2 · Seat/Role Billing · Self‑Serve Upgrade/Cancel (No-Gemini)  ## v0.3.3 — 2025-11-02 - Gate-N: SSO/OAuth·Org/Projects·Fine-Grained RBAC — No-Gemini  ## v0.3.4 — 2025-11-02 - Gate-O: Connectors·ETL/CDC·Data Contracts v1·Ontology Mapping·Quality Gates (No-Gemini)  ## v0.3.6 — 2025-11-02 - Gate-P: Search & Catalog · Lineage v2 · Data Products (No-Gemini)  ## v0.3.7 — 2025-11-03 - Gate-Q: Guardrails v2 · Explainability · Model Audit Trails (No-Gemini)  ## v0.4.3 — 2025-11-05 - Gate-W: Policies & ABAC · Data Boundaries · Masking/Tokenization · Residency (No-Gemini)  ## v0.4.0 — 2025-11-04 - Gate-T: Observability v2 · SLI/SLO · Traces/Logs/Metrics · Error-Budget Gating (No-Gemini)  ## v0.4.4 — 2025-11-05 - Gate-X: Edge/Offline · Store-and-Forward · Sync/Conflict · Local Policy · Secure Cache (No-Gemini)  ## v0.4.5 — 2025-11-05 - Gate-Y: BCP/DR · Backups · Failover · Chaos Drills · RPO/RTO (No-Gemini)  ## v0.4.6 — 2025-11-05 - Gate-Z: GA Readiness · Sec/Perf/Legal/Pricing · PenTest/Load · SRE/Support · Release (No-Gemini)  ## v0.4.7 — 2025-11-05 - Gate-AA: Growth & GTM Runbooks · Sales/Marketing/Partner · PQL/PLG · CRM/Sequencer (No-Gemini)  ## v0.4.8 — 2025-11-06 - Gate-S: Multi-Tenancy · Usage/Metering/Rating · Quota/Throttling · Cost-Guard v1 · Invoicing Stubs (No-Gemini)  ## v0.4.8a — 2025-11-06 - Gate-S Codex Sync: Tenancy models+RLS/CLS, Metering pipeline split, Rating/Proration, TokenBucket, Cost-Guard(EWMA), Invoice Draft  ## v0.4.9 — 2025-11-06 - Gate-U: Payments · Refunds · Tax/Receipts · Dunning · Chargeback · Reconciliation (No-Gemini)  ## v0.5.0 — 2025-11-06 - Gate-Q: Audit & Guardrails · Explain/Replay · Change Mgmt · HITL (No-Gemini)  ## v0.5.1 — 2025-11-06 - Gate-AB: Academy · Certification · Labs (No-Gemini)  ## v0.5.2 — 2025-11-06 - Gate-AC: FinOps v2 — Unit Economics · Forecast · Optimizers (No-Gemini)  ## v0.5.3 — 2025-11-06 - Gate-AD: Data Privacy Ops — Discovery/Consent/Retention/DSAR/Legal Hold (No-Gemini)  ## v0.5.4 — 2025-11-06 - Gate-AE: LLM Safety v2 — PI/JB/DLP/Toolcall Guard & Router Hardening (No-Gemini)  ## v0.5.5 — 2025-11-06 - Gate-AF: Geo/Residency Enforcement v2 — Routing/Transfers/Ledger/Orchestrator (No-Gemini)  ## v0.5.6 — 2025-11-06 - Gate-AG: Ontology v2 · Decision Graph · Contracts · Codegen (No-Gemini)  ## v0.5.7 — 2025-11-06 - Gate-AH: Model Ops v2 — Feature Store · Train/Serve Sync · Shadow/Canary · Skew/Drift (No-Gemini)  ## v0.5.8a — 2025-11-06 - DocOps Hotfix: plan.md Gate-Scoped Upsert — 게이트별 섹션 분리 및 upsert 모드 적용 (No-Gemini)  ## v0.5.10a — 2025-11-07 - Gate-AJ Hotfix — No-SPOF, Witness-based Judge, Quorum(2/3)  ## v0.5.10b — 2025-11-07 - Gate-T Hotfix v2 — Dual Witness Exporters, Quorum-of-Measurement, Backfill Reconcile  ## v0.5.10c — 2025-11-07 - Gate-AJ/T: CLI DSL Judge + Backfill Reconcile + Golden Trace harness  ## v0.5.11a — 2025-11-10 - Gate-S · Metering Contracts v1 (schema/ingest/reconcile/idempotency) + test  ## v0.5.11b — 2025-11-10 - Gate-S — IdempoStore pluggable (InMemory/SQLite) + factory injection + tests  ## v0.5.11c — 2025-11-10 - Gate-S — Watermark/Lateness 처리 + Window 누수 방지 + V2 리포트  ## v0.5.11d — 2025-11-10 - Gate-S — Rating(요금계산) / Quota(한도) / Cost-Guard(예산/이상징후) v1  ## v0.5.11e — 2025-11-10 - Gate-T + Gate-S Integration — Witness CSV → Metering → Rating/Quota smoke test  ## v0.5.11f — 2025-11-10 - Witness → Metering → Rating/Quota → Cost-Guard(예산·EWMA) 통합 + Evidence 스냅샷(JSON) 생성  ## v0.5.11g — 2025-11-10 - slo.json 스키마 + Evidence 비교 Judge(단일) + Multi-Judge(2/3 합의) + RBAC Hook + CLI  ## v0.5.11h — 2025-11-10 - Gate-T 성능 증빙(p50/p95/p99, error_rate) + Evidence.perf + SLO(latency/error) + Judge 확장 + CLI  ## v0.5.11i — 2025-11-10 - 원격 저지(HTTP/RPC) k-of-n 합의, 서명검증, Degraded 시 Fail-Closed, Evidence에 투표 로그 포함  ## v0.5.11i.1 — 2025-11-10 - 분산 저지 마감: dosctl CLI, k-of-n 통합/단위/E2E 테스트, HMAC+Nonce Anti-Replay, Evidence.judges 병합, CI 확장  ## v0.5.11i.2 — 2025-11-10 - 분산 저지 하드닝: 키 로테이션·RBAC 강제·리플레이 스토어 플러그인화·릴리스 게이트  ## v0.5.11k — 2025-11-10 - 카나리/블루-그린 라우팅 · 섀도 트래픽 수집 · 증빙 비교 · 카나리 SLO 판정 · 자동 롤백  ## v0.5.11l — 2025-11-10 - 실트래픽 배포 파이프라인 연결(카나리/블루그린), 로그→Evidence 자동화, 운영 게이트/런북  ## v0.5.11m — 2025-11-10 - stage 파일 원자화·드리프트 가드, Evidence 불변성, 카나리 장애/롤백 시뮬, 키/시계/권한 하드닝, CI 게이트 강화  ## v0.5.11n — 2025-11-11 - RBAC default-deny · Evidence GC tiering · Judge infra SLO 파라미터화 · Stage 무결성(서명) 강제  ## v0.5.11o — 2025-11-11 - RBAC default-deny · Evidence GC tiering · Judge infra SLO 파라미터화 · Stage 무결성(서명) 강제  ## v0.5.11p — 2025-11-11 - Ops API(Reason Trend 카드) + PR 코멘트 아티팩트 링크 + Top-impact 레이블러  ## v0.5.11p-1 — 2025-11-11 - Ops Reason Trend 카드 API에 캐싱/ETag 및 RBAC(ops:read) 보호 추가  ## v0.5.11q — 2025-11-11 - Prod Cutover 준비: Ops API 캐싱/ETag · Judge HA(/readyz) · KMS/Redis · Evidence LOCK/GC · 카나리 자동승격 · Prometheus 지표  ## v0.5.11q-1 — 2025-11-11 - PR 주석 자동 템플릿 도입 + 아티팩트 링크 유효성 검사 + CI 릴리스 게이트 주석 강화  ## v0.5.11q-2 — 2025-11-11 - PR 코멘트 마커 업서트/중복 억제, 실패 사유 자동 라벨링, 모듈 가중 Top-Impact 산출 및 CI 연동  ## v0.5.11q-3 — 2025-11-11 - 라벨 가시성(색상·설명 자동 생성) 및 PR 코멘트 diff-permalink 자동 첨부  ## v0.5.11q-4 — 2025-11-11 - 라벨-카드 자동 전파, 이유군 롤업, 포크-세이프 코멘터, 라벨 드리프트 리포트 + CI 통합  ## v0.5.11s-1 — 2025-11-12 - 운영값(슬랙 Webhook/채널, SSM 파라미터, Redis DSN, 카나리 스텝 스케줄) 반영 핫픽스  ## v0.5.11s-2 — 2025-11-12 - 운영 채널 분기(환경/사유별), Slack 알림 레이트-리밋, 라벨 팔레트 v2 정교화 및 CI 테스트 배선   ## v0.5.11t ? 2025-11-16 - PR-D: CI pre→gate→post 루프 추가(인덱스/GC → ObjectLock → DR) 및 stub 기본값 정리. - .env.example 재정비, Evidence GC/DR 문서에 CI 연동 절차 보강.  ## v0.5.11u ? 2025-11-16 - Release gate visibility: artifact validation, GitHub checks, PR comment/label auto-sync. - New CI scripts (`scripts/ci/validate_artifacts.py`, `github_checks.py`, `annotate_release_gate.py`) plus docs at `docs/ops/PR-VISIBILITY.md`.


## vX.Y.Z — YYYY-MM-DD
- 한 줄 변경 요약

## v0.4.1 — 2025-11-04
- Gate-U: Payments & KYC · PG Integration · Settlement · Refunds/Adjustments (No-Gemini)

## v0.5.10h — 2025-11-10
- Gate-S/P/O 테스트 시드 추가 및 CI 매트릭스 확장 (xfail 기반)

## v0.5.11q-4.1 — 2025-11-11
- Cards API에 그룹 가중치/Top-N(라벨·그룹) 동시 반환, PR 코멘트에 라벨 카탈로그 SHA 표시

## v0.5.11q-4.6.1 — 2025-11-11
- Cards API ETag v2(키 확장) + PR 코멘트에 Alerts URL 자동 삽입

## v0.5.11r-o — 2025-11-11
- Labels/PR 주석 정밀화 + Canary 정책 미세튜닝(o-round)

## v0.5.11t-1 — 2025-11-11
- 시뮬레이터 분산/신뢰구간 + Heatmap 상위 가중 하이라이트 + 카나리 실측 Δ ↔ 오프라인 예측 Δ 정합성 리포트

## v0.5.11t-3 — 2025-11-11
- Calibrated-Δ 기반 자동 승격 임계 재조정 + posterior drift 모니터 + Cards Stream ETag-Delta/버킷 통합

## v0.5.11t-4 — 2025-11-11
- Autotune 안전장치(바운드·slew·롤백) + Drift SLO 게이트 연계 + 버킷 explain 가시화

## v0.5.11t-6 — 2025-11-11
- Risk Governor(다중 신호 융합) + Error-Budget Burn-rate 게이트 + Shadow Sampler(부하 적응형) + 경보/플레이북 코멘트 확장 + 프로메테우스 계측 + CI 게이트 연동


## v0.0.1 — 2025-01-01
- 

## v0.0.2 — 2025-02-02
- sum

## v0.0.3 — 2025-03-03
- e2e

