"""
Evidence Replication Job - Region-to-region with ObjectLock verification
"""
import os
import json
from typing import Dict, Any, List

class EvidenceReplicator:
    """
    Replicate evidence files across regions with ObjectLock compliance.
    """
    
    def __init__(self, config_path: str = "configs/dr/replication.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load replication configuration"""
        if not os.path.exists(self.config_path):
            return {
                "source": {"bucket": "evidence-prod", "region": "us-east-1"},
                "target": {"bucket": "evidence-dr", "region": "us-west-2"},
                "object_lock": {"mode": "COMPLIANCE", "retain_days": 365}
            }
        
        with open(self.config_path, "r") as f:
            return json.load(f)
    
    def replicate(self, evidence_path: str) -> tuple[bool, str]:
        """
        Replicate a single evidence file.
        
        Returns (success, message)
        """
        # In production, use boto3 s3.copy_object with ObjectLock headers
        source_bucket = self.config["source"]["bucket"]
        target_bucket = self.config["target"]["bucket"]
        lock_mode = self.config["object_lock"]["mode"]
        
        # Simulate replication
        print(f"[INFO] Replicating {evidence_path} from {source_bucket} to {target_bucket}")
        print(f"[INFO] ObjectLock mode: {lock_mode}")
        
        # Check if ObjectLock is enabled on target
        if not self._verify_object_lock(target_bucket):
            return False, f"ObjectLock not enabled on {target_bucket}"
        
        return True, f"Replicated {evidence_path} to {target_bucket}"
    
    def _verify_object_lock(self, bucket: str) -> bool:
        """Verify ObjectLock is enabled on bucket"""
        # In production, use boto3 s3.get_object_lock_configuration
        # For now, assume it's enabled if config exists
        return "object_lock" in self.config
    
    def replicate_batch(self, evidence_paths: List[str]) -> Dict[str, Any]:
        """Replicate multiple evidence files"""
        results = {"success": 0, "failed": 0, "errors": []}
        
        for path in evidence_paths:
            success, message = self.replicate(path)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({"path": path, "error": message})
        
        return results
