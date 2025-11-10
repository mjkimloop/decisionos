# Logging Standard — Structured Logging, PII Scrubbing, Observability

**Version**: 2.0.0
**Last Updated**: 2025-11-04
**Owner**: Platform Observability Team
**Status**: Active

---

## 1. Overview

### 1.1 Purpose

This standard defines **how to log** in DecisionOS services to achieve:
1. **Structured logs**: Machine-parseable (JSON), not freeform text
2. **Correlation**: Link logs to traces (`trace_id`, `span_id`) and business context (`corr_id`)
3. **Security**: Scrub PII/secrets before emission
4. **Cost efficiency**: Sample appropriately, avoid log spam
5. **Actionability**: Logs enable debugging, not just noise

**Scope**: All services (APIs, pipelines, batch jobs, scripts).

---

### 1.2 Log Levels

| Level | Severity | Purpose | Example | Sampling |
|-------|----------|---------|---------|----------|
| **DEBUG** | Verbose details | Dev troubleshooting (not prod by default) | `User input validation passed` | 1% in prod (flag-enabled) |
| **INFO** | Informational | Normal business events | `Decision approved for application_id=123` | 10% (sample non-critical) |
| **WARN** | Warning | Degraded state, non-critical errors | `Retry attempt 2/3 for risk-scoring API` | 100% |
| **ERROR** | Error | Request failed, user-visible impact | `NullPointerException in CreditValidator` | 100% |
| **FATAL** | Critical | Service cannot continue | `Database connection pool exhausted` | 100% + alert |

**Default Level (Production)**: `INFO` (DEBUG disabled unless troubleshooting active incident).

**Key Principle**: *Logs should be signal, not noise.* If you log at INFO, it should be something you'd want to search for later.

---

## 2. Structured Logging Format

### 2.1 JSON Schema

**Every log line MUST be valid JSON** (not freeform text). Enables easy parsing by Loki, Elasticsearch, etc.

**Mandatory Fields**:
```json
{
  "timestamp": "2025-11-04T14:23:45.123Z",        // ISO 8601, UTC
  "level": "ERROR",                               // DEBUG|INFO|WARN|ERROR|FATAL
  "service": "decision-api",                      // Service name (lowercase, hyphenated)
  "environment": "production",                    // production|staging|dev
  "message": "Credit score API timeout",          // Human-readable summary
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", // OpenTelemetry trace ID (hex)
  "span_id": "00f067aa0ba902b7",                  // OpenTelemetry span ID (hex)
  "corr_id": "app-20251104-987654",               // Business correlation ID (application, case, txn)
  "host": "pod-decision-api-5d6f7c8b9-xyz12",     // Pod/instance name
  "version": "2.34.5"                             // App version (semantic versioning)
}
```

**Optional Fields** (context-specific):
```json
{
  "user_id": "user_12345",               // ⚠️ Scrub if PII
  "application_id": "app_98765",         // Business entity ID
  "endpoint": "/api/v1/decisions",       // HTTP endpoint
  "method": "POST",                      // HTTP method
  "status_code": 500,                    // HTTP response code
  "duration_ms": 1234,                   // Request duration
  "error": {                             // Error details (if ERROR/FATAL)
    "type": "NullPointerException",
    "message": "creditScore was null",
    "stack_trace": "..."                 // ⚠️ Scrub file paths, tokens
  },
  "context": {                           // Additional business context
    "credit_score": 650,
    "requested_amount": 50000
  }
}
```

---

### 2.2 Example Logs

**INFO — Successful Decision**:
```json
{
  "timestamp": "2025-11-04T14:23:45.123Z",
  "level": "INFO",
  "service": "decision-api",
  "environment": "production",
  "message": "Decision approved",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "corr_id": "app-20251104-987654",
  "application_id": "app_98765",
  "endpoint": "/api/v1/decisions",
  "method": "POST",
  "status_code": 200,
  "duration_ms": 234,
  "context": {
    "decision": "approved",
    "credit_score": 720,
    "requested_amount": 50000,
    "approved_amount": 50000
  }
}
```

**ERROR — Dependency Timeout**:
```json
{
  "timestamp": "2025-11-04T14:25:12.456Z",
  "level": "ERROR",
  "service": "decision-api",
  "environment": "production",
  "message": "Credit score API timeout",
  "trace_id": "7ac8e3b2c91f4a5d8f6b2e1c9d0a8b3f",
  "span_id": "a1b2c3d4e5f6g7h8",
  "corr_id": "app-20251104-987655",
  "application_id": "app_98766",
  "endpoint": "/api/v1/decisions",
  "method": "POST",
  "status_code": 503,
  "duration_ms": 5001,
  "error": {
    "type": "TimeoutException",
    "message": "Credit score API did not respond within 5s",
    "dependency": "credit-score-api",
    "retry_attempt": 3,
    "retry_max": 3
  }
}
```

