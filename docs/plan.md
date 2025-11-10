<!--
version: v0.5.11p-1ponmmllki.2i.2i.1ihgfedcbaccbabaaa
date: 2025-11-11
status: locked
summary: Ops Reason Trend 카드 API에 캐싱/ETag 및 RBAC(ops:read) 보호 추가
-->

# DecisionOS Implementation Plan

## Milestones — Gate-A
W2 Gate-A 마일스톤(현행):
- /decide e2e 3케이스 200 OK, 평균 <300ms(모델 미호출)
- dosctl simulate → JSON+HTML 리포트 산출
- 보안 최소통제 6/6 체크 통과
- 감사 NDJSON 해시 체인(prev→curr) 일관 확인

## Next Actions — Gate-A
Day 0–1: 스키마/DSL/Executor 코어
Day 2: Gateway 3 API + dosctl
Day 3: Switchboard 폴백 + Offline Eval 리포트
Day 4–5: 보안 6/6 + Lending 규칙 6개 튜닝

## Milestones — Gate-B
Gate‑B 마일스톤(현행):
- 조기신호 3개 중 2개 달성(2주 관찰 윈도)
- 보안 6/6 **문서화** 및 점검표 서명본
- PoV Runbook, 위험분담표, 롤백계획 완성
- 실벤더 라우팅(모의→실) 드라이런 1회

## Next Actions — Gate-B
Day 6–7: 메트릭 수집/노출(/metrics), 감사 리플레이 강화
Day 8: Consent API /grant|/revoke|/list 구현 + RBAC 라우트 보호
Day 9: Switchboard openai 어댑터(실 호출 제한/예산) + 폴백 테스트
Day 10: PoV Runbook 초안(운영절차/장애대응/데이터보호) + 위험분담표 완성

## Milestones — Gate-C
Gate‑C 마일스톤(드라이런 완료 조건):
- docker-compose 기동 + 스모크 성공
- 커넥터 v1로 샘플 1,000행 이상 적재 성공
- Reality‑Seal 재실행(4게이트 유지)
- Runbook/롤백 리허설 1회 기록

## Next Actions — Gate-C
Day 14: 도커 패키징(Dockerfile/compose/Makefile) + env.sample
Day 15: 커넥터 v1(CSV/Sheets/S3) + APScheduler 폴링 러너
Day 16: 관측성(/metrics 확장·로그 회전) + 로드테스트 1차
Day 17: 익명화 시드 생성(≥1,000행) + 대량 ingest 드라이런
Day 18: Runbook/롤백 스크립트 완성 + Reality‑Seal 재실행

## Milestones — Gate-D
Gate‑D 마일스톤(현장 PoV 준비 완료):
- 테넌트 구성 적용(tenant.yaml) + 재로드 엔드포인트 동작
- 커넥터 자격증명 설정 후 초기 적재 ≥10k
- 관측성/보안 증빙 바인더 구비
- 드레스리허설(현장 시나리오) 1회 통과, Go/No‑Go 자료 승인

## Next Actions — Gate-D
Day 19: 테넌트 구성 로더/미들웨어 + X‑Tenant‑ID 전파
Day 20: DPA/Consent 라우팅 점검(tenant scope) + IP Allowlist 적용
Day 21: 커넥터 자격증명 설치(secrets/) + 초기 ingest(≥10k) + DLQ triage
Day 22: /metrics 테넌트 라벨 추가, 로그 보존/회전 정책 점검
Day 23: Reality‑Seal(고객 데이터) 재실행 + 리포트/바인더 정리
Day 24: 드레스리허설 + Go/No‑Go 미팅팩(요약/위험/롤백)

## Milestones — Gate-E
Gate‑E 마일스톤(유료 PoV 개통):
- SOW/Order Form/가격표 패키지 승인 및 서명
- usage_events 수집→summary 집계→인보이스 PDF 발행(드라이런)
- /billing 경로 e2e 캡처 + Evidence Binder 반영
- No‑Gemini 유지, OpenAI 비용 전가 경로 문서화

## Next Actions — Gate-E
Day 25: SOW/Order Form/가격표 패키지(문서) 동결
Day 26: usage_events 수집기 + idempotency/HMAC 구현
Day 27: 집계기/요약 API + dosctl usage/invoice preview
Day 28: billing_engine PDF + finalize 흐름, Evidence Binder 추가
Day 29–30: 드레스리허설(실데이터) → 첫 인보이스 발행

## Milestones — Gate-F
Gate‑F 마일스톤(완료 조건):
- RLS 정책/마이그레이션 적용 + 교차 접근 차단 테스트 통과
- mt-lite docker-compose 구동 + standby 복제 동기화
- DR/Failover 리허설 1회 → 보고서 첨부
- 글로벌 /global/metrics 노출 + 테넌트/리전 라벨 검증

## Next Actions — Gate-F
Day 31: RLS 정책/스크립트 작성 + 테넌트 미들웨어 강화
Day 32: mt-lite compose 작성(standby DB 포함) + 백업/로그 전송 세팅
Day 33: 글로벌 메트릭스 엔드포인트 + 라우터 region 라벨링
Day 34: Failover/Failback 스크립트 + 드라이런 문서화
Day 35: 교차 테넌트 차단 테스트/리포트 + Evidence Binder 갱신

## Milestones — Gate-G
Gate‑G 마일스톤(완료 조건):
- 자동 Failover 드라이런 2회 통과(RTO≤20m, split‑brain 0)
- 프로브 3종 배포 + 디그레이드 동작 캡처
- 카나리 5%→25%→100% 롤아웃 24h 내 무사 통과
- 에러버짓 대시보드/정책 문서화 및 적용

