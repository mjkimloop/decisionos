from __future__ import annotations
import asyncio
from pathlib import Path
from apps.connectors.csv_ingest import ingest_csv

async def run_once():
    # scaffold: load connectors.yaml and run one cycle
    p = Path('config/connectors.yaml')
    if not p.exists():
        return 0
    # naive demo: ingest sample csv if exists
    sample = Path('packages/samples/offline_eval.sample.csv')
    if sample.exists():
        return await ingest_csv(sample)
    return 0

if __name__=='__main__':
    print(asyncio.run(run_once()))