**WARN — Retry Attempt**:
```json
{
  "timestamp": "2025-11-04T14:25:08.789Z",
  "level": "WARN",
  "service": "decision-api",
  "environment": "production",
  "message": "Retrying credit score API",
  "trace_id": "7ac8e3b2c91f4a5d8f6b2e1c9d0a8b3f",
  "span_id": "a1b2c3d4e5f6g7h8",
  "corr_id": "app-20251104-987655",
  "application_id": "app_98766",
  "context": {
    "dependency": "credit-score-api",
    "retry_attempt": 2,
    "retry_max": 3,
    "backoff_ms": 2000
  }
}
```

---

## 3. PII & Secret Scrubbing

### 3.1 What to Scrub

**PII (Personally Identifiable Information)**:
- **Names**: Full name, first/last name
- **Contact**: Email, phone, address
- **Government IDs**: SSN, passport, driver's license
- **Financial**: Credit card, bank account, routing number
- **Health**: Medical records, diagnoses (HIPAA)
- **Biometric**: Fingerprints, facial recognition data

**Secrets**:
- **Credentials**: Passwords, API keys, tokens, JWTs
- **Cryptographic**: Private keys, certificates, encryption keys
- **Session**: Session IDs, cookies (if contain PII)

**Safe to Log** (non-PII identifiers):
- **Internal IDs**: `user_id=user_12345` (opaque, not linkable to real identity)
- **Application IDs**: `application_id=app_98765`
- **Correlation IDs**: `corr_id=req-20251104-xyz`
- **Aggregated metrics**: Credit score (numeric), approval rate (percentage)

---

### 3.2 Scrubbing Techniques

**Redaction** (replace with placeholder):
```json
// Before scrubbing:
{
  "message": "User email: alice@example.com applied for loan"
}

// After scrubbing:
{
  "message": "User email: [REDACTED_EMAIL] applied for loan"
}
```

**Hashing** (one-way, preserves uniqueness for correlation):
```json
// Before:
{
  "user_email": "alice@example.com"
}

// After:
{
  "user_email_hash": "5d41402abc4b2a76b9719d911017c592"  // MD5 hash (not reversible, but consistent)
}
```

**Truncation** (show partial data for debugging):
```json
// Before:
{
  "credit_card": "4111-1111-1111-1111"
}

// After:
{
  "credit_card_last4": "1111"  // Only last 4 digits (safe for customer support)
}
```

**Tokenization** (replace with lookup token):
```json
// Before:
{
  "ssn": "123-45-6789"
}

// After:
{
  "ssn_token": "tok_a1b2c3d4e5f6"  // Token maps to SSN in secure vault
}
```

---

### 3.3 Scrubbing Rules (Regex Patterns)

**See**: [configs/pii_scrub_rules.yaml](../configs/pii_scrub_rules.yaml) for full ruleset.

**Common Patterns**:
```yaml
scrub_rules:
  - name: email
    pattern: '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    replacement: '[REDACTED_EMAIL]'

  - name: ssn
    pattern: '\b\d{3}-\d{2}-\d{4}\b'
    replacement: '[REDACTED_SSN]'

  - name: credit_card
    pattern: '\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'
    replacement: '[REDACTED_CC]'

  - name: phone_us
    pattern: '\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    replacement: '[REDACTED_PHONE]'

  - name: jwt_token
    pattern: '\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b'
    replacement: '[REDACTED_JWT]'

  - name: api_key
    pattern: '\b(api[_-]?key|apikey|access[_-]?token)[\s:=]+[A-Za-z0-9_-]{20,}\b'
    replacement: '[REDACTED_API_KEY]'
    case_insensitive: true
```

**Application**:
- **Pre-emit**: Scrubbing happens in logging library before log written to disk/network
- **Post-collection**: Additional scrubbing in log aggregator (defense-in-depth)

---

### 3.4 PII Scrubbing — Code Example

