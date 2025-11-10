from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .schema import ProductSpec, ProductVersion


def build_manifest(product: ProductVersion | ProductSpec) -> Dict[str, Any]:
    if isinstance(product, ProductVersion):
        spec = product.spec
    else:
        spec = product
    return {
        "product": spec.name,
        "version": spec.version,
        "owner": spec.owner,
        "inputs": spec.input_datasets,
        "transforms": spec.transforms,
        "slas": spec.slas,
        "contracts": spec.contracts,
        "publish": [target.model_dump(mode="json") for target in spec.publish],
        "metadata": spec.metadata,
        "fingerprint": spec.fingerprint(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


__all__ = ["build_manifest"]
