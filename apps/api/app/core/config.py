from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    database_url: str = "postgresql+asyncpg://grisk:grisk@postgres:5432/grisk"
    redis_url: str = "redis://redis:6379/0"
    cors_origins: str = "http://localhost:8080,http://localhost:5000"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
