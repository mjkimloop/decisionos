import json
import hashlib
from datetime import datetime
from pathlib import Path
from packages.common.config import settings

def export_ndjson(ledger_path: Path, output_path: Path):
    """
    Exports the audit ledger to NDJSON format.
    """
    if not ledger_path.exists():
        print(f"Ledger file not found: {ledger_path}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("r", encoding="utf-8") as infile, \
         output_path.open("w", encoding="utf-8") as outfile:
        for line in infile:
            outfile.write(line)
    print(f"Exported ledger to {output_path}")

def generate_manifest(ledger_path: Path, manifest_path: Path):
    """
    Generates a monthly manifest of daily ledger file hashes.
    This is a simplified example assuming one ledger file per month.
    A more robust implementation would handle daily log rotations.
    """
    if not ledger_path.exists():
        print(f"Ledger file not found: {ledger_path}")
        return

    with ledger_path.open("rb") as f:
        ledger_hash = hashlib.sha256(f.read()).hexdigest()

    manifest = {
        "month": datetime.now().strftime("%Y-%m"),
        "files": [
            {
                "filename": str(ledger_path.name),
                "hash": ledger_hash,
            }
        ],
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Generated manifest at {manifest_path}")

def main():
    ledger_file = Path(settings.audit_log_path)
    
    # Export to NDJSON
    ndjson_output = ledger_file.parent / f"{ledger_file.stem}.ndjson"
    export_ndjson(ledger_file, ndjson_output)
    
    # Generate manifest
    manifest_file = ledger_file.parent / f"manifest-{datetime.now().strftime('%Y-%m')}.json"
    generate_manifest(ledger_file, manifest_file)

if __name__ == "__main__":
    main()
