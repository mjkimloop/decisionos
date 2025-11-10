import json
import hashlib
from pathlib import Path
from packages.common.config import settings
from cryptography.fernet import Fernet
import base64

def _get_cipher() -> Fernet | None:
    if settings.aes_key_b64:
        try:
            key = settings.aes_key_b64.encode("utf-8")
            return Fernet(key)
        except Exception:
            return None
    return None

def verify_chain(ledger_path: Path):
    """
    Verifies the hash chain of the audit ledger.
    """
    if not ledger_path.exists():
        print(f"Ledger file not found: {ledger_path}")
        return False

    prev_hash = "0" * 64
    cipher = _get_cipher()

    with ledger_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            try:
                record = json.loads(line)
                
                # Check if prev_hash matches
                if record["prev_hash"] != prev_hash:
                    print(f"Hash chain broken at line {i+1}: prev_hash mismatch.")
                    return False
                
                # Re-calculate curr_hash
                payload = record["payload"]
                raw = json.dumps(payload, sort_keys=True).encode("utf-8") if isinstance(payload, dict) else payload.encode("utf-8")
                curr_hash = hashlib.sha256(prev_hash.encode("utf-8") + raw).hexdigest()

                if record["curr_hash"] != curr_hash:
                    print(f"Hash chain broken at line {i+1}: curr_hash mismatch.")
                    return False
                
                prev_hash = record["curr_hash"]

            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing record at line {i+1}: {e}")
                return False
    
    print("Hash chain verified successfully.")
    return True

def main():
    ledger_file = Path(settings.audit_log_path)
    verify_chain(ledger_file)

if __name__ == "__main__":
    main()
