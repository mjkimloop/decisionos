from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class S3Connector:
    name = "s3"

    def __init__(self, uri: str) -> None:
        self.uri = uri

    def fetch(self, download_to: Path | None = None) -> Dict[str, Any]:
        # Stub: emulate download by writing a placeholder file when requested
        if download_to:
            download_to.parent.mkdir(parents=True, exist_ok=True)
            download_to.write_text("stub", encoding="utf-8")
        return {"uri": self.uri, "bytes": 4}


async def ingest_s3(uri: str, download_to: Path) -> int:
    connector = S3Connector(uri)
    meta = connector.fetch(download_to)
    return int(meta.get("bytes", 0))


__all__ = ["S3Connector", "ingest_s3"]
