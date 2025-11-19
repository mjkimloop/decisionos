# tests/evidence/test_gc_config_v2_compat_v1.py
"""
Test Evidence GC config Pydantic v2 compatibility (v0.5.11u-15d).

Ensures GC configuration models work with both Pydantic v1 and v2.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.obs.evidence.gc_config import ObjectLockCfg, GCCfg
from apps.common.pydantic_compat import PYDANTIC_V2, model_to_dict


def test_object_lock_cfg_defaults():
    """Test ObjectLockCfg default values."""
    cfg = ObjectLockCfg()

    assert cfg.enabled is True
    assert cfg.retention_days == 365
    assert cfg.s3_bucket is None
    assert cfg.s3_prefix is None


def test_object_lock_cfg_custom():
    """Test ObjectLockCfg with custom values."""
    cfg = ObjectLockCfg(
        enabled=False,
        retention_days=180,
        s3_bucket="my-bucket",
        s3_prefix="evidence/",
    )

    assert cfg.enabled is False
    assert cfg.retention_days == 180
    assert cfg.s3_bucket == "my-bucket"
    assert cfg.s3_prefix == "evidence/"


def test_gc_cfg_defaults():
    """Test GCCfg default values."""
    cfg = GCCfg()

    assert cfg.retention_days == {"WIP": 7, "LOCKED": 365}
    assert cfg.keep_min_per_tenant == 5
    assert cfg.exclude_globs == ["**/*locked.json"]
    assert cfg.dry_run is True
    assert isinstance(cfg.object_lock, ObjectLockCfg)
    assert cfg.object_lock.enabled is True


def test_gc_cfg_custom_retention():
    """Test GCCfg with custom retention days."""
    cfg = GCCfg(
        retention_days={"WIP": 3, "LOCKED": 180, "ARCHIVED": 730},
        keep_min_per_tenant=10,
    )

    assert cfg.retention_days == {"WIP": 3, "LOCKED": 180, "ARCHIVED": 730}
    assert cfg.keep_min_per_tenant == 10


def test_gc_cfg_custom_exclude_globs():
    """Test GCCfg with custom exclude patterns."""
    cfg = GCCfg(
        exclude_globs=["**/*.tmp", "**/.DS_Store"],
        dry_run=False,
    )

    assert cfg.exclude_globs == ["**/*.tmp", "**/.DS_Store"]
    assert cfg.dry_run is False


def test_gc_cfg_nested_object_lock():
    """Test GCCfg with nested ObjectLockCfg."""
    cfg = GCCfg(
        object_lock=ObjectLockCfg(
            enabled=False,
            retention_days=90,
            s3_bucket="custom-bucket",
        )
    )

    assert cfg.object_lock.enabled is False
    assert cfg.object_lock.retention_days == 90
    assert cfg.object_lock.s3_bucket == "custom-bucket"


def test_gc_cfg_model_validate():
    """Test GCCfg.model_validate() for v1/v2 compatibility."""
    data = {
        "retention_days": {"WIP": 1, "LOCKED": 30},
        "keep_min_per_tenant": 3,
        "dry_run": False,
    }

    if PYDANTIC_V2:
        cfg = GCCfg.model_validate(data)
    else:
        cfg = GCCfg.parse_obj(data)

    assert cfg.retention_days == {"WIP": 1, "LOCKED": 30}
    assert cfg.keep_min_per_tenant == 3
    assert cfg.dry_run is False


def test_gc_cfg_to_dict():
    """Test GCCfg serialization to dict."""
    cfg = GCCfg(
        retention_days={"WIP": 7},
        keep_min_per_tenant=5,
        dry_run=True,
    )

    result = model_to_dict(cfg, exclude_none=True)

    assert "retention_days" in result
    assert "keep_min_per_tenant" in result
    assert "dry_run" in result
    assert result["retention_days"] == {"WIP": 7}


def test_gc_cfg_extra_fields_forbidden():
    """Test GCCfg rejects extra fields (v2 extra='forbid')."""
    data = {
        "retention_days": {"WIP": 7},
        "unknown_field": "should_fail",
    }

    if PYDANTIC_V2:
        with pytest.raises(ValidationError) as exc_info:
            GCCfg.model_validate(data)

        # v2 extra='forbid' 에러 확인
        assert "unknown_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()
    else:
        # v1에서는 extra 필드 무시
        cfg = GCCfg.parse_obj(data)
        assert cfg.retention_days == {"WIP": 7}


def test_object_lock_cfg_extra_fields_forbidden():
    """Test ObjectLockCfg rejects extra fields (v2 extra='forbid')."""
    data = {
        "enabled": True,
        "retention_days": 180,
        "bad_field": "not_allowed",
    }

    if PYDANTIC_V2:
        with pytest.raises(ValidationError) as exc_info:
            ObjectLockCfg.model_validate(data)

        assert "bad_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()
    else:
        cfg = ObjectLockCfg.parse_obj(data)
        assert cfg.enabled is True


def test_gc_cfg_retention_days_type():
    """Test GCCfg retention_days is Dict[str, int]."""
    cfg = GCCfg(retention_days={"TEST": 99})

    assert isinstance(cfg.retention_days, dict)
    assert "TEST" in cfg.retention_days
    assert cfg.retention_days["TEST"] == 99
    assert isinstance(cfg.retention_days["TEST"], int)


def test_gc_cfg_object_lock_default_instance():
    """Test GCCfg creates default ObjectLockCfg instance."""
    cfg = GCCfg()

    assert isinstance(cfg.object_lock, ObjectLockCfg)
    assert cfg.object_lock.enabled is True
    assert cfg.object_lock.retention_days == 365
