<!--
version: v0.4.3
date: 2025-11-05
status: locked
summary: Gate-W: Policies & ABAC · Data Boundaries · Masking/Tokenization · Residency (No-Gemini)
-->













































# DecisionOS‑Lite Tech Spec (SSoT)

본 파일은 TechSpec의 단일 진실원본(SSoT)입니다. 구현 세부는 상위 문서 `docs/TechSpec.md`와 동치이며, 버전/날짜/상태는 본 헤더를 기준으로 운영합니다.

- 참조: docs/TechSpec.md




<!-- AUTOGEN:BEGIN:Open Issues -->
- Gate‑C: 도커 패키징, 커넥터 v1, 관측성 확장, Runbook/롤백 문서
- Metrics 엔드포인트 확장(p95/error_rate/req_count)
- Backup/Restore/Manifest 회전 프로시저 문서화
<!-- AUTOGEN:END:Open Issues -->

<!-- AUTOGEN:BEGIN:Security Controls -->
(툴이 이 영역을 관리합니다)
- AES at-rest(Fernet) 키 적용 경로 문서화
- API Key + RBAC 3계층
- DLP/CSV 제한
- Consent DDL 및 감사
- API Key 필수 + RBAC 3계층(admin/agent/auditor)
- OAuth2(+MFA 옵션) 개발 토큰 엔드포인트 문서화
- DLP/마스킹(주민/계좌/연락처), CSV Export 제한 고지
- Consent API(/grant|/revoke|/list) + 감사 로그
- OPENAI_API_KEY 미설정 시 모든 추론 경로 local 고정
- 리포트 산출 경로에 DLP/익명화 필수 적용
- .env.sample 제공, 비밀은 로컬 .env로만
- Ingest 시 consent 검사 및 DLQ 처리 원칙 명시
추가 통제(고객 PoV):
- IP Allowlist(nginx/middleware) — tenant.yaml의 ip_allowlist 반영
- Secrets Handling — secrets/ 볼륨 마운트(읽기전용), .env.client만 참조
- Lineage — consent_snapshot + decision_input_hash 함께 보관
<!-- AUTOGEN:END:Security Controls -->


<!-- AUTOGEN:BEGIN:Tenancy & Config -->
싱글 테넌트(고객별 분리) v0.1.7:
- tenant.yaml: {tenant_id, name, ip_allowlist, rbac_map, connectors, budgets}
- 구성 주입: X-Tenant-ID 헤더 또는 /t/{tenant}/ 경로 프리픽스
- 암호/키: filesystem keystore(mounted secrets/, mode 0400)
- 예산: budgets:{max_cost_usd, hard_timeout_ms, retries}
- 감사: audit.ndjson에 tenant_id 필수 포함
<!-- AUTOGEN:END:Tenancy & Config -->

<!-- AUTOGEN:BEGIN:Interfaces -->
API:
- GET /api/v1/catalog/assets?type=&domain=&tag=
- GET /api/v1/catalog/datasets/{id}
- GET /api/v1/search?q=&scope=asset|dataset|field
- GET /api/v1/lineage/graph?dataset=&depth=
- GET /api/v1/lineage/impact?dataset=&field?=
- POST /api/v1/products/register {product.yaml}
- POST /api/v1/products/publish {name, version}
- GET /api/v1/products/list
CLI(dosctl): `catalog add|ls|show`, `search`, `lineage graph|impact`, `product register|publish|list`
<!-- AUTOGEN:END:Interfaces -->

<!-- AUTOGEN:BEGIN:SLO & KPIs -->
PoV 성공 기준(Gate‑D):
- 운영: 가동시간 99.5%+ (PoV 기간), /health 에러율 <1%
- 성능: /decide p95 < 800ms(모델 미호출), 오류율 < 1%
- 데이터: 초기 적재 ≥ 10k rows, DLQ < 2%
- 품질: Reality‑Seal 4게이트 유지, 리딩KPI 2/3 충족(2주 관찰)
<!-- AUTOGEN:END:SLO & KPIs -->

<!-- AUTOGEN:BEGIN:Evidence Binder -->
보안/운영 증빙 바인더(v0.1.7):
- logs/: 구조화 로그 샘플 + 회전 설정
- reports/: Reality‑Seal, rule coverage, ingest summary
- screenshots/: /metrics, /consent 호출, RBAC/401 캡처
- runbooks/: runbook_pov.md, rollback.md
- manifests/: 월간 manifest + 해시 검증 출력
<!-- AUTOGEN:END:Evidence Binder -->

