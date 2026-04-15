from functools import lru_cache
from typing import Any

from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    project_name: str = "Plataforma IBP"
    api_v1_prefix: str = "/api/v1"
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    public_sign_url_base: str = "http://localhost:3000/assinatura"
    backend_cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = "localhost:9000"
    s3_secure: bool = False
    s3_bucket: str = "plataforma-ibp"
    s3_access_key: str
    s3_secret_key: str
    s3_presigned_expires_seconds: int = 900

    max_upload_mb: int = 8
    login_rate_limit: str = "8/minute"
    public_rate_limit: str = "30/minute"

    initial_admin_name: str | None = None
    initial_admin_email: EmailStr | None = None
    initial_admin_password: str | None = None
    bootstrap_default_template: bool = True

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("initial_admin_name", "initial_admin_email", "initial_admin_password", mode="before")
    @classmethod
    def empty_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY deve ter pelo menos 32 caracteres")
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
