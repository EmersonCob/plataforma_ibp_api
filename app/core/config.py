from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from pydantic import AliasChoices, EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    project_name: str = "Plataforma IBP"
    api_v1_prefix: str = "/api/v1"
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    public_sign_url_base: str = "https://ibp-web-qa.jbtechinnova.com/assinatura"
    backend_cors_origins: str = "https://ibp-web-qa.jbtechinnova.com"

    database_url: str
    database_schema: str = "plataforma_ibp"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = Field(
        default="s3-infra-qa.jbtechinnova.com",
        validation_alias=AliasChoices("OBJECT_STORAGE_API_ENDPOINT", "OBJECT_STORAGE_ENDPOINT", "S3_ENDPOINT"),
    )
    s3_secure: bool = True
    s3_bucket: str = "plataforma-ibp"
    s3_access_key: str
    s3_secret_key: str
    s3_presigned_expires_seconds: int = 900

    max_upload_mb: int = 8
    image_max_dimension: int = 1280
    image_jpeg_quality: int = 86
    login_rate_limit: str = "8/minute"
    public_rate_limit: str = "30/minute"
    password_reset_rate_limit: str = "5/minute"
    password_reset_token_expire_minutes: int = 60
    frontend_app_url: str = "https://ibp-web-qa.jbtechinnova.com"
    display_timezone: str = "America/Sao_Paulo"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: EmailStr | None = None
    smtp_from_name: str = "IBP Saúde Mental"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 10

    initial_admin_name: str | None = None
    initial_admin_email: EmailStr | None = None
    initial_admin_password: str | None = None
    bootstrap_default_template: bool = True

    @field_validator(
        "initial_admin_name",
        "initial_admin_email",
        "initial_admin_password",
        "smtp_host",
        "smtp_username",
        "smtp_password",
        "smtp_from_email",
        mode="before",
    )
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

    @field_validator("database_schema")
    @classmethod
    def validate_database_schema(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ValueError("DATABASE_SCHEMA deve conter apenas letras, numeros e underscore, sem iniciar por numero")
        return value

    @field_validator("image_max_dimension")
    @classmethod
    def validate_image_max_dimension(cls, value: int) -> int:
        if not 640 <= value <= 4096:
            raise ValueError("IMAGE_MAX_DIMENSION deve estar entre 640 e 4096")
        return value

    @field_validator("image_jpeg_quality")
    @classmethod
    def validate_image_jpeg_quality(cls, value: int) -> int:
        if not 60 <= value <= 95:
            raise ValueError("IMAGE_JPEG_QUALITY deve estar entre 60 e 95")
        return value

    @field_validator("password_reset_token_expire_minutes")
    @classmethod
    def validate_password_reset_token_expire_minutes(cls, value: int) -> int:
        if not 10 <= value <= 1440:
            raise ValueError("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES deve estar entre 10 e 1440")
        return value

    @field_validator("smtp_port")
    @classmethod
    def validate_smtp_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("SMTP_PORT deve estar entre 1 e 65535")
        return value

    @field_validator("s3_endpoint", mode="before")
    @classmethod
    def normalize_s3_endpoint(cls, value: Any) -> Any:
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            parsed = urlparse(value)
            return parsed.netloc
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