## Next Actions — Gate-G
Day 36: 프로브 3종 구현 + 라우팅 디그레이드 연동
Day 37: Auto‑failover controller(watcher/promoter) + 펜싱
Day 38: 카나리 라우터/플래그 + 롤백 훅, /admin/canary
Day 39: 카오스 스크립트/DR 드릴 + /admin/failover/simulate
Day 40: 에러버짓 계산/노출 + 문서/런북 업데이트

## Milestones — Gate-H
Gate‑H 마일스톤(완료 조건):
- OTEL 전파(X-Corr-ID/Span) + traces.ndjson/OTLP 중 택1 정상 수집
- Cost Sentry: 사전예측→예산검사→폴백/차단 e2e
- Vendor v2: local/openai 마이그레이션 + capabilities 노출
- Reality‑Seal 재실행(품질게이트 유지) + 오버헤드 측정 리포트

## Next Actions — Gate-H
Day 41: correlation middleware + otel span 컨텍스트/로그 연동
Day 42: exporter(traces.ndjson/OTLP), 샘플링/테일샘플링 + /traces API
Day 43: Cost Sentry 모듈(estimate/enforce) + switchboard 통합
Day 44: Vendor v2 ProviderBase/Registry + openai/local 마이그레이션
Day 45: /costs/summary, /vendors/capabilities, /admin/sampling + Reality‑Seal 재실행

## Milestones — Gate-I
Gate‑I 마일스톤(완료 조건):
- Policy Engine v1 배포(DSL+평가기) + /policy 시뮬레이터
- PII Vault v1 배포(seal/unseal/rotate) + consent/RBAC 연동
- HITL v1(대기열·승인 액션·SLA·에스컬레이트) + 리포트
- Reality‑Seal 재실행(보안/재현성 영향 0) + PII 스캔 통과

## Next Actions — Gate-I
Day 46: 정책 DSL 스키마/린터 + 평가 순서/집행 지점 구현
Day 47: Vault service(seal/unseal) + 키 저장소/로테이션 스크립트
Day 48: HITL API/대기열/승인·반려 + reason_codes.yaml
Day 49: /policy validate/simulate + dosctl policy/vault/hitl 확장
Day 50: PoV 시나리오 리허설(정책→HITL→재시도) + Reality‑Seal 재실행

## Milestones — Gate-J
Gate‑J 마일스톤(완료 조건):
- 스키마/린터/시뮬레이터/스캐폴더 제공
- packs API/dosctl 연동 → import/enable/disable 동작
- 초기 도메인 팩 3종 발행(lending, collections, ecommerce)
- Reality‑Seal 재실행 + 도메인별 증빙

## Next Actions — Gate-J
Day 51: 스키마 정의/린터/밸리데이터 구현
Day 52: 스캐폴더/임포트·서명 검증/레지스트리 메타
Day 53: 시뮬레이터(drivers) + /packs API + dosctl pack/ scaffold
Day 54: 도메인 팩 3종 시드 작성 + datasets 합성
Day 55: PoV 대상에 lending_brokerage 팩 적용 드라이런 + Reality‑Seal

## Milestones — Gate-K
Gate‑K 마일스톤(완료 조건):
- docs/site 빌드/배포 + 내비 동기화
- /signup → tenant 부트스트랩 e2e
- pricing 계산기 페이지 + 요율 반영
- support 인테이크/트리아지 동작 + SLA 측정
- status 페이지 공개 + 인시던트 템플릿 준비
- Go/No‑Go 리뷰팩(운영/법무/영업) 승인

## Next Actions — Gate-K
Day 56: mkdocs 테마/내비 구성 + ToS/Privacy/DPA 초안 업로드 + status 스켈레톤
Day 57: /signup API + tenant bootstrap 서비스 + welcome 메일/키 발급
Day 58: pricing 계산기(프론트/백엔드) + /costs/summary 연동
Day 59: support 인테이크(메일→큐) + SLA 계측 + incident 템플릿/상태페이지 완성
Day 60: 샌드박스 트라이얼 e2e 드라이런 + Evidence Binder 업데이트 + Go/No‑Go

## Milestones — Gate-L
Gate‑L 마일스톤(완료 조건):
- 이벤트 SDK(서버·프론트) + 수집/집계 라우트 가동
- 퍼널/리텐션/리스크 API + 대시보드 1차본 공개
- NPS 스니펫/이메일 루프 가동 + detractor 핸들링 런북 연결
- 백로그 API/우선순위 스코어러 + 주간 분류 회의 운용 개시

## Next Actions — Gate-L
Day 61: 이벤트 스키마·SDK·수집기 배포(샘플 계기 장착)
Day 62: 퍼널 계산기/리텐션 코호트·리스크 스코어러 구현
Day 63: NPS 스니펫/이메일·피드백 라우트·분류기 v1
Day 64: 웹 대시보드(퍼널/활성/리텐션/NPS) + /analytics API
Day 65: 백로그 API·RICE 스코어러 + 주간 분류 의식(문서)

## Milestones — Gate-M
Gate‑M 마일스톤(완료 조건):
- ratebook.yaml/entitlements.yaml 확정·적용 + 라인아이템 생성 검증
- self‑serve API/UI + 프로레이션·세금·쿠폰 동작
- payments 어댑터 + 웹훅 검증·던닝 워크플로우 가동
- 대조/정확도 리포트 + Evidence Binder(Billing v2) 업데이트

