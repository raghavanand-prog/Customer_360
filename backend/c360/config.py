"""All settings declared once here via pydantic-settings (§16.4).

No module outside this file reads ``os.getenv`` directly.
"""
from __future__ import annotations

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_SECRETS = {"changeme", "secret", "dev", ""}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    c360_env: str = "local"
    database_url: str = "postgresql+psycopg://c360_app:c360_app@localhost:5432/c360"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    cors_allowed_origins: str = "http://localhost:5173"
    rate_limit_default: str = "100/minute"
    rate_limit_login: str = "5/minute"
    log_level: str = "INFO"
    log_format: str = "json"
    mask_pii_roles: str = "analyst,viewer"
    enable_docs: bool = True
    data_lake_root: str = "./data/lake"
    feature_recommendations: bool = False
    feature_ml_churn: bool = False

    @field_validator("database_url")
    @classmethod
    def _normalise_database_url(cls, v: str) -> str:
        # Managed providers (e.g. Neon via the Vercel integration) hand out a
        # driver-less `postgresql://`/`postgres://` URL; only psycopg3 is
        # installed here, so route it to the `+psycopg` dialect explicitly
        # rather than falling back to SQLAlchemy's psycopg2 default.
        if v.startswith("postgres://"):
            return "postgresql+psycopg://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            return "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def mask_pii_roles_set(self) -> set[str]:
        return {r.strip() for r in self.mask_pii_roles.split(",") if r.strip()}

    @model_validator(mode="after")
    def _validate_startup_invariants(self) -> "Settings":
        if not self.jwt_secret_key or self.jwt_secret_key.lower() in PLACEHOLDER_SECRETS:
            raise RuntimeError("JWT_SECRET_KEY is missing or a placeholder value; refusing to start.")
        if self.c360_env == "prod":
            if self.enable_docs:
                raise RuntimeError("ENABLE_DOCS must be false in the prod environment.")
            if self.cors_allowed_origins.strip() == "*":
                raise RuntimeError("CORS_ALLOWED_ORIGINS must not be '*' in the prod environment.")
        return self


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
