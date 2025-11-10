from __future__ import annotations

from typing import Dict

from .sdk import registry
from . import csv_ingest, gsheet_ingest, s3_ingest


def bootstrap() -> Dict[str, str]:
    registry.register("csv", csv_ingest.CSVConnector, "CSV file loader")
    registry.register("gsheet", gsheet_ingest.GoogleSheetConnector, "Google Sheets range loader")
    registry.register("s3", s3_ingest.S3Connector, "S3 object loader")
    return registry.list()


BOOTSTRAPPED = bootstrap()


__all__ = ["bootstrap", "BOOTSTRAPPED"]

