# Day 0 체크리스트 (엔지니어링)

**프로젝트**: DecisionOS
**배포 대상**: Production
**예정일**: Sprint 1 완료 후
**최종 업데이트**: 2025-11-02

---

## 📅 배포 전 준비 (D-7 ~ D-1)

### D-7: 인프라 준비

- [ ] **Docker 이미지 빌드 및 테스트**
  ```bash
  docker build -t decisionos-gateway:sprint1 .
  docker run -p 8000:8000 decisionos-gateway:sprint1
  curl http://localhost:8000/health
  ```

- [ ] **Docker Compose 검증**
  ```bash
  make up
  make logs
  # 모든 서비스 healthy 확인
  ```

- [ ] **환경 변수 설정**
  ```bash
  # .env.production 파일 생성
  AUTH_ENABLED=true
  DATA_DIR=/app/packages
  CONTRACTS_DIR=/app/packages/contracts
  LOG_LEVEL=INFO
  ```

- [ ] **볼륨/스토리지 준비**
  - [ ] `/var` 디렉토리 영구 스토리지 마운트
  - [ ] 로그 디렉토리 권한 설정
  - [ ] 백업 스토리지 구성

---

### D-5: 데이터 및 설정 준비

- [ ] **계약(Contract) 적용**
  ```bash
  python cli/dosctl/main.py apply contract \
    packages/contracts/lead_triage.contract.json
  ```

- [ ] **규칙(Rules) 적용**
  ```bash
  python cli/dosctl/main.py apply rules \
    packages/rules/triage
  ```

- [ ] **라우팅(Routes) 설정**
  ```bash
  python cli/dosctl/main.py route set \
    packages/routes/model_routes.yaml
  ```

- [ ] **린트 최종 검증**
  ```bash
  python -m apps.rule_engine.linter packages/rules/triage
  # 예상: No issues found!
  ```

---

### D-3: 테스트 및 검증

- [ ] **전체 테스트 스위트 실행**
  ```bash
  make test
  # 예상: 핵심 모듈 100% 통과
  ```

- [ ] **커버리지 확인**
  ```bash
  make coverage
  # 예상: ≥70% (실제 83%)
  ```

- [ ] **E2E 테스트 (3 시나리오)**
  ```bash
  # 시나리오 1: Approve
  curl -X POST http://localhost:8000/api/v1/decide/lead_triage \
    -H "Authorization: Bearer user@example.com" \
    -H "Content-Type: application/json" \
    -d @packages/samples/requests/lead_triage_01_high_credit.json

  # 시나리오 2: Reject
  curl -X POST http://localhost:8000/api/v1/decide/lead_triage \
    -H "Authorization: Bearer user@example.com" \
    -H "Content-Type: application/json" \
    -d @packages/samples/requests/lead_triage_02_low_credit.json

  # 시나리오 3: Review
  curl -X POST http://localhost:8000/api/v1/decide/lead_triage \
    -H "Authorization: Bearer user@example.com" \
    -H "Content-Type: application/json" \
    -d @packages/samples/requests/lead_triage_04_missing_docs.json
  ```

- [ ] **오프라인 평가 실행**
  ```bash
  make simulate
  # HTML/JSON 리포트 생성 확인
  ```

- [ ] **부하 테스트 (선택)**
  ```bash
  # 100 req/sec로 1분간
  ab -n 6000 -c 10 -T application/json \
    -H "Authorization: Bearer user@example.com" \
    -p packages/samples/requests/lead_triage_01_high_credit.json \
    http://localhost:8000/api/v1/decide/lead_triage
  ```

---

### D-1: 보안 및 모니터링

- [ ] **보안 체크리스트 완료**
  ```bash
  pytest tests/test_security.py -v
  # 예상: 3 passed
  ```

  - [x] 인증(Authentication) 작동
  - [x] 인가(Authorization/RBAC) 작동
  - [x] 데이터 마스킹 활성화
  - [x] 동의 관리 엔드포인트 작동
  - [x] 입력 검증 활성화
  - [x] AST 안전성 검증

- [ ] **로깅 설정 확인**
  ```python
  # apps/gateway/security/logging.py
  # MaskingFilter 활성화 확인
  ```

- [ ] **헬스체크 엔드포인트 테스트**
  ```bash
  curl http://localhost:8000/health
  # 예상: {"status":"healthy"}
  ```

- [ ] **모니터링 대시보드 준비** (선택)
  - [ ] Prometheus metrics 활성화
  - [ ] Grafana 대시보드 구성
  - [ ] 알림 규칙 설정

---

## 🚀 Day 0: 배포 당일

### 배포 전 (09:00 - 10:00)

- [ ] **최종 코드 프리즈**
  - [ ] main 브랜치 lock
  - [ ] 배포 태그 생성: `v1.0.0-sprint1`

- [ ] **백업 생성**
  ```bash
  # 현재 운영 환경 백업
  docker compose down
  tar -czf backup-$(date +%Y%m%d).tar.gz packages/ var/
  ```

- [ ] **배포 체크리스트 최종 확인**
  - [ ] 모든 테스트 통과
  - [ ] 품질 게이트 통과
  - [ ] 문서 최신화
  - [ ] 팀원 배포 준비 완료

---

### 배포 실행 (10:00 - 11:00)

- [ ] **1단계: 서비스 중단**
  ```bash
  make down
  ```