## Next Actions — Gate-M
Day 66: ratebook/entitlements 스키마·적용기 + 좌석 일할/프로레이션 구현
Day 67: self‑serve API(업/다운/취소/재개/결제수단/쿠폰) + 단위테스트
Day 68: payments 어댑터/웹훅 + 멱등/HMAC + 던닝 잡
Day 69: UI(billing center) 1차본 + 인보이스 PDF 템플릿
Day 70: 대조/정확도 테스트 50건 + Evidence Binder 업데이트

## Milestones — Gate-N
Gate‑N 마일스톤(완료 조건):
- OIDC 서버/클라이언트 플로우 + JWKS/Introspect/Logout e2e
- Org/Projects 리소스 모델/마이그레이션 + API 가동
- RBAC 엔진/미들웨어 + 권한 매트릭스/감사 연동
- Access Review & JIT Elevation + 2인 승인 경로
- Reality‑Seal 재실행(보안 영향 0)

## Next Actions — Gate-N
Day 71: OIDC issuer·JWKS·/authorize|/token 구현, 세션/쿠키·PKCE·회전
Day 72: Org/Projects 스키마·마이그레이션 + API(생성/목록/삭제)
Day 73: RBAC 엔진(roles→perms, scope) + 게이트웨이 집행 미들웨어
Day 74: Invite/Users·PAT·Audit 해시체인 + Access Review/JIT 승격
Day 75: Admin UI 최소본(RBAC/Projects) + Reality‑Seal·보안 스캔

## Milestones — Gate-O
Gate‑O 마일스톤(완료 조건):
- 커넥터 프레임워크/카탈로그 + 등록/실행 API·CLI
- Data Contracts v1·레지스트리·린터·호환성 검사기
- ETL/CDC 파이프라인(변환·온톨로지 매핑·적재) + 격리 큐
- 품질 대시·SLO 측정 + Evidence Binder(Data) 업데이트

## Next Actions — Gate-O
Day 76: connector SDK·registry·register/list API + local_csv/s3_csv 구현
Day 77: postgres_logical CDC + kafka_topic 소비자 + idempotency 키 처리
Day 78: data_contracts 스키마/린터/호환성 검사기 + /contracts API
Day 79: transforms(cleanse/pii_mask/ontology_map) + pipelines create/run/backfill
Day 80: 품질 대시·SLO 집계 + DecisionContract 연동 샘플 e2e

## Milestones — Gate-P
Gate‑P 마일스톤(완료 조건):
- 카탈로그 스키마/레지스트리 + 인덱서/검색 API
- 계보 v2 수집기/저장/임팩트 API + 그래프 UI
- 데이터 제품 레지스트리/빌더 + publish/rollback 흐름
- 증빙: 성능/SLO/보안 테스트 리포트 + Evidence Binder(Catalog)

## Next Actions — Gate-P
Day 81: catalog schema·registry·indexer(FTS) + /catalog, /search API
Day 82: lineage_edges 스키마·수집기 + /lineage/graph, /impact API
Day 83: product.yaml 스키마·빌더·/products API + publish/rollback
Day 84: UI(web/catalog, web/lineage, web/products) 1차본 + 캡처 스크립트
Day 85: 성능·보안 테스트·SLO 증빙 + Evidence Binder 업데이트

## Milestones — Gate-Q
Gate‑Q 마일스톤(완료 조건):
- Guardrails v2(입출력 검증·정책·롤아웃) + /guardrails API/CLI
- Explainability(Trace/Reason/Attribution/Evidence Export) + /decisions/explain
- Audit Trail(해시체인) + Replay Runner + /audit, /replay
- Drift 모듈·대시보드 + 알림/롤백 연동
- Evidence Binder(Model) 섹션 업데이트

## Next Actions — Gate-Q
Day 86: guardrails validators/enforcer + canary/rollout + /guardrails API
Day 87: rule trace/reason codes 스키마 + explain API + PDF/JSON exporter
Day 88: audit hash-chain logger + model_card 저장 + replay runner
Day 89: drift metrics/alerts + monitor API + 대시보드
Day 90: 성능/보안 시험·SLO 증빙 + Evidence Binder(Model) 업데이트

## Milestones — Gate-R
Gate-R 마일스톤(완료 조건):
  - Case/Task/Queue/SLA 모델·API·CLI·UI
  - 라우팅 엔진·오버플로우·페어니스·스킬 매칭
  - Appeals 레이어·템플릿·evidence export
  - 감사 연동·PII 스크럽·보존/레드액션
  - SLO/리포트·운영 런북/Evidence Binder(Ops)

## Next Actions — Gate-R
Day 91: 데이터 모델·마이그레이션·/cases·/tasks 기본 API + dosctl(cases|tasks)
Day 92: 라우팅 엔진(스킬/우선순위/공정성) + /queues, SLA 타이머/브리치
Day 93: Appeals API/UI + export(설명서 PDF/JSON), 템플릿
Day 94: Inbox/Case UI·단축키·체크리스트·첨부 업로드(AV/PII)
Day 95: SLO 시험·리포트·감사 링크 검증·런북/Evidence 업데이트

## Milestones — Gate-S
Gate-S 마일스톤(완료 조건):
  - Org/Project/RBAC 모델·마이그레이션·API/CLI
  - Plans/Entitlements/Quotas 적용기 + 미들웨어
  - Metering 수집기/집계기/조회 API + 유효성 테스트
  - Billing(요금계산/인보이스) + Export(PDF/JSON) + Stub 결제
  - Cost Guard(원가피드/마진/경보/대시)
  - Evidence Binder(Billing/Ops) 업데이트

