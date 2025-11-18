# Judge Readyz Policy (Fail-Closed)

## Checks

1. **Key freshness** — `MultiKeyLoader.info()` must report ≥1 active key and `age_seconds <= DECISIONOS_KEY_GRACE_SEC`.
2. **Replay store** — `.ping()` succeeds for the configured replay backend (SQLite or Redis).
3. **Clock skew config** — `DECISIONOS_CLOCK_SKEW_MAX > 0`.
4. **Storage ping** — `var/judge/readyz.probe` writable.

All failures are reported under `/readyz` as:

```json
{
  "status": "fail",
  "checks": {
    "keys": {"key_count": 0, "reason": "keys.missing"},
    "replay": {"reason": "replay.unreachable:..."},
    "clock": {"max_skew": 10},
    "storage": {"reason": "storage.write_failed:..."}
  }
}
```

## Modes

- `DECISIONOS_READY_FAIL_CLOSED=1` (default) → any failure returns HTTP 503.
- `DECISIONOS_READY_FAIL_CLOSED=0` → degraded mode returns HTTP 200 with `"status": "degraded"`.

## Runbook

1. **Keys** — ensure KMS/SSM secrets up to date, rerun `MultiKeyLoader.force_reload()`.
2. **Replay** — verify Redis or SQLite path accessibility; restart service on failure.
3. **Clock** — update env var `DECISIONOS_CLOCK_SKEW_MAX`.
4. **Storage** — check disk space/permissions on `var/judge`.

## CI

`pytest -q -m gate_aj` covers fail-closed permutations (missing keys, broken replay store, invalid skew).
