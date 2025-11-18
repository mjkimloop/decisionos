# Security Hardening — Ops & Judge

## Middleware Stack

| Layer | Description | Env |
|-------|-------------|-----|
| Security headers | HSTS, CSP, Referrer, Permissions, NoSniff | `DECISIONOS_SECURITY_HEADERS_ENABLE=1` |
| Trusted proxy enforcement | `X-Forwarded-*` only honored when the immediate peer IP matches the CIDR allow list | `DECISIONOS_TRUSTED_PROXY_CIDRS` |
| Host allow list | Rejects traffic whose `Host/X-Forwarded-Host` values do not match the configured list | `DECISIONOS_ALLOWED_HOSTS`, `DECISIONOS_JUDGE_ALLOWED_HOSTS` |
| Rate limiting | Memory token bucket by default; optional Redis backend | `DECISIONOS_RL_ENABLE`, `DECISIONOS_RL_BACKEND`, `DECISIONOS_REDIS_DSN` |
| PII middleware | Request/response redaction (default OFF) | `DECISIONOS_PII_ENABLE` |

### Recommended Header Set

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Referrer-Policy: no-referrer
Permissions-Policy: geolocation=(), microphone=()
X-Content-Type-Options: nosniff
```

## Rate Limiting Profile

- Defaults: 600 requests/min window, burst of 120.
- Enable via `DECISIONOS_RL_ENABLE=1`.
- Memory-based limiter for single-node dev, Redis (`DECISIONOS_RL_BACKEND=redis`) for multi replica.
- Scope format: `ops:read` for Ops routes, `judge:<client_ip>` for Judge requests.

## Proxy Trust

1. Determine outbound proxy CIDRs (e.g. `10.0.0.0/8,192.168.0.0/16`).
2. Set `DECISIONOS_TRUSTED_PROXY_CIDRS` accordingly.
3. Only when the upstream client IP matches one of those CIDRs will `X-Forwarded-For/Host` be honored.
4. `DECISIONOS_ALLOWED_HOSTS` and `DECISIONOS_JUDGE_ALLOWED_HOSTS` define canonical hostnames that must appear on inbound requests.

## ReadyZ Fail Closed

- Enable via `DECISIONOS_READY_FAIL_CLOSED=1` (default). Any key/replay/clock/storage check failure returns HTTP 503 with structured JSON.
- Disable temporarily with `DECISIONOS_READY_FAIL_CLOSED=0` during maintenance to avoid flapping.

## CI Security Checks

| Stage | Command |
|-------|---------|
| pre_gate | `python -m scripts.ci.secret_scan --paths apps --fail-on-hit 1` |
| pre_gate | `python -m scripts.ci.pii_lint --paths apps --exclude tests --fail-on-hit 1` |
| pre_gate | `python -m scripts.ci.pip_audit_wrapper --requirements requirements.txt --out var/ci/pip_audit.json` |
| pre_gate | `python -m scripts.ci.license_check --requirements requirements.txt --allow "MIT,BSD,Apache-2.0"` |
| gate | `pytest -q -m "gate_aj or gate_ops"` + Judge quorum |
| post_gate | Artifact bundle `var/ci/security_artifacts.tgz` + PR annotation |

Failing any pre_gate step stops the workflow.
