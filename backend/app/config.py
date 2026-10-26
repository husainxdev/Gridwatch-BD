from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
