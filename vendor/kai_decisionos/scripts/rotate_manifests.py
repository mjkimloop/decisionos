import json
from datetime import UTC, datetime
from pathlib import Path

from packages.common.config import settings


def rotate(ledger_path: Path | None = None, out_dir: Path | None = None) -> Path:
    ledger = ledger_path or Path(settings.audit_log_path)
    out = out_dir or Path('var/manifests')

    out.mkdir(parents=True, exist_ok=True)
    if not ledger.exists():
        raise FileNotFoundError(str(ledger))

    last_line = None
    with ledger.open('r', encoding='utf-8') as f:
        for line in f:
            last_line = line
    if not last_line:
        raise RuntimeError('empty ledger')
    rec = json.loads(last_line)
    anchor = {
        'decision_id': rec.get('decision_id'),
        'curr_hash': rec.get('curr_hash'),
        'ts': rec.get('created_at'),
    }
    today = datetime.now(UTC).strftime('%Y-%m-%d')
    out_file = out / f'manifest_{today}.json'
    manifest = {
        'date': today,
        'ledger_path': str(ledger),
        'size_bytes': ledger.stat().st_size,
        'anchor': anchor,
    }
    out_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return out_file


if __name__ == '__main__':
    p = rotate()
    print(p)
