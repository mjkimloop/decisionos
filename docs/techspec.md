<!--
version: v0.5.11gfedcbaccbabaaaaa
date: 2025-11-10
status: locked
summary: slo.json 스키마 + Evidence 비교 Judge(단일) + Multi-Judge(2/3 합의) + RBAC Hook + CLI
-->










<!-- AUTOGEN:BEGIN:HITL Ops v2 — Concepts & Roles -->
목적: 규칙/모델/가드레일 이후 '사람 검토'가 필요한 결정을 안전·신속·감사가능하게 처리.
주요 객체:
  - Case: 결정/리드/신청 단위의 검토 컨테이너
  - Task: Case 하위의 수행 단위(검토, 자료요청, 콜백 등)
  - Queue: 우선순위·스킬·조직 기준의 작업 대기열
  - Action: approve|deny|request_docs|escalate|comment|close
  - Appeal: 최초 결정에 대한 이의 제기 흐름(상위 심사)
역할/권한(RBAC 연계):
  - reviewer, senior_reviewer, qa, ops_admin, auditor
연계:
  - Guardrails v2(Gate-Q) review 모드 → Queue 적재
  - DecisionContract → Case 초기 컨텍스트
  - Audit Hash-chain → Case/Action 이벤트 서명/연결
<!-- AUTOGEN:END:HITL Ops v2 — Concepts & Roles -->

<!-- AUTOGEN:BEGIN:Data Model — Case/Task/Appeal -->
테이블(요지):
  cases{ id, org_id, project_id, decision_id, status[open|pending|awaiting_docs|escalated|closed],
         priority[p0..p3], reason_codes[], sla_due_at, owner_user_id?, created_at, updated_at }
  tasks{ id, case_id, kind[review|qa|request_docs|call|verify], status[ready|in_progress|blocked|done],
         assignee_user_id?, queue_id, due_at, payload_json, created_at, updated_at }
  appeals{ id, case_id, level[int], status[submitted|in_review|resolved|rejected],
           submitted_by, resolution, created_at, updated_at }
  case_notes{ id, case_id, author, body_md, redacted?:bool, created_at }
  attachments{ id, case_id, task_id?, name, uri, sha256, size, mime, scanned[ok|flagged], created_at }
  queues{ id, name, routing_rule, skills[], sla_policy_id }
  sla_policies{ id, name, p95_hours, breach_actions[notify|auto_escalate] }
제약:
  - attachments는 업로드시 AV 스캔·PII 스크럽 필수
  - case_notes.redacted=true 시 원본은 보관소 암호화, UI는 마스킹
<!-- AUTOGEN:END:Data Model — Case/Task/Appeal -->

<!-- AUTOGEN:BEGIN:Routing & SLA -->
라우팅:
  - 규칙: priority, org/project, product, reason_code, risk_score, availability
  - 알고리즘: weighted round-robin + skill match + fairness(최대 동시건수)
  - 오버플로우: 대기열 초과 시 burst_queue → senior_queue
SLA:
  - 기본: P0=4h, P1=24h, P2=48h, P3=72h (조정 가능)
  - 측정: first_pick_time, resolution_time, re-open_rate
  - 위반: 자동 notify → escalate → breach_action 실행
<!-- AUTOGEN:END:Routing & SLA -->

<!-- AUTOGEN:BEGIN:Dispute/Appeals Flow -->
단계:
  1) 고객/파트너가 이의 제출 → appeal level 1 생성
  2) senior_reviewer 전담 큐로 라우팅
  3) 추가 증빙 수집(attachments/notes) → 재평가
  4) 결과: uphold(유지)/overturn(번복)/partial(조건부) + 설명서 재발급
정책:
  - 동일 reviewer가 아닌 상위 reviewer 배정
  - 최대 level=2 (정책에 따라 확장)
  - 모든 변경은 audit hash-chain에 서명
<!-- AUTOGEN:END:Dispute/Appeals Flow -->

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

<!-- AUTOGEN:BEGIN:UI — Inbox/Case/Appeals -->
web/hitl/:
  - Inbox: 개인 작업함, 대기열, 필터(우선순위/도메인/상태)
  - Case View: 컨텍스트(입력, Reason Codes, Evidence Pack), 액션버튼, 체크리스트, 노트/첨부
  - Appeals View: 제출 사유, 타임라인, 새 설명서 미리보기, 결론 발행
  - 품질: 키보드 단축키, 대량 작업(approve/deny) 보호(2-step)
<!-- AUTOGEN:END:UI — Inbox/Case/Appeals -->

<!-- AUTOGEN:BEGIN:Security/Compliance -->
- 기본 거부, 허용은 최소 범위. 모든 예외는 만료/사후감사 필요
- 정책 번들 서명/검증, 배포 전 dry-run + 영향분석
- 로그/트레이스에 policy_id, decision, masked_fields 라벨 필수
- RLS/CLS/Masking 단위 테스트 + 공격 패턴 회귀(예: always-true bypass)
- 데이터 경계 위반 감지 → 자동 차단 + P0 알림(Gate-T 경로)
<!-- AUTOGEN:END:Security/Compliance -->

<!-- AUTOGEN:BEGIN:SLO & Acceptance -->
Gate-AH 성공 기준:
  - Feature parity: 수치 Δ≤0.5%p, 범주 JSD≤0.02(@10k) — 실패시 배포 중지
  - Train-Serve skew: PSI≤0.2 유지, 위반시 경보/카나리 동결
  - Shadow→Canary 승급: 에러Δ≤1.0%p, p95 지연 Δ≤+10%, 안전사건 0건
  - 실패시 자동 롤백 TTR ≤ 10분, 롤백 재현 로그 100%
  - Registry 재현성: 재서빙/재학습 성공률 100%
  - Evidence Binder(ModelOps) 업데이트
<!-- AUTOGEN:END:SLO & Acceptance -->

<!-- AUTOGEN:BEGIN:Tenant/Org · Project · RBAC -->
모델:
  orgs{ id, name, plan[free|pro|enterprise], status[active|suspended], created_at }
  projects{ id, org_id, name, tags[], created_at }
  users{ id, email, name, status, created_at }
  memberships{ user_id, org_id, role[owner|admin|member|auditor] }
  project_members{ user_id, project_id, role[manager|contributor|viewer] }
정책:
  - org 스코프 RBAC + project 세분화
  - 모든 API는 org/project 스코프 필수. 로그/감사에 스코프 포함
<!-- AUTOGEN:END:Tenant/Org · Project · RBAC -->

<!-- AUTOGEN:BEGIN:Entitlements · Plans · Quotas -->
plans.yaml:
  free:
    entitlements: [catalog.read, lineage.read, decisions.run.basic]
    quotas: { decisions_per_day: 200, storage_gb: 5, connectors: 2 }
    rate_card: { decision_call: 0, storage_gb_month: 0 }
  pro:
    entitlements: [catalog.*, lineage.*, decisions.run, pipelines.run, guardrails.v2, hitl.basic]
    quotas: { decisions_per_day: 5000, storage_gb: 200, connectors: 10 }
    rate_card: { decision_call: 0.002, storage_gb_month: 0.08 }
  enterprise:
    entitlements: ["*"]
    quotas: { decisions_per_day: 200000, storage_gb: 2000, connectors: 100 }
    rate_card: { decision_call: negotiated, storage_gb_month: 0.06 }
enforcement:
  - API 게이트 전/후에 entitlement 체크 → 403/usage_exceeded
  - quota 카운터는 슬라이딩 윈도우(1d/1m), soft/hard limit 구분
<!-- AUTOGEN:END:Entitlements · Plans · Quotas -->

<!-- AUTOGEN:BEGIN:Usage Metering -->
이벤트 스키마(meter_events):
  { id, org_id, project_id, ts, metric, value, unit, corr_id, source, meta_json }
핵심 메트릭:
  - decision_calls (count)
  - data_scanned_bytes (bytes)
  - storage_gb_hours (gbh)
  - compute_seconds (sec)
  - api_requests (count)
수집:
  - SDK/게이트웨이 훅(동기 최소화), 배치 집계기(5m)
정합성:
  - idempotency(corr_id), 해시체크, 드리프트 감시(±1.5% 알림)
집계 테이블:
  usage_daily{ org_id, project_id, metric, date, value }
  usage_monthly{ org_id, metric, yyyymm, value, last_closed_at }
<!-- AUTOGEN:END:Usage Metering -->

<!-- AUTOGEN:BEGIN:Billing · Invoicing · Revenue Logs -->
빌링 흐름(월말 청구, 프로레이트 지원):
  1) rate_card × usage_monthly → amount 계산(세금/수수료는 외부 PG 연동 시 확장)
  2) invoice{ id, org_id, period, subtotal, tax, total, status[draft|issued|paid|void] }
  3) invoice_lines{ invoice_id, metric, quantity, unit_price, amount, meta }
  4) revenue_logs(append-only): 결제/조정 이력
결제 어댑터:
  - adapters/{manual_stub.py, stripe_stub.py} (실 PG는 차기 Gate-U)
증빙:
  - /billing/invoices/: PDF/JSON 생성, 감사 체인 링크
<!-- AUTOGEN:END:Billing · Invoicing · Revenue Logs -->

<!-- AUTOGEN:BEGIN:Cost Guard (Cloud/Model Cost → Margin) -->
원가 입력(cost_feeds):
  - model_costs{ model_id, unit, cost_per_unit }  # 예: tokens, decision_call
  - infra_costs{ resource, unit, cost_per_unit }  # 예: s3_gb_month, compute_sec
마진 계산:
  - margin_monthly = billed_total - (alloc_model_cost + alloc_infra_cost)
경보:
  - org/프로젝트 별 마진<목표치(예: 40%) 시 알림/자동 조정 제안(요금제/쿼터)
대시:
  - /ops/cost-guard: 손익 트리(조직/제품/메트릭)
<!-- AUTOGEN:END:Cost Guard (Cloud/Model Cost → Margin) -->

<!-- AUTOGEN:BEGIN:Open Issues -->
- Gate‑C: 도커 패키징, 커넥터 v1, 관측성 확장, Runbook/롤백 문서
- Metrics 엔드포인트 확장(p95/error_rate/req_count)
- Backup/Restore/Manifest 회전 프로시저 문서화
- Switchboard 실벤더 2종 채택(모의→실제) — v0.2.0 후보
- Consent API 스키마 확장(주체/범위/유효기간) — v0.2.0 후보
- Rule Linter 커버리지 리포트 시각화 — v0.2.0 후보
- Switchboard 실벤더 2종 채택(모의→실제) — v0.2.0 후보
- Consent API 스키마 확장(주체/범위/유효기간) — v0.2.0 후보
- Rule Linter 커버리지 리포트 시각화 — v0.2.0 후보
<!-- AUTOGEN:END:Open Issues -->