## Next Actions — Gate-S
Day 221: Gate-T Witness 대조 통합 테스트(witness_vs_metering)
Day 222: Cost-Guard 조치의 Evidence(치명 로그) 연동 및 RBAC hook
## Milestones — Gate-T
- backfill_runner CLI (witness+raw) + Δ 보고
- calibration/golden_trace.py 스크립트 및 문서
- daily cron에서 golden trace → backfill → judge 스모크 자동화
## Next Actions — Gate-T
Day 201: 스키마/인변식 구현, Δ 허용치 적용
Day 202: exporter_x/exporter_c 가동 · Δ 비교 리포트
Day 203: backfill_runner 배치, golden_trace 교정
Day 204: 알림/대시 카드, Q-ledger 앵커링 점검
Day 205: 문서/런북 PR
## Milestones — Gate-U
- PG 어댑터/코어 상태머신/웹훅 검증
- KYC 수집·검증·보존 + HITL 연계
- 정산/대사·수수료 처리 + 리포트
- 세금/VAT 룰 + 영수증 발행
- 운영 런북·증빙 번들(Evidence Binder: Payments/KYC)

## Next Actions — Gate-U
Day 106: payments_core(세션/의도/상태머신) + adapters(manual, stripe_stub) + /payments API
Day 107: webhook_verify 공통·멱등키·재시도·감사 연동 + dosctl(pay)
Day 108: KYC 수집/검증 스텁(adapter_kyc_stub) + /kyc API + HITL 큐 연동
Day 109: settlement/recon 배치 + 수수료 라인 + 리포트 UI
Day 110: VAT/세금 룰·영수증 PDF/JSON + SLO·증빙·런북 마감

## Milestones — Gate-V
- 샌드박스/권한/서명 체인 · 설치/업데이트/롤백
- SDK(py/node) · 스캐폴드/로컬 실행기
- 플러그인 계약(Decision/Connector/Policy) v1
- 레지스트리/마켓(베타) · 설치/감사
- 웹훅/임베드 위젯(읽기 전용) · Evidence Bundle

## Next Actions — Gate-V
Day 111: 샌드박스 실행기(ext-run)·리소스/네트워크 가드·권한 스키마
Day 112: 서명/검증 파이프라인·`dosctl ext sign|push` · 설치/롤백 API
Day 113: SDK(py/node)·스캐폴드·HelloWorld(Decision/Connector)
Day 114: 레지스트리/마켓(베타)·카드 뷰·설치 감사
Day 115: 웹훅/임베드(읽기)·보안 시험·SLO 증빙·Evidence 업데이트

## Milestones — Gate-W
- PDP/PEP/정책저장소·언어(v1) · 정책 번들 서명/배포
- 카탈로그 태깅 + 경계/거주지 강제 · Export 통제
- DB RLS/CLS/마스킹/토큰화 · API 후처리 PEP
- Consent/Purpose Binding · 감사 라벨/리포트
- 테스트/런북/증빙 번들(보안/정책)

## Next Actions — Gate-W
Day 116: abac_eval(PDP) · cedar-lite parser · policy_store + dosctl policy lint|eval
Day 117: PEP 미들웨어(API/Gateway/SQL) · deny-by-default 적용 · 오버헤드 측정
Day 118: 카탈로그 태깅·경계/거주지 검사 · export 통제(목적/티켓/만료토큰)
Day 119: RLS/CLS/Masking/Tokenization 구현 · 단위/회귀 테스트 60+
Day 120: Consent/Purpose Binding · 롤아웃/롤백·증빙/런북·SLO 검수

## Milestones — Gate-X
- edge_agent + secure_store + pkg signer/verify
- store-and-forward 큐 + syncd(증분/해시체인/재전송)
- ABAC-subset 컴파일러 + edge 정책 평가기 + break-glass
- 관측성/빌링 연동 + 디바이스 수명주기(등록/폐기)
- e2e 테스트/게임데이(48h 오프라인) + 증빙 번들

## Next Actions — Gate-X
Day 121: edge_agent 골격, secure_store(AES-GCM), pkg 서명/검증
Day 122: outbox 큐, sync 프레임(해시/시그), 재시도/멱등, dosctl edge 기본
Day 123: ABAC-subset 컴파일/평가기, break-glass·감사 라벨
Day 124: heartbeat/attestation, obs/billing 적재, 24h 오프라인 리허설
Day 125: 48h 오프라인 게임데이, 성능/무결성 리포트, Evidence 정리

## Milestones — Gate-Y
- 계층형 백업·무결성 검증 파이프라인
- DR 자동화(API/CLI)·트래픽 전환
- Chaos/GameDay 시나리오·운영 대시/리포트
- Residency/Policy 정합·감사 라벨·접근 통제
- RPO/RTO 실측 충족·증빙 번들

## Next Actions — Gate-Y
Day 126: 백업 파이프라인(db 물리/논리, objects, meta)·무결성 검증 샌드박스
Day 127: DR API/CLI(failover/failback)·DNS/Traffic 연계·카나리 전환
Day 128: Chaos 주입기·게임데이 스크립트·대시/리포트 패널
Day 129: Residency/Policy 연동·접근권한·감사 라벨·자동 증빙
Day 130: P0/P1 게임데이 실행(RPO/RTO 실측)·런북/Evidence 확정

