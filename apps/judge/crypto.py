from __future__ import annotations
import base64
import hmac, hashlib, json, os, time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

@dataclass
class KeyMaterial:
    key_id: str
    secret: bytes
    state: str  # "active" | "grace" | "retired"

class MultiKeyLoader:
    """ENV(JSON) 기반 멀티키 로더. 예:
    DECISIONOS_JUDGE_KEYS='[{"key_id":"k1","secret":"base64|hex|plain","state":"active"}]'
    """
    def __init__(self, env_var: str = "DECISIONOS_JUDGE_KEYS"):
        self.env_var = env_var
        self._cache_ts = 0
        self._ttl = 5
        self._keys: Dict[str, KeyMaterial] = {}

    def _parse_secret(self, s: str) -> bytes:
        if s.startswith("hex:"):
            return bytes.fromhex(s[4:])
        if s.startswith("b64:"):
            return base64.b64decode(s[4:])
        return s.encode("utf-8")

    def _reload_if_needed(self):
        now = time.time()
        if now - self._cache_ts < self._ttl:
            return
        raw = os.getenv(self.env_var)
        if raw:
            data = json.loads(raw)
        else:
            legacy = os.getenv("DECISIONOS_JUDGE_HMAC_KEY")
            if legacy:
                data = [{"key_id": "legacy", "secret": legacy, "state": "active"}]
            else:
                data = []
        m: Dict[str, KeyMaterial] = {}
        for item in data:
            km = KeyMaterial(
                key_id=item["key_id"],
                secret=self._parse_secret(item["secret"]),
                state=item.get("state","active"),
            )
            m[km.key_id] = km
        self._keys = m
        self._cache_ts = now

    def get(self, key_id: str) -> Optional[KeyMaterial]:
        self._reload_if_needed()
        return self._keys.get(key_id)

    def choose_active(self) -> Optional[KeyMaterial]:
        self._reload_if_needed()
        for km in self._keys.values():
            if km.state == "active":
                return km
        return None

def canonical_json(obj) -> bytes:
    return json.dumps(obj, separators=(",",":"), sort_keys=True).encode("utf-8")

def hmac_sign(payload_obj, key: bytes) -> str:
    return hmac.new(key, canonical_json(payload_obj), hashlib.sha256).hexdigest()

def hmac_verify(payload_obj, key: bytes, signature_hex: str) -> bool:
    expected = hmac_sign(payload_obj, key)
    return hmac.compare_digest(expected, signature_hex)


def _coerce_secret(secret: str | bytes) -> bytes:
    if isinstance(secret, bytes):
        return secret
    try:
        return bytes.fromhex(secret)
    except ValueError:
        return secret.encode("utf-8")


def hmac_sign_canonical(payload_obj, secret: str | bytes) -> str:
    return hmac_sign(payload_obj, _coerce_secret(secret))


def hmac_verify_canonical(payload_obj, secret: str | bytes, signature_hex: str) -> bool:
    return hmac_verify(payload_obj, _coerce_secret(secret), signature_hex)

def verify_with_multikey(payload_obj, signature_hex: str, key_id: str, loader: MultiKeyLoader) -> Tuple[bool,str]:
    km = loader.get(key_id)
    if not km:
        return False, "key.missing"
    ok = hmac_verify(payload_obj, km.secret, signature_hex)
    if not ok:
        return False, "sig.mismatch"
    if km.state == "retired":
        return False, "key.retired"
    # grace는 검증만 허용
    return True, "ok"
