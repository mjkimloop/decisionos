"""
Integration — Evidence replication tests
"""
import os
from jobs.evidence_replication import EvidenceReplicator

def test_replicator_loads_config():
    """Test replicator loads configuration"""
    replicator = EvidenceReplicator()
    assert replicator.config is not None
    assert "source" in replicator.config
    assert "target" in replicator.config

def test_replicate_single_file():
    """Test replicating a single evidence file"""
    replicator = EvidenceReplicator()
    success, message = replicator.replicate("evidence-001.json")

    assert success
    assert "Replicated" in message

def test_replicate_batch():
    """Test batch replication"""
    replicator = EvidenceReplicator()
    paths = ["evidence-001.json", "evidence-002.json", "evidence-003.json"]

    results = replicator.replicate_batch(paths)

    assert results["success"] == 3
    assert results["failed"] == 0

def test_verify_object_lock():
    """Test ObjectLock verification"""
    replicator = EvidenceReplicator()
    assert replicator._verify_object_lock("target-bucket")
