from __future__ import annotations

from pathlib import Path


def test_connectors_scaffold_present():
    assert Path('kai-decisionos/apps/connectors/csv_ingest.py').exists()
    assert Path('kai-decisionos/services/ingest_runner.py').exists()
    assert Path('kai-decisionos/config/connectors.yaml').exists()


def test_pov_docs_scaffold_present():
    assert Path('kai-decisionos/ops/runbook_pov.md').exists()
    assert Path('kai-decisionos/ops/rollback.md').exists()


def test_backup_restore_scripts_present():
    assert Path('kai-decisionos/scripts/backup.sh').exists()
    assert Path('kai-decisionos/scripts/restore.sh').exists()
