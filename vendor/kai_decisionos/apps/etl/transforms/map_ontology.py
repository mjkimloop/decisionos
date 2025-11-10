from __future__ import annotations

from typing import Dict, Any


ONTOLOGY = {
    "income": "financial.income",
    "credit_score": "financial.credit_score",
    "region": "geo.region",
}


def map_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in record.items():
        mapped = ONTOLOGY.get(key, key)
        result[mapped] = value
    return result


__all__ = ["map_fields", "ONTOLOGY"]
