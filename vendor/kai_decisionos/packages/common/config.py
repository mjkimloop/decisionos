from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "DecisionOS-Lite"
    environment: str = Field(default="dev")
    # Security
    auth_enabled: bool = True
    oauth2_dummy: bool = True
    admin_api_key: str | None = None
    rbac_roles: dict[str, list[str]] = {"admin": ["*"], "analyst": ["read", "simulate"], "writer": ["apply"]}
    aes_key_b64: str | None = None  # Optional AES key for audit encryption (base64)
    # HMAC/Webhook
    usage_hmac_secret: str | None = None
    billing_webhook_secret: str | None = None
    # Region/Failover
    active_region: str = "region-a"
    secondary_region: str | None = "region-b"
    region_config_path: str = "config/region.yaml"
    # Database
    db_url: str | None = None

    # Paths
    audit_log_path: str = "var/audit_ledger.jsonl"
    data_dir: str = "packages"
    tenant_config_path: str = "config/tenant.yaml"

    # Rule engine
    rules_dir: str = "packages/rules"
    contracts_dir: str = "packages/contracts"
    routes_path: str = "packages/routes/model_routes.yaml"

    class Config:
        env_prefix = "DOS_"


settings = Settings()