<!-- AUTOGEN:BEGIN:Pricing & Packaging -->
초기 패키지(v0.1.8):
- Plan Basic(PoV): 월 정액 30만원 + 과금건당 20원(/decide 성공건)
- Add‑on: OpenAI 경로 사용 시 실제 비용 + 10% 핸들링(옵션)
- Seat: agent 5명 포함, 초과 seat/월 1만원
- SLA(초안): PoV 기간 가용성 99.0%, p95<800ms(모델 미호출 경로)
- 캡/버짓: tenant.yaml budgets로 제어(초과 시 폴백 또는 차단)
<!-- AUTOGEN:END:Pricing & Packaging -->

<!-- AUTOGEN:BEGIN:Entitlements -->
권한/기능 할당(tenant scope):
- feature_flags: {simulate, decide, explain, metrics, consent, ingest, billing}
- rate_limits: {rps, rpm, daily_caps}
- budgets: {max_cost_usd, hard_timeout_ms, retries}
<!-- AUTOGEN:END:Entitlements -->

<!-- AUTOGEN:BEGIN:Metering & Billing -->
계량/청구 아키텍처:
- usage_events: {ts, tenant_id, event, key, value, attrs(json)}
- events: decide.ok, decide.err, model.spend_usd, ingest.row_ok, ingest.row_err, seat.active
- aggregator: 일/월 집계 → usage_summary{tenant, period, metrics}
- billing_engine: KRW 기준, VAT 10%, 할인/크레딧/프로레이션 지원(초안), 인보이스 PDF 생성
- 결제: 수기 송장(계좌이체) — 웹훅은 알림용(HMAC)
<!-- AUTOGEN:END:Metering & Billing -->

<!-- AUTOGEN:BEGIN:Multi-Region Lite -->
Active‑Passive(초기) 구성 v0.1.9:
- 복제: primary→standby(지역 B), RPO 5m / RTO 60m 목표
- 승격: scripts/failover_promote.sh(수동), 복귀: failback_prepare.sh
- 라우팅: apps/region/router.py가 region 선호/폴백 처리
- 관측성: /global/metrics에 region 라벨/에러버짓 노출
<!-- AUTOGEN:END:Multi-Region Lite -->

<!-- AUTOGEN:BEGIN:Tenant Isolation (RLS) -->
테넌트 분리 강제(RLS + 미들웨어):
- DB: scripts/rls_apply.sql로 정책 적용, rls_verify.sql로 교차 접근 차단 검증
- Gateway: tenant_scope 미들웨어에서 X‑Tenant‑ID 강제/검증
- 감사/증빙: 교차 접근 테스트 시나리오/캡처 리포지터리 보관
<!-- AUTOGEN:END:Tenant Isolation (RLS) -->

<!-- AUTOGEN:BEGIN:Probes -->
프로브(v0.2.0):
- /healthz: 종합 헬스(의존성 가중치 적용)
- /readyz: 트래픽 수신 가능 여부(디그레이드 게이트 반영)
- /livez: 프로세스 생존 여부(경량)
- 디그레이드 훅: apps/region/degrade.py — 의존성별 차단/완화 정책
<!-- AUTOGEN:END:Probes -->

<!-- AUTOGEN:BEGIN:Auto‑Failover -->
자동 Failover(v0.2.0):
- Watcher/Promoter: apps/region/auto_failover.py (promote/fence 시나리오)
- 스크립트: scripts/promote_standby.sh, scripts/fence_old_primary.sh
- 목표: RTO ≤ 20m, split‑brain 0, 라우터 플래그 동기화
<!-- AUTOGEN:END:Auto‑Failover -->

<!-- AUTOGEN:BEGIN:SLO & Error Budgets -->
에러버짓 정책(v0.2.0):
- 소진 50%: 변경 동결, 80%: 카나리 롤백, 100%: 릴리스 금지
- /decide p95<800ms(모델 미호출), 오류율<1% 준수
<!-- AUTOGEN:END:SLO & Error Budgets -->

