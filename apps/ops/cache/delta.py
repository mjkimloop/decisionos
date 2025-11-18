import hashlib
import json
from typing import Any, Optional

def compute_etag(payload: Any) -> str:
    b = json.dumps(payload, sort_keys=True, separators=(",",":")).encode("utf-8")
    return hashlib.sha256(b).hexdigest()

def make_delta_etag(prev_etag: Optional[str], payload: Any) -> str:
    base = (prev_etag or "") + ":" + compute_etag(payload)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

def not_modified(client_etag: Optional[str], server_etag: str) -> bool:
    return client_etag is not None and client_etag == server_etag