**Python (using custom logger)**:
```python
import logging
import re
from pythonjsonlogger import jsonlogger

class PIIScrubber(logging.Filter):
    def filter(self, record):
        # Scrub message
        record.msg = self.scrub(record.msg)
        # Scrub context (if dict)
        if isinstance(record.args, dict):
            record.args = {k: self.scrub(str(v)) for k, v in record.args.items()}
        return True

    def scrub(self, text):
        # Email
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', text)
        # SSN
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED_SSN]', text)
        # Credit card
        text = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[REDACTED_CC]', text)
        return text

# Configure logger
logger = logging.getLogger("decision-api")
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(timestamp)s %(level)s %(service)s %(message)s %(trace_id)s %(span_id)s'
)
handler.setFormatter(formatter)
handler.addFilter(PIIScrubber())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Example usage
logger.info("User alice@example.com submitted application", extra={
    "trace_id": "abc123",
    "corr_id": "app-001"
})
# Output (email scrubbed):
# {"timestamp": "...", "level": "INFO", "message": "User [REDACTED_EMAIL] submitted application", ...}
```

---

## 4. Correlation IDs

### 4.1 Trace Context (OpenTelemetry)

**Propagation**: `trace_id` and `span_id` injected into logs automatically by OTel SDK.

**Middleware** (auto-inject trace context):
```python
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# Flask app
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# Logging middleware (inject trace_id into every log)
@app.before_request
def inject_trace_context():
    span = trace.get_current_span()
    g.trace_id = format(span.get_span_context().trace_id, '032x')
    g.span_id = format(span.get_span_context().span_id, '016x')

# Custom logger filter
class TraceContextFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = getattr(g, 'trace_id', 'N/A')
        record.span_id = getattr(g, 'span_id', 'N/A')
        return True

logger.addFilter(TraceContextFilter())
```

**Result**: Every log line includes `trace_id` and `span_id` → Can jump from log to trace in Jaeger.

---

### 4.2 Business Correlation ID

**Purpose**: Link logs across multiple requests for a single business transaction.

**Example**: User submits application → Creates decision → Triggers HITL review → Sends notification.
- All 4 steps have different `trace_id` (separate requests)
- All 4 share same `corr_id=app-20251104-987654` (same application)

**Generation**:
```python
from datetime import datetime, UTC

# At application creation
corr_id = f"app-{datetime.now(UTC).strftime('%Y%m%d')}-{application.id}"

# Pass to downstream services (HTTP header)
headers = {"X-Correlation-ID": corr_id}
requests.post("https://hitl-api/cases", json=payload, headers=headers)

# Log with corr_id
logger.info("Application created", extra={"corr_id": corr_id})
```

**Querying**:
```bash
# Find all logs for a specific application
dosctl logs search --query 'corr_id="app-20251104-987654"'
```

---

## 5. Sampling & Rate Limiting

### 5.1 Why Sample?

**Problem**: High-traffic services generate millions of logs/day → Cost, storage, performance overhead.

**Solution**: Sample low-value logs (e.g., INFO "request received"), keep high-value (ERROR, WARN).

---

### 5.2 Sampling Strategy

**Tail-Based Sampling** (keep logs for interesting requests):
```
Rule 1: Keep 100% of ERROR/FATAL logs
Rule 2: Keep 100% of logs where duration > p95 (slow requests)
Rule 3: Keep 100% of logs where status_code >= 500
Rule 4: Sample 10% of INFO logs (uniform random)
Rule 5: Sample 1% of DEBUG logs (only if DEBUG enabled)
```

**Implementation** (pseudo-code):
```python
def should_log(level, status_code, duration_ms):
    # Always log errors
    if level in ['ERROR', 'FATAL']:
        return True
    # Always log slow requests
    if duration_ms > p95_threshold:
        return True
    # Always log server errors
    if status_code >= 500:
        return True
    # Sample INFO (10%)
    if level == 'INFO':
        return random.random() < 0.1
    # Sample DEBUG (1%)
    if level == 'DEBUG':
        return random.random() < 0.01
    return False
```

**Result**: Keep critical logs (100%), reduce noise (90% of INFO dropped).

---

### 5.3 Rate Limiting (Per-Logger)

**Problem**: Infinite loop logs same error 1M times → Log bomb, storage exhausted.

**Solution**: Rate-limit per logger (e.g., max 100 logs/sec from same source).

**Implementation** (using token bucket):
```python
from ratelimit import limits, RateLimitException

class RateLimitedLogger(logging.Logger):
    @limits(calls=100, period=1)  # Max 100 logs/sec
    def _log(self, level, msg, args, **kwargs):
        try:
            super()._log(level, msg, args, **kwargs)
        except RateLimitException:
            # Silently drop (or emit 1 "logs dropped" message)
            pass
```

**Fallback**: If rate limit hit, emit summary log: `"Dropped 5000 logs in last 1s (rate limit exceeded)"`

---

## 6. Log Retention & Storage

### 6.1 Retention Policy