## Milestones — Gate-Z
- AppSec/SBOM/공급망 가드 + 펜테스트 리포트
- Load/Soak/Spike 테스트·용량/오토스케일 정책
- Legal/Privacy 문서·DSAR/쿠키·삭제 워크플로
- Packaging/Pricing·Billing 정합·오버리지 처리
- Support/SRE·Status Page·Sev/SLA·릴리즈 관리·롤아웃·문서 번들

## Next Actions — Gate-Z
Day 131: SAST/DAST·시크릿/IaC 스캔·SBOM 생성·CVE 게이팅 · PenTest 스코프 정의
Day 132: 부하/침수/스파이크 시나리오·HPA 튜닝·자동 롤백 트리거 검증
Day 133: ToS/Privacy/DPA/Subprocessors 게시·DSAR/쿠키/삭제 워크플로 구현
Day 134: SKUs/쿼터/오버리지·청구 정합·Status Page/Support 포털
Day 135: CAB·릴리즈 노트·코호트 롤아웃·Evidence Binder(GA) 확정

## Milestones — Gate-AA
- ICP/포지셔닝/메시지 맵·금지표현·법무 검토
- 이벤트 택소노미·퍼널 대시보드·PQL 규칙·PLG 가드
- CRM 어댑터/라우팅/시퀀서·템플릿·SLA 타이머
- 채널 실행(SEO/컨텐츠/웨비나)·파트너 프로그램(v1)
- 가격/패키징 실험·증빙/Evidence Bundle

## Next Actions — Gate-AA
Day 136: ICP/메시지 맵 초안 + 금지표현·법무 검토/승인(ko)
Day 137: events.yaml v1 + 대시보드 카드(퍼널/CAC/LTV) + PQL 규칙 구현
Day 138: CRM adapter(generic/stub) + 리드 라우터 + 시퀀서 MVP + SLA 타이머
Day 139: 채널 킷(가이드/케이스스터디/웨비나) + 파트너 등급/정책 + 마켓 연동
Day 140: 가격 실험 스위치·쿠폰·환불흐름 + GTM Evidence 정리·SLO 검수

## Milestones — Gate-S
- 테넌시/격리/네임스페이스 · 빌링 스코프
- 메터링 수집/정합 파이프라인 · 오차 검증
- 레이팅/플랜/프레이싱 · 프러레이션
- 쿼터/스로틀/코스트가드 v1
- 인보이스 드래프트 · API/CLI · 증빙 번들

## Next Actions — Gate-S
Day 141: tenancy 모델/스키마/RLS 매핑 · billing scope 태그
Day 142: meter_event 스키마/수집·멱등/워터마크 · usage(obs) 대조
Day 143: rating 엔진 · 플랜/계층단가/프레이션 · 대시 카드
Day 144: quota/throttle/guard · 예산/알림 · freeze/override
Day 145: invoice draft JSON/PDF · SLO 검수 · Evidence(Billing/Cost)

