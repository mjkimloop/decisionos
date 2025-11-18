"""
Evidence Partition Manager

Manages tenant-partitioned evidence storage with date-based subdirectories.
"""
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


class EvidencePartition:
    """
    Evidence partition manager with tenant isolation.

    Directory structure:
        var/evidence/{tenant}/{YYYY-MM}/evidence_{timestamp}.json
    """

    def __init__(self, base_path: str = "var/evidence"):
        """
        Initialize partition manager.

        Args:
            base_path: Base evidence directory
        """
        self.base_path = Path(base_path)

    def get_partition_path(
        self,
        tenant_id: str,
        date: Optional[datetime] = None
    ) -> Path:
        """
        Get partition path for tenant and date.

        Args:
            tenant_id: Tenant identifier
            date: Date for partition (default: today)

        Returns:
            Path object for partition directory
        """
        if date is None:
            date = datetime.now(timezone.utc)

        # Format: var/evidence/{tenant}/{YYYY-MM}
        year_month = date.strftime("%Y-%m")
        partition_path = self.base_path / tenant_id / year_month

        return partition_path

    def ensure_partition(
        self,
        tenant_id: str,
        date: Optional[datetime] = None
    ) -> Path:
        """
        Ensure partition directory exists.

        Args:
            tenant_id: Tenant identifier
            date: Date for partition (default: today)

        Returns:
            Path object for created partition directory
        """
        partition_path = self.get_partition_path(tenant_id, date)
        partition_path.mkdir(parents=True, exist_ok=True)
        return partition_path

    def list_partitions(self, tenant_id: str) -> list[Path]:
        """
        List all partitions for tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of partition directory paths, sorted by date
        """
        tenant_path = self.base_path / tenant_id

        if not tenant_path.exists():
            return []

        partitions = [
            p for p in tenant_path.iterdir()
            if p.is_dir() and self._is_valid_partition_name(p.name)
        ]

        return sorted(partitions)

    def list_all_tenant_partitions(self) -> dict[str, list[Path]]:
        """
        List all partitions for all tenants.

        Returns:
            Dict mapping tenant_id to list of partition paths
        """
        if not self.base_path.exists():
            return {}

        result = {}

        for tenant_dir in self.base_path.iterdir():
            if tenant_dir.is_dir():
                tenant_id = tenant_dir.name
                result[tenant_id] = self.list_partitions(tenant_id)

        return result

    def get_evidence_path(
        self,
        tenant_id: str,
        evidence_id: str,
        date: Optional[datetime] = None,
        locked: bool = False
    ) -> Path:
        """
        Get full path for evidence file.

        Args:
            tenant_id: Tenant identifier
            evidence_id: Evidence identifier
            date: Date for partition (default: today)
            locked: Whether evidence is locked (immutable)

        Returns:
            Full path for evidence file
        """
        partition_path = self.get_partition_path(tenant_id, date)
        suffix = ".locked.json" if locked else ".json"
        filename = f"evidence_{evidence_id}{suffix}"

        return partition_path / filename

    @staticmethod
    def _is_valid_partition_name(name: str) -> bool:
        """
        Check if directory name is valid partition format (YYYY-MM).

        Args:
            name: Directory name

        Returns:
            True if valid partition format
        """
        if len(name) != 7:
            return False

        if name[4] != "-":
            return False

        try:
            year = int(name[:4])
            month = int(name[5:7])
            return 1900 <= year <= 2100 and 1 <= month <= 12
        except ValueError:
            return False


def get_partition_manager(base_path: str = "var/evidence") -> EvidencePartition:
    """
    Get evidence partition manager instance.

    Args:
        base_path: Base evidence directory

    Returns:
        EvidencePartition instance
    """
    return EvidencePartition(base_path)