- [ ] **2단계: 새 버전 배포**
  ```bash
  git pull origin main
  git checkout v1.0.0-sprint1
  make up
  ```

- [ ] **3단계: 헬스체크 확인**
  ```bash
  # 30초 대기
  sleep 30
  curl http://localhost:8000/health
  ```

- [ ] **4단계: 스모크 테스트**
  ```bash
  # /decide 엔드포인트 동작 확인
  curl -X POST http://localhost:8000/api/v1/decide/lead_triage \
    -H "Authorization: Bearer user@example.com" \
    -H "Content-Type: application/json" \
    -d '{"org_id":"smoke_test","payload":{"credit_score":750,"dti":0.3,"income_verified":true}}'

  # 예상: HTTP 200 OK
  ```

- [ ] **5단계: 로그 모니터링**
  ```bash
  make logs | grep -i error
  # 심각한 에러 없어야 함
  ```

---

### 배포 후 검증 (11:00 - 12:00)

- [ ] **기능 검증**
  - [ ] /decide 엔드포인트 (3 시나리오)
  - [ ] /simulate 엔드포인트
  - [ ] /explain 엔드포인트
  - [ ] /consent 엔드포인트

- [ ] **성능 모니터링**
  - [ ] 응답 시간 < 500ms
  - [ ] CPU 사용률 < 70%
  - [ ] 메모리 사용률 < 80%

- [ ] **에러율 확인**
  - [ ] 4xx 에러 < 5%
  - [ ] 5xx 에러 = 0%

---

### 롤백 계획 (필요 시)

- [ ] **롤백 트리거 조건**
  - [ ] 헬스체크 실패
  - [ ] 5xx 에러율 > 1%
  - [ ] 응답 시간 > 2초
  - [ ] 서비스 크래시

- [ ] **롤백 절차**
  ```bash
  # 1. 서비스 중단
  make down

  # 2. 이전 버전 복구
  tar -xzf backup-$(date +%Y%m%d).tar.gz

  # 3. 서비스 재시작
  make up

  # 4. 헬스체크
  curl http://localhost:8000/health
  ```

---

## 📊 Day 0 이후 (D+1 ~ D+7)

### D+1: 안정화

- [ ] **24시간 모니터링**
  - [ ] 에러 로그 리뷰
  - [ ] 성능 메트릭스 확인
  - [ ] 사용자 피드백 수집

- [ ] **핫픽스 준비**
  - [ ] 긴급 패치 브랜치 준비
  - [ ] 빠른 배포 프로세스 점검

---

### D+3: 성능 분석

- [ ] **메트릭스 분석**
  ```bash
  # Offline Eval 재실행 (실데이터)
  python cli/dosctl/main.py simulate lead_triage \
    --csv production_data_sample.csv \
    --label label \
    --html-out var/production_eval.html
  ```

- [ ] **비교 분석**
  - [ ] 샘플 데이터 vs 실데이터 결과 비교
  - [ ] 규칙 정확도 검증
  - [ ] 개선 포인트 도출

---

### D+7: 회고 및 개선

- [ ] **배포 회고**
  - [ ] What went well?
  - [ ] What could be improved?
  - [ ] Action items for next sprint

- [ ] **문서 업데이트**
  - [ ] 운영 매뉴얼 보완
  - [ ] 트러블슈팅 가이드 작성
  - [ ] FAQ 업데이트

- [ ] **Sprint 2 계획**
  - [ ] 백로그 우선순위 재조정
  - [ ] 리소스 할당
  - [ ] 일정 확정

---

## ✅ 체크리스트 요약

### 필수 항목 (Must Complete)

| 항목 | 담당자 | 상태 | 완료일 |
|-----|--------|------|--------|
| Docker 이미지 빌드 | DevOps | ☐ | _____ |
| 환경 변수 설정 | DevOps | ☐ | _____ |
| 계약/규칙/라우트 적용 | Dev | ☐ | _____ |
| 전체 테스트 통과 | QA | ☐ | _____ |
| 보안 검증 완료 | Security | ☐ | _____ |
| E2E 테스트 통과 | QA | ☐ | _____ |
| 배포 실행 | DevOps | ☐ | _____ |
| 스모크 테스트 | QA | ☐ | _____ |

### 선택 항목 (Nice to Have)

| 항목 | 담당자 | 상태 | 완료일 |
|-----|--------|------|--------|
| 부하 테스트 | QA | ☐ | _____ |
| 모니터링 대시보드 | DevOps | ☐ | _____ |
| 알림 설정 | DevOps | ☐ | _____ |

---

## 📞 연락처

### 배포 당일 On-Call

| 역할 | 이름 | 연락처 | 백업 |
|-----|------|--------|------|
| Tech Lead | _________ | _________ | _________ |
| DevOps | _________ | _________ | _________ |
| QA | _________ | _________ | _________ |
| Security | _________ | _________ | _________ |

### 에스컬레이션

- **Level 1**: 팀 Slack 채널
- **Level 2**: On-Call Engineer
- **Level 3**: Tech Lead
- **Level 4**: CTO

---

## 📝 배포 로그

| 날짜 | 버전 | 담당자 | 결과 | 비고 |
|-----|------|--------|------|------|
| YYYY-MM-DD | v1.0.0-sprint1 | _________ | ☐ 성공 ☐ 실패 | _________ |

---

**최종 승인**:
- Tech Lead: _________ (서명/날짜)
- PM: _________ (서명/날짜)
- Security: _________ (서명/날짜)
