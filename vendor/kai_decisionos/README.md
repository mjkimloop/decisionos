DecisionOS-Lite (OS-Lite + Lending Pack v1)

This repo contains a minimal but functional DecisionOS kernel with:
- FastAPI gateway exposing /api/v1/decide, /simulate, /explain
- Rule Engine (YAML DSL) and Switchboard
- Executor pipeline with Audit Ledger (append-only JSONL with hash chain)
- CLI `dosctl` to apply configs, run simulations, and export audit
- Offline evaluation harness to produce simple HTML metrics

See docs/runbook.md and docs/api.md for usage.

