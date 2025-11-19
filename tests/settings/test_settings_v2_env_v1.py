# tests/settings/test_settings_v2_env_v1.py
"""Test Settings with Pydantic v2 BaseSettings (v0.5.11u-15a)."""
from __future__ import annotations

import pytest


def test_settings_import():
    """Test settings can be imported."""
    from apps.config.settings import settings

    assert settings is not None
    assert hasattr(settings, 'ENV')
    assert hasattr(settings, 'TENANT')


def test_settings_default_values():
    """Test settings have correct default values."""
    from apps.config.settings import settings

    assert settings.ENV == "dev"
    assert settings.S3_MODE == "stub"
    assert settings.CARDS_TTL == 60
    assert settings.COMPRESS_ENABLE == 1
    assert settings.RBAC_TEST_MODE == 0


def test_settings_env_override(monkeypatch):
    """Test settings can be overridden by environment variables."""
    monkeypatch.setenv("DECISIONOS_ENV", "staging")
    monkeypatch.setenv("DECISIONOS_CARDS_TTL", "120")
    monkeypatch.setenv("DECISIONOS_COMPRESS_MIN_BYTES", "8192")

    # Force reload settings
    import importlib
    from apps.config import settings as settings_module
    importlib.reload(settings_module)

    from apps.config.settings import settings

    assert settings.ENV == "staging"
    assert settings.CARDS_TTL == 120
    assert settings.COMPRESS_MIN_BYTES == 8192


def test_get_cors_origins_dev():
    """Test get_cors_origins returns dev defaults."""
    from apps.config.settings import Settings

    settings = Settings(ENV="dev", CORS_ALLOWLIST="")
    origins = settings.get_cors_origins()

    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins


def test_get_cors_origins_explicit():
    """Test get_cors_origins parses comma-separated list."""
    from apps.config.settings import Settings

    settings = Settings(
        ENV="prod",
        CORS_ALLOWLIST="https://app.example.com,https://console.example.com"
    )
    origins = settings.get_cors_origins()

    assert len(origins) == 2
    assert "https://app.example.com" in origins
    assert "https://console.example.com" in origins


def test_get_cors_origins_prod_rejects_wildcard():
    """Test get_cors_origins rejects wildcard in production."""
    from apps.config.settings import Settings

    settings = Settings(ENV="prod", CORS_ALLOWLIST="*")

    with pytest.raises(ValueError, match="no wildcard"):
        settings.get_cors_origins()


def test_get_cors_origins_prod_rejects_empty():
    """Test get_cors_origins rejects empty list in production."""
    from apps.config.settings import Settings

    settings = Settings(ENV="prod", CORS_ALLOWLIST="")

    with pytest.raises(ValueError, match="explicit"):
        settings.get_cors_origins()


def test_get_allow_scopes():
    """Test get_allow_scopes parses space-separated scopes."""
    from apps.config.settings import Settings

    settings = Settings(ALLOW_SCOPES="ops:read judge:run deploy:promote")
    scopes = settings.get_allow_scopes()

    assert len(scopes) == 3
    assert "ops:read" in scopes
    assert "judge:run" in scopes
    assert "deploy:promote" in scopes


def test_is_prod():
    """Test is_prod helper."""
    from apps.config.settings import Settings

    assert Settings(ENV="prod").is_prod() is True
    assert Settings(ENV="PROD").is_prod() is True
    assert Settings(ENV="dev").is_prod() is False
    assert Settings(ENV="staging").is_prod() is False


def test_is_dev():
    """Test is_dev helper."""
    from apps.config.settings import Settings

    assert Settings(ENV="dev").is_dev() is True
    assert Settings(ENV="DEV").is_dev() is True
    assert Settings(ENV="prod").is_dev() is False
    assert Settings(ENV="staging").is_dev() is False
