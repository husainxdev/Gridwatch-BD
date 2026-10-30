from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True
    )
    db_pool_size: int = Field(default=3, ge=1, le=20)
    db_max_overflow: int = Field(default=2, ge=0, le=20)
    db_pool_timeout: int = Field(default=10, ge=1, le=60)
    db_pool_recycle: int = Field(default=300, ge=30, le=3600)
    release_revision: str = Field(
        default="unversioned", pattern=r"^(unversioned|[0-9a-f]{40})$"
    )
    demo_instance: bool = False
    community_window_minutes: int = Field(default=60, ge=5, le=1440)
    report_backdate_hours: int = Field(default=24, ge=1, le=168)
    report_future_seconds: int = Field(default=300, ge=0, le=600)
    report_rate_limit: int = Field(default=20, ge=1, le=1000)
    report_cooldown_seconds: int = Field(default=600, ge=0, le=3600)
    auth_rate_limit: int = Field(default=60, ge=1, le=10000)
    auth_rate_window_seconds: int = Field(default=60, ge=1, le=86400)
    database_url: str
    jwt_secret: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 1025
    smtp_starttls: bool = False
    smtp_username: str | None = None
    smtp_password: str | None = None
    mail_from: str = "no-reply@gridwatch.local"
    frontend_url: str = "http://localhost:5173"
    app_env: Literal["development", "test", "production"] = "development"
    demo_enabled: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, value):
        if "*" in value:
            raise ValueError("Credentialed CORS requires explicit origins")
        return value

    @field_validator("database_url")
    @classmethod
    def postgres_url(cls, value):
        if value.startswith("postgres://"):
            value = "postgresql+psycopg://" + value[len("postgres://") :]
        elif value.startswith("postgresql://"):
            value = "postgresql+psycopg://" + value[len("postgresql://") :]
        try:
            parsed = make_url(value)
            if parsed.drivername != "postgresql+psycopg" or not parsed.database:
                raise ValueError
            _ = parsed.port
        except Exception:
            raise ValueError(
                "A valid PostgreSQL psycopg connection URL is required"
            ) from None
        return parsed.render_as_string(hide_password=False)

    @model_validator(mode="after")
    def release_configuration(self):
        url = make_url(self.database_url)
        if self.demo_instance and not (url.database or "").startswith(
            "gridwatch_demo_"
        ):
            raise ValueError(
                "Demo instances require a separate gridwatch_demo_ database"
            )
        if (url.database or "").startswith(
            "gridwatch_demo_"
        ) and not self.demo_instance:
            raise ValueError("A gridwatch_demo_ database must keep DEMO_INSTANCE=true")
        if self.app_env == "production":
            front = urlsplit(self.frontend_url)
            if (
                front.scheme != "https"
                or not front.hostname
                or front.username
                or front.password
                or front.path not in ("", "/")
                or front.query
                or front.fragment
            ):
                raise ValueError(
                    "Production FRONTEND_URL must be a trusted HTTPS origin"
                )
            if self.cors_origins != [self.frontend_url.rstrip("/")]:
                raise ValueError(
                    "Production CORS must contain only the exact trusted frontend origin"
                )
            if url.query.get("sslmode") not in ("require", "verify-ca", "verify-full"):
                raise ValueError(
                    "Production PostgreSQL requires an explicit TLS sslmode"
                )
            if self.release_revision == "unversioned":
                raise ValueError(
                    "Production RELEASE_REVISION must identify the full Git commit"
                )
            if (
                not self.jwt_secret
                or len(self.jwt_secret) < 32
                or any(
                    x in self.jwt_secret.upper()
                    for x in ("CHANGE_ME", "REPLACE_", "SET_A_")
                )
            ):
                raise ValueError(
                    "Production JWT_SECRET must be a securely generated signing secret"
                )
            if self.demo_enabled and not self.demo_instance:
                raise ValueError(
                    "Production demo fixtures require a separate demo instance"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