<!-- AUTOGEN:BEGIN:Canary -->
카나리 롤아웃(v0.2.0):
- 분배: percent/tenant 기반(1→3→10→25→100)
- 임계치 초과 시 자동 롤백 훅(Feature Flags 연동)
- Admin API: /api/v1/admin/canary/*
<!-- AUTOGEN:END:Canary -->

<!-- AUTOGEN:BEGIN:Chaos & Drills -->
카오스/DR 드릴(v0.2.0):
- 네트워크/프로세스/Failover 시나리오 스크립트 3종
- 주간/월간 계획 수립 및 리포트 산출(타임라인/로그)
<!-- AUTOGEN:END:Chaos & Drills -->

<!-- AUTOGEN:BEGIN:Observability & Tracing -->
분산추적/관측성(v0.2.1):
- Correlation: X‑Corr‑ID 주입/전파, 요청‑결정‑모델 호출 상관관계 저장
- Sampling: 기본 10%, 오류/슬로우 100%
- Export: traces.ndjson 또는 OTLP(옵션)
- Scrub: pii_scrub_map에 따른 로그/트레이스 필드 스크럽
<!-- AUTOGEN:END:Observability & Tracing -->

<!-- AUTOGEN:BEGIN:Cost Sentry -->
비용 감시(v0.2.1):
- 사전 비용예측 → 예산 검사 → 폴백/차단, 드리프트 ≤1% 목표
- budget_enforcer 미들웨어로 X‑Budget-* 및 tenant budgets 적용
<!-- AUTOGEN:END:Cost Sentry -->

<!-- AUTOGEN:BEGIN:Vendor Abstraction v2 -->
ProviderBase/Registry(v0.2.1):
- adapters: local_v2/openai_v2/mock_v2
- 공통 인터페이스: capabilities/estimate/invoke, 오류 분류/재시도 정책 통일
<!-- AUTOGEN:END:Vendor Abstraction v2 -->

<!-- AUTOGEN:BEGIN:Policy Engine -->
정책엔진 v1(선언형 DSL):
- 액션: allow/deny/require_hitl/route/mask
- 구성: 파일 정책 + 린터 + 시뮬레이터
- 집행 훅: gateway/ingest/executor/export 경로에 적용
<!-- AUTOGEN:END:Policy Engine -->

<!-- AUTOGEN:BEGIN:PII Vault -->
Vault v1:
- 암호화: AES‑256‑GCM 엔벌로프, 키로테이션
- API: seal/unseal/rotate, 토크나이즈
- 연동: consent/RBAC/audit
<!-- AUTOGEN:END:PII Vault -->

<!-- AUTOGEN:BEGIN:HITL -->
Human‑in‑the‑Loop v1:
- 승인/반려 대기열, 사유코드, SLA(95% < 30m), 에스컬레이션
- 경량 UI: web/hitl/index.html(리스트/승인/반려)
<!-- AUTOGEN:END:HITL -->

<!-- AUTOGEN:BEGIN:Enforcement -->
집행/리플레이:
- 미들웨어: policy_enforcer
- 훅: hitl_gate
- 재현: test_policy_hitl_replay로 결정 경로 일치 검증
<!-- AUTOGEN:END:Enforcement -->

<!-- AUTOGEN:BEGIN:Playbooks & Templates -->
운영 플레이북·결정 템플릿(v0.2.3):
- Playbooks: 운영/장애/보안/DR 절차 표준화
- Decision Templates: 계약/규칙/모델/훅 조합의 베이스라인
- Registry: packs/registry에 메타/서명/호환성 관리
<!-- AUTOGEN:END:Playbooks & Templates -->

<!-- AUTOGEN:BEGIN:Domain Packs -->
도메인 팩 표준(v0.2.3):
- 구조: meta.yaml, README, fixtures/, datasets/, signatures/
- 필수 필드: id, name, version, min_os_version, compatibility, checks[]
- 서명/해시: SIGNING.md 절차 준수, 해시·서명 파일 포함
<!-- AUTOGEN:END:Domain Packs -->

<!-- AUTOGEN:BEGIN:Docs Site & Builder -->
문서 사이트(v0.3.0):
- 빌더: mkdocs 기반 정적 사이트, build_docs.py
- 배포: /public/docs 제공(nginx/docs.conf)
- 내비: TechSpec/Plan 자동 반영
<!-- AUTOGEN:END:Docs Site & Builder -->

<!-- AUTOGEN:BEGIN:Trials & Onboarding -->
트라이얼·온보딩(v0.3.0):
- /signup → tenant bootstrap(키 발급, budgets/flags 저장)
- SKU: Sandbox/PoV/Pilot, HITL 옵션
- rate limit/캡, 승인 흐름 문서화
<!-- AUTOGEN:END:Trials & Onboarding -->

<!-- AUTOGEN:BEGIN:Support & Status -->
지원·상태(v0.3.0):
- Status: /status, incidents.json 보존 정책
- Support: 메일 인테이크/트리아지/SLA 계측
- 템플릿: 커뮤니케이션/인시던트 템플릿
<!-- AUTOGEN:END:Support & Status -->

<!-- AUTOGEN:BEGIN:Legal Pack -->
법무팩(v0.3.0):
- ToS/Privacy/DPA 초안(KR/EN)
- DSAR/삭제 플로우, 책임/면책/해지/환불/분쟁 범위 명시
<!-- AUTOGEN:END:Legal Pack -->

<!-- AUTOGEN:BEGIN:Adoption Analytics -->
제품 분석(v0.3.1):
- SDK: 서버/프론트 이벤트 수집, 샘플링/중복 필터
- Ingest: /analytics/events, 유효성 검사/드롭률<0.1%
- API: 퍼널/리텐션/리스크 반환, 기간/플랜/테넌트 필터
- Dashboard: web/analytics/index.html(차트 5종)
<!-- AUTOGEN:END:Adoption Analytics -->

<!-- AUTOGEN:BEGIN:NPS & Feedback -->
NPS/피드백(v0.3.1):
- NPS 라우트, 유효성 검사, 응답률 관리
- Feedback 분류기 v1(rule/키워드), 정확도≥80%(샘플 라벨 기준)
<!-- AUTOGEN:END:NPS & Feedback -->

<!-- AUTOGEN:BEGIN:Roadmap & Backlog -->
로드맵 백로그(v0.3.1):
- Backlog API, RICE 스코어링, 주간 분류 보고서
- 수집→스코어→게이트 배정→진척 관리
<!-- AUTOGEN:END:Roadmap & Backlog -->

<!-- AUTOGEN:BEGIN:Usage‑Pricing v2 -->
사용량 과금 v2(v0.3.2):
- Ratebook: tier/seat/role 단가, 할인/쿠폰, KR VAT 10% 라인 분리
- Proration: 업/다운/취소/재개 시 일할/프로레이션 규칙
- Accuracy: 인보이스↔원천사용량/원가 대조 드리프트 ≤ 1%
<!-- AUTOGEN:END:Usage‑Pricing v2 -->

<!-- AUTOGEN:BEGIN:Entitlements v2 -->
권한/집행 v2(v0.3.2):
- entitlements.yaml: feature/rate_limits/caps/flags
- Enforcement: 초과 시 소프트캡→하드캡, 결제 실패 유예 7일 후 단계적 제한
<!-- AUTOGEN:END:Entitlements v2 -->

<!-- AUTOGEN:BEGIN:Self‑Serve Billing -->
셀프서브(v0.3.2):
- 업/다운/취소/재개, 결제수단 관리, 쿠폰 적용
- 정책: 프로레이션/환불 규칙 적용, RBAC/HMAC 검증
<!-- AUTOGEN:END:Self‑Serve Billing -->

<!-- AUTOGEN:BEGIN:Payments & Dunning -->
결제/던닝(v0.3.2):
- 어댑터: pg_local/stripe_opt, 웹훅(HMAC·멱등)
- 던닝: 0/3/7/10/20일 일정, 알림/락 단계
<!-- AUTOGEN:END:Payments & Dunning -->

<!-- AUTOGEN:BEGIN:Invoicer & Reconciler -->
청구/대조(v0.3.2):
- invoicer: PDF 인보이스 생성, 요약/라인아이템
- reconciler: usage/billing 대조, 드리프트 리포트
<!-- AUTOGEN:END:Invoicer & Reconciler -->

<!-- AUTOGEN:BEGIN:SSO/OIDC -->
OAuth 2.1 + OIDC(v0.3.3):
- Flow: Authorization Code + PKCE, state/nonce 검사
- Keys: JWKS, 키 롤테이션, 토큰 회전/재사용 탐지
- RP-Logout 지원, Introspection(옵션)
<!-- AUTOGEN:END:SSO/OIDC -->

<!-- AUTOGEN:BEGIN:Org & Projects -->
자원 모델(v0.3.3): Org → Project → Env
- 스코프: 결정/정책/팩/볼트/분석은 프로젝트 스코프, 과금은 Org 스코프
- 마이그레이션: org_projects.sql, 기존 리소스 스코프 매핑
<!-- AUTOGEN:END:Org & Projects -->

<!-- AUTOGEN:BEGIN:RBAC -->
세분화 RBAC(v0.3.3):
- roles.yaml↔permissions.yaml 매핑, scope(org/project/env)
- deny 우선, 2인 승인(keys.rotate·vault.unseal)
<!-- AUTOGEN:END:RBAC -->

<!-- AUTOGEN:BEGIN:Audit & Sessions -->
감사/세션(v0.3.3):
- 감사: 해시체인 로그, 액터/스코프/행위/결과 기록
- 세션: 동시세션 제한·위험탐지, JIT 권한승격·정기 접근검토
<!-- AUTOGEN:END:Audit & Sessions -->

<!-- AUTOGEN:BEGIN:Connectors & CDC -->
커넥터/CDC(v0.3.4):
- Connector SDK/Registry, 등록/테스트/실행 API
- CDC: Postgres logical, Kafka consumer, dedupe/idempotency
- 목표: p95 ≤ 5s, 중복 드롭 ≥ 99.99%
<!-- AUTOGEN:END:Connectors & CDC -->

<!-- AUTOGEN:BEGIN:Data Contracts v1 -->
데이터 컨트랙트(v0.3.4):
- schema/validator/compat, 등록/검증/호환성 API
- 위반 레코드 quarantine, 알림/대시보드 연동
<!-- AUTOGEN:END:Data Contracts v1 -->

<!-- AUTOGEN:BEGIN:ETL & Ontology Mapping -->
ETL 파이프라인(v0.3.4):
- cleanse/pii_mask/map_ontology 변환 체인
- 매핑: config/map_ontology.yaml 기반 → DecisionContract 입력 생성
<!-- AUTOGEN:END:ETL & Ontology Mapping -->

<!-- AUTOGEN:BEGIN:Quality Gates -->
품질 게이트(v0.3.4):
- freshness/completeness/distinctness/violation
- SLO 계산 및 대시보드(web/quality)
<!-- AUTOGEN:END:Quality Gates -->

<!-- AUTOGEN:BEGIN:Catalog & Search -->
카탈로그/검색(v0.3.5):
- Registry: 데이터셋/파이프라인/제품 메타 등록·조회
- Indexer: FTS 인덱스, 업데이트 지연 ≤ 5m 목표
- Search: 키워드/필터/스코프(sensitivity/RBAC)
<!-- AUTOGEN:END:Catalog & Search -->

<!-- AUTOGEN:BEGIN:Lineage v2 -->
라인리지 v2(v0.3.5):
- Collector: idempotent 수집, 커버리지≥90%
- Graph: 영향도 계산 p95≤1200ms, override 지원
- APIs: 그래프/임팩트 조회
<!-- AUTOGEN:END:Lineage v2 -->

<!-- AUTOGEN:BEGIN:Data Products -->
제품 기술서(product.yaml): {name, version, owner, input_datasets[], transforms(ref), slas{freshness,quality}, publish{s3_parquet|db_view}, contracts{output_contract}}
배포: product_builder.py(스냅샷 버전), 실패 시 롤백(직전 alias 유지)
소비: /products API·카탈로그 UI(골드 레이어)
<!-- AUTOGEN:END:Data Products -->

<!-- AUTOGEN:BEGIN:Dashboards & UI -->
UI(경량):
- web/catalog/: 검색·필터(도메인/민감도/티어)·자산 상세·스키마 미리보기
- web/lineage/: 그래프 뷰(줌/패닝/하이라이트)·임팩트 패널
- web/products/: 제품 목록·버전·SLA 상태·소비 경로
<!-- AUTOGEN:END:Dashboards & UI -->

<!-- AUTOGEN:BEGIN:SLO & Acceptance -->
Gate-W 성공 기준:
  - 정책 평가 p95 ≤ 30ms, API 오버헤드 ≤ 10%
  - 보호 리소스 커버리지 100%(카탈로그 태그 기반 샘플링 검증)
  - 거주지 위반 0, 교차지역 export는 전부 목적구속/승인 로그 보유
  - RLS/CLS/마스킹/토큰화 e2e 테스트 60+ 전부 통과
  - 정책 번들 롤아웃/롤백 e2e + dry-run 영향분석 증빙
  - Evidence Binder(Security/Policy) 업데이트
<!-- AUTOGEN:END:SLO & Acceptance -->

<!-- AUTOGEN:BEGIN:Observability v2 — Architecture -->
표준 스택:
  - OpenTelemetry SDK/Collector(otlp/http, grpc)
  - Metrics: Prometheus-compatible (pull) + remote-write
  - Traces: otlp → collector → Tempo/Jaeger 호환
  - Logs: JSON 구조화 로그 → collector → Loki 호환
상관관계:
  - trace_id/span_id를 로그·메트릭 라벨에 삽입 (context propagation)
  - corr_id(업무 상관키) → decisions/hitl/billing 등 공통 라벨
오버헤드 목표:
  - 에이전트 도입 후 p95 레이턴시 증가 ≤ 5%, CPU 오버헤드 ≤ 8%
<!-- AUTOGEN:END:Observability v2 — Architecture -->

<!-- AUTOGEN:BEGIN:SLI/SLO Catalog -->
서비스 SLI(대표):
  - API: 성공율(2xx/모든 요청), p95/p99 레이턴시, 스루풋
  - Pipeline: freshness lag, 성공율, 재처리율
  - Catalog/Search: 적중률@10(라벨셋), 검색 p95
  - Guardrails: 차단율, 오탐율, 오버헤드 p95
  - Explain/Audit: 재현성 성공률, 감사 누락 0
  - HITL: first_pick_time p95, resolution_time p95, 재오픈율
  - Billing/Metering: 집계 지연 p95, 정합 오차
SLO 정책:
  - 서비스별 월간 SLO(가용성, 레이턴시, 품질) 정의
  - 에러버짓 계산(1 - SLO) 및 번레이트(5m/1h/6h 윈도우) 측정
  - 번레이트 임계 초과 시 배포 게이팅/카나리 강제
<!-- AUTOGEN:END:SLI/SLO Catalog -->

<!-- AUTOGEN:BEGIN:Error Budget Gating — Release Policy -->
정책:
  - burn_rate > 2.0 (1h) 또는 > 1.0 (6h) → 배포 금지, 롤백 검토
  - P0 알림: burn_rate > 4.0 (1h) → 즉시 카나리 0%로 롤백
  - 예외 승인: oncall + duty_manager 동시 승인 필요
CI/CD 연계:
  - gate job: /api/v1/obs/errorbudget/status?service=
  - 상태: allow|review|block (PR 체크·머지 게이팅)
<!-- AUTOGEN:END:Error Budget Gating — Release Policy -->

<!-- AUTOGEN:BEGIN:Synthetic & Blackbox -->
합성 모니터:
  - /healthz, /readyz, /api smoke, decision e2e stub
블랙박스 프로브:
  - 외부 엔드포인트 가용성/SSL/도메인 만료
목표: 무중단 상시 1분 간격, 경보 억제 룰(3/5 실패 시)
<!-- AUTOGEN:END:Synthetic & Blackbox -->

<!-- AUTOGEN:BEGIN:Interfaces — API/CLI -->
API:
  - POST /api/v1/policies/apply {bundle.tgz}  # 서명·검증, dry-run 옵션
  - GET  /api/v1/policies/eval {subject, action, resource, context}
  - GET  /api/v1/policies/list | GET /api/v1/policies/changes
  - POST /api/v1/policies/approve {policy_id, comment}
  - GET  /api/v1/boundaries/check?dataset=&org_id=
CLI(dosctl):
  - `dosctl policy init|lint|dryrun|apply|rollback`
  - `dosctl policy eval --subject '{"role":"reviewer"}' --action read --resource dataset://loans`
  - `dosctl boundary check --dataset loans_kr --org 123`
<!-- AUTOGEN:END:Interfaces — API/CLI -->

<!-- AUTOGEN:BEGIN:Dashboards & Runbooks -->
대시:
  - /web/obs/overview: RED/USE 메트릭, burn-rate 패널
  - /web/obs/service/<name>: SLI·트레이스·로그 상관
  - /web/ops/oncall: 경보 인박스, 사일런스/승인
런북:
  - P0/P1 절차, 롤백·카나리, 데이터 파이프라인 지연 대응
  - 공통 체크리스트: 최근 배포, 트래픽 급증, 외부 의존성
<!-- AUTOGEN:END:Dashboards & Runbooks -->

<!-- AUTOGEN:BEGIN:Security/Compliance -->
- 기본 거부, 허용은 최소 범위. 모든 예외는 만료/사후감사 필요
- 정책 번들 서명/검증, 배포 전 dry-run + 영향분석
- 로그/트레이스에 policy_id, decision, masked_fields 라벨 필수
- RLS/CLS/Masking 단위 테스트 + 공격 패턴 회귀(예: always-true bypass)
- 데이터 경계 위반 감지 → 자동 차단 + P0 알림(Gate-T 경로)
<!-- AUTOGEN:END:Security/Compliance -->

<!-- AUTOGEN:BEGIN:Payments — Architecture -->
목표:
  - Gate-S의 인보이스/사용량을 실제 결제로 연결
  - 다중 PG 어댑터, 안전한 웹훅, 정산/대사, 환불·조정
구성:
  - adapters/: pg별 모듈(토큰화, auth/capture/refund/void, webhooks)
  - payments_core/: 결제 세션, 결제 의도, 영수증, 결제 상태머신
  - settlement/: 정산 배치, 대사 엔진(내부 원장 vs PG 정산 파일)
  - taxes/: VAT/세율 룰, 인보이스 라인별 세금 계산 훅
  - disputes/: 차지백/분쟁 수신·응답 스텁
통화/지역:
  - 기본 KRW, 멀티통화 설계(ISO-4217) + 환율 스냅샷 테이블
<!-- AUTOGEN:END:Payments — Architecture -->

<!-- AUTOGEN:BEGIN:PG Adapters & Flows -->
표준 인터페이스(IPayAdapter):
  - create_payment_intent(amount, currency, customer_ref, meta)
  - confirm/authorize(intent_id, payment_method)
  - capture(charge_id, amount?) / void(intent_id)
  - refund(charge_id, amount?, reason)
  - webhook_verify(headers, payload) → event
제공 어댑터(초기):
  - manual_stub(테스트), stripe_stub(맵핑), generic_pg(서명검증/웹훅 공통)
상태머신:
  - intent: created → authorized → captured → settled
  - 실패: requires_action(3DS 등), canceled, charge_failed, refund_pending → refunded
웹훅:
  - events: payment_succeeded/failed, refund_succeeded/failed, chargeback_open/closed
  - 재시도: idempotency_key·리플레이 방지 해시
<!-- AUTOGEN:END:PG Adapters & Flows -->

<!-- AUTOGEN:BEGIN:KYC / AML — Collection & Verification -->
대상:
  - 개인고객: 이름, 생년월일, 이메일/전화, 신분증 스캔(스텁), 셀피(옵션)
  - 사업자: 상호/사업자번호, 대표자, 사업자등록증(스캔), 통신판매업번호(옵션)
프로세스:
  - risk_tier 평가(low/med/high) → 요구 서류 다름
  - 검증: 외부 KYC provider 스텁(adapter_kyc_stub) + 수동 검토(HITL queue)
  - 결과: verified|needs_more|rejected, 유효기간 및 재검증 주기(예: 12개월)
보존/보안:
  - 원본은 암호화 저장(AES-256), 썸네일/PII 마스킹, 접근 RBAC(billing_admin|auditor)
  - 삭제요청은 보존정책 예외 저장소로 이관(감사 링크 유지)
<!-- AUTOGEN:END:KYC / AML — Collection & Verification -->

<!-- AUTOGEN:BEGIN:Settlement & Reconciliation -->
원장:
  - ledger_txns{ id, org_id, invoice_id?, charge_id?, type[charge|refund|fee|payout],
                 amount, currency, pg, status[pending|posted], ts }
정산:
  - settlement_batches{ id, pg, period, file_uri, imported_at }
  - 대사(recon): ledger vs settlement 파일 매칭 → 불일치 보고서(diff)
수수료:
  - pg_fee, fx_fee, 플랫폼 수수료 라인 분리 → margin 계산과 연동(Gate-S)
<!-- AUTOGEN:END:Settlement & Reconciliation -->

<!-- AUTOGEN:BEGIN:Taxes & Invoicing -->
VAT/세금:
  - region_rules.yaml: 국가/지역별 세율/면세/과세구분
  - invoice_lines에 tax_rate/tax_amount 계산/표기, 영수증에도 반영
영수증:
  - receipts{ id, charge_id, org_id, total, tax_amount, issued_at, pdf_uri, json_uri }
<!-- AUTOGEN:END:Taxes & Invoicing -->

<!-- AUTOGEN:BEGIN:Interfaces — API/CLI/Webhooks -->
API:
  - POST /api/v1/payments/intent {org_id, amount, currency, customer_ref}
  - POST /api/v1/payments/confirm {intent_id, payment_method}
  - POST /api/v1/payments/capture {charge_id, amount?}
  - POST /api/v1/payments/refund {charge_id, amount?, reason}
  - GET  /api/v1/payments/charges/:id | GET /api/v1/payments/receipts/:id
  - POST /api/v1/kyc/submit {org_id, type, docs[]}
  - GET  /api/v1/kyc/status?org_id=
  - POST /api/v1/webhooks/pg/{adapter}  # 서명검증
CLI(dosctl):
  - `dosctl pay intent --org <id> --amount 100000 --ccy KRW`
  - `dosctl pay confirm --intent <id> --pm tok_test`
  - `dosctl pay refund --charge <id> --amount 50000`
  - `dosctl kyc submit --org <id> --type business --docs ...`
  - `dosctl kyc status --org <id>`
Webhooks(ours→partners):
  - billing.invoice.issued, payment.charge.succeeded, refund.processed, kyc.updated
<!-- AUTOGEN:END:Interfaces — API/CLI/Webhooks -->

<!-- AUTOGEN:BEGIN:Security / Compliance -->
- 카드 데이터 비저장(토큰만 저장), 웹훅 서명검증 필수, 재생공격 방지
- PII/문서 암호화, 접근 로깅, 7년 보존, 감사 해시체인 링크(Gate-Q)
- 차지백 알림 수신 → HITL 케이스 자동 생성(Gate-R)
- 권한: billing_admin, finance_ops, auditor 전용 API 분리
<!-- AUTOGEN:END:Security / Compliance -->

<!-- AUTOGEN:BEGIN:Policy Architecture — PDP/PEP & ABAC -->
목적: 모델/벤더 중립의 정책 계층 확립. '기본 거부(deny-by-default)' 원칙.
구성:
  - PDP(Policy Decision Point): 정책 평가 엔진(abac_eval) — Cedar-like 규칙문법
  - PEP(Policy Enforcement Point): API Gateway/Router/SQL/RPC 미들웨어
  - PAP(Policy Admin Point): 정책 저장소(policy_store), 버전/승인 워크플로
  - PIP(Policy Info Point): 속성 공급자(tenant/org/role, data tags, residency, purpose)
ABAC 핵심 속성:
  - Subject: role, clearance, skills, org_plan, region, mfa_level
  - Resource: dataset.classification, data.tags[], residency, lineage_path
  - Action: read/write/export/run_decision/admin
  - Context: time, network_zone, evidence_required, purpose(binding)
<!-- AUTOGEN:END:Policy Architecture — PDP/PEP & ABAC -->

<!-- AUTOGEN:BEGIN:Policy Language — Cedar-lite (v1) -->
문법(요지):
  permit(action, subject, resource)
    when { subject.role in ["owner","admin"] && resource.classification != "PII-S" }
    unless { context.network_zone == "public" && action == "export" }
기능: allow/deny, 조건식(and/or/not, in), 속성 비교, 리스트 교차, 시간/지역, 목적구속(purpose-binding)
버전: policy@semver + change log + 서명(hash-chain)
<!-- AUTOGEN:END:Policy Language — Cedar-lite (v1) -->

<!-- AUTOGEN:BEGIN:Data Boundaries & Residency -->
데이터 경계:
  - 경계 단위: region(KR, JP, EU, US), org boundary, project boundary
  - 카탈로그 태깅: dataset.tags[residency, pii, finance, restricted]
거주지(Residency):
  - residency=="KR" 데이터는 KR 리전 저장/처리 의무
  - cross-region 전송은 policy 'allow_with_controls' + DPA 레코드 요구
Export 정책:
  - export는 항상 purpose, ticket_id, retention_days 요구
  - 고위험(restricted, PII-S)은 HITL 승인 + 워터마크 + 만료토큰
<!-- AUTOGEN:END:Data Boundaries & Residency -->

<!-- AUTOGEN:BEGIN:RLS/CLS · Dynamic Masking · Tokenization -->
DB 보안:
  - RLS(Row-Level Security): org_id, residency, clearance 기준
  - CLS(Column-Level Security): classification별 select 허용/차단
  - Dynamic Masking: 전화/주민번호/계좌 — show_last4(), hash_email()
  - Tokenization: format-preserving token(FPE)로 저장, on-demand detokenize(권한 필요)
API 계층:
  - 결과셋 후처리 마스킹(PEP) + 감사 라벨(trace_id, policy_id)
<!-- AUTOGEN:END:RLS/CLS · Dynamic Masking · Tokenization -->

<!-- AUTOGEN:BEGIN:Consent & Purpose Binding -->
동의/목적 구속:
  - consents{org_id, subject, purpose, scope, valid_until}
  - policy에서 purpose 필수. 미충족 시 deny 또는 HITL 요구
감사:
  - 모든 허가 결정에 policy_id/consent_id 링크, Evidence Binder(Security)에 보관
<!-- AUTOGEN:END:Consent & Purpose Binding -->

<!-- AUTOGEN:BEGIN:Marketplace/Ext 연동(게이트-V) -->
확장/플러그인 권한:
  - ext.yaml의 scopes를 정책에 매핑(최소권한)
  - 네트워크 egress는 policy로 제한(allowlist)
  - break-glass: 시간제한 승격(<= 2h), 사후 리뷰·감사필수
<!-- AUTOGEN:END:Marketplace/Ext 연동(게이트-V) -->
