from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_URL = "postgresql+asyncpg://grisk:grisk@postgres:5432/grisk"


class Settings(BaseSettings):
    app_name: str = "gRisk API"
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    jwt_issuer: str = "grisk-api"
    jwt_audience: str = "grisk-web"
    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 300

    database_url: str = DEFAULT_DATABASE_URL
    redis_url: str = "redis://redis:6379/0"
    cors_origins: str = "http://localhost:8080,http://localhost:5000"

    document_storage_path: str = "/data/documents"
    document_max_upload_mb: int = 20

    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_name: str = "gRisk Administrator"

    model_config = SettingsConfigDict(
        env_prefix="GRISK_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_settings(self):
        if self.document_max_upload_mb < 1 or self.document_max_upload_mb > 100:
            raise ValueError("GRISK_DOCUMENT_MAX_UPLOAD_MB must be between 1 and 100")
        if self.environment.lower() != "production":
            return self
        if self.secret_key == "change-me" or len(self.secret_key) < 32:
            raise ValueError("GRISK_SECRET_KEY must be at least 32 characters in production")
        if self.database_url == DEFAULT_DATABASE_URL:
            raise ValueError("GRISK_DATABASE_URL must use explicit production credentials")
        if not self.cors_origin_list:
            raise ValueError("GRISK_CORS_ORIGINS must contain at least one production origin")
        if "*" in self.cors_origin_list:
            raise ValueError("Wildcard CORS origins are not allowed in production")
        insecure_origins = [origin for origin in self.cors_origin_list if not origin.startswith("https://")]
        if insecure_origins:
            raise ValueError("Production CORS origins must use HTTPS")
        if self.login_rate_limit_attempts < 1:
            raise ValueError("GRISK_LOGIN_RATE_LIMIT_ATTEMPTS must be at least 1")
        if self.login_rate_limit_window_seconds < 30:
            raise ValueError("GRISK_LOGIN_RATE_LIMIT_WINDOW_SECONDS must be at least 30")
        if self.bootstrap_admin_password and len(self.bootstrap_admin_password) < 12:
            raise ValueError("GRISK_BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
