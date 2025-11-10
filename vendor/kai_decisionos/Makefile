PY=python

.PHONY: up test gate-a docs-guard simulate audit-export

up:
	uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000

test:
	$(PY) -m pytest -q

test-cov:
	$(PY) -m pip install -q pytest-cov
	$(PY) -m pytest --cov=apps/rule_engine --cov=apps/executor --cov=apps/gateway --cov-report=term-missing:skip-covered -q

docs-guard:
	$(PY) scripts/doc_guard.py

simulate:
	$(PY) -m cli.dosctl.main simulate lead_triage packages/samples/offline_eval.sample.csv --label-key label

audit-export:
	$(PY) -m cli.dosctl.main audit export var/audit_export.jsonl

# Gate-A 판정 자동화(개략)
gate-a: docs-guard
	$(PY) -m pytest -q apps/rule_engine apps/executor/tests apps/switchboard/tests
	$(MAKE) -s simulate
	@echo "Gate-A checks executed (manual review: e2e / security / audit hash)."
.PHONY: down logs seed

# Gate-C scaffolds
down:
	docker compose -f infra/docker-compose.yml down || true
logs:
	docker compose -f infra/docker-compose.yml logs -f || true
seed:
	$(PY) scripts/anonymize_seed.py packages/samples/offline_eval.sample.csv var/seed_anonymized.csv || true
