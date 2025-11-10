from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .store import STORE
from .parser import PolicyRule

SAFE_GLOBALS: Dict[str, Any] = {
    "__builtins__": {},
    "any": any,
    "all": all,
    "len": len,
    "min": min,
    "max": max,
    "set": set,
}


@dataclass
class RuleEvaluation:
    policy_ref: str
    effect: str
    priority: int
    matched: bool
    when_result: bool | None = None
    unless_result: bool | None = None
    purpose: str | None = None
    error: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    bundle: str | None = None


@dataclass
class Decision:
    allow: bool
    effect: str
    policy_id: str | None = None
    reason: str | None = None
    purpose: str | None = None
    bundle: str | None = None
    trace: List[RuleEvaluation] = field(default_factory=list)


def evaluate(subject: Dict[str, Any], action: str, resource: Dict[str, Any], context: Dict[str, Any]) -> Decision:
    trace: List[RuleEvaluation] = []
    candidates = _candidate_policies(action)

    for priority, order, bundle_name, policy, metadata in candidates:
        policy_ref = policy.policy_id or f"{bundle_name}:{order}"
        metadata = dict(metadata)
        try:
            when_result = _eval_expression(policy.when, subject, action, resource, context)
        except Exception as exc:
            trace.append(
                RuleEvaluation(
                    policy_ref=policy_ref,
                    effect=policy.effect,
                    priority=policy.priority,
                    matched=False,
                    when_result=None,
                    unless_result=None,
                    purpose=policy.purpose,
                    error=f"when_error:{exc}",
                    metadata=metadata,
                    bundle=bundle_name,
                )
            )
            continue

        if not when_result:
            trace.append(
                RuleEvaluation(
                    policy_ref=policy_ref,
                    effect=policy.effect,
                    priority=policy.priority,
                    matched=False,
                    when_result=False,
                    unless_result=None,
                    purpose=policy.purpose,
                    metadata=metadata,
                    bundle=bundle_name,
                )
            )
            continue

        unless_result: bool | None = None
        if policy.unless:
            try:
                unless_result = _eval_expression(policy.unless, subject, action, resource, context)
            except Exception as exc:
                trace.append(
                    RuleEvaluation(
                        policy_ref=policy_ref,
                        effect=policy.effect,
                        priority=policy.priority,
                        matched=False,
                        when_result=True,
                        unless_result=None,
                        purpose=policy.purpose,
                        error=f"unless_error:{exc}",
                        metadata=metadata,
                        bundle=bundle_name,
                    )
                )
                continue
            if unless_result:
                trace.append(
                    RuleEvaluation(
                        policy_ref=policy_ref,
                        effect=policy.effect,
                        priority=policy.priority,
                        matched=False,
                        when_result=True,
                        unless_result=True,
                        purpose=policy.purpose,
                        metadata=metadata,
                        bundle=bundle_name,
                    )
                )
                continue

        evaluation = RuleEvaluation(
            policy_ref=policy_ref,
            effect=policy.effect,
            priority=policy.priority,
            matched=True,
            when_result=True,
            unless_result=unless_result if unless_result is not None else False,
            purpose=policy.purpose,
            metadata=metadata,
            bundle=bundle_name,
        )
        trace.append(evaluation)

        if policy.effect == "deny":
            return Decision(
                allow=False,
                effect="deny",
                policy_id=policy_ref,
                reason="explicit_deny",
                purpose=policy.purpose,
                bundle=bundle_name,
                trace=trace,
            )
        return Decision(
            allow=True,
            effect="allow",
            policy_id=policy_ref,
            purpose=policy.purpose,
            bundle=bundle_name,
            trace=trace,
        )

    return Decision(
        allow=False,
        effect="deny",
        reason="deny_by_default",
        trace=trace,
    )


def _candidate_policies(action: str) -> List[Tuple[int, int, str, PolicyRule, Dict[str, Any]]]:
    records: List[Tuple[int, int, str, PolicyRule, Dict[str, Any]]] = []
    for bundle_name, bundle in STORE.list_policies().items():
        for order, policy in enumerate(bundle.policies):
            if policy.action != action and policy.action != "*":
                continue
            combined_meta: Dict[str, Any] = {}
            combined_meta.update(bundle.metadata)
            combined_meta.update(policy.metadata)
            records.append((policy.priority, order, bundle_name, policy, combined_meta))
    records.sort(key=lambda item: (-item[0], 0 if item[3].effect == "deny" else 1, item[1]))
    return records


def _eval_expression(expr: str, subject: Dict[str, Any], action: str, resource: Dict[str, Any], context: Dict[str, Any]) -> bool:
    namespace = {
        "subject": subject,
        "action": action,
        "resource": resource,
        "context": context,
    }
    normalized = expr.replace("&&", " and ").replace("||", " or ")
    compiled = compile(normalized, "<policy>", "eval")
    return bool(eval(compiled, SAFE_GLOBALS, namespace))


__all__ = ["Decision", "RuleEvaluation", "evaluate"]
