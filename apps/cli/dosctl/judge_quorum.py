from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from apps.judge.pool import quorum_decide
from apps.judge.providers.http import HTTPJudgeProvider
from apps.judge.providers.local import LocalJudgeProvider
from apps.obs.evidence.ops import recompute_integrity
from apps.policy.pep import require


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def _load_providers(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    return data.get("providers", [])


def _parse_quorum(expr: str) -> Tuple[int, int]:
    try:
        k_str, n_str = expr.split("/", 1)
        return int(k_str), int(n_str)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"invalid quorum expression: {expr}") from exc


def _build_providers(defs: List[Dict[str, Any]]):
    providers = []
    for entry in defs:
        p_type = entry.get("type")
        p_id = entry.get("id")
        if not p_type or not p_id:
            raise ValueError("provider definition must include id/type")

        if p_type == "local":
            providers.append(LocalJudgeProvider(p_id))
        elif p_type == "http":
            providers.append(
                HTTPJudgeProvider(
                    provider_id=p_id,
                    url=entry["url"],
                    timeout_ms=entry.get("timeout_ms", 2000),
                    retries=entry.get("retries", 2),
                    require_signature=entry.get("require_sig", True),
                    key_id=entry.get("key_id", "k1"),
                    breaker_max_failures=entry.get("breaker_max_failures", 3),
                    breaker_reset_seconds=entry.get("breaker_reset_seconds", 5.0),
                    verify_ssl=not entry.get("insecure", False),
                )
            )
        else:
            raise ValueError(f"unknown provider type: {p_type}")
    return providers


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="dosctl judge quorum")
    parser.add_argument("--slo", required=True, help="SLO JSON 경로")
    parser.add_argument("--evidence", required=True, help="Evidence JSON 경로")
    parser.add_argument("--providers", required=True, help="providers.yaml 경로")
    parser.add_argument("--quorum", required=True, help="k/n 표기 (예: 2/3)")
    parser.add_argument("--attach-evidence", action="store_true", help="Evidence에 judges 블록 병합")
    parser.add_argument("--out", default="var/evidence/evidence-with-judges.json", help="attach 시 저장 경로")
    args = parser.parse_args(argv)
    try:
        require("judge:run")
    except PermissionError:
        raise SystemExit(3)
    slo = _load_json(args.slo)
    evidence = _load_json(args.evidence)
    provider_defs = _load_providers(args.providers)
    providers = _build_providers(provider_defs)

    if not providers:
        raise SystemExit("no providers configured")

    k, n = _parse_quorum(args.quorum)
    fail_closed = slo.get("quorum", {}).get("fail_closed_on_degrade", True)

    try:
        result = asyncio.run(quorum_decide(providers, evidence, slo, k=k, n=n, fail_closed_on_degrade=fail_closed))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    final = result["final"]

    print(f"[dosctl] quorum result = {final} (pass={result['pass_count']} / k={k}, n={n})")
    for vote in result["votes"]:
        pid = vote.get("id")
        decision = vote.get("decision")
        latency = vote.get("meta", {}).get("latency_ms")
        reasons = ", ".join(vote.get("reasons", [])) or "-"
        print(f"  - {pid}: {decision} (latency={latency}ms, reasons={reasons})")

    if args.attach_evidence:
        evidence["judges"] = {
            "k": k,
            "n": n,
            "final": final,
            "votes": result["votes"],
        }
        recompute_integrity(evidence)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(f"[dosctl] judges block attached → {out_path}")

    raise SystemExit(0 if final == "pass" else 2)


if __name__ == "__main__":  # pragma: no cover
    main()