## Next Actions — Gate-S
D+0: apps/tenancy/models.py/service.py 스캐폴드 · db/migrations/tenancy.sql 초안
D+1: apps/metering/{schema,ingest,reconcile} · ingest.apply_event(source-aware lag)
D+2: rating {plans,engine,proration} · configs/billing/pricing.yaml · dashboards/billing/*
D+3: limits {quota,throttle} · cost_guard {budget,anomaly(EWMA),actions} · Evidence 훅
D+4: invoice {draft,pdf} · routers/* · dosctl billing · tests/test_gate_s_* · 리포트/증빙 생성

## Milestones — Gate-U
- PSP 어댑터/게이트웨이/웹훅 · 멱등/서명검증
- 세금 어댑터·영수증 렌더 · KR/EU 프리셋
- Dunning 파이프라인·Downgrade/Freeze 연동(Gate-S)
- 대사/정산·서브레저 · 리포트
- e2e 테스트/증빙 번들(결제/환불/세금/정산)

## Next Actions — Gate-U
Day 146: pay_gateway(Stripe/Generic/KR-stub) · webhook 서명검증 · idempotency
Day 147: tax_adapter · receipt PDF/JSON · invoice_draft 연동(Gate-S)
Day 148: dunning 일정/알림/조치 훅 · downgrade/freeze 통합
Day 149: reconcile 매칭/불일치 큐 · subledger 분개 · 리포트 카드
Day 150: e2e 시나리오(성공/실패/환불/차지백) · SLO 측정 · Evidence 정리

## Milestones — Gate-Q
- Decision Ledger v1(체인 해시·7년 보존) · Evidence Export
- Replay Engine · Explain Layer(rule_path/shap or surrogate)
- Change Registry(모델/규칙/정책) · 4-eyes/CAB-lite
- HITL 큐/조치/SLA · 샘플링 QA
- API/CLI · 대시/리포트 · Evidence Bundle(Audit)

## Next Actions — Gate-Q
Day 151: decision_record 스키마·체인해시·evidence exporter
Day 152: replay.py(버전 고정 로딩)·불일치 diff 리포트
Day 153: explain(rule_path/reason_codes, shap-surrogate 어댑터)
Day 154: change registries·impact report·4-eyes/CAB-lite·카나리/롤백 훅
Day 155: HITL 큐/조치/SLA·API/CLI 정리·SLO 측정·Evidence(Audit)

## Milestones — Gate-AB
- 커리큘럼/템플릿/금지표현 정리(법무 리뷰)
- Lab Runner/Grader·합성 데이터 키트·샌드박스 토큰
- Exam Engine·Item Bank·배지/증서 발급
- Partner Tracks·PQL/세일즈 라우팅 Hook
- 대시보드/리포트·Evidence(Academy)

## Next Actions — Gate-AB
Day 156: 커리큘럼 아웃라인·템플릿·금지표현(ko)·법무 리뷰
Day 157: Lab runner/grader·합성 데이터셋·자동채점 기준
Day 158: Exam 엔진·문항은행·배지/증서 템플릿(JSON/PDF)
Day 159: Partner 트랙 요건·PQL/세일즈 라우팅 Hook(e2e)
Day 160: 대시보드·레포트·SLO 측정·Evidence(Academy)

## Milestones — Gate-AC
- 코스트 온톨로지/귀속 엔진
- 유닛 이코노믹스·쇼백/차지백 리포트
- 예측/예산 계획 엔진
- 옵티마이저(모델/배치/스토리지/커넥터)
- 커밋먼트 관리·대시보드·증빙

## Next Actions — Gate-AC
Day 161: cost_model/attribution 스키마·엔진 · billing/obs 대조
Day 162: unit economics 리포트 · showback/chargeback 스텁
Day 163: forecast 엔진(p50/p90) · budget_suggest · 대시 카드
Day 164: optimizers(model_policy/router_cost/batcher/cache/sampler/storage_lifecycle)
Day 165: commitments 관리/활용률 · API/CLI · SLO 측정 · Evidence(FinOps)

## Milestones — Gate-AD
- Discovery/Classification · 태깅/맵
- Consent/Purpose · PEP 연동
- Retention/Lifecycle · Vault(Tokenization)
- DSAR 엔진/Redactor/Exporter · 통지
- Legal Hold · API/CLI · Evidence/대시

## Next Actions — Gate-AD
Day 166: discovery 스캐너/분류기 · 카탈로그 태깅/맵 산출
Day 167: consent/purpose 모델·PEP 훅 · 정책 교차검증
Day 168: retention 스케줄러·삭제/익명화·vault 토큰화
Day 169: dsar 엔진/검증/레닥터/익스포터 · 통지 템플릿
Day 170: legal_hold · API/CLI · SLO 측정 · Evidence(Privacy)

## Milestones — Gate-AE
- Safety Policies v2 · Detector Suite(PI/JB/DLP/URL/PII)
- Toolcall Guard(전/후 훅·샌드박스·쿼터)
- Router Hardening(정책 통합)
- Red Team Harness(코퍼스/시나리오/리포트)
- 대시/증빙·SLO 측정

## Next Actions — Gate-AE
Day 171: safety_policies 초안 · detectors(PI/JB/DLP) 스캐폴드
Day 172: toolcall_guard 전/후 훅 · 샌드박스/쿼터 통합(Gate-S limits)
Day 173: router_hardening 통합 · 안전 스코어 반영 로직
Day 174: redteam runner · corpora seed · 리포트 카드
Day 175: API/CLI · 대시보드 · SLO 측정·Evidence(Safety) 정리

## Milestones — Gate-AF
- Region/Residency 모델·구성(매트릭스/라벨)
- PEP 훅·Router(LLM/API/Jobs) 통합
- Transfer 평가/승인/레저·SCC 번들
- Orchestrator(복제/승격/회수)·지연/실패 복구
- 대시/증빙·SLO 측정

## Next Actions — Gate-AF
Day 176: regions.yaml/transfer_matrix.yaml · models/service 스캐폴드
Day 177: PEP 훅(residency) · Router 통합(LLM/API)
Day 178: transfer assessor/ledger · 승인흐름(Q 연계) · SCC 템플릿
Day 179: orchestrator(복제/승격/회수) · lag 측정 · 실패 보상
Day 180: API/CLI · 대시보드 · SLO 측정 · Evidence(Residency)

## Milestones — Gate-AG
- Ontology v2 스키마/핸드북/스타일가이드
- Decision Graph 엔진/플래너
- DecisionContract v2 + 검증기
- Source Mapping 정의 + 검증
- Codegen 파이프라인(모델/DB/그래프/클라이언트)
- 대시/증빙·SLO 측정

## Next Actions — Gate-AG
Day 181: 핵심 타입 스키마(Entity/Event/Decision/Policy) · 핸드북/스타일가이드
Day 182: Decision Graph 엔진/플래너 스켈레톤 · .dot/.json export
Day 183: Contract v2 스키마·검증기 · API/CLI validate
Day 184: Mapping 정의/검증 · PII/Residency 태깅 교차검사(AD/AF)
Day 185: Codegen 파이프라인(파이썬/SQL/그래프/클라이언트) · CI drift 체크 · 대시/증빙

## Milestones — Gate-AH
- 레지스트리/계약(AG 링크) · 환경 재현
- 피처스토어(offline/online) · 파리티 체커
- 학습/평가/패키징/서빙 파이프라인
- 스큐/드리프트 감지 · 롤아웃/롤백 자동화
- 대시/증빙 · SLO 측정
## Next Actions — Gate-AH
Day 186: Model Registry/Env manifest · DecisionContract v2 연결(AG)
Day 187: Feature Store offline/online 스캐폴드 · parity_checker
Day 188: Train/Eval/Serve 파이프라인 · router_adapter
Day 189: Skew/Drift detectors · alerts · retrain triggers
Day 190: Shadow/Canary/BlueGreen · API/CLI · 대시/증빙 · SLO 측정
## Milestones — Gate-Scoped
- wo_apply.py에 upsert_section() + apply_plan_patch() 추가
- 메인 루프 plan 타겟 감지 로직 추가
- plan_migrate.py 스크립트로 기존 내용 게이트별 분리
- 모든 Gate work order 검증 및 테스트

## Next Actions — Gate-Scoped
Day 191: wo_apply.py 수정 완료 (upsert 함수 + 라우팅)
Day 192: plan_migrate.py 작성 및 실행 (기존 내용 복원)
Day 193: 전체 Gate work order 재적용 테스트 (A~AH 37개)
Day 194: doc_guard.py 검증 통과
Day 195: 문서화 및 PR 체크리스트 완료

## Milestones — Gate-DocOps
- wo_apply.py에 upsert_section() + apply_plan_patch() 추가
- 메인 루프 plan 타겟 감지 로직 추가
- plan_migrate.py 스크립트로 기존 내용 게이트별 분리
- 모든 Gate work order 검증 및 테스트

## Next Actions — Gate-DocOps
Day 191: wo_apply.py 수정 완료 (upsert 함수 + 라우팅)
Day 192: plan_migrate.py 작성 및 실행 (기존 내용 복원)
Day 193: 전체 Gate work order 재적용 테스트 (A~AH 37개)
Day 194: doc_guard.py 검증 통과
Day 195: 문서화 및 PR 체크리스트 완료

## Milestones — Gate-AJ
- dosctl exp_judge DSL 모드 릴리스(기본 slo.json+ad-hoc)
- golden_trace self-test 번들(evidence/golden/*)
- verdicts_cli.json → witness 참조 자동화
## Next Actions — Gate-AJ
Day 201: Gate-T witness exporter 스키마/샘플
Day 202: X-190a(codex) judge 구현 · gold_witness 작성
Day 203: C-102(claude) judge 구현 · dosctl DSL 판
Day 204: quorum 합의/불일치 처리 · AH/S 훅 교체
Day 205: 백테스트 크론 · Evidence/대시 업데이트

## Milestones — Gate-S v1
- schema/ingest/reconcile 구현
- test_metering_contract_v1 Green
- requirements-dev에 pydantic 추가

## Milestones — Gate-S v1.1
- store.py/factory.py 추가
- plugin 테스트: InMemory/SQLite 중복 필터 검증
- .gitignore var/ 보강

## Milestones — Gate-S v1.2
- watermark.py 추가, reconcile V2 함수 추가
- test_watermark_lateness_v1 Green

## Milestones — Gate-S v1.3
- rating/ plans.py + engine.py
- limits/ quota.py
- cost_guard/ budget.py + anomaly.py (+ actions stub)
- 단위 테스트 3종 Green

## Milestones — Gate-S v1.4
- apps/obs/witness/io.py (CSV 파서)
- tests/integration/test_witness_vs_metering_rating_quota_v1.py
- End-to-end smoke: witness → metering → rating → quota

## Next Actions — Integration
Day 221: Gate-T Witness 대조 통합 테스트(witness_vs_metering) ✓
Day 222: Cost-Guard 조치의 Evidence 연동 + RBAC hook

## Milestones — v0.5.11f
- Evidence 스냅샷 모듈(apps/obs/evidence/snapshot.py) 추가
- 통합 테스트(test_integration_costguard_evidence_v1.py) Green
- 스냅샷 파일 저장 및 해시 무결성 확인

## Next Actions — v0.5.11f
Day 222: 통합 테스트 Green 및 Evidence 샘플 커밋
Day 223: slo.json 기반 Judge(멀티쿼럼) 연계 스냅샷(v0.5.11g)

## Milestones — v0.5.11g
- slo_schema.py, slo_judge.py, quorum.py 구현
- CLI: dosctl judge slo ... 추가
- 테스트: gate_aj 3종(단일판정, 쿼럼 2/3, 무결성 실패)
- 샘플 slo 파일 2종 추가 (canary, strict)

## Next Actions — v0.5.11g
Day 223: 코드/테스트/CLI Green
Day 224: CI 매트릭스(gate_aj) 확장 및 샘플 evidence/slo 아카이브

## Milestones — v0.5.11h
- Witness: perf.py + CLI 추가
- Evidence: perf 블록 병합 지원
- SLO 스키마/저지: latency/error 정책 추가
- 샘플 SLO v2 2종 (canary/strict)
- 테스트: gate_t(1), gate_aj(2), integration(1) Green

## Next Actions — v0.5.11h
Day 223: perf witness/CLI 구현 및 단위테스트
Day 224: slo(latency/error) + judge 확장, 통합테스트 및 CI 매트릭스 업데이트

## Milestones — v0.5.11i
- Provider ABC/Local/HTTP 구현
- Pool quorum_decide 구현
- providers.yaml 샘플
- Evidence.judges 블록 병합
- CLI: dosctl judge quorum --slo ... --evidence ... --providers ... --quorum 2/3
- 테스트: unit 6, integration 2, e2e 1 (모두 Green)

## Next Actions — v0.5.11i
Day 224: providers/base/local/http, pool, 서명 로직
Day 225: Evidence.judges 병합, CLI, 테스트/CI 매트릭스 업데이트

## Milestones — v0.5.11i.1
- CLI dosctl judge quorum 구현
- Evidence.judges 병합 옵션(--attach-evidence)
- Anti-Replay(minimal SQLite) 유틸(테스트용)
- 단위/통합/E2E 테스트 그린
- CI 매트릭스 업데이트(gate_aj async)

## Next Actions — v0.5.11i.1
Day 224: CLI/증빙 병합/반복방지 유틸
Day 225: unit+integration+e2e 테스트, CI 확장, 커밋/태깅

## Milestones — v0.5.11i.2
- crypto: multi-key loader + verify
- providers: HTTP 헤더 kid/nonce/timestamp + 서명
- replay: ABC + SQLite/Redis 플러그인
- rbac: PEP 강제, CLI 진입점 연결
- ci: release_gate 스텝 추가
- time: utcnow→UTC 리팩터 스크립트
## Next Actions — v0.5.11i.2
Day 226: crypto/provider/replay 구현 + 단위테스트
Day 227: RBAC/CLI/통합/E2E 테스트, utcnow 리팩터
Day 228: CI release_gate 활성화, 문서 갱신

## Milestones — v0.5.11k
- M1: controller/shadow/compare 스켈레톤 + 정책 파일
- M2: Evidence.canary 병합 + Judge canary 판정
- M3: 통합/E2E + CI release gate

## Next Actions — v0.5.11k
Day 232: controller.py, shadow.py, compare.py, 정책/샘플 CSV
Day 233: evidence.canary 병합, slo-canary.json, judge 확장
Day 234: 통합/E2E/CI 파이프라인, strict infra gate on

## Milestones — v0.5.11l
Day 1-2: 배포 파이프라인 훅 연결(옵션A/B 중 택1), 환경변수/시크릿 배선
Day 3: 로그→Evidence 자동화(Job/Cron) + 보존정책
Day 4: KMS 키 로테이션 드라이런 + RBAC 정책 배포
Day 5: SLO 알람/런북 + CI 릴리스 게이트 확장(운영 스텝)
## Next Actions — v0.5.11l
• pipeline/release: canary_step.sh, promote.sh, abort.sh 추가
• configs/: ingress-mirror.* 또는 rollouts/*.yaml 추가
• jobs/: evidence_harvest_{reqlog,judgelog}.py + cron 스케줄
• docs/ops/: RUNBOOK-SLO.md, RUNBOOK-ROLLBACK.md, CLI-DEPLOY.md


<!-- AUTOGEN:BEGIN:Acceptance — v0.5.11l -->
- 카나리 단계(최소 25/50/100)에서 shadow_capture→canary_compare→judge quorum 2/3 통과 시만 promote
- reqlog/judgelog로부터 Evidence(perf, perf_judge, canary) 자동 생성·업로드, SHA256 무결성 검증
- KMS 키 로테이션 드라이런 성공(활성/예비 교대, 만료키 거부, 로그 남김)
- SLO 알람 트리거 시 rollout 자동 pause 및 증빙 링크 포함 알림
<!-- AUTOGEN:END:Acceptance — v0.5.11l -->


<!-- AUTOGEN:BEGIN:Out of Scope — v0.5.11l -->
- Gate-O/P 기능 본개발(별도 v0.5.12에서 착수)
<!-- AUTOGEN:END:Out of Scope — v0.5.11l -->

## Milestones — v0.5.11m
- Day 1: indexer/clock_guard/chaos·DR 스크립트 추가, 로컬 스모크
- Day 2: CI pre-gate(clock) → evidence_harvest → indexer → infra·canary gate 순서 확정
- Day 3: S3 ObjectLock 잡(옵션) 연결, 운영 런북 보강
## Next Actions — v0.5.11m
- jobs/evidence_indexer.py, apps/obs/evidence/indexer.py
- jobs/evidence_objectlock.py (옵션, boto3)
- apps/common/clock.py, jobs/clock_guard.py
- pipeline/chaos/chaos_inject.sh, pipeline/release/abort_on_gate_fail.sh
- tests/* 스모크 추가, CI 매트릭스에 pre-gate 삽입

## Milestones — v0.5.11n
- RBAC default-deny 적용(pep.py)
- SLO 인프라 파라미터(min_samples/window/grace) 반영
- evidence GC 잡(dry-run 포함) + CI 프리게이트 삽입
- stage 서명 사이드카 도입 및 테스트 보강


<!-- AUTOGEN:BEGIN:Pre/Release Gates -->
- Pre-gate: clock_guard → evidence_indexer → evidence_gc(dry-run) → artifacts
- Release-gate: infra/canary SLO → 실패 시 abort_on_gate_fail.sh
<!-- AUTOGEN:END:Pre/Release Gates -->

## Milestones — v0.5.11o
Day 1: Reasons 표준화 훅 적용(slo_judge) + 문서(REA S ONS.md)
Day 2: Stage Safe-Mode 구현(controller/stage_file)
Day 3: GC 외부화 로더 + 잡 갱신(indexer/gc)
Day 4: CLI 종료코드 E2E, 문서 반영
Day 5: grace_burst 경계 테스트 추가 및 CI 매트릭스 편입

## Next Actions — Ops Hardening
• CI에 pre_gate: clock_guard → evidence_index → gc(dry-run) 아티팩트 업로드
• release_gate: infra+canary SLO 통과 시에만 promote
• RUNBOOK 갱신: 이유코드/롤백/키미설정 시 Safe-Mode 동작

## Milestones — v0.5.11p
Day 1: API/스크립트 구현 및 단위 테스트
Day 2: CI 배선(PR 코멘트/레이블러) 및 아티팩트 링크 검증
Day 3: 운영문서 업데이트(Ops API/대시보드 카드)


<!-- AUTOGEN:BEGIN:Releases -->
- v0.5.11p: Ops Trend API, PR artifacts 링크, Top-impact 레이블러
- v0.5.11p-1: Ops 카드 API 캐싱/ETag + RBAC(ops:read)
<!-- AUTOGEN:END:Releases -->

## Milestones — v0.5.11p-1
Day 1: cache/etag/RBAC 적용 및 단위 테스트
Day 2: CI 매트릭스에 gate_ops 포함, API 304 경로 스모크
