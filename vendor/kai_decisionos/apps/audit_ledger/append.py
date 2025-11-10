import json
import argparse
from apps.audit_ledger.ledger import AuditLedger

def main():
    parser = argparse.ArgumentParser(description="Append a record to the audit ledger.")
    parser.add_argument("decision_id", help="The decision ID.")
    parser.add_argument("payload", help="The JSON payload.")
    args = parser.parse_args()

    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError:
        print("Error: Invalid JSON payload.")
        return

    ledger = AuditLedger()
    record = ledger.append(args.decision_id, payload)
    print(f"Appended record: {record.decision_id}")
    print(f"  - Previous Hash: {record.prev_hash}")
    print(f"  - Current Hash:  {record.curr_hash}")

if __name__ == "__main__":
    main()