| Log Level | Retention (Raw) | Retention (Aggregated) | Storage |
|-----------|-----------------|------------------------|---------|
| **DEBUG** | 7 days | N/A (not aggregated) | Hot (SSD) |
| **INFO** | 30 days | 1 year (daily rollups) | Warm (HDD) |
| **WARN** | 90 days | 2 years | Warm |
| **ERROR/FATAL** | 1 year | 7 years (compliance) | Cold (S3 Glacier) |

**Aggregation** (reduce storage cost):
- After 30 days, INFO logs aggregated to daily summaries (counts, top errors, etc.)
- Raw logs deleted, only summaries kept

**Compliance**:
- ERROR/FATAL logs retained for 7 years (audit trail for regulatory investigations)

---

### 6.2 Storage Optimization

**Compression**: gzip (90% reduction for JSON text)

**Indexing**: Index on `timestamp`, `service`, `level`, `trace_id`, `corr_id` only (not every field).

**Partitioning**: Store logs by date (daily partitions) → Faster queries, easier deletion.

**Example** (Loki query):
```logql
{service="decision-api", level="ERROR"}
  | json
  | corr_id="app-20251104-987654"
```
→ Queries only ERROR logs for decision-api on 2025-11-04 partition.

---

## 7. Observability Integration

### 7.1 Logs ↔ Traces ↔ Metrics

**Flow**:
1. **User request** → Generates trace (`trace_id`)
2. **Application logs** → Include `trace_id` in every log line
3. **Metrics** → Label with `trace_id` (exemplar support in Prometheus)

**Example Workflow**:
```
1. User sees error "Decision failed"
2. Support finds trace_id in UI: trace_id=abc123
3. Query logs: dosctl logs search --query 'trace_id="abc123"'
   → Shows ERROR: "Credit score API timeout"
4. Query trace: Open Jaeger, search trace_id=abc123
   → Shows 5s spent waiting for credit-score-api
5. Query metrics: Prometheus → credit_score_api_duration{quantile="0.95"}
   → Confirms p95 latency spiked to 5s at that time
```

**Result**: Seamless navigation logs → traces → metrics (no manual correlation).

---

### 7.2 Log-Based Alerts

**Use Case**: Alert on ERROR logs (not just metrics).

**Example** (Prometheus Alertmanager):
```yaml
- alert: HighErrorLogRate
  expr: |
    sum(rate(log_entries_total{level="ERROR", service="decision-api"}[5m])) > 10
  for: 5m
  annotations:
    summary: "decision-api logging >10 errors/sec"
    action: "Check logs: dosctl logs tail decision-api --level error --since 10m"
```

**Advantage**: Catches errors that don't surface in metrics (e.g., background jobs, async tasks).

---

## 8. Implementation Guide

### 8.1 Logging Libraries (by Language)

| Language | Library | Structured JSON | OTel Integration |
|----------|---------|-----------------|------------------|
| **Python** | `python-json-logger` + `opentelemetry-instrumentation` | ✅ | ✅ |
| **Java** | `logback` + `logstash-logback-encoder` + `opentelemetry-java` | ✅ | ✅ |
| **Go** | `zap` + `opentelemetry-go` | ✅ | ✅ |
| **Node.js** | `winston` + `@opentelemetry/instrumentation` | ✅ | ✅ |

---

### 8.2 Configuration Template (Python)

**File**: `logging_config.yaml`
```yaml
version: 1
disable_existing_loggers: false

formatters:
  json:
    class: pythonjsonlogger.jsonlogger.JsonFormatter
    format: '%(timestamp)s %(level)s %(service)s %(message)s %(trace_id)s %(span_id)s %(corr_id)s'

filters:
  pii_scrubber:
    (): myapp.logging.PIIScrubber
  trace_context:
    (): myapp.logging.TraceContextFilter

handlers:
  console:
    class: logging.StreamHandler
    formatter: json
    filters: [pii_scrubber, trace_context]
    stream: ext://sys.stdout

loggers:
  myapp:
    level: INFO
    handlers: [console]
    propagate: false

root:
  level: WARNING
  handlers: [console]
```

**Usage**:
```python
import logging.config
import yaml

with open('logging_config.yaml') as f:
    config = yaml.safe_load(f)
logging.config.dictConfig(config)

logger = logging.getLogger('myapp')
logger.info("Application started", extra={"version": "2.34.5"})
```

---

## 9. Anti-Patterns (What NOT to Do)

### 9.1 Freeform Text Logs

