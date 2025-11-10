from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, TypedDict, Optional

import jsonschema

from apps.rule_engine.engine import load_rules_for_contract, evaluate_rules, load_contract
from apps.switchboard.switch import choose_route
from apps.meter.collector import ingest_event
from apps.audit_ledger.ledger import AuditLedger
from .hooks.checklist import required_docs_hook
from .exceptions import DomainError


_DECISIONS: dict[str, dict] = {}
_LEDGER = AuditLedger()


class DecisionResult(TypedDict, total=False):
    decision_id: str
    contract: str
    org_id: str
    reasons: List[str]
    confidence: float
    required_docs: List[str]
    rules_applied: List[str]
    model_meta: Dict[str, Any]
    rules_version: str
    created_at: str
    input_hash: str


def _hash_obj(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


def _load_json(path: str) -> dict:
    from pathlib import Path

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _validate_payload(contract_name: str, payload: Dict[str, Any]) -> None:
    """Validate payload against contract's input schema if present.

    Raises DomainError(400) on validation failure.
    """
    try:
        contract = load_contract(contract_name)
    except FileNotFoundError as e:
        raise DomainError(f"contract not found: {contract_name}", status_code=404, code="contract_not_found") from e

    schema_ref = contract.get("input_schema")
    if not schema_ref:
        return
    # Resolve path relative to packages/ or project root
    from pathlib import Path

    candidates = [Path(schema_ref), Path("packages") / schema_ref, Path(__file__).resolve().parents[2] / schema_ref, Path(__file__).resolve().parents[2] / "packages" / schema_ref, ]
    schema_path: Optional[Path] = None
    for c in candidates:
        if c.exists():
            schema_path = c
            break
    if not schema_path:
        raise DomainError("input_schema path not found in contract", status_code=500, code="schema_missing")
    schema = _load_json(str(schema_path))
    try:
        jsonschema.validate(instance=payload, schema=schema)
    except jsonschema.ValidationError as e:  # pragma: no cover - exercised in tests
        raise DomainError(f"payload invalid: {e.message}", status_code=400, code="payload_invalid") from e


def decide(contract: str, org_id: str, payload: Dict[str, Any], budgets: Optional[dict[str, float]] = None) -> DecisionResult:
    _validate_payload(contract, payload)
    try:
        ruleset = load_rules_for_contract(contract)
    except FileNotFoundError as e:
        raise DomainError(f"ruleset not found for contract: {contract}", status_code=404, code="rules_missing") from e

    route_meta = choose_route(contract, budgets)
    if isinstance(route_meta, dict) and "budgets" not in route_meta and "budgets_applied" in route_meta:
        try:
            route_meta["budgets"] = route_meta.get("budgets_applied", {})
        except Exception:
            route_meta["budgets"] = budgets or {}

    outcome = evaluate_rules(ruleset, payload)

    # Optional model call (degrade on failure)
    chosen_model = route_meta.get("chosen_model")
    if chosen_model and chosen_model != "rules-only":
        try:
            _invoke_model(route_meta, payload)
        except Exception:
            route_meta["degraded"] = True

    decision_id = str(uuid.uuid4())

    result: DecisionResult = {
        "decision_id": decision_id,
        "contract": contract,
        "org_id": org_id,
        "class": outcome.get("class", "review"),
        "reasons": list(outcome.get("reasons", [])),
        "confidence": float(outcome.get("confidence", 0.5)),
        "required_docs": required_docs_hook(outcome),
        "rules_applied": list(outcome.get("rules_applied", [])),
        "model_meta": route_meta,
        "rules_version": ruleset.version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_hash": _hash_obj(payload),
    }
    _DECISIONS[decision_id] = result  # type: ignore[assignment]
    rec = _LEDGER.append(decision_id, {"input": payload, "output": {k: v for k, v in result.items() if k != "input_hash"}})

    # Optional: persist to DB (best-effort)
    try:  # audit to DB
        from apps.audit_ledger.pg import append_audit_pg  # local import to avoid hard dep when no DB
        append_audit_pg(rec.decision_id, rec.prev_hash, rec.curr_hash, rec.payload, rec.created_at)
    except Exception:
        pass
    try:  # decision to DB
        from apps.db.write import persist_decision
        persist_decision(result)
    except Exception:
        pass

    # metering: count a decision call
    try:
        ingest_event({"org_id": org_id, "project_id": payload.get("project_id"), "metric": "decision_calls", "value": 1, "source": "gateway"})
    except Exception:
        pass

    # cost sentry (best-effort)
    try:
        from apps.cost_sentry.sentry import record_from_meta
        record_from_meta(org_id, route_meta)
    except Exception:
        pass

    return result


def simulate(contract: str, rows: List[Dict[str, Any]], label_key: Optional[str] = None) -> dict:
    tp = fp = tn = fn = reviews = 0
    for row in rows:
        org_id = str(row.get("org_id", "sim"))
        label = row.get(label_key) if label_key else None
        payload = {k: v for k, v in row.items() if k not in {"org_id", label_key}}
        res = decide(contract, org_id, payload)
        klass = res.get("class")
        if label is None:
            if klass == "review":
                reviews += 1
            continue
        # assume label 1 = converted (good), 0 = not converted (bad); reject means bad predicted
        if klass == "reject" and label == 0:
            tp += 1
        elif klass == "reject" and label == 1:
            fp += 1
        elif klass != "reject" and label == 1:
            tn += 1
        elif klass != "reject" and label == 0:
            fn += 1
        if klass == "review":
            reviews += 1
    n = len(rows)
    reject_precision = tp / (tp + fp) if (tp + fp) else 0.0
    reject_recall = tp / (tp + fn) if (tp + fn) else 0.0
    review_rate = reviews / max(n, 1)
    return {"metrics": {"reject_precision": reject_precision, "reject_recall": reject_recall, "review_rate": review_rate, "n": n}}


def explain(decision_id: str) -> dict:
    item = _DECISIONS.get(decision_id)
    if not item:
        raise KeyError("decision_id not found")
    output = {
        "rules_applied": item.get("rules_applied", []),
        "model_meta": item.get("model_meta", {}),
        "input_hash": item.get("input_hash", ""),
        "output_hash": _hash_obj({k: v for k, v in item.items() if k not in {"input_hash"}}),
        "timestamp": item.get("created_at"),
    }
    return output


def _invoke_model(route_meta: Dict[str, Any], payload: Dict[str, Any]) -> None:
    """Placeholder for model invocation.

    Intentionally a no-op for OS-Lite. Raise in tests to simulate failure.
    """
    return None



