from __future__ import annotations

from typing import Dict, List


def required_docs_hook(outcome: Dict) -> List[str]:
    docs = set(outcome.get("required_docs") or [])
    # heuristic: if review, add base checklist
    if outcome.get("class") == "review":
        docs.update({"identity", "income_proof"})
    return sorted(docs)