❌ **Bad**:
```python
logger.info("User alice@example.com submitted app 123 for $50000")
```
**Problems**:
- Not machine-parseable (can't query by amount)
- PII (email) exposed
- No structure (can't filter by user or application)

✅ **Good**:
```python
logger.info("Application submitted", extra={
    "user_id": "user_12345",  # Opaque ID, no PII
    "application_id": "app_123",
    "requested_amount": 50000
})
```

---

### 9.2 Logging Secrets

❌ **Bad**:
```python
logger.debug(f"API key: {api_key}")
```
**Risk**: API key leaked to logs → Attacker gains access.

✅ **Good**:
```python
logger.debug(f"API key: {api_key[:8]}***")  # Show only first 8 chars (or scrub entirely)
```

---

### 9.3 Log Spam

❌ **Bad**:
```python
for item in items:
    logger.info(f"Processing item {item}")  # Logs 1M times if items is large
```
**Problem**: Log bomb, storage exhausted.

✅ **Good**:
```python
logger.info(f"Processing {len(items)} items")
# Log only summary, or sample (1%)
for i, item in enumerate(items):
    if i % 100 == 0:
        logger.debug(f"Processed {i}/{len(items)} items")
```

---

### 9.4 Missing Context

❌ **Bad**:
```python
logger.error("Validation failed")
```
**Problem**: No context (which field? which user? which request?).

✅ **Good**:
```python
logger.error("Validation failed", extra={
    "field": "credit_score",
    "value": None,
    "application_id": "app_123",
    "trace_id": trace_id
})
```

---

## 10. Compliance & Audit

### 10.1 Regulatory Requirements

**GDPR (EU)**:
- **Right to erasure**: User can request deletion → Logs with PII must be scrubbed or deleted
- **Minimization**: Only log PII if necessary (prefer opaque IDs)

**CCPA (California)**:
- Similar to GDPR (user can request deletion of logs containing PII)

**SOX (Financial)**:
- Audit trail: Retain ERROR/FATAL logs for 7 years (prove no unauthorized changes)

**HIPAA (Healthcare)**:
- Protect PHI (health info): Scrub diagnoses, medical records from logs

---

### 10.2 Audit Trail Best Practices

**What to Log** (for compliance):
- **Who**: User ID (not email/name, use opaque ID)
- **What**: Action (created, updated, deleted)
- **When**: Timestamp (UTC, ISO 8601)
- **Where**: Service, endpoint
- **Result**: Success/failure

**Example**:
```json
{
  "timestamp": "2025-11-04T14:23:45.123Z",
  "level": "INFO",
  "service": "decision-api",
  "message": "Decision approved",
  "actor_id": "user_12345",        // Who
  "action": "decision.approve",    // What
  "resource_id": "app_98765",      // Which resource
  "result": "success"              // Outcome
}
```

**Storage**: Immutable (write-once), tamper-evident (cryptographic checksums).

---

## 11. Monitoring & Alerting

### 11.1 Log-Based Metrics

**Export metrics from logs** (via Loki/Promtail):
```promql
# Count ERROR logs per service
sum(rate(log_entries_total{level="ERROR"}[5m])) by (service)

# Top error messages
topk(5, count_over_time({level="ERROR"} | json | unwrap message [1h]))
```

**Alerts**:
```yaml
- alert: HighErrorLogRate
  expr: sum(rate(log_entries_total{level="ERROR", service="decision-api"}[5m])) > 10
  for: 5m
  annotations:
    summary: "decision-api logging >10 errors/sec (investigate)"
```

---

### 11.2 Log Anomaly Detection

**Use Case**: Detect unusual log patterns (e.g., sudden spike in "TimeoutException").

**Approach**:
1. **Baseline**: Normal ERROR rate: 1/min
2. **Anomaly**: ERROR rate spikes to 100/min
3. **Alert**: ML-based anomaly detection (e.g., Prometheus `anomaly_detection` or custom model)

**Tool**: Loki + Grafana Machine Learning plugin.

---

## 12. References

- **OpenTelemetry Logging**: https://opentelemetry.io/docs/specs/otel/logs/
- **Google SRE — Observability**: https://sre.google/workbook/monitoring/
- **PII Scrubbing Rules**: [configs/pii_scrub_rules.yaml](../configs/pii_scrub_rules.yaml)
- **SLI/SLO Catalog**: [sli_slo_catalog.md](sli_slo_catalog.md) (log-based SLIs)
- **Oncall Runbook**: [ops/runbook_oncall.md](../ops/runbook_oncall.md) (how to query logs during incidents)

---

## 13. Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0.0 | 2025-11-04 | Observability Team | Gate-T: Add OTel trace context, PII scrubbing, sampling strategy |
| 1.1.0 | 2025-08-01 | Dev Team | Add correlation ID, business context fields |
| 1.0.0 | 2025-05-01 | Platform Team | Initial structured logging standard |

---

**END OF DOCUMENT**