<!-- AUTOGEN:BEGIN:Security Controls -->
최소 통제 6/6 (v0.1.3 기준) — 구현 + 문서화
1) at-rest 암호화(AES-256 키랩퍼 스텁) — audit.ndjson, export/* 마스킹
2) in-transit 보호(TLS dev 예외, API Key 필수) — prod는 TLS 강제
3) RBAC 3계층(admin/agent/auditor) — 라우트별 접근표 첨부
4) OAuth2(+MFA 옵션) dev 토큰 발급 — /auth/token(mock)
5) DLP/마스킹(주민/계좌/연락처), CSV export 제한 — 패턴/샘플 포함
6) 동의/철회/파기 API + 감사 로그 — /api/v1/consent/*
추가 통제(고객 PoV):
- IP Allowlist(nginx/middleware) — tenant.yaml의 ip_allowlist 반영
- Secrets Handling — secrets/ 볼륨 마운트(읽기전용), .env.client만 참조
- Lineage — consent_snapshot + decision_input_hash 함께 보관
청구 보안/컴플라이언스 추가:
- PII 최소화: 인보이스에 개인식별정보 금지(회사명/담당 성만)
- 보존: usage_events 90일, summary 1년(드라이런)
- 무결성: 인보이스 해시/서명, 웹훅 HMAC(shared secret)
- 멱등성: idempotency‑key 필수, 중복 요청 차단
보호 조치:
- /healthz는 내부 전용, /readyz는 IP allowlist, /livez와 /admin/*는 RBAC+HMAC 옵션
- 카오스/드릴 엔드포인트는 로컬 인증 토큰 별도
<!-- AUTOGEN:END:Security Controls -->


<!-- AUTOGEN:BEGIN:Deployment Profiles -->
배포 프로파일(v0.1.6):
- local-dev: uvicorn 직부팅, sqlite/postgres(dev), OPENAI 비활성(기본)
- pov-singletenant: docker-compose 3컨테이너(gateway, worker, db), audit 볼륨 WORM, 로그 회전
환경변수(필수):
- DOS_ENV (local|pov), API_KEY, DB_URL, LOG_LEVEL
- OPENAI_API_KEY(옵션 — 없으면 local 고정), BUDGET_MAX_USD=0.02, HARD_TIMEOUT_MS=3000
백업/보존: audit.ndjson 일 단위 회전, 월간 manifest, 90일 보존(드라이런)
배포 프로파일 추가(v0.1.9):
- mt-lite: gateway + worker + db(primary) + db(standby) + redis(optional)
- DR 파라미터: RPO=5m(로그 전송), RTO=60m(수동 승격) — PoV 한정 값
<!-- AUTOGEN:END:Deployment Profiles -->


<!-- AUTOGEN:BEGIN:Data Connectors -->
커넥터 v1(ingest→leads):
- CSV: 로컬/업로드 폴더 폴링 → 스키마 매핑 → consent 체크 후 적재
- Google Sheets: 서비스계정(keyfile)로 읽기 전용 → 스키마 매핑
- S3/GCS: prefix 폴링, .csv만 처리 → 실패/성공 큐 분리
공통 규칙: 동의 없는 행 drop, PII 마스킹 후 저장, 실패행 dead-letter 폴더 보관
<!-- AUTOGEN:END:Data Connectors -->


<!-- AUTOGEN:BEGIN:Observability -->
관측성(최소):
- /api/v1/metrics: p95_latency, error_rate, req_count, ingest_lag_sec
- 구조화 로그(NDJSON): 결정/감사/에러 채널 분리, 일 회전
- 알림(선택): ERR_RATE>1% 또는 p95>800ms 10분 지속 시 경고 로그
글로벌 관측성:
- /api/v1/global/metrics: {region:{p95, error_rate, req_count, ingest_lag}, tenants:n}
- 구조화 로그에 region 라벨 추가, 회전/보존 기존 정책 준수
- 에러버짓: p95>800ms 또는 error_rate>1%가 10분 지속 시 경고 이벤트
SLO/버짓 노출:
- /metrics에 error_budget_remaining, canary_active, failover_state 추가
- synthetic check: /probes/synthetic_decide (내부만)
<!-- AUTOGEN:END:Observability -->


<!-- AUTOGEN:BEGIN:Runbook & Rollback -->
PoV Runbook 요약:
1) 배포: docker-compose up -d → /health 확인
2) 시드: anonymize_seed.py → seed.csv → dosctl simulate
3) 스모크: /decide 샘플 3건, /explain 3건, 해시 체인 확인
4) 라우팅: local 기본, OPENAI_API_KEY 설정 시 옵션 경로 검증
5) 롤백: docker-compose down, DB 스냅샷 복구(scripts/restore.sh), manifest 롤백
<!-- AUTOGEN:END:Runbook & Rollback -->


<!-- AUTOGEN:BEGIN:Cost Guardrails -->
비용 가드레일:
- 기본 로컬 우선, openai는 예산 내에서만
- 예산 초과/타임아웃 시 즉시 폴백(local)
- budget 헤더 미설정 시 BUDGET_MAX_USD 적용(기본 0.02)
<!-- AUTOGEN:END:Cost Guardrails -->


<!-- AUTOGEN:BEGIN:Tenancy & Config -->
싱글 테넌트(고객별 분리) v0.1.7:
- tenant.yaml: {tenant_id, name, ip_allowlist, rbac_map, connectors, budgets}
- 구성 주입: X-Tenant-ID 헤더 또는 /t/{tenant}/ 경로 프리픽스
- 암호/키: filesystem keystore(mounted secrets/, mode 0400)
- 예산: budgets:{max_cost_usd, hard_timeout_ms, retries}
- 감사: audit.ndjson에 tenant_id 필수 포함
멀티테넌트 확장(v0.1.9):
- Tenant Directory: tenants/<tenant>/tenant.yaml → {rbac, budgets, connectors, secrets_ref, ip_allowlist}
- Request 스코핑: Header X-Tenant-ID 또는 경로 /api/v1/t/{tenant}/... (둘 다 지원)
- 데이터 스코프: Postgres **RLS(Row-Level Security)** on tenant_id (기본), 필요 시 schema-per-tenant 옵션
- 감사: audit.ndjson 모든 항목에 tenant_id 포함, Evidence Binder 테넌트 분리 보관
<!-- AUTOGEN:END:Tenancy & Config -->


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


<!-- AUTOGEN:BEGIN:Data Partitioning -->
파티셔닝 전략(v0.1.9):
- 기본: 공유 DB + RLS 정책 (POLICY: tenant_id = current_setting('app.tenant_id'))
- 인덱스: (tenant_id, ts) 복합 인덱스 공통 적용
- 선택: 대용량 테넌트는 schema-per-tenant로 승격 (마이그레이션 스크립트 제공)
<!-- AUTOGEN:END:Data Partitioning -->


<!-- AUTOGEN:BEGIN:Routing & Traffic -->
라우팅/트래픽 정책:
- Region‑Aware Gateway: /api/v1/r/{region}/t/{tenant}/... (옵션 prefix)
- 기본: 단일 엔드포인트 + 내부 region 선호 설정(DOS_REGION=ap)
- Failover: primary 타임아웃/장애 시 **패시브 리전**으로 폴백 (쓰기 멈춤, 읽기 전용 허용)
- Rate Limit: tenant별 rpm/rps, region별 예산(budgets.region)
<!-- AUTOGEN:END:Routing & Traffic -->


<!-- AUTOGEN:BEGIN:Disaster Recovery -->
DR/Failover 절차(v0.1.9):
1) 백업: base backup 일 1회 + WAL/작업 로그 5분 회전
2) 검증: scripts/verify_replica.sh 해시/LSN 비교
3) 장애: scripts/failover_promote.sh(standby 승격) → apps/region/router failover flag 갱신
4) 복귀: scripts/failback_prepare.sh → 재동기화 후 원복
5) 감사: manifests/region/*.json에 타임라인 기록
<!-- AUTOGEN:END:Disaster Recovery -->


<!-- AUTOGEN:BEGIN:Health Probes & Degradation -->
프로브 정의(v0.2.0):
- /healthz (liveness): 프로세스 생존·핵심 스레드 동작
- /readyz (readiness): 필수 의존성(DB 읽기, router state, config load)
- /livez  (readiness+write): 쓰기 경로 허용 여부(승격·락 상태 반영)
디그레이드 정책:
- DB 장애 시: 읽기 전용 모드, /decide 차단, /simulate 허용
- switchboard 장애: local 폴백 강제, openai 경로 차단
- failover 중: /livez=fail, /readyz=ok(읽기는 허용)
<!-- AUTOGEN:END:Health Probes & Degradation -->


<!-- AUTOGEN:BEGIN:Auto‑Failover Controller -->
구성요소:
- watcher: DB health/replication lag 모니터 (5s 주기)
- quorum(옵션): file‑based lock 또는 redis(옵션)로 단일 승격 보장
- promoter: standby 승격(promote) + write‑block 구 노드(펜싱)
- router sync: region/router failover flag 업데이트
보호장치:
- split‑brain 방지: 승격 전 old‑primary 접근 차단 목록 반영 + connection kill
- post‑promote 검증: LSN/해시 일치 확인 후 /livez 오픈
<!-- AUTOGEN:END:Auto‑Failover Controller -->


<!-- AUTOGEN:BEGIN:Error Budget Policy -->
에러버짓 정책(v0.2.0):
- SLO: /decide p95<800ms, 오류율<1%, 가용성 99.5%/월
- 버짓 계산: (1‑SLO)×기간 분으로 산정, /api/v1/metrics에 노출
- 소진 규칙: 버짓 50% 초과→릴리즈 동결, 80% 초과→기능 플래그 롤백, 100%→변경동결+사후분석
<!-- AUTOGEN:END:Error Budget Policy -->


<!-- AUTOGEN:BEGIN:Canary & Progressive Delivery -->
카나리 전략:
- 대상: tenant 또는 percent 기반(1%→5%→25%→100%)
- 제어: feature_flags.canary:{enabled, percent, tenants[]}
- 게이트: 카나리 동안 p95/오류율/에러버짓 감시, 임계치 초과 시 자동 롤백
- 인터페이스: POST /api/v1/admin/canary {enabled, percent, tenants}
<!-- AUTOGEN:END:Canary & Progressive Delivery -->


<!-- AUTOGEN:BEGIN:Chaos & DR Drills -->
카오스 항목:
- 네트워크 단절/지연(게이트웨이↔DB)
- 프로세스 강제 종료(watcher/promoter)
- region 장애 시나리오(standby만 정상)
주기: PoV 기간 주1회 소규모, 월1회 DR 리허설
스크립트: scripts/chaos_net.sh, scripts/chaos_kill.sh, scripts/drill_failover.sh
<!-- AUTOGEN:END:Chaos & DR Drills -->


<!-- AUTOGEN:BEGIN:Extensibility — Scope & Types -->
확장 유형(v1):
  - Decision Plugin: 규칙/모델 실행 전·후 훅(pre|post), 커스텀 스코어러/피처 계산기
  - Connector Plugin: 신규 데이터 소스/싱크(읽기/쓰기)
  - Policy Hook: 가드레일/정책 평가 커스텀 모듈
  - Webhook: 이벤트 구독(case.opened, decision.made, invoice.issued 등)
  - Embed Widget: 대시/케이스뷰에 삽입 가능한 UI 위젯(read-only 우선)
표준 계약(Manifest ext.yaml):
  name, version(semver), type, entrypoint, permissions(scopes[]),
  resources(cpus, mem_mb, tmp_mb, timeout_ms), network_egress[none|allow_domains[]],
  secrets(required[]), runtime[python-3.11|node-20|wasm], compat{api_min, api_max}
<!-- AUTOGEN:END:Extensibility — Scope & Types -->


<!-- AUTOGEN:BEGIN:Security — Sandbox & Permissions -->
샌드박스:
  - 런타임: WASI/wasmtime 우선, python/node는 파이어크래커 경량VM
  - 파일: 읽기전용 바인드, /tmp만 쓰기, 용량 제한
  - 네트워크: 기본 차단, allowlist 도메인별 승인
  - 시크릿: 런타임 주입(단건 스코프), 환경변수/파일 저장 금지
권한/스코프 예:
  - data.read: 카탈로그/라인리지 조회
  - decisions.run: DecisionContract 호출
  - hitl.write: 케이스/노트/첨부 쓰기
  - billing.read: 사용량/인보이스 조회
서명/신뢰:
  - dev 서명(Self-signed) → staging, org 서명(Org CA) → 내부 배포, platform CA → 마켓 승인
  - ext.tgz + ext.yaml + sig 파일(sha256 + x509) 검증
<!-- AUTOGEN:END:Security — Sandbox & Permissions -->


<!-- AUTOGEN:BEGIN:SDKs & DevEx -->
SDK:
  - sdk/python: decorators(@pre_hook, @post_hook, @feature), client(dos-api)
  - sdk/node: 동일 컨셉
로컬 실행기:
  - ext-run: 샌드박스 에뮬레이터(리소스·네트워크 제한 시뮬레이션)
스캐폴드:
  - `dosctl ext init --type decision --runtime python` → 예제 생성
테스트:
  - 계약·권한·리소스·시간초과·네트워크 제한 단위/통합 테스트
<!-- AUTOGEN:END:SDKs & DevEx -->


<!-- AUTOGEN:BEGIN:Distribution — Registry/Marketplace (Beta) -->
레지스트리:
  - 내부 OCI 호환 레지스트리(artifact: ext:namespace/name:version)
  - 채널: dev, staging, private-beta
승인 플로우:
  - 제출 → 자동 검사(정적분석/권한/크기/라이선스) → 보안 리뷰 → 샌드박스 e2e → 서명 → 게시
마켓(베타, 비공개):
  - web/marketplace: 카드 뷰(이름/권한/지원 도메인), 설치/업데이트 이력
  - 설치는 org owner만, 변경 사항 감사 로그
<!-- AUTOGEN:END:Distribution — Registry/Marketplace (Beta) -->


<!-- AUTOGEN:BEGIN:Lifecycle & APIs -->
설치/업데이트/롤백:
  - install: ext artifact pull → 검증/서명 확인 → 배치 → 활성화
  - update: 호환성 검사(api range) → 트래픽 1% 카나리 → 100%
  - rollback: 이전 해시로 복귀
API:
  - POST /api/v1/ext/install {org_id, artifact_ref}
  - POST /api/v1/ext/enable {org_id, name, version}
  - POST /api/v1/ext/disable {org_id, name}
  - GET  /api/v1/ext/list?org_id=
  - POST /api/v1/webhooks/subscribe {event, target_url, secret?}
  - GET  /api/v1/marketplace/list?channel=private-beta
CLI(dosctl):
  - `dosctl ext init|pack|sign|push|install|enable|disable|ls`
  - `dosctl webhooks add|ls|rm`
  - `dosctl market ls --channel private-beta`
<!-- AUTOGEN:END:Lifecycle & APIs -->


<!-- AUTOGEN:BEGIN:Interfaces — Plugin Contracts -->
Decision Plugin(예):
  def pre_hook(request: DecisionRequest, ctx: Ctx) -> DecisionRequest|Error
  def post_hook(response: DecisionResponse, ctx: Ctx) -> DecisionResponse|Error
Connector Plugin(예):
  class Source:
    def scan(self, since_cursor) -> RecordsPage
  class Sink:
    def write(self, records: list[Record]) -> Result
모든 콜은 ctx.trace_id/corr_id/tenant 스코프 포함, 시간제한 기본 3s
<!-- AUTOGEN:END:Interfaces — Plugin Contracts -->


<!-- AUTOGEN:BEGIN:Observability & Tracing -->
OpenTelemetry 기반 분산추적(v0.2.1):
- SDK: otel-api(내장) + OTLP Exporter(옵션). 외부 수집기 미사용 시 traces.ndjson 로컬 기록
- 상관관계: inbound X-Corr-ID 생성/전파, decision_id/span_link 연계, 로그에 corr_id, span_id 삽입
- 샘플링: 기본 10% 헤드샘플링, 오류/슬로우케이스는 테일샘플링 강제(100%)
- PII 스크럽: 로그/트레이스 필드에 주민·계좌·연락처·주소 패턴 마스킹(apply before export)
- 메트릭 확장: 히스토그램(latency p50/p90/p95/p99), ingest_lag_sec, cost_estimate_ms
- 보존: traces.ndjson 7일, logs 일 회전. Evidence Binder에 대표 트레이스 3건 보관
<!-- AUTOGEN:END:Observability & Tracing -->


<!-- AUTOGEN:BEGIN:Cost Sentry -->
비용 감시/제어(v0.2.1):
- 모델 호출 전 비용예측: provider price_table × tokens_estimate ⇒ expected_usd
- 예산검사: remaining_budget_usd < expected_usd → 폴백(local) 또는 차단(policy)
- 실비 집계: cost_event{ts, tenant_id, provider, route, usd, tokens} 기록, summary와 대조(오차≤1%)
- 알림: 예산 80%/100% 임계치 도달 시 경고 이벤트(로그)
- 구성: tenants/<tenant>/tenant.yaml 내 budgets.{max_cost_usd, hard_timeout_ms, retries}
<!-- AUTOGEN:END:Cost Sentry -->


<!-- AUTOGEN:BEGIN:Vendor Abstraction v2 -->
프로바이더 플러그인 구조(v2):
- ProviderBase: capabilities(), estimate(tokens), invoke(prompt, opts), map_error(e)
- Registry: providers.yaml 로드({name, type, base_url, pricing, limits, features})
- 어댑터: local_v2, openai_v2(실), mock_v2(테스트)
- 오류 분류: {Retryable, RateLimited, BudgetExceeded, InvalidInput, ProviderDown}
- 회복탄력성: 공통 백오프/서킷브레이커/재시도 정책 내장
<!-- AUTOGEN:END:Vendor Abstraction v2 -->


<!-- AUTOGEN:BEGIN:Data Classification -->
데이터 등급 체계(v0.2.2):
- PUBLIC, INTERNAL, CONFIDENTIAL, PII(민감)
- 태깅: 스키마 레벨 label, 필드 레벨 label, 소스별 default
- 처리원칙: PII는 Vault 필수, 로그/트레이스/리포트 출력 금지
<!-- AUTOGEN:END:Data Classification -->


<!-- AUTOGEN:BEGIN:Policy Engine -->
선언형 정책엔진(v0.2.2):
- 정책 타입: access, data, consent, retention, decision, routing, feature
- 정책 DSL(YAML):
  kind: decision | access | data
  version: v1
  match: {tenant, route, labels[], user_role}
  when:  expr(DSL)  # 예: dsr>40 && income<200
  then:  actions[]  # 예: {deny|allow|require_hitl|mask|route:local}
  audit: {reason_code, message}
- 평가 순서: system → tenant → product → route → rule
- 집행 지점: gateway(mw), ingest(pre), executor(pre/post), export(pre)
- 버저닝/검증: 정책 해시/사인, dry-run 모드, 시뮬레이터 포함
<!-- AUTOGEN:END:Policy Engine -->


<!-- AUTOGEN:BEGIN:PII Vault -->
PII 금고(v0.2.2):
- 저장소: table vault_blobs(id, key_id, algo, iv, tag, ciphertext, meta, created_at)
- 암호화: AES-256-GCM(엔벌로프) — master_key(keystore)로 data_key 랩핑/언랩
- 키 저장소: filesystem keystore(secrets/keys/*, 0400), KMS 연동 옵셔널
- 키 로테이션: rotate_keys.sh → rewrap 배치, key_id 버전 관리
- API: seal(subject, field, bytes)->token, unseal(token, scope)->bytes
- 의무사항: 접근 시 consent 검증·RBAC·audit append
- 토크나이즈: vault_token: vt_<hash_prefix> 사용(리포트/로그는 토큰만)
<!-- AUTOGEN:END:PII Vault -->


<!-- AUTOGEN:BEGIN:Human-in-the-Loop (HITL) -->
승인/오버라이드 UI(v0.2.2):
- 역할: agent(요청), reviewer(승인/반려), admin(정책관리)
- 워크플로우: require_hitl 액션 → /hitl/queue 적재 → reviewer가 사유코드 선택 후 승인/반려 → executor 재시도
- SLA: 대기 95%<30m, 최대 24h 타임아웃(자동 반려 또는 escalate)
- 사유코드/가이드: reason_codes.yaml (거절/예외/수동서류)
<!-- AUTOGEN:END:Human-in-the-Loop (HITL) -->


<!-- AUTOGEN:BEGIN:Content Registry -->
레지스트리(v0.2.3):
- 구조: registry/
  - playbooks/<name>/<version>/playbook.yaml
  - templates/decision/<name>/<version>/template.yaml
  - domain_packs/<domain>/<version>/{README.md, datasets/, rules/, playbooks/, templates/}
- 메타스키마: registry/meta.yaml {name, version, domain, owner, license, min_os_version, hash}
- 배포: zip(tar.gz) + 서명(.sig), 해시 검증 필수
- 호환성: min_os_version 불일치 시 import 차단(dry-run 옵션)
<!-- AUTOGEN:END:Content Registry -->


<!-- AUTOGEN:BEGIN:Playbook Spec -->
Playbook YAML 스키마(v0.2.3):
kind: playbook
version: v1
meta: {name, domain, owner, kpis[], risk_level}
trigger: {route: decide|ingest|alert, match:{tenant?, labels?, threshold?}}
inputs: [{name, type, required, source}]
actions:
  - type: policy.apply | hitl.require | notify | route.set | throttle | enrich
    params: {...}
guardrails: {error_budget_max, budget_max_usd, timeout_ms}
kpis: {leading:[...], lagging:[...]}
tests: [{name, fixture, expect:{decision, kpi_delta?}}]
docs: {summary, steps[], rollback}
<!-- AUTOGEN:END:Playbook Spec -->


<!-- AUTOGEN:BEGIN:Decision Template Spec -->
Decision Template YAML(v0.2.3):
kind: decision_template
version: v1
graph:
  nodes:
    - id: ingest|validate|policy|hitl|execute|notify|end
      spec: {policy_ref?, rule_ref?, template?, retries?, timeout_ms?}
  edges: [{from, to, when?}]
defaults: {policy_set, reason_codes, sla: {p95_ms, hitl_sla_min}}
simulate: {fixtures: [path], asserts: [expr]}
<!-- AUTOGEN:END:Decision Template Spec -->


<!-- AUTOGEN:BEGIN:Domain Packs -->
도메인 팩(v0.2.3):
- 최소 구성: README.md(문맥/가정/범위), datasets/(synthetic_csv), rules/(yaml), playbooks/(yaml), templates/(yaml)
- 예시 도메인(초기 제공):
  1) lending_brokerage v0.1 — 리드 트리아지·서류체크·부적합 컷 플레이북 포함
  2) collections v0.1 — 채무상담 우선순위·연락 빈도 조절 템플릿
  3) insurance_underwriting v0.1 — 서류 누락 감지·HITL 라우팅
  4) ecommerce_fraud v0.1 — 고위험 주문 차단·리뷰 요청
  5) healthcare_intake v0.1 — 민감정보 처리·동의 라우팅
  6) logistics_routing v0.1 — SLA 기반 라우팅·우회 규칙
- 호환성 테스트: Reality‑Seal·Policy/HITL 연동·PII Vault 준수 필수
<!-- AUTOGEN:END:Domain Packs -->


<!-- AUTOGEN:BEGIN:Tooling -->
도구체인:
- Scaffolder: dosctl scaffold {playbook|template|domain} --name --domain --version
- Import/Export: dosctl pack import|export <path-or-url>
- Lint/Validate: dosctl pack validate <path> (스키마+lints)
- Simulate: dosctl simulate --pack <path> --fixtures datasets/
- Docs Build: scripts/build_docs.py → docs/site/ (mkdocs 호환)
<!-- AUTOGEN:END:Tooling -->


<!-- AUTOGEN:BEGIN:Interfaces -->
API:
- POST /api/v1/guardrails/check {stage:pre|post, payload}
- POST /api/v1/decisions/explain {decision_id|payload}
- GET  /api/v1/audit/logs?from=&to=&actor=&model_id=
- POST /api/v1/replay/run {decision_id|artifact_refs}
- GET  /api/v1/monitor/metrics | GET /api/v1/monitor/drift
CLI(dosctl):
- `dosctl guardrails test|enable|rollout|rollback`
- `dosctl explain --decision <id> --export pdf|json`
- `dosctl audit ls|show --model <id>`
- `dosctl replay run --decision <id>`
<!-- AUTOGEN:END:Interfaces -->


<!-- AUTOGEN:BEGIN:SLO & KPIs -->
Gate‑N 성공 기준:
- OIDC 컨포먼스 테스트 통과, 로그인 성공률 ≥ 99.5%, 중간 로그인 p50 ≤ 1200ms
- RBAC 오탑재(권한거부 오검) ≤ 0.1%, 감사 누락 0
- 2인 승인 액션 100% 강제, 세션 동시성·위험탐지 동작
- Evidence Binder(Security/RBAC) 섹션 업데이트
<!-- AUTOGEN:END:SLO & KPIs -->


<!-- AUTOGEN:BEGIN:Docs & Site -->
문서/사이트(v0.3.0):
- docs/site/: mkdocs 기반 정적 사이트(내부 호스팅)
- 섹션: Getting Started, API, Runbooks, Security, Pricing, Changelog
- 내비게이션: techspec/plan 자동 동기화(scripts/build_docs.py)
- 배포: docs/site/ → /public/docs (Nginx) — 캐시 10m
<!-- AUTOGEN:END:Docs & Site -->


<!-- AUTOGEN:BEGIN:Trials & Onboarding -->
트라이얼 SKU:
- Sandbox(무료·14일): /decide 10k건/월, 모델 실경로 off, 지역=ap, 지원=P3
- Paid PoV(월30만원+건당20원): 계약/SOW 필요, 지원=P2, KPI 리포트 제공
- Pilot(3개월): 월 200만원 최소, 커넥터 확장/카나리 허용, 지원=P1(업무시간)
온보딩 파이프라인:
- POST /api/v1/signup → 이메일 도메인 검증 → tenant 생성(tenant.yaml 템플릿)
- budgets/feature_flags 기본값 주입 → welcome 메일(+API 키)
- SSO(OAuth) 옵션(도입은 차기 게이트)
<!-- AUTOGEN:END:Trials & Onboarding -->


<!-- AUTOGEN:BEGIN:Pricing & Calculator -->
가격/계산기:
- 초기 플랜: Sandbox(무료), PoV, Pilot, Enterprise(문의)
- 계산기: usage_summary × 단가 → 예상 청구액(부가세 10%)
- 캡: tenant.budgets로 과금 캡/차단 옵션 반영
<!-- AUTOGEN:END:Pricing & Calculator -->


<!-- AUTOGEN:BEGIN:Support & Incident -->
지원/인시던트:
- 접점: support@ (메일 인테이크) → triage 큐(HITL 기반)
- 심각도: P1(1h)·P2(4h)·P3(24h)·P4(3일) 최초 응답SLA
- 운영문서: runbook_support.md, comms_incident_templates.md
- 지표: 응답SLA 준수율, 티켓 해소시간 p95
<!-- AUTOGEN:END:Support & Incident -->


<!-- AUTOGEN:BEGIN:Status Page -->
상태페이지(경량):
- components: API, Ingest, DB, Provider, Billing
- 엔드포인트: GET /api/v1/status, POST /api/v1/status/incident (admin)
- 웹: /status/index.html(정적), 과거 인시던트 보관 JSON
<!-- AUTOGEN:END:Status Page -->


<!-- AUTOGEN:BEGIN:Legal & Compliance -->
법무/컴플라이언스(초기):
- ToS(이용약관), Privacy(개인정보처리방침·KR/EN), DPA(처리위탁) 초안 확정
- 데이터 위치: ap 기본(선언), 로그/트레이스 PII 스크럽 준수
- DSAR/삭제요청: tickets로 접수 → vault 토큰 기반 삭제
- 쿠키/분쟁/해지/환불 정책 명시
<!-- AUTOGEN:END:Legal & Compliance -->


<!-- AUTOGEN:BEGIN:Product Analytics Model -->
이벤트 스키마(v0.3.1):
- envelope: {ts, event, tenant_id, user_id?, session_id?, corr_id, attrs(json)}
- identity: tenant_id 필수, user_id는 해시(PII 금지), session_id는 24h 회전
- 표준 이벤트:
  * app.install, app.first_run
  * decide.request, decide.ok, decide.err, decide.hitl_required
  * ingest.ok, ingest.err
  * policy.hit, policy.deny, policy.require_hitl
  * billing.invoice_finalized
  * nps.shown, nps.submitted, feedback.created
- 저장: analytics_events(parquet/append) + summary 테이블(fct_*)
- 프라이버시: PII 필드 금지, corr_id는 X-Corr-ID 재사용
<!-- AUTOGEN:END:Product Analytics Model -->


<!-- AUTOGEN:BEGIN:Funnels & KPIs -->
핵심 퍼널/지표:
- Onboarding 퍼널: signup → key_issued → first_decide_ok(≤24h)
- Activation: W1 active tenants(#decide_ok≥50), W4 retention(tenant), seat adoption
- Value: decision_time_p95, triage_accuracy, blocked_bad_leads, hitl_sla
- Revenue: ARPA, MRR, Gross/Net expansion, churn(logo/revenue)
- Cost-to-Serve: compute_usd/tenant, support_hours, incident_count
- North Star(초안): monthly_decisions_per_active_tenant
<!-- AUTOGEN:END:Funnels & KPIs -->


<!-- AUTOGEN:BEGIN:Retention & Churn -->
코호트/이탈 위험(v0.3.1):
- Cohorts: by signup_month, plan
- Risk score r∈[0,1]: f(usage_drop, error_rate, hitl_delay, unpaid_invoice, ticket_p2plus)
- 임계치 r≥0.7 시 CSM 알림 + playbook(trigger: notify)
<!-- AUTOGEN:END:Retention & Churn -->


<!-- AUTOGEN:BEGIN:NPS & Feedback Loop -->
NPS 운영(v0.3.1):
- 트리거: first_decide_ok+7d, 이후 분기 1회
- 채널: in-app 스니펫 + 이메일(옵션)
- 스키마: nps{score(0..10), comment?, contact_ok}
- 처리: detractor(0..6) → 티켓 생성·CSM 통보, promoter(9..10) → 리뷰요청 템플릿
- 분류: feedback classifier v1(rule/키워드), 카테고리{속도,정확도,UX,가격,지원,기타}
<!-- AUTOGEN:END:NPS & Feedback Loop -->


<!-- AUTOGEN:BEGIN:Roadmap Backlog -->
백로그 운영(v0.3.1):
- 수집: /feedback·support·sales 입력 → backlog_items
- 필드: {title, source, tenant, impact_note, effort_tshirt, type[bug/feat/doc], links, status}
- 우선순위: RICE 점수, 에러버짓 정책 고려, 규제/보안 플래그
- 의사결정: 주간 분류 → 월간 계획 → Gate 배정(시맨틱 버전)
<!-- AUTOGEN:END:Roadmap Backlog -->


<!-- AUTOGEN:BEGIN:Dashboards -->
dashboards/finops:
  - unit_economics.json (per decision/lead/org)
  - forecast.json (p50/p90 bands)
  - optimizers.json (savings, cache hit, batch ratio)
  - commitments.json (utilization, break-even)
<!-- AUTOGEN:END:Dashboards -->


<!-- AUTOGEN:BEGIN:Pricing Model v2 -->
플랜/요율(v2):
- Plan Tiers: Sandbox(무료), PoV(계량), Pilot(계량+최저요금), Enterprise(견적)
- Metrics:
  * decide_calls (1000건 단위), ingest_calls, storage_gb_days, hitl_tasks
  * seats: {agent, reviewer, admin} — 역할별 단가
- Rating Rules:
  * 계량 단가는 계층형(tiered) — 예: 0-100k, 100k-1M, 1M+
  * seats는 일할 계산(일 단위), 중도 변경 시 프로레이션
- Taxes: VAT 10%(KR) — 금액·세액 라인 분리, 영수증/인보이스에 표기
- Discounts/Coupons: 퍼센트·정액·구간 한도 지원, 소진/만료 추적
<!-- AUTOGEN:END:Pricing Model v2 -->


<!-- AUTOGEN:BEGIN:Entitlements & Enforcement -->
권한/한도(v2):
- entitlements.yaml: {feature_flags, rate_limits, seat_limits, region, vendors}
- Enforcement: gateway/budget_enforcer와 통합, 초과 시 소프트캡(경고)→하드캡(차단)
- Grace: 결제실패 시 7일 유예, 이후 좌석 downsize→필수 기능만 유지
<!-- AUTOGEN:END:Entitlements & Enforcement -->


<!-- AUTOGEN:BEGIN:Billing Engine v2 -->
과금 엔진 구성:
- Collector: usage_event{ts, tenant_id, metric, qty} 수집(버전·출처 포함)
- Rater: 요율표(ratebook.yaml)로 rating → line_items
- Invoicer: 월말/중도 결산, 프로레이션·세금·할인 적용 → invoice_{id}.pdf
- Reconciler: provider 정산과 대조(드리프트 ≤ 1%), 조정분 생성
- Currency: KRW 기본(소수점 원단위 반올림), 멀티통화는 차기 게이트
<!-- AUTOGEN:END:Billing Engine v2 -->


<!-- AUTOGEN:BEGIN:Self‑Serve Flows -->
셀프서비스:
- 업그레이드/다운그레이드: seats·plan 변경 즉시 적용(프로레이션), 일부 기능은 주기 말에 적용 옵션
- 취소/중지/재개: cancel(at_period_end|immediate), resume; 환불 정책은 ToS 연동
- 결제수단 관리: 카드 교체/검증, 영수증 이메일 설정
- Dunning: 0d/3d/7d 알림 → 10d 제한(읽기전용) → 20d 중지
<!-- AUTOGEN:END:Self‑Serve Flows -->


<!-- AUTOGEN:BEGIN:Payments Adapter -->
결제 어댑터:
- ProviderBase: create_customer, attach_payment_method, charge, refund, webhook_verify
- 어댑터: provider_pg(local 테스트), provider_stripe(옵션) — 실제 PG는 .env로 선택
- Webhook: /api/v1/billing/webhook (HMAC 서명, 멱등키)
<!-- AUTOGEN:END:Payments Adapter -->


<!-- AUTOGEN:BEGIN:Reports & KPIs -->
지표/리포트:
- Revenue: MRR/ARR, ARPA, Expansion/Contraction, Churn
- Usage: per‑metric histograms, overage events, seat utilization
- Billing: failed_payment_rate, dunning_success_rate, refund_rate
- 정확도: 인보이스 vs 원천사용량·원가 드리프트 ≤ 1%
<!-- AUTOGEN:END:Reports & KPIs -->


<!-- AUTOGEN:BEGIN:Identity & SSO -->
OAuth 2.1 + OIDC Core(v0.3.3):
- 플로우: Authorization Code + PKCE, Refresh Rotation(재사용 감지)
- 토큰: access(JWT, 15m), refresh(opaque, 30d), PAT(서비스계정, 스코프 제한)
- issuer: https://<host>/.well-known/openid-configuration, jwks.json 제공
- 스코프: openid profile email offline_access org:read/write project:read/write policy:write vault:unseal hitl:approve billing:manage admin:*
- 클레임: sub, tid(tenant), oid(org_id), pid(project_id?), roles[], perms[], corr_id
- 프로바이더: generic_oidc(Okta/AzureAD/Google) — per-tenant federation(옵션)
- 보안: nonce·state, pkce 필수, client_secret_post 금지, SameSite=strict 쿠키, IP/UA 바인딩(옵션)
- 로그아웃: RP‑Initiated Logout(세션쿠키 제거), refresh revoke
<!-- AUTOGEN:END:Identity & SSO -->


<!-- AUTOGEN:BEGIN:Org/Projects Model -->
자원모델(v0.3.3):
- Org(조직) → Projects(업무단위) → Environments(dev/stage/prod)
- 멀티테넌트: tenant == org 기본, enterprise에서 org 내 multi‑project 지원
- 맵핑: decisions/policies/vault_tokens/packs/analytics는 project 스코프, billing은 org 스코프
- 좌석(seats): org 레벨로 구매, project에 할당(Seat Utilization 리포트 연계)
<!-- AUTOGEN:END:Org/Projects Model -->


<!-- AUTOGEN:BEGIN:RBAC (Fine‑Grained) -->
역할/권한(v0.3.3):
- 표준 역할: owner, admin, security_admin, billing_admin, project_admin, agent, reviewer, auditor, read_only
- 권한(primitives): tenant.admin, org.manage, project.manage, policy.read/write, hitl.approve, vault.seal/unseal(scope), sampling.admin, canary.manage, packs.enable, billing.read/manage, analytics.read, keys.rotate(2인 승인)
- 부여: role→permissions 매핑 + 커스텀 grant(deny 우선)
- 범위(scope): org|project|environment
- 집행: gateway 미들웨어 + routers 레벨 데코레이터 + PII Vault/Policy Enforcer 훅
- 감사: 모든 grant/revoke/critical action은 append‑only 로그 + 해시체인(sha256)
<!-- AUTOGEN:END:RBAC (Fine‑Grained) -->


<!-- AUTOGEN:BEGIN:Access Reviews & Just‑in‑Time Elevation -->
접근검토/승격:
- 정기 리뷰: 분기 1회, 만료기한(expiry) 필수, 비활성 사용자 자동 해지
- JIT 승격: reviewer→security_admin 요청 → HITL 큐 승인 시 임시 권한(≤4h)
- 이중 통제: keys.rotate, vault.unseal(scope=PII) 2인 승인 강제
<!-- AUTOGEN:END:Access Reviews & Just‑in‑Time Elevation -->


<!-- AUTOGEN:BEGIN:Audit & Session Management -->
감사/세션:
- audit_event{ts, actor, action, resource, scope, reason, ip, ua, hash, prev_hash}
- tamper‑evident: prev_hash 체인 + 일일 앵커 해시 보관(Evidence Binder)
- 세션: last_seen, device lock, 동시세션 제한(기본 3), 위험 탐지(이상 위치/UA)
<!-- AUTOGEN:END:Audit & Session Management -->


<!-- AUTOGEN:BEGIN:Connectors Catalog -->
초기 커넥터(v0.3.4):
- Batch: local_csv, s3_csv, http_json
- DB-CDC: postgres_logical, mysql_binlog
- Streaming: kafka_topic(local)
공통 규격:
- connector.yaml {name, kind[batch|cdc|stream], version, source{...}, schedule|offset, schema_ref, pii:bool, owner}
- 출력: records(line-delimited JSON) + _meta{src, ts, offset, schema_hash}
- 보안: 자격증명은 secrets/ 에 K/V, IAM role은 차기 게이트
<!-- AUTOGEN:END:Connectors Catalog -->


<!-- AUTOGEN:BEGIN:ETL/CDC Pipelines -->
파이프라인 구성(v0.3.4):
- Orchestrator: jobs/runner.py(간단 스케줄러, cron/interval), retries(지수백오프)
- Transforms: apps/etl/transforms/{cleanse.py, map_ontology.py, pii_mask.py}
- Loads: apps/etl/loaders/{parquet_sink.py, kafka_sink.py}
- CDC 보장: at-least-once + idempotency key(_meta.offset), 지연 p95<5s(동일 DC)
- 재처리: backfill window(ISO-interval), quarantine_bucket(스키마 위반)
<!-- AUTOGEN:END:ETL/CDC Pipelines -->


<!-- AUTOGEN:BEGIN:Data Contracts v1 -->
컨트랙트 스키마(v1): YAML/JSON
kind: data_contract
version: v1
dataset: {name, domain, owner, slas:{freshness, completeness_min, distinctness_min}}
schema:
  fields:
    - {name, type, mode[required|optional], pii?:bool, tags[], description?, constraints?{min?,max?,enum?}}
compatibility:
  policy: semver
  rules:
    - backward_add_optional: allow
    - remove_or_narrow: require major bump
    - pii_flag_drop: deny(승인필요)
validation:
  on: ingest|transform|export
  actions: {reject|quarantine|mask|coerce}
lineage: {sources[], owner, change_log[]}
<!-- AUTOGEN:END:Data Contracts v1 -->


<!-- AUTOGEN:BEGIN:Ontology Mapping -->
온톨로지 매핑(v0.3.4):
- decision_ontology.yaml(표준 엔티티: Applicant/Asset/Loan/Decision/Reason)
- 매핑 규칙: map_ontology.yaml {source_field -> ontology_field, transform, pii_policy}
- 품질 체크: 필수 온톨로지 필드 누락 시 reject/quarantine
- 계약 연결: contract.schema.fields.tags에 ontology key를 표준화(tag: do:Applicant.income_monthly 등)
<!-- AUTOGEN:END:Ontology Mapping -->


<!-- AUTOGEN:BEGIN:Quality Gates & Metrics -->
품질게이트/KPI:
- 스키마 위반율 ≤ 0.5%, quarantine 처리는 24h내 95%
- freshness: 계약 SLA 충족률 ≥ 99%
- completeness/distinctness 계약 기준 준수
- CDC 지연 p95 ≤ 5s(동일 DC), 데이터 유실 0(리플레이 기준)
<!-- AUTOGEN:END:Quality Gates & Metrics -->


<!-- AUTOGEN:BEGIN:Data Catalog & Taxonomy -->
카탈로그 모델(v0.3.6):
- asset: {id, type[connector|dataset|table|view|product|policy|pipeline], name, domain, owner, tags[], pii?:bool, contract_ref?, created_at}
- dataset: {id, asset_id, schema_version, fields[]}
- field: {name, type, mode, pii?:bool, ontology_tag?, description?}
- ownership: owner(primary), stewards[], slack_channel?, escalation?
- 분류체계: domain(credit, risk, ops...), tier(gold|silver|bronze), sensitivity(public|internal|restricted)
- 계약 연결: data_contract(dataset) ↔ catalog.dataset.schema_version 동기화
<!-- AUTOGEN:END:Data Catalog & Taxonomy -->


<!-- AUTOGEN:BEGIN:Search & Indexing -->
검색/인덱싱(v0.3.6):
- 인덱서: jobs/indexer.py (delta index, 5m 주기)
- 저장: pg tsvector 기반 FTS(기본) + file trigram(보조), 필요시 OpenSearch 어댑터(opt)
- 인덱스 대상: asset.name/tags, dataset.fields(name/type/desc), contracts, lineage summary, runbooks
- 보안: sensitivity 필터, tenant/org 스코프, pii 필드명 부분 마스킹(예: na**e)
- 랭킹: text_rank + freshness_boost + usage_boost(최근 조회/결정 연동)
<!-- AUTOGEN:END:Search & Indexing -->


<!-- AUTOGEN:BEGIN:Lineage v2 (Column‑Level) -->
계보 수집/저장:
- 소스: pipelines(run logs), contracts(compat), transforms(map_ontology), cdc offsets
- 테이블: lineage_edges{src_asset, src_field?, dst_asset, dst_field?, op, run_id, ts}
- 보장: at-least-once, 동일 run_id idempotent
- 커버리지 목표: Gate‑O 파이프라인 산출물의 필드 기준 ≥90%
- 영향분석: impact(dataset|field) = 역방향 탐색, 병합 규칙(op별 가중치)
<!-- AUTOGEN:END:Lineage v2 (Column‑Level) -->


<!-- AUTOGEN:BEGIN:Data Products -->
데이터 제품 정의(v1):
- product.yaml {name, version, owner, input_datasets[], transforms(ref), slas{freshness, quality}, publish{s3_parquet|db_view}, contracts{output_contract}}
- 배포: product_builder.py(스냅샷 버전), 실패 시 롤백(직전 버전 alias 유지)
- 소비: /products API·카탈로그 UI(골드 레이어)
<!-- AUTOGEN:END:Data Products -->


<!-- AUTOGEN:BEGIN:Dashboards & UI -->
UI(경량):
- web/catalog/: 검색창·필터(도메인/민감도/티어)·자산 상세·스키마 미리보기
- web/lineage/: 그래프 뷰(줌/패닝/하이라이트)·임팩트 패널
- web/products/: 제품 목록·버전·SLA 상태·소비 경로
<!-- AUTOGEN:END:Dashboards & UI -->


<!-- AUTOGEN:BEGIN:Guardrails v2 (Runtime) -->
구성요소(v0.3.7):
- Input Validators: schema/PII redaction, prompt-injection/RCE 패턴, max_tokens/entropy 한도
- Output Validators: type/constraint, toxicity/PHI, leakage(scan: API keys/PII), policy denylist
- Policy Enforcer: DecisionContract 전/후 훅(pre/post), allow|review|block, HITL 큐 연계
- Canary & Shadow: perc% 샘플을 shadow 모델/정책으로 병행평가, 이탈 시 alarm
- Rollout: staged(1%→5%→25%→100%), 자동 롤백(오탐/미탐 임계 초과)
측정:
- 공격 차단율(Injection/Leak) ≥ 99.5%, 오탐 ≤ 1.0%, p95 오버헤드 ≤ 120ms
<!-- AUTOGEN:END:Guardrails v2 (Runtime) -->


<!-- AUTOGEN:BEGIN:Decision Explainability -->
설명 레이어(v0.3.7):
- Rule Trace: 규칙기반 결정의 매칭 규칙/스코어/임계값·불만족 규칙 목록
- Reason Codes: 표준화 코드셋(credit/risk) + 인간가독 메시지(ko)
- Feature/Factor Attribution: 모델형 결정은 surrogate(샘플링·simple tree/shap-lite)로 기여도 요약
- Evidence Pack: 입력 요약, 사용 정책/버전, 데이터 계약/온톨로지 링크, 유사 결정 3건
- Export: PDF/JSON, 고객제출용(민감항목 자동 마스킹)
품질:
- Fidelity(rule) = 1.0, Fidelity(model surrogate) ≥ 0.9 (val set), 민감정보 노출 0
<!-- AUTOGEN:END:Decision Explainability -->


<!-- AUTOGEN:BEGIN:Model Audit Trails & Replay -->
감사/재현(v0.3.7):
- Audit Log(append-only, hash chain): {ts, model_id, version, policy_id, input_hash, output_hash, features_hash, reason_code[], latency, actor, corr_id, prev_hash}
- Artifact Store: 모델 카드(model_card.yaml), 모델/정책/컨피그 아카이브, 샘플 입출력 스냅샷
- Replay Runner: 동일 아티팩트/시드/정책으로 재실행 → 해시일치 검증
- Access: /audit, /replay API + RBAC( auditor, security_admin ) 전용
SLO: 재현 성공률 100%(동일 아티팩트), 감사 누락 0, 무결성 위변조 탐지 100%
<!-- AUTOGEN:END:Model Audit Trails & Replay -->


<!-- AUTOGEN:BEGIN:Monitoring & Drift -->
모니터링/드리프트:
- Metrics: accuracy@pilot, denial/approval rate by segment, reject inference rate, latency, guardrail hit rate
- Drift: feature popshift(jsd/psi), reason_code distribution drift, data_contract violations
- Alerts: 임계 초과 시 Slack/Webhook, 자동 canary/roll-back 트리거
<!-- AUTOGEN:END:Monitoring & Drift -->


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


<!-- AUTOGEN:BEGIN:Dashboards & Runbooks -->
대시:
  - /web/obs/overview: RED/USE 메트릭, burn-rate 패널
  - /web/obs/service/<name>: SLI·트레이스·로그 상관
  - /web/ops/oncall: 경보 인박스, 사일런스/승인
런북:
  - P0/P1 절차, 롤백·카나리, 데이터 파이프라인 지연 대응
  - 공통 체크리스트: 최근 배포, 트래픽 급증, 외부 의존성
<!-- AUTOGEN:END:Dashboards & Runbooks -->


<!-- AUTOGEN:BEGIN:Edge/Offline — Architecture -->
구성요소:
  - edge_agent: 경량 실행기(결정 호출 프록시, 로컬 큐/캐시, 정책 집행)
  - syncd: 증분 동기화 데몬(배치프레임, 서명검증, 재전송)
  - secure_store: SQLite(WAL) + AES-GCM-at-rest (OS keyring/KMS로 키 보호)
  - pkg signer: 엣지 번들(바이너리/정책/설정) 서명·검증
운영모드:
  - online: 클라우드 우선, 로컬 캐시 히트/미스 관리
  - offline: 로컬 규칙/계약만으로 결정 수행, 큐 적재 후 연결 시 재전송
타깃:
  - OS: Linux(x64/arm64), Windows, macOS
  - 배포: 압축 번들 + 서명(sig) + 해시(manifest.json)
<!-- AUTOGEN:END:Edge/Offline — Architecture -->


<!-- AUTOGEN:BEGIN:Store-and-Forward & Sync Protocol -->
큐:
  - outbox{ id, corr_id, type, payload_blob, retries, next_at, status }
  - 전송 전략: 지수백오프(<= 5m), 최대 재시도 12, 멱등키 = corr_id
동기화:
  - 채널: configs, policies, catalogs, decisions_logs, usage
  - 프레임: seq_no, range_hash, items[], sig
  - 무결성: 해시-체인 검증, 틀림 발생 시 범위 재동기화
충돌해결:
  - 기본 LWW + policy guard(deny 우선)
  - 로그/케이스류: vector clock 기반 merge, 불가 시 HITL 큐로 에스컬레이션
<!-- AUTOGEN:END:Store-and-Forward & Sync Protocol -->


<!-- AUTOGEN:BEGIN:Local Policy (ABAC Subset) & Break-Glass -->
정책:
  - Gate-W의 Cedar-lite 서브셋을 edge용 바이트코드로 컴파일
  - 평가 캐시 TTL=60s, p95 ≤ 10ms
브레이크글라스:
  - offline_override ≤ 2h, 사유/티켓 필수, 모든 행위 감사 라벨 포함
  - 온라인 복귀 즉시 리포트 업로드·심사 대기열
<!-- AUTOGEN:END:Local Policy (ABAC Subset) & Break-Glass -->


<!-- AUTOGEN:BEGIN:Secure Cache · Data Minimization -->
캐시:
  - decision_cache: key(hash(DecisionRequest.contract+features)), value, ttl
  - 최대항목/TTL 플랜별 상한(Free/Pro/Ent)
  - PII/비밀 필드 마스킹 후 저장(마지막4자리 등)
최소수집:
  - 필요 필드만 저장, 로그/메트릭은 압축+샘플링(헤드10%/테일 p95)
<!-- AUTOGEN:END:Secure Cache · Data Minimization -->


<!-- AUTOGEN:BEGIN:Device Lifecycle & Attestation -->
등록:
  - device_enroll: CSR 제출 → mTLS 발급 → org/project 스코프 부여
상태:
  - heartbeat: 버전/디스크/큐/오류 카운터 보고
폐기:
  - remote_revoke: 인증서 폐기·키 와이프·데이터 파쇄(보존정책 예외만 남김)
<!-- AUTOGEN:END:Device Lifecycle & Attestation -->


<!-- AUTOGEN:BEGIN:Observability & Billing Integration -->
관측성(Gate-T):
  - trace_id/corr_id 전파, 로컬 스풀 → 온라인 시 일괄 업로드
  - synthetic probe: edge-health(큐 적재율, 지연 p95)
빌링(Gate-S):
  - usage 이벤트 오프라인 적재 → 월간/일별 집계로 병합(idempotent)
<!-- AUTOGEN:END:Observability & Billing Integration -->


<!-- AUTOGEN:BEGIN:BCP/DR — Architecture -->
목표:
  - P0 서비스 RPO ≤ 15m, RTO ≤ 60m (P1: RPO ≤ 60m, RTO ≤ 4h)
  - 멀티리전 액티브-패시브(기본) + 일부 액티브-액티브(카탈로그/로그)
구성:
  - DB: 물리복제(WAL/LSN) + PITR, 논리덤프 주기 백업
  - 오브젝트 저장소: 버전닝 + Object Lock(WORM) + 크로스리전 복제
  - 메타데이터: 카탈로그/정책/라인리지/빌링/사용량 스냅샷
  - 비밀/키: KMS-backed, 주기적 회전 + DR-키 에스코(row)트
  - 트래픽 전환: DNS/Traffic Manager + 헬스체크 + 카나리 검증
  - 복구 관측: Gate-T 번레이트/SLO 게이팅과 연동
<!-- AUTOGEN:END:BCP/DR — Architecture -->


<!-- AUTOGEN:BEGIN:Backups — Strategy & Integrity -->
유형/주기(기본값):
  - DB 물리: 지속적 WAL, 베이스라인 24h, 보존 35d
  - DB 논리: 1일 1회 pg_dump/스키마/권한, 보존 14d
  - 오브젝트: 실시간 버전닝 + 주간 불변 스냅샷(보존 30d)
  - 메타/설정: 6h 스냅샷
무결성:
  - 백업 완료 후 자동 복원 리허설(샌드박스) + 체크섬 검증
  - 샘플 테이블·카탈로그 비교, 정책/권한 드리프트 검사
보안/거버넌스:
  - AES-256 at rest, TLS in transit, 키는 KMS + 외부 금고(sealed)
  - 보존/파기 정책: ISMS-P 기준, 삭제는 지연삭제 + 감사체인
<!-- AUTOGEN:END:Backups — Strategy & Integrity -->


<!-- AUTOGEN:BEGIN:Disaster Recovery — Failover/Failback -->
시나리오:
  - 리전 장애, DB 손상, 스토리지 파손, 비밀/키 손상
절차:
  - 선언(incident/IM) → 트래픽 중지/리드온리 → 데이터 경계 확인(Gate-W)
  - DB 승격(스탠바이→프라이머리) → 앱/큐/배치 재바인드
  - 헬스/SLI 패스 후 DNS 전환 → 모니터링/번레이트 정상화 확인
  - Failback: 원리전 복구·재복제·검증 후 재전환
자동화:
  - `/api/v1/dr/failover` 카나리 0→10→100 단계, 롤백 훅 포함
<!-- AUTOGEN:END:Disaster Recovery — Failover/Failback -->


<!-- AUTOGEN:BEGIN:Chaos & GameDay -->
혼란 주입:
  - DB read-only, 노드 장애, 네트워크 블랙홀, 키 회전 실패
게임데이:
  - 분기별 P0 풀 시나리오 1회, 월간 부분 시나리오 1회
  - 각 시나리오마다 RPO/RTO 측정·증빙, 런북 업데이트
<!-- AUTOGEN:END:Chaos & GameDay -->


<!-- AUTOGEN:BEGIN:Residency/Policy Alignment -->
- Residency=="KR" 데이터는 KR 내 백업/복구만(크로스리전 금지)
- 교차전송 필요 시 purpose-binding·승인 티켓·만료토큰 요구(Gate-W)
- 백업 접근은 최소권한(RBAC)·감사 라벨(trace_id, policy_id) 필수
<!-- AUTOGEN:END:Residency/Policy Alignment -->


<!-- AUTOGEN:BEGIN:Dashboards/Runbooks/Evidence -->
대시/리포트:
  - 백업 성공율/복원시간, RPO 시계, DR 카나리 성공율
런북:
  - IM 절차, DR 선언, 권한/승인, 체크리스트(서비스별)
Evidence:
  - 백업 무결성 리포트, RPO/RTO 실측, 게임데이 결과, 변경점 기록
<!-- AUTOGEN:END:Dashboards/Runbooks/Evidence -->


<!-- AUTOGEN:BEGIN:GA Criteria & Exit Checklist -->
GA 통과 필수:
  - PenTest: 하이/크리티컬 취약점 0, 미디엄은 accepted fix plan ≤ 30d
  - Load: P0 경로 3×베타 피크에서 에러율 ≤ 0.2%, p95 ≤ 800ms, p99 ≤ 1500ms
  - SRE: SLO·에러버짓 게이팅 활성(Gate-T), 온콜 로테이션 주 1회, 게임데이 1회 통과
  - Policy/Privacy: Gate-W 준수, DSR(삭제/정정/열람) TAT ≤ 14d, 보존·삭제 정책 문서화
  - Billing: Gate-S 정합(메터링 오차 ≤ ±1%), 인보이스/환불 e2e 100%
  - Legal: ToS/Privacy/DPA/Subprocessors 게시, 쿠키/트래킹 동의 배너 동작
  - Docs: 운영/개발/고객 문서 세트, 릴리즈 노트·마이그레이션 가이드
  - Support: 티켓/슬라 진입, Sev 매트릭스·SLA, Status Page 라이브
  - Rollout: 코호트 롤아웃/플래그/롤백 절차·증빙
<!-- AUTOGEN:END:GA Criteria & Exit Checklist -->


<!-- AUTOGEN:BEGIN:Security — AppSec · Supply Chain · SBOM -->
AppSec:
  - SAST/DAST 파이프라인(semgrep+ZAP 스텁), 시크릿 스캔, IaC 스캐너
  - 최소권한 검토(CI 정책), 서드파티 라이선스 검증
공급망:
  - 의존성 핀/재현빌드, 서명 아티팩트, 출처 검증
SBOM:
  - 포맷: SPDX 2.3, 경로: artifacts/sbom/sbom-<version>.spdx.json
  - 릴리즈마다 생성/보관, 크리티컬 CVE 자동 차단 정책
<!-- AUTOGEN:END:Security — AppSec · Supply Chain · SBOM -->


<!-- AUTOGEN:BEGIN:Performance/Capacity — Load/Soak/Scale -->
테스트:
  - Load: 30분 3×피크, Soak: 6h 1.5×피크, Spike: 10×피크 5분
오토스케일:
  - HPA/큐기반 스케일 정책, 워크로드별 목표 CPU 65%·큐 지연 p95 2s
배포:
  - 블루/그린 + 카나리(1%→10%→50%→100%), 자동 롤백 트리거=burn_rate > 4.0
<!-- AUTOGEN:END:Performance/Capacity — Load/Soak/Scale -->


<!-- AUTOGEN:BEGIN:Privacy/Legal — ToS/Privacy/DPA · DSAR · Cookie -->
문서:
  - /legal/tos, /legal/privacy, /legal/dpa, /legal/subprocessors
DSAR:
  - 요청 채널: /support/dsar (템플릿), 내부 워크플로: evidence link + SLA
쿠키/트래킹:
  - 배너: 필수/통계/마케팅 구분, 옵트인 기반, 지역별 규칙(EU/US/KR)
데이터 삭제:
  - 보존 기간·삭제 지연·백업 삭제 예외 명시, 삭제증빙 레코드 보관
<!-- AUTOGEN:END:Privacy/Legal — ToS/Privacy/DPA · DSAR · Cookie -->


<!-- AUTOGEN:BEGIN:Packaging/Pricing — SKUs/Quota/Overage -->
플랜(v1):
  - Basic: 100k decisions/mo, 3 connectors, 1 tenant, SLA 99.0%
  - Pro:   1M decisions/mo, 10 connectors, 3 tenants, SLA 99.5%
  - Ent:   계약형, 전용 한도·커스텀 SLA(≥99.9%), 전용 VPC 옵션
과금:
  - 초과분 Overage 단가(결정/1k), 스토리지/로그·플러그인 리소스 쿼터
거버넌스:
  - 가격/플랜은 Gate-S 빌링 정책과 동기, 플래그 기반 플랜 스위치
<!-- AUTOGEN:END:Packaging/Pricing — SKUs/Quota/Overage -->


<!-- AUTOGEN:BEGIN:Support/SRE — Sev Matrix · SLA · Status Page -->
심각도:
  - Sev0(전면 중단)·Sev1(중대한 기능)·Sev2(부분)·Sev3(경미)
SLA(응답/복구):
  - Basic: 1d/Best-effort, Pro: 4h/1d, Ent: 1h/8h(Sev1 기준)
채널:
  - /support 포털(티켓), 이메일, 상태 페이지(/status)
운영:
  - 온콜 캘린더, 핸드오프 템플릿, PIR(Post Incident Review) 폼
<!-- AUTOGEN:END:Support/SRE — Sev Matrix · SLA · Status Page -->


<!-- AUTOGEN:BEGIN:Release Mgmt — Versioning · Notes · CAB -->
버저닝: CalVer+SemVer 혼합(YYYY.MINOR.PATCH)
변경관리:
  - Change Advisory Brief(CAB) 승인, 위험등급·롤백 플랜 필수
문서:
  - RELEASE_NOTES.md, BREAKING_CHANGES.md, MIGRATION_GUIDE.md
<!-- AUTOGEN:END:Release Mgmt — Versioning · Notes · CAB -->


<!-- AUTOGEN:BEGIN:Rollout Plan — Cohorts · Flags · Rollback -->
코호트:
  - 내부→친구/가족→프라이빗 베타→퍼블릭
플래그:
  - 서버/클라이언트 플래그, 1코호트 단위 증분
롤백:
  - 기능/데이터 롤백 분리, 데이터 마이그는 DRY-RUN + 스냅샷 선행
<!-- AUTOGEN:END:Rollout Plan — Cohorts · Flags · Rollback -->


<!-- AUTOGEN:BEGIN:Docs Set — Operator/Dev/Customer -->
오퍼레이터: 온콜·런북·DR·보안·정책
개발자: API 레퍼런스·SDK 가이드·예제
고객: 시작하기·FAQ·가격·SLA·법무 문서
<!-- AUTOGEN:END:Docs Set — Operator/Dev/Customer -->


<!-- AUTOGEN:BEGIN:Growth Architecture — Funnel & Definitions -->
목적: '리드 → 수익' 경로를 표준화, 각 단계에 SLO·증빙 부착.
표준 퍼널:
  - Site → Lead → MQL → SQL/PoV → PQL/PQA → Paid → Expansion
용어 정의:
  - MQL: 대상 ICP + 의도 시그널(폼/세미나/가이드 다운로드)
  - SQL: PoV 제안 자격(예산/권한/니즈/타임라인 3/4 충족)
  - PQL: 제품 내 행동 기반 자격(결정 호출 ≥ N, triage 정확도 ≥ X%)
  - PQA: 조직 단위 제품 자격(활성 사용자 ≥ K, 채널 ≥ L)
계측:
  - event taxonomy v1 (events.yaml): lead.created, content.viewed, seq.sent, pql.hit 등
  - 대시보드: 퍼널 전환, CAC/LTV, 채널 ROI, PQL 승격률, 코호트 잔존
<!-- AUTOGEN:END:Growth Architecture — Funnel & Definitions -->


<!-- AUTOGEN:BEGIN:ICP · Segmentation · Positioning -->
ICP v1:
  - Primary: 중소형 대출 브로커리지(10~100 seats, KR 우선)
  - Secondary: 리스크/컴플팀이 있는 금융 파트너(연동 PoV)
세분화: seat 규모·월 리드량·규제 민감도·IT 성숙도 점수.
메시지 맵(핵심/증거/반론대응)과 금지표현(과도한 보장/오인 우려) 목록.
<!-- AUTOGEN:END:ICP · Segmentation · Positioning -->


<!-- AUTOGEN:BEGIN:Packaging & Pricing Experiments -->
플랜(초안): Basic/Pro/Ent (Gate-Z와 동기).
실험:
  - A/B: 월정액 vs 사용량 혼합, 연간 선결제 -10%, PoV fee 환급 규칙.
  - 할인: 파트너/비영리/초기고객 쿠폰 정책.
환불/조정: Gate-U API 사용, 환불 SLA/감사라벨 부착.
<!-- AUTOGEN:END:Packaging & Pricing Experiments -->


<!-- AUTOGEN:BEGIN:Channels & Motions -->
인바운드: SEO/콘텐츠(가이드/케이스스터디), 웨비나, 마켓플레이스(Gate-V).
아웃바운드: SDR 시퀀스(3주, 6터치), 이벤트-트리거(신규 규제 이슈 등).
파트너: 등급(Silver/Gold/Platinum), 공동세일즈/리드쉐어/Co-op 마케팅.
<!-- AUTOGEN:END:Channels & Motions -->


<!-- AUTOGEN:BEGIN:CRM Abstraction & Sequencer -->
CRM Adapter:
  - 통합 인터페이스(ICRM): upsert_lead, add_activity, move_stage, assign_owner.
  - 지원: generic_crm(webhook/CSV), crm_stub, 나중에 상용 CRM 커넥터 추가.
Router:
  - 리드 라우팅 규칙(ICP 적합도, 지역/좌석, SLA 타이머).
Sequencer:
  - 템플릿(이메일/콜/링크드인 DM), 윈도우/쿨다운, 실패/성공 후크.
<!-- AUTOGEN:END:CRM Abstraction & Sequencer -->


<!-- AUTOGEN:BEGIN:Product-Led Growth (PLG) -->
트라이얼: 14일, 결정 호출/커넥터/시뮬 제한. 인앱 가이드/체크리스트.
PQL 규칙 예: 72시간 내 결정 50회 + triage 정확도 ≥ 65% + 팀원 3명 초대.
업셀: PQL→SQL 자동 생성, /billing 업그레이드 딥링크(Gate-S/U).
<!-- AUTOGEN:END:Product-Led Growth (PLG) -->


<!-- AUTOGEN:BEGIN:Compliance & Consent (Growth) -->
- 모든 메시징/랜딩은 Gate-W 정책 라벨/동의 스코프 부여.
- 옵트인 수집/구독취소, 쿠키/추적 배너 지역 규칙(Gate-Z 연동).
- 세일즈 주장에는 근거 링크(케이스스터디/지표), 과장 금지.
<!-- AUTOGEN:END:Compliance & Consent (Growth) -->


<!-- AUTOGEN:BEGIN:Tenancy Model & Isolation -->
계층: org → project → workspace → user/service-account.
모델(코드): apps/tenancy/models.py (Pydantic) · 정책/슬러그/소유권은 service.py.
DB: db/migrations/tenancy.sql — 파티셔닝(org_id), RLS(tenant_id), CLS(residency).
조인키: tenant_id, residency. in-memory 사전은 tenancy.service 레이어로 캡슐화(추후 영속화 전환).
<!-- AUTOGEN:END:Tenancy Model & Isolation -->


<!-- AUTOGEN:BEGIN:Usage & Metering -->
과금단위 v1:
  - decisions.count, rules.eval.ms, storage.gb_month, egress.gb,
    plugins.cpu_min, webhooks.deliveries, catalog.assets, lineage.ops.
이벤트 규격(meter_event):
  - {id, ts, tenant_id, project_id?, product, metric, value, corr_id, source, signature}
수집:
  - 실시간 스트림 + 배치 수합, 멱등키=hash(tenant_id|metric|corr_id).
  - 지연/중복/역전 처리(워터마크+재계산), Edge(X) 업로드 병합.
정합:
  - 관측(T) 카운터와 샘플 대조, 오차 허용 ±1%.
<!-- AUTOGEN:END:Usage & Metering -->


<!-- AUTOGEN:BEGIN:Rating · Plans · Proration -->
정의: apps/rating/{plans.py, engine.py, proration.py}
플랜: Basic/Pro/Ent — 포함량/계층단가. 환율/세율 프리셋: configs/billing/pricing.yaml.
출력: dashboards/billing/{usage.json, costs.json} — 코스트 카드.
<!-- AUTOGEN:END:Rating · Plans · Proration -->


<!-- AUTOGEN:BEGIN:Quota & Throttling -->
쿼터: 플랜/애드온 기준 하드/소프트 한도.
스로틀: 토큰버킷(초당/분당) + 버스트 허용, 공정성(tenant 라운드로빈).
초과 처리:
  - soft: 경고 + 코스트가드 경보, grace 윈도우.
  - hard: 429/스로틀 + 기능 단계적 비활성화(읽기전용 전환 등).
<!-- AUTOGEN:END:Quota & Throttling -->


<!-- AUTOGEN:BEGIN:Cost-Guard v1 (Budgets/Anomaly/Freeze) -->
예산: 월/일 기준 budget{amount, currency, notify_thresholds}.
경보: 예산 50/80/100%, 급격한 사용량 변화(EWMA 6x, p95 이상).
조치: 이메일/웹훅/슬랙·플래그, 일시중지(freeze), 일회성 한도 상향(승인필요).
증빙: 모든 조치에 ticket_id/trace_id, Evidence(Billing/Cost) 링크.
<!-- AUTOGEN:END:Cost-Guard v1 (Budgets/Anomaly/Freeze) -->


<!-- AUTOGEN:BEGIN:Invoicing (Stub) & Artifacts -->
산출물: invoice_draft.json + PDF 렌더(고객명/기간/항목/세금/잔액).
환불/수납/영수는 Gate-U에서. 여기서는 드래프트/조정/크레딧 노트만.
세금: KR/EU 기본 VAT 필드 포함(계산은 외부 택스 엔진 어댑터로 위임 가능).
<!-- AUTOGEN:END:Invoicing (Stub) & Artifacts -->


<!-- AUTOGEN:BEGIN:APIs & CLI -->
API:
  - POST /api/v1/modelops/register {model, metrics, artifacts, env}
  - POST /api/v1/modelops/deploy {id, strategy:shadow|canary|bluegreen}
  - POST /api/v1/modelops/rollback {deployment_id}
  - GET  /api/v1/modelops/health {id}
  - GET  /api/v1/featurestore/parity?feature_set=...&version=...
  - GET  /api/v1/modelops/skew?model_id=...
  - GET  /api/v1/modelops/drift?model_id=...
CLI(dosctl):
  - dosctl model register|deploy|promote|rollback|metrics
  - dosctl feature parity|backfill|ttl
  - dosctl model skew-check|drift-check
<!-- AUTOGEN:END:APIs & CLI -->


<!-- AUTOGEN:BEGIN:Security/Compliance Alignment -->
ABAC(W)로 빌링 데이터 접근 통제. PII 최소화(해시/가명).
Residency 준수: 사용량/인보이스 저장 지역은 데이터 경계에 따름.
감사 라벨: 모든 요금 결정에 policy_id/consent_id 링크(해당 시).
<!-- AUTOGEN:END:Security/Compliance Alignment -->


<!-- AUTOGEN:BEGIN:Usage & Metering — Pipeline Split -->
모듈: apps/metering/{schema.py, ingest.py, reconcile.py}
스키마: JSON Schema+Pydantic 동시 검증.
멱등키: hash(tenant_id|metric|corr_id). 워터마크: ISO8601 ts + source.
Edge(X): ingest.apply_event에서 source별 지연 허용 차등, 병합 전략 포함.
정합성: reconcile.build_report가 Observability(T) 대비 ±1% 검증.
<!-- AUTOGEN:END:Usage & Metering — Pipeline Split -->


<!-- AUTOGEN:BEGIN:Quota/Throttling · Cost-Guard v1 -->
quota.py: 소프트/하드 한도. throttle.py: 토큰버킷(초/분), 버스트, tenant 라운드로빈.
cost_guard: apps/cost_guard/{budget.py, anomaly.py(EWMA), actions.py}
모든 조치: ticket_id/trace_id 의무, Evidence(Billing/Cost) 링크.
<!-- AUTOGEN:END:Quota/Throttling · Cost-Guard v1 -->


<!-- AUTOGEN:BEGIN:Invoice Drafts -->
apps/invoice/{draft.py, pdf.py}: usage→라인→세금 계산(택스 어댑터 훅).
REST: apps/gateway/routers/invoice.py, CLI: dosctl billing 하위 커맨드.
크레딧 노트 반영. (결제/환불은 Gate-U).
<!-- AUTOGEN:END:Invoice Drafts -->


<!-- AUTOGEN:BEGIN:APIs/CLI · PEP/ABAC -->
routers 추가: apps/gateway/routers/{meter.py, rating.py, quota.py, cost.py, invoice.py}
정책: Depends(enforce_policy("billing.read|write")), ABAC(Gate-W) 연계, 마스킹 Hook 재사용.
CLI: apps/cli/dosctl/main.py에 meter/rating/quota/cost/invoice 서브커맨드.
<!-- AUTOGEN:END:APIs/CLI · PEP/ABAC -->


<!-- AUTOGEN:BEGIN:Tests & Evidence -->
tests/test_gate_s_*: 멱등/워터마크, proration, token-bucket p95, freeze/unfreeze.
fixtures: Gate-T 카운터 모킹.
리포트: reports/billing/{usage_vs_obs.csv, cost_guard_events.json}, invoice PDF 샘플 5종.
Evidence Binder(Billing/Cost) 업데이트.
<!-- AUTOGEN:END:Tests & Evidence -->


<!-- AUTOGEN:BEGIN:Payments Architecture — Scope & PCI Boundary -->
목표: SAQ-A 범위 유지(민감 카드정보 저장 금지). PSP 토큰화/호스티드 결제폼 우선.
구성요소:
  - pay_gateway: PSP 라우터(Stripe/Generic REST/KR-PG Stub)
  - tax_adapter: VAT/국가별 세금 계산(외부 엔진 연동 포인트)
  - receipter: 영수증/세금서류 PDF/JSON 생성
  - dunning: 실패 결제 재시도·알림·Downgrade/Freeze 훅(Gate-S)
  - reconcile: PSP 이벤트 ↔ invoice_draft( Gate-S ) 대사
  - subledger: 더블엔트리(AR/Cash/Revenue/Tax/Refund/Chargeback)
PCI/보안: PAN/CSC 비보관, PSP 토큰만 저장. 3DS/SCA 지원. 웹훅 서명 검증/재생공격 방지.
<!-- AUTOGEN:END:Payments Architecture — Scope & PCI Boundary -->


<!-- AUTOGEN:BEGIN:Data Model — Billing Accounts & Payment Methods -->
billing_account{org_id, currency, tax_profile_id, default_pm, delinquent, dunning_state}
payment_method{pm_id, org_id, psp, token, type[card/bank/wallet], brand,last4,exp, billing_addr}
tax_profile{org_id, country, region, vat_id?, tax_exempt[none/partial/exempt], evidence[]}
receipt{id, invoice_id, amount, tax, currency, pdf_url, issued_at}
chargeback{id, psp_ref, stage[notice/won/lost], amount, reason, due_at}
ledger_entry{id, ts, account, debit, credit, currency, tenant_id, ref(invoice/charge/refund)}
<!-- AUTOGEN:END:Data Model — Billing Accounts & Payment Methods -->


<!-- AUTOGEN:BEGIN:APIs — Charges/Refunds/Tax/Receipts/Webhooks -->
API:
  - POST /api/v1/pay/charge {invoice_id|amount, currency, pm_id|payment_intent, idempotency_key}
  - POST /api/v1/pay/refund {charge_id|invoice_id, amount?, reason}
  - POST /api/v1/tax/calc {invoice_id|lines[]} -> {tax_total, breakdown}
  - POST /api/v1/receipt/issue {invoice_id} -> {receipt_id, pdf_url}
  - GET  /api/v1/reconcile/status?period=
  - POST /api/v1/pay/dunning/run {org_id?}
  - POST /api/v1/pay/chargeback/update {psp_ref, stage, evidence_url?}
  - Webhooks: /api/v1/pay/webhook/stripe | /generic | /krpg
규범:
  - 모든 write API는 Idempotency-Key 필수, 멱등키 중복 시 409 대신 기존 결과 리턴
  - 결제 시 Gate-S quota/throttle/guard 체크 후 진행
<!-- AUTOGEN:END:APIs — Charges/Refunds/Tax/Receipts/Webhooks -->


<!-- AUTOGEN:BEGIN:PSP Adapters — Routing & Idempotency -->
어댑터:
  - stripe_adapter.py: PaymentIntent/Refund/Webhooks/3DS
  - generic_psp_adapter.py: REST/OpenAPI 매핑, 서명검증 훅
  - kr_pg_stub.py: 카드/계좌이체/가상계좌 시뮬레이터(샌드박스)
라우팅 전략:
  - Geo/플랜/SLA 기반 PSP 우선순위, 장애 시 페일오버
멱등성:
  - corr_id 기반 PSP키 매핑, 재시도 안전
<!-- AUTOGEN:END:PSP Adapters — Routing & Idempotency -->


<!-- AUTOGEN:BEGIN:Dunning & Collections — Policy -->
재시도 일정(기본): 0h → 24h → 72h → 7d → 14d
알림 채널: 이메일/슬랙/웹훅, 인앱 배너
조치:
  - 72h 실패: 플랜 제한(soft), 14d 실패: freeze( Gate-S ), PQL/시퀀스에 알림( Gate-AA )
해제:
  - 성공 결제 시 자동 정상화, 실패 누적 카운트 리셋
로깅:
  - 모든 단계 ticket_id/trace_id, Evidence(Billing/Cost)
<!-- AUTOGEN:END:Dunning & Collections — Policy -->


<!-- AUTOGEN:BEGIN:Refunds & Credits — Rules -->
환불 유형: 전액/부분/라인별. PoV Fee 환급 규칙(Gate-Z/AA 실험 반영).
크레딧 노트: invoice 조정( Gate-S ), 차월 상계.
Anti-fraud:
  - 환불 윈도우, 고액 환불 HITL 승인(Gate-Q 예정), 중복 환불 차단(멱등키)
<!-- AUTOGEN:END:Refunds & Credits — Rules -->


<!-- AUTOGEN:BEGIN:Tax & Receipts — Minimal Viable -->
세금:
  - tax_adapter: 국가/지역 코드·VAT율 로딩, 역외 과세/면세 처리, 증빙 필드(vat_id)
영수증:
  - invoice_draft → receipt PDF 렌더(금액/세액/품목/기간/사업자정보)
지역정책:
  - KR/EU 프리셋, 최종 전자세금계산서/현금영수증 정식 연동은 후속 Gate 제안
<!-- AUTOGEN:END:Tax & Receipts — Minimal Viable -->


<!-- AUTOGEN:BEGIN:Reconciliation — Matching & Settlement -->
대사:
  - PSP 이벤트(charge/refund/payout) ↔ invoice/ledger 매칭(금액/통화/시점)
  - 불일치: pending_report로 큐잉, 수동 조정/조사 라우팅
정산:
  - 입금 스케줄/수수료 반영, 수익/세금/수수료 분개 자동화
<!-- AUTOGEN:END:Reconciliation — Matching & Settlement -->


<!-- AUTOGEN:BEGIN:Subledger — Double-Entry -->
계정:
  - AR(미수금), Cash(현금), Revenue(수익), TaxPayable(부가세), Refunds, Chargebacks, Fees
트랜잭션 예:
  - 청구 결제 성공: AR↓, Cash↑, Revenue↑, Tax↑
  - 환불: Revenue↓, Tax↓, Cash↓, Refunds↑
  - 차지백: Cash↓, Chargebacks↑ (승소 시 반대분개)
폐쇄:
  - 월말 집계/시산표 산출, 외부 회계 연동 어댑터 훅
<!-- AUTOGEN:END:Subledger — Double-Entry -->


<!-- AUTOGEN:BEGIN:Security/Privacy/Compliance -->
ABAC(Gate-W)로 정책/결과 접근 최소화, 민감 로그 마스킹·TTL.
Q게이트 레저에 safety_decision 요약 링크, DSAR 시 redaction 적용.
거버넌스: 정책 변경은 Gate-Q(4-eyes) 승인.
<!-- AUTOGEN:END:Security/Privacy/Compliance -->


<!-- AUTOGEN:BEGIN:Decision Ledger — Evidence & Integrity -->
목적: 모든 결정의 재현·설명·증빙 가능 상태 보장.
스키마(decision_record v1):
  - ids: decision_id, tenant_id, subject_id, corr_id
  - time: decided_at, policy_ts, model_ts, rules_ts
  - inputs: input_hash, feature_snapshot(json, masked by ABAC/W)
  - outputs: decision, confidence, reason_codes[], scores{}
  - context: rule_id@ver, model_id@ver, policy_id@ver, contract_id
  - expl: rule_path[], shap_topk[]?, notes
  - consent/dsr: consent_id?, dsar_id?
  - security: prev_hash, curr_hash, signer, signature
보존: 7년, 해시체인(prev_hash→curr_hash)로 변조 방지, 월별 체크포인트 스냅샷.
<!-- AUTOGEN:END:Decision Ledger — Evidence & Integrity -->


<!-- AUTOGEN:BEGIN:Replay Engine — Deterministic Reconstruction -->
구성: apps/audit/replay.py
입력: decision_id 또는 {ts, policy_id@ver, model_id@ver, rule_id@ver, features}
출력: 재현 결과(동일/불일치), 차이 분석(diff: 모델/규칙/데이터/환경)
모드: offline(batch), on-demand(API), bulk(export). 정책/모델/규칙 아카이브에서 버전 고정 로딩.
<!-- AUTOGEN:END:Replay Engine — Deterministic Reconstruction -->


<!-- AUTOGEN:BEGIN:Explainability — Rule Path & Reason Codes -->
규칙형: DSL 실행 트레이스→rule_path 추출, reason_codes 매핑 테이블(reason_code→고객 설명문).
모델형: 모델 어댑터가 shap/k-lime 등 지원 시 shap_topk[] 저장, 미지원 시 surrogate linear로 근사.
표준 API 응답 필드: reason_codes[], rule_path[], confidence, caveats.
<!-- AUTOGEN:END:Explainability — Rule Path & Reason Codes -->


<!-- AUTOGEN:BEGIN:Change Management — Models/Rules/Policies -->
레지스트리: apps/change/{model_registry.py, rule_registry.py, policy_registry.py}
불변 아티팩트: 해시+서명, provenance(학습데이터 스냅샷/seed/파라미터)
게이트: pre-merge impact report(오탐/미탐, KPI deltas), 위험등급에 따른 4-eyes 승인(CAB-lite)
롤아웃: 카나리/코호트/플래그, 자동 롤백 훅(T) 연계, Evidence(Change) 보관.
<!-- AUTOGEN:END:Change Management — Models/Rules/Policies -->


<!-- AUTOGEN:BEGIN:HITL — Review/Override Workflow -->
큐: apps/hitl/{inbox.py, reviewer.py}, 라우팅(리스크/민감도/금액)
SLA: Sev1 4h/1d, Sev2 1d/3d, CoI(이해상충) 차단
조치: approve/override/request-more-info, override 시 이유·근거·권한 기록, 모든 변경은 ledger patch로 트래킹
샘플링 QA: 무작위/위험중심 샘플 재검토 비율 타겟(≥5%)
<!-- AUTOGEN:END:HITL — Review/Override Workflow -->


<!-- AUTOGEN:BEGIN:APIs & CLI — Evidence/Explain/Replay/Change/HITL -->
API:
  - GET  /api/v1/decisions/{id}
  - POST /api/v1/decisions/{id}/replay
  - GET  /api/v1/decisions/{id}/evidence  # zip bundle
  - POST /api/v1/change/propose {artifact, type[model|rule|policy], notes}
  - POST /api/v1/change/approve {change_id}
  - POST /api/v1/hitl/queue {decision_id|payload}
  - POST /api/v1/hitl/{id}/action {approve|override|rfi, notes}
CLI(dosctl):
  - dosctl audit get|replay|evidence
  - dosctl change propose|approve|status
  - dosctl hitl queue|action|report
<!-- AUTOGEN:END:APIs & CLI — Evidence/Explain/Replay/Change/HITL -->


<!-- AUTOGEN:BEGIN:Academy Architecture — Scope -->
목적: 고객/파트너가 제품을 '안전하게' 익혀 KPI를 개선하도록 표준 커리큘럼·평가·증빙을 제공.
구성요소:
  - Course/Module/Lesson(콘텐츠), Lab(실습), Exam(평가), Badge/Certificate(인증), Partner Tracks.
  - Storage: academy_bucket(콘텐츠), item_bank(문항), lab_kits(데이터/시나리오).
  - Policy/Consent: Gate-W 스코프 라벨, 개인정보 최소화.
  - Evidence: 학습/시험/랩 로그를 Evidence(Academy)에 보관, Gate-Q 레저에 요약 레코드 링크.
<!-- AUTOGEN:END:Academy Architecture — Scope -->


<!-- AUTOGEN:BEGIN:Learning Objects & Content Types -->
콘텐츠 타입: mdx(텍스트/코드 포함), 영상 링크, 인터랙티브 위젯(퀴즈/체크리스트).
메타: locale, level(101/201/301), estimated_time, prerequisites, outcomes.
접근성: 캡션/대체텍스트, 색대비 기준 준수.
<!-- AUTOGEN:END:Learning Objects & Content Types -->


<!-- AUTOGEN:BEGIN:Labs (Hands-on) — Safe Sandbox -->
Lab Kit: 입력CSV/JSON(합성 데이터), 목표/채점 규칙, 솔루션 워크북.
실행: apps/academy/labs/{runner.py, grader.py}, 샌드박스 토큰(테넌트 격리).
금융 도메인 예시: 리드 triage 정확도 65% 달성, 규칙 튜닝, Evidence 번들 제출.
보안: 실데이터 금지, 합성/익명화 강제, 업로드 파일 AV 스캔.
<!-- AUTOGEN:END:Labs (Hands-on) — Safe Sandbox -->


<!-- AUTOGEN:BEGIN:Certification & Proctoring (Stub) -->
Exam Engine: item_bank(객관/서술/실습), 난이도/Blueprint, 시간제한, 무작위화.
Proctor Stub: 웹캠/브라우저 잠금은 '미포함', 대신 행동로그/탭 전환 탐지·세션 감사.
합격선: 101(70%), 201(75%), 301(80%). 재응시 정책/대기기간.
발급: Badge/Certificate(JSON+PDF), 만료/갱신 규칙.
<!-- AUTOGEN:END:Certification & Proctoring (Stub) -->


<!-- AUTOGEN:BEGIN:Partner Enablement & Tracks -->
트랙: Partner-L1(구축 기초), L2(통합/보안), L3(성능/감사). Gate-AA 등급(S/G/P)과 매핑.
요건: 코스/랩/시험 조합, 실적/레퍼런스 제출, 연간 갱신.
리드 정책: 인증 등급별 공동세일즈/리드쉐어 한도.
<!-- AUTOGEN:END:Partner Enablement & Tracks -->


<!-- AUTOGEN:BEGIN:Analytics & PQL/Partner Hooks -->
지표: 등록→수료율, 최초수료 TTV, 랩 통과율, 시험 재응시율, 코호트별 KPI(현장 전환/시간감소).
Hook:
  - 수료/배지 취득 → Gate-AA PQL 점수 가산/세일즈 라우팅 우선순위 상향.
  - 파트너 등급 승인/다운그레이드 자동화, Evidence(Academy) 링크.
<!-- AUTOGEN:END:Analytics & PQL/Partner Hooks -->


<!-- AUTOGEN:BEGIN:Cost Ontology & Attribution -->
원가 계층: provider→service→resource→operation(metric)→decision/event.
기본 매핑:
  - LLM/모델: tokens_in/out, requests, router_path
  - 데이터: storage.gb_month, egress.gb, scans.ops
  - 실행: cpu_min, gpu_min, job.exec_ms
귀속(Attribution):
  - tenant/org/project/workspace/tag(cost_center) 기준 가중배분
  - shared cost: fanout 비율/시간/사용량 기반 apportion
정합성: Gate-S usage/rating과 1% 이내 차이, Gate-T counters와 교차검증
<!-- AUTOGEN:END:Cost Ontology & Attribution -->


<!-- AUTOGEN:BEGIN:Unit Economics · Showback/Chargeback -->
KPI: cost_per_decision, cost_per_lead, gross_margin_per_org, channel_CAC, payback.
Showback: 월별/채널별 리포트, Cost Center별 분해.
Chargeback: org 단위 내부 정산 스텁(회계 연동은 후속).
<!-- AUTOGEN:END:Unit Economics · Showback/Chargeback -->


<!-- AUTOGEN:BEGIN:Forecast & Budget Planning -->
Forecast 엔진: 프로파일 기반(주/월 seasonality) + 간단한 Prophet/ARIMA 스텁 선택.
출력: next_1/3/6/12개월 usage/cost 예측(MAPE 목표 ≤ 15%).
예산 계획: budget_suggest{amount, bands(p50/p90), notes}, Gate-S 코스트가드와 연동.
<!-- AUTOGEN:END:Forecast & Budget Planning -->


<!-- AUTOGEN:BEGIN:Optimizers (Policies & Executors) -->
모델 최적화:
  - model_policy: quality tier(hi/med/low)·latency·cost ceiling
  - router_cost: 저비용 경로 우선, 실패/품질 저하 시 승급
실행 최적화:
  - batcher: 미세 호출 묶기, dedupe/cache(hit ratio 카드)
  - sampler: 커넥터/ETL 샘플링율/주기 조정
  - storage_lifecycle: hot→warm→cold TTL/압축/삭제 정책
커밋먼트:
  - committed_use/_reserved 관리, 이용률 추적, 언더/오버 유틸 경보
<!-- AUTOGEN:END:Optimizers (Policies & Executors) -->


<!-- AUTOGEN:BEGIN:Privacy Architecture — Scope -->
목표: 테넌트별 개인정보 처리의 합법성/최소화/목적제한/보존·삭제/권리행사(DSAR) 보장.
구성: discovery(classify) · consent/purpose · retention/lifecycle · dsar · redaction · legal_hold · privacy_vault(tokenize) · evidence.
<!-- AUTOGEN:END:Privacy Architecture — Scope -->


<!-- AUTOGEN:BEGIN:Data Discovery & Classification -->
스캐너: apps/privacy/discovery/{scanner.py, classifiers.py}
규칙: 정규식/국가별 식별자(주민/전화/계좌/카드/이메일), ML-stub(이름/주소 문맥).
민감도: P0(민감), P1(식별), P2(준식별), P3(비식별). 스키마/컬럼/샘플링 1k행.
출력: catalog.tagging(prv.pii=type, prv.sensitivity), evidence/map.json.
오탐제어: 샘플 수동확인 큐(허용오차 ≤ 1.0%).
<!-- AUTOGEN:END:Data Discovery & Classification -->


<!-- AUTOGEN:BEGIN:Consent & Purpose Limitation -->
모델: consent{subject_id, purposes[], scopes[], lawful_basis, ts, expiry?}
목적: marketing/analytics/service/contract/legal 등. 정책ID(Gate-W)와 링크.
검증: API 호출 시 PEP가 consent/purpose 교차·만료 검증, 비합치 시 차단/마스킹.
기록: consent_id를 decision ledger(Gate-Q) reason_codes에 포함.
<!-- AUTOGEN:END:Consent & Purpose Limitation -->


<!-- AUTOGEN:BEGIN:Retention & Deletion Lifecycle -->
정책: retention_rule{dataset, sensitivity, ttl, action[delete|anonymize|tokenize], legal_basis}
스케줄러: apps/privacy/retention/scheduler.py — 일일 배치, dry-run → 승인 → 실행.
삭제: soft→hard 단계, 종속 관계/참조 무결성 처리, 연결 시스템(O) 전파.
익명화/토큰화: reversible(privacy_vault) vs irreversible(redaction) 선택.
<!-- AUTOGEN:END:Retention & Deletion Lifecycle -->


<!-- AUTOGEN:BEGIN:Privacy Vault (Tokenization/KMS) -->
vault: apps/privacy/vault/{service.py, kms_adapter.py}
토큰화: det/randomizable 해시·포맷보존(FPE) 스텁. 키는 KMS(내부/외부)로 관리.
접근: ABAC 최소권한, 토큰→원문 복구는 승인형(HITL/4-eyes) 플로우로 제한.
<!-- AUTOGEN:END:Privacy Vault (Tokenization/KMS) -->


<!-- AUTOGEN:BEGIN:DSAR/SAR — Intake · Verify · Fulfill -->
파이프라인: intake → identity verify(KYC-lite) → scope resolve → collect → redact → export → fulfill.
엔진: apps/privacy/dsar/{engine.py, exporter.py, redactor.py, verifiers.py}
산출: subject_export.zip(JSON+CSV+PDF 요약), 타임라인/출처/동의/정책 링크 포함.
SLA: 법정 30일 내, 내부 목표 7일 내. 진행상태/통지 템플릿 포함.
<!-- AUTOGEN:END:DSAR/SAR — Intake · Verify · Fulfill -->


<!-- AUTOGEN:BEGIN:Legal Hold -->
legal_hold{id, scope(datasets|subjects|cases), reason, start, end?}
효과: 삭제/수정 정지, 실행 로그·증빙 필요. 해제 시 보류기간 동안 누락된 보존 동기화.
<!-- AUTOGEN:END:Legal Hold -->


<!-- AUTOGEN:BEGIN:Safety Architecture — Scope -->
목표: LLM 경로에 대한 공격/유출/오남용을 '정책→탐지→조치→증빙' 루프에 통합.
구성요소:
  - safety_policies: 허용/금지/경계 규칙(콘텐츠/행동/데이터/툴).
  - detectors: PI(프롬프트 인젝션)/JB(탈옥)/DLP/PII/허위출처/악성URL/설정유도.
  - toolcall_guard: 함수·커넥터 호출 전/후 파라미터 검증·샌드박스·쿼터.
  - router_hardening: 모델/경로 선택 시 안전 스코어 반영(코스트/품질/위험).
  - safety_ledger: Q게이트 레저와 링크된 증빙/결정 기록.
  - redteam_harness: 공격 말뭉치·시나리오·성공률/차단률 측정.
<!-- AUTOGEN:END:Safety Architecture — Scope -->


<!-- AUTOGEN:BEGIN:Detectors — Signals & Scores -->
시그널:
  - PI/JB 패턴: 탈출 토큰, 시스템 프롬프트 노출 유도, 권한 상승 문구.
  - DLP/PII: 키/비밀번호/주민·계좌·카드·주소/이메일/고유식별자.
  - URL/파일: 비허용 도메인, 확장자 블록, 피싱/멀웨어 휴리스틱.
  - Hallucination proxy: 출처 없는 단언, 금지된 근거 재사용.
스코어:
  - risk_score∈[0,1], reason_codes[], signals{} (가중 합성, 임계치 다단계: warn/block).
  - false_positive_budget: 테넌트별 월간 허용 FP 비율 상한(운영 튜닝).
<!-- AUTOGEN:END:Detectors — Signals & Scores -->


<!-- AUTOGEN:BEGIN:Toolcall Guard — Sandbox & Quotas -->
전/후 훅:
  - pre: 파라미터 스키마 검증, ABAC 정책 검사, DLP 필터(키/토큰/PII 샘플링).
  - exec: 샌드박스(타임/메모리/네트워크 범위), graylist 도메인 차단.
  - post: 반환 객체 표본 DLP 스캔, 레드액션/마스킹.
쿼터/스로틀: 테넌트/워크스페이스/액터별 호출 한도(Gate-S limits 연계).
증빙: toolcall_id, trace_id, policy_id@ver, safety_decision 레코드화.
<!-- AUTOGEN:END:Toolcall Guard — Sandbox & Quotas -->


<!-- AUTOGEN:BEGIN:Router Hardening — Cost/Quality/Safety -->
router_policy:
  - 안전 임계 초과 시: 경량 검열모델→안전필터→안전등급 높은 경로로 상승.
  - 고위험 요청: 고비용 모델 허용(품질 우선), 로그 강화·HITL 큐.
  - 저위험: 저비용 경로·배치/캐시 적극 사용.
메트릭: blocked, escalated, downgraded 비율·추가 비용·품질 영향.
<!-- AUTOGEN:END:Router Hardening — Cost/Quality/Safety -->


<!-- AUTOGEN:BEGIN:Red Team Harness — Corpora & Scenarios -->
corpora: jailbreak_sets, prompt_injection_sets, dlp_leak_sets, tool_abuse_sets, rag_poison_sets.
scenarios: zero-shot, few-shot, chain-of-thought誘導, toolcall-bypass, long-context overflow.
실행: apps/safety/redteam/{runner.py, corpora/*.jsonl, reports/*}
결과: ASR(Attack Success Rate), BPR(Block/Prevent Rate), FPR/TPR, Latency overhead.
<!-- AUTOGEN:END:Red Team Harness — Corpora & Scenarios -->


<!-- AUTOGEN:BEGIN:Dashboards & Evidence -->
evidence/expops/<run_id>/
  - witness_refs.json (gate-t 소스/해시/기간)
  - verdicts_{x190a,c102,cli}.json
  - quorum_verdict.json
  - discrepancies.csv (판정 불일치)
<!-- AUTOGEN:END:Dashboards & Evidence -->


<!-- AUTOGEN:BEGIN:Residency Model & Region Topology -->
목적: 데이터/결정/아티팩트를 지역 경계에 맞게 저장·처리·이동.
모델:
  - region{id, provider, geo: KR|AP|EU|US, zones[], llm_routes[]}
  - residency_label{dataset_id|connector_id, region_id, basis[law|contract|consent], sensitivity(P0..P3)}
  - transfer_matrix{from_region -> to_region: allowed[true|false], basis[], safeguards[SCC|BCR|Encryption]}
구성요소:
  - configs/residency/{regions.yaml, transfer_matrix.yaml}
  - apps/residency/{models.py, service.py}
  - 카탈로그 태그: catalog.tags.prv.residency=region_id, prv.sensitivity=P*
원칙: 기본은 **in-region 우선**, 교차 전송은 **사전 승인**·**증빙 필수**.
<!-- AUTOGEN:END:Residency Model & Region Topology -->


<!-- AUTOGEN:BEGIN:Ingest/Process Residency Gate (PEP Hook) -->
훅: apps/policy/pep_hooks/residency.py
검사: action[ingest|read|export|train|replicate], actor, dataset.tags(prv.*), region(context).
조치: allow / queue_for_transfer / block. 위반 시 reason_codes[], policy_id@ver 기록.
마스킹: 교차허용 전 read/export는 자동 redaction(민감 필드).
<!-- AUTOGEN:END:Ingest/Process Residency Gate (PEP Hook) -->


<!-- AUTOGEN:BEGIN:Cross-Border Transfer Controls & Ledger -->
전송 요청: apps/residency/transfer/{request.py, assessor.py, ledger.py}
평가: 목적/법적근거/민감도/대체가능성/암호화/수탁자.
승인흐름: 위험등급별 4-eyes(Gate-Q)·법무 확인·SCC 템플릿 링크.
실행: 암호화 전송, 무결성 체크섬, 대상 리전 키/권한 검증.
레저: transfer_id, from/to, basis, approvers, evidence_paths, prev_hash→curr_hash 체인.
<!-- AUTOGEN:END:Cross-Border Transfer Controls & Ledger -->


<!-- AUTOGEN:BEGIN:Region-Aware Router (API/LLM/Jobs) -->
apps/residency/router.py — 요청의 지역/정책/성능을 고려해 경로 결정.
LLM 경로: region→허용 모델 목록, 금지/대체 경로(품질/비용/보안) 스코어링.
Fallback: 인-리전 불가 시 '승급 경로' + 로그 강화 + HITL 옵션.
<!-- AUTOGEN:END:Region-Aware Router (API/LLM/Jobs) -->


<!-- AUTOGEN:BEGIN:Data Movement Orchestrator -->
jobs/residency/orchestrator.py — snapshot diff(메타/파티션) 기반 복제/동기화.
모드: replicate(one-way), promote(cutover), recall(delete back).
제약: 워터마크·레이트리밋·레거시 커넥터 지연 큐, 실패 재시도/보상 트랜잭션.
<!-- AUTOGEN:END:Data Movement Orchestrator -->


<!-- AUTOGEN:BEGIN:Edge Cache/CDN & Temp Artifacts -->
규칙: P0/P1는 캐시 금지, P2는 단기 TTL+암호화, P3는 표준 TTL.
임시물: tmp artifacts는 지역별 버킷 분리·자동 수거·태그 상속.
<!-- AUTOGEN:END:Edge Cache/CDN & Temp Artifacts -->


<!-- AUTOGEN:BEGIN:Discovery/Privacy Integration -->
Gate-AD 태그(prv.sensitivity, prv.pii_type)를 residency 훅이 소비.
DSAR/삭제 전파 시 cross-region 링크 추적·삭제 롤업 리포트 생성.
<!-- AUTOGEN:END:Discovery/Privacy Integration -->


<!-- AUTOGEN:BEGIN:Security/Compliance & SLO -->
암호화: at-rest AES-256, in-transit TLS1.2+, 키는 region-local KMS.
접근: ABAC 최소권한, 레플리카 읽기는 승인 필요.
SLO/수락기준:
  - 불허 전송 차단율 100%, 미스라우트 0건
  - 레플리케이션 지연 p95 ≤ 30m (정책 대상 세트)
  - DSAR 삭제 전파 cross-region 누락 ≤ 0.5%
  - Router 정책 일관성 테스트 100% 통과
  - Evidence Binder(Residency) 업데이트
<!-- AUTOGEN:END:Security/Compliance & SLO -->


<!-- AUTOGEN:BEGIN:Ontology v2 — Scope & Principles -->
목적: 데이터/규칙/모델/정책을 '동일 온톨로지'로 연결하여 일관된 의사결정과 재현을 보장.
원칙:
  - Type System: Entity, Event, Decision, Policy, Metric, Artifact.
  - Strong IDs: {tenant_id, natural_key, version, valid_time, system_time}.
  - Time Semantics: Bitemporal(valid/system), late arrival 허용, correction 추적.
  - Compatibility: SemVer(major/minor/patch)·Back/Forward 호환 규칙.
  - Provenance: source, transform, contract_id, lineage_ref(Gate-P), hash.
<!-- AUTOGEN:END:Ontology v2 — Scope & Principles -->


<!-- AUTOGEN:BEGIN:Core Types & Schemas -->
폴더: ontology/schemas/
필수 타입:
  - Entity: Person, Organization, Asset(Property/Account), Product(Loan/ProductRule).
  - Event: LeadSubmitted, DocUploaded, PriceQuoted, DecisionMade, PaymentPosted.
  - Decision: Eligibility, Pricing, Routing, RiskFlag, PrivacyAllow/Deny.
  - Policy/Rule: PolicySet, RuleSet(DSL path), PolicyBinding(scope/priority).
스키마 형식: YAML(v2) with jsonschema draft2020-12 변환 지원.
공통 규약: id rules, required fields, reason_codes, consent/ref links.
<!-- AUTOGEN:END:Core Types & Schemas -->


<!-- AUTOGEN:BEGIN:Decision Graph — Nodes & Edges -->
그래프 모델:
  - Node: {type[Rule|Model|Contract|Human|Policy], ref(id@ver), io{expects, produces}}
  - Edge: {from, to, when{predicate}, audit_tags[], cost, safety}
실행: apps/decision/graph/{engine.py, planner.py}
기능: 경로 추론(필수/대체/폴백), 비용/위험/품질 스코어 합성, 가시화 export(.dot/.json).
<!-- AUTOGEN:END:Decision Graph — Nodes & Edges -->


<!-- AUTOGEN:BEGIN:DecisionContract v2 -->
계약 스키마: contract{inputs(schema_ref), outputs(schema_ref), pre/post-conditions, metrics, sla, pii_tags, residency, evidence_hooks}
검증기: tools/contracts/validator.py — Pydantic+JSON Schema 검증, Gate-W/Q/AD/AF 연동 검사.
<!-- AUTOGEN:END:DecisionContract v2 -->


<!-- AUTOGEN:BEGIN:Source Mapping — ETL/CDC Binding -->
매핑 정의: ontology/mappings/{source}/*.map.yaml
내용: field map, unit/enum 정규화, pii/sensitivity 태깅(Gate-AD), residency 라벨(Gate-AF), lineage anchor(Gate-P).
검사: tools/mapping/verify.py — 샘플 10k 레코드 기준 손실/오류 보고.
<!-- AUTOGEN:END:Source Mapping — ETL/CDC Binding -->


<!-- AUTOGEN:BEGIN:Codegen — Models/DB/Graph/Clients -->
도구: tools/ontogen/{parser.py, codegen_py.py, codegen_sql.py, codegen_graph.py, codegen_client.py}
산출물:
  - Pydantic 모델(apis에서 공용)
  - DDL/마이그(문서화 포함)
  - Graph 어댑터(neo4j/networkx 스텁)
  - API 클라이언트 스텁(dosctl/SDK)
정책: 생성물은 /generated/** 에 위치, CI에서 drift 검사.
<!-- AUTOGEN:END:Codegen — Models/DB/Graph/Clients -->


<!-- AUTOGEN:BEGIN:Dashboards & Docs -->
dashboards/ontology/{coverage.json, drift.json, graph_paths.json}
docs/ontology/handbook.md, docs/ontology/style_guide.md, docs/decision_contract_v2.md
<!-- AUTOGEN:END:Dashboards & Docs -->


<!-- AUTOGEN:BEGIN:Model Ops Architecture — Scope -->
목표: 모델/피처/데이터/정책/결정(AG)의 일관 실행. 학습·배포·관측·개선 루프 표준화.
구성요소:
  - Model Registry(재현성): 모델/아티팩트/환경/데이터스냅샷/계약.
  - Feature Store: offline(batch) ↔ online(serving) 동형성 보장.
  - Pipelines: 학습(batch/증분)·평가·패키징·서빙(REST/gRPC)·A/B/카나리.
  - Skew/Drift: 입력/피처/라벨/출력 분포 차이·성능 드리프트 탐지.
  - Rollout Controls: shadow→canary→blue/green, 자동 롤백·승급 규칙.
  - Evidence/Lineage: Gate-P(라인리지), Gate-Q(레저), Gate-T(메트릭)에 연계.
<!-- AUTOGEN:END:Model Ops Architecture — Scope -->


<!-- AUTOGEN:BEGIN:Model Registry — Reproducibility -->
레코드: model{id, name, semver, hash, framework, params, metrics, dataset_refs, feature_contract, env(manifest), policies}.
아티팩트: /models/{id}/(weights.bin|onnx|tokenizer|preproc), /env/{id}/conda.lock|dockerfile.
계약: DecisionContract v2(AG) 링크로 입력/출력/PII/Residency/SLA 보증.
재현성: build recipe + digest 검증, 재학습/재서빙 성공률 100% 목표.
<!-- AUTOGEN:END:Model Registry — Reproducibility -->


<!-- AUTOGEN:BEGIN:Feature Store — Offline/Online Parity -->
폴더: apps/feature_store/{registry.py, offline.py, online.py, parity_checker.py}
스키마: feature_set{id, version, entity_key, freshness_sla, ttl, pii/residency tags}.
매핑: AG-ontology mapping 사용, ETL/CDC 바인딩(Gate-O).
파리티: offline→online 샘플 10k 기준 수치형 Δ≤0.5%p, 범주형 JSD≤0.02.
<!-- AUTOGEN:END:Feature Store — Offline/Online Parity -->


<!-- AUTOGEN:BEGIN:Pipelines — Train/Eval/Package/Serve -->
학습: jobs/train/{trainer.py, scheduler.py} — batch/증분, resume/checkpoint, cost budget(AC).
평가: apps/modelops/eval/{offline_eval.py, online_eval.py} — metric spec, slice, fairness stub.
패키징/서빙: apps/serving/{server.py (REST/gRPC), router_adapter.py}, autoscale, warmup/coldstart 관리.
배포전략: shadow(미러 트래픽)→canary(1→5→20→50%)→blue/green, 자동 롤백/승급.
<!-- AUTOGEN:END:Pipelines — Train/Eval/Package/Serve -->


<!-- AUTOGEN:BEGIN:Skew/Drift Detection -->
스큐: train vs serve — PSI/JSD/KL, 임계 PSI≤0.2, 알림/차단 규칙.
드리프트: 라벨 지연 보정, 성능 드리프트 CUSUM/EWMA, 재학습 트리거.
대시: dashboards/modelops/{skew.json, drift.json}, 이벤트는 Gate-T.
<!-- AUTOGEN:END:Skew/Drift Detection -->


<!-- AUTOGEN:BEGIN:Safety/Privacy/Residency Integration -->
입력/출력 DLP/PII 스캔(AE/AD), 레지던시 훅(AF) — 리전 외 학습/서빙 차단.
정책: 고위험 모델 경로는 Router 하드닝(AE)·승인(HITL) 필요.
계약 위반시 배포 금지(AG·W), Q레저에 사유 기록.
<!-- AUTOGEN:END:Safety/Privacy/Residency Integration -->


<!-- AUTOGEN:BEGIN:DocOps — Gate-Scoped Plan Sections -->
목표: plan.md가 각 Gate의 마일스톤/액션을 영구 보존하도록 게이트별 섹션 분리 및 upsert 모드 도입.

문제점:
  - 기존 wo_apply.py는 plan 섹션에 mode: replace 사용
  - 새 Gate 적용 시 이전 Gate 내용이 덮어써짐
  - 결과: plan.md에 최신 Gate 하나만 남음

해결책:
  - 섹션명 변경: "Milestones" → "Milestones — Gate-XX"
  - 모드 변경: replace → upsert
  - upsert_section() 함수: ## 헤더 기준으로 해당 섹션만 갱신/추가
  - apply_plan_patch() 함수: plan.md 전용 패치 핸들러

구현:
  - wo_apply.py에 upsert_section() 추가 (H2 regex 패턴 매칭)
  - apply_plan_patch() 추가 (upsert/append 모드 처리)
  - 메인 루프에서 plan + upsert/append 조합 시 apply_plan_patch() 호출
  - 기존 replace 모드는 하위 호환성 유지 (AUTOGEN 마커 사용)
<!-- AUTOGEN:END:DocOps — Gate-Scoped Plan Sections -->


<!-- AUTOGEN:BEGIN:Experiment Ops — Scope & Principles -->
Judge는 측정을 수행하지 않는다. 모든 SLO 판정은 Gate-T가 산출한 증빙(witness) 아티팩트에만 의존한다.
판정은 최소 2개 독립 구현의 합의(2/3)를 필요로 한다. 합의 실패 시 Fail-Closed.
<!-- AUTOGEN:END:Experiment Ops — Scope & Principles -->


<!-- AUTOGEN:BEGIN:SLO-as-Code — Schema -->
slo.json에 'witness_requirements' 추가:
  - source: gate-t
  - kinds: [histogram, counter, gauge, custom:rag_citation]
  - integrity: sha256(q-ledger hash)
예: RAG_Answer_Standard -> latency_p95_ms, err_rate, citation_cov
<!-- AUTOGEN:END:SLO-as-Code — Schema -->


<!-- AUTOGEN:BEGIN:Runner & Judge -->
runner는 부하 합성/재생만 제공(선택). 판정 데이터는 witness에서만 읽는다.
judge는 3경로 구현: X-190a(codex), C-102(claude), dosctl 내장 DSL. 합의(2/3) 필수.
self-test: gold_witness 케이스 통과 필수.
<!-- AUTOGEN:END:Runner & Judge -->


<!-- AUTOGEN:BEGIN:AB/N-Way & Guarded Rollout -->
승급 조건: (i) witness 정합성 OK, (ii) 합의된 Pass, (iii) 비용가드(S) 미위반.
불일치/누락 시 자동 동결·롤백(최대 TTR 10분).
<!-- AUTOGEN:END:AB/N-Way & Guarded Rollout -->


<!-- AUTOGEN:BEGIN:Cross-Gate Integration — Interface Freeze & Topo Build -->
순환 의존성 해소:
  - Interface Freeze 윈도우: 각 게이트 API/계약은 주 1회(금요일 16:00 KST)만 변경.
  - 변경은 adjacent-gates 승인 필요(Gate-AG 계약 검증기 사용).
  - Topo Build: build_order.json에 의존 그래프 기록, CI에서 위상 정렬 실패시 차단.
  - Mocks/Adapters: 상호 의존 구간은 계약 스냅샷(Mock)으로 단절, 병렬 개발 유지.
<!-- AUTOGEN:END:Cross-Gate Integration — Interface Freeze & Topo Build -->


<!-- AUTOGEN:BEGIN:Performance & Cost Engineering -->
성능 예산:
  - route별 p95/p99, 서버 CPU/RAM, 임베딩/토큰/리랭크 단가 상한을 slo.json에 명세.
  - 부하/회귀: k6/Locust 선택, 러너에서 서브프로세스 호출.
  - 코스트 가드: Gate-S와 동일 임계(월간 예산/테넌트/경로별 상한).
  - 위반 시 judge가 Fail+차단 신호, Gate-Q 레저에 사유 기록.
<!-- AUTOGEN:END:Performance & Cost Engineering -->


<!-- AUTOGEN:BEGIN:API/CLI -->
API:
  - POST /api/v1/exp/run {suite, route_ids[], load, seed}
  - POST /api/v1/exp/judge {run_id}
  - GET  /api/v1/exp/status {run_id}
  - POST /api/v1/exp/abort {run_id}
CLI:
  - dosctl exp run --suite e2e-core --routes RAG_Answer_Standard,Elig_Path_A
  - dosctl exp judge --run-id <id> --export evidence
  - dosctl exp list --status failed --since 7d
  - dosctl exp slo validate --file configs/slo/slo.json
<!-- AUTOGEN:END:API/CLI -->


<!-- AUTOGEN:BEGIN:Observability — Witness Schema & Invariants -->
Witness 필수 필드:
  period_start, period_end, sample_n, coverage_ratio, dropped_spans,
  latency_p95, latency_p99, err_rate, cost_krw, citation_cov, parity_delta,
  watermark_ts, clock_skew_ms, build_id, commit_sha, source_id, sha256, q_ledger_ref.
불변식:
  - period_end >= period_start
  - sample_n >= min_n, coverage_ratio >= min_ratio
  - clock_skew_ms ≤ 50ms (초과시 Stale)
  - sha256(Q-ledger) 일치 필수
<!-- AUTOGEN:END:Observability — Witness Schema & Invariants -->


<!-- AUTOGEN:BEGIN:Observability — Dual/Triple Exporters -->
Exporter 구현 2종 이상(Codex: X-190b-x; Claude: C-190b-c).
합의 규칙:
  - 공통 메트릭 Δ 허용치 이내일 때만 Valid (p95 ≤2%, err ≤0.1pp, cost ≤1%, citation ≤0.5pp, parity ≤0.2pp).
  - 불일치 시 Fail-Closed + discrepancies.csv + 알림.
<!-- AUTOGEN:END:Observability — Dual/Triple Exporters -->


<!-- AUTOGEN:BEGIN:Observability — Backfill & Calibration -->
Backfill Reconcile(일 1회): 원시 로그→재집계→Witness 대조.
Golden Trace Suite: 합성 분포로 p95/p99/err/cost 교정 검증.
Supply Chain: 서명/해시 검증, SBOM, 재현 빌드.
<!-- AUTOGEN:END:Observability — Backfill & Calibration -->


<!-- AUTOGEN:BEGIN:Experiment Ops — CLI & Golden Trace -->
dosctl exp_judge는 witness JSON + ad-hoc DSL(<=,<,>=,>,==,!=, AND-only)을 평가하여 verdicts_cli.json을 산출한다.
기본 경로는 slo.json의 measurement_quorum_tolerances를 참조하며, --expr 모드에서는 단일 DSL에 대해 PASS/FAIL만 출력한다.
Golden Trace 스크립트는 evidence/golden/raw_events.jsonl + witness.json을 생성하고, downstream judge/backfill이 이를 참조하여 self-test를 수행한다.
<!-- AUTOGEN:END:Experiment Ops — CLI & Golden Trace -->


<!-- AUTOGEN:BEGIN:Observability — Backfill Runner & Calibration -->
backfill_runner는기존 witness(primary)와 raw_events.jsonl를 입력으로 받아 재집계(witness exporter_x) → measurement_quorum_tolerances 준수 여부를 평가한다.
산출물: backfill_report.json, discrepancies.csv. Fail 시 metrics별 delta/허용폭을 명시한다.
apps/obs/calibration/golden_trace.py는 가짜 분포를 합성하여 err/p95/coverage 목표에 맞춘 raw/witness 쌍을 생성하고 evidence/obs/golden_trace.md에 기록한다.
<!-- AUTOGEN:END:Observability — Backfill Runner & Calibration -->


<!-- AUTOGEN:BEGIN:Gate-S — Metering v1 -->
- 이벤트 계약: tenant, metric, corr_id, ts, value, tags
- 멱등키: sha256(tenant|metric|corr_id)
- 윈도: hour, 집계: count/sum/min/max
- 리포트: buckets(dict), duplicates(int)
<!-- AUTOGEN:END:Gate-S — Metering v1 -->


<!-- AUTOGEN:BEGIN:Gate-S — Idempotency Store Plugins -->
- Store 인터페이스(IdempoStore)와 구현체 InMemory/SQLite 제공.
- factory: ENV DECISIONOS_METERING_STORE 로 구성 주입.
- ingest API: filter_idempotent_with(store, events), 기존 filter_idempotent는 InMemory 기본.
<!-- AUTOGEN:END:Gate-S — Idempotency Store Plugins -->


<!-- AUTOGEN:BEGIN:Gate-S — Watermark & Lateness -->
- WatermarkPolicy(max_lag_sec, drop_too_late).
- classify: on_time / late_kept / late_dropped.
- aggregate_hourly_with_watermark: 이벤트 타임스탬프 기준 윈도 집계.
- 카운터: duplicates, late_kept, late_dropped.
<!-- AUTOGEN:END:Gate-S — Watermark & Lateness -->


<!-- AUTOGEN:BEGIN:Gate-S — Rating v1 -->
- 입력: ReconcileReport(V1/V2) buckets (metric별 사용량 sum).
- 계획(Plan): metric별 포함량(included), 초과단가(overage_rate) 단순 테이블.
- 출력: subtotal, overage_units, details[].
- 단위/환율/세금은 v1에서 제외(후속 단계).
<!-- AUTOGEN:END:Gate-S — Rating v1 -->


<!-- AUTOGEN:BEGIN:Gate-S — Quota v1 -->
- per-tenant, per-metric soft/hard quota.
- soft 초과시 'throttle' 권고, hard 초과시 'deny'.
- InMemory 상태 저장(후속: pluggable store).
<!-- AUTOGEN:END:Gate-S — Quota v1 -->


<!-- AUTOGEN:BEGIN:Gate-S — Cost-Guard v1 -->
- BudgetPolicy: 월간 한도와 경보 임계(0.8, 1.0).
- EWMA 기반 급증 탐지(알파/임계치) — 간단 모델.
- 조치: alert/freeze/none (fail-closed는 상위 게이트에서).
<!-- AUTOGEN:END:Gate-S — Cost-Guard v1 -->


<!-- AUTOGEN:BEGIN:Gate-T + Gate-S Integration v1 -->
- Witness CSV 더미 파서: apps/obs/witness/io.py (parse_witness_csv).
- Integration test: Witness 4건 → Metering 시간 집계 → Rating 요금 → Quota 한도.
- 전체 파이프라인 검증: tokens=130 (over=30 → 0.6 KRW), quota=throttle.
- v1: 더미 CSV만 지원 (실제 witness 포맷은 별도).
<!-- AUTOGEN:END:Gate-T + Gate-S Integration v1 -->


<!-- AUTOGEN:BEGIN:Integration — Witness↔Metering↔Rating/Quota↔Cost-Guard v1 -->
목적: Gate-T의 witness CSV를 기준으로 Gate-S 전체 체인(rating/quota/cost-guard)을 실행하고,
     판정 근거를 Evidence(JSON)로 스냅샷 저장.
구성:
  - 파서: apps.obs.witness.io::parse_witness_csv()
  - 집계: apps.metering.reconcile.aggregate_hourly_with_watermark(now, policy)
  - 요금: apps.rating.engine.rate_report(plan, report)
  - 한도: apps.limits.quota.apply_quota_batch(tenant, deltas, cfg, state)
  - 예산: apps.cost_guard.budget.check_budget(spent, policy)
  - 이상: apps.cost_guard.anomaly.ewma_detect(series, cfg, current=spent)
  - 스냅샷: apps.obs.evidence.snapshot.build_snapshot(...).to_json()
Evidence 필수 필드:
  - meta: version, generated_at, tenant
  - witness: csv_sha256, rows
  - usage: buckets(sum/min/max/count), deltas_by_metric
  - rating: subtotal, items[metric, included, overage, amount]
  - quota: decisions[metric → action(allow/throttle/deny), used, soft, hard]
  - budget: level(ok/warn/exceeded), spent, limit
  - anomaly: is_spike, ewma, ratio
  - integrity: signature_sha256(메인 필드 정렬 JSON의 SHA-256)
수락 기준:
  - snapshot JSON에 상기 키 존재 및 타입 일치
  - budget.level과 anomaly.is_spike가 테스트 시나리오대로 판정
  - 파일 저장: var/evidence/evidence-YYYYMMDDTHHMMSS.json 생성
<!-- AUTOGEN:END:Integration — Witness↔Metering↔Rating/Quota↔Cost-Guard v1 -->


<!-- AUTOGEN:BEGIN:Gate-AJ — SLO-as-Code v1 -->
목적: Evidence(JSON) ↔ slo.json 비교로 배포/롤아웃 판정 자동화.
구성요소:
  - SLO 스키마: configs/slo/*.json (pydantic 검증)
  - Local Judge: apps.judge.slo_judge.evaluate(evidence, slo)
  - Quorum: apps.judge.quorum.decide(providers, k_of_n)
  - RBAC: judge.run 권한 확인(Hook)
  - CLI: dosctl judge slo --slo ... --evidence ... --quorum 2/3
기본 정책(예):
  - budget.level ∉ {"exceeded"}
  - quota.forbid: {"tokens": ["deny"]}
  - anomaly.is_spike == false (옵션)
  - witness.csv_sha256 필수 & integrity.signature 검증
Fail-Closed:
  - SLO/증빙 파싱 실패, 무결성 검증 실패, witness 누락 시 → FAIL
<!-- AUTOGEN:END:Gate-AJ — SLO-as-Code v1 -->


<!-- AUTOGEN:BEGIN:Security — RBAC Hooks for Judge -->
- 정책키: "judge.run"
- CLI 실행 전에 pep.enforce("judge.run", actor, resource)
- 실패 시 403 스타일 에러로 중단
<!-- AUTOGEN:END:Security — RBAC Hooks for Judge -->
