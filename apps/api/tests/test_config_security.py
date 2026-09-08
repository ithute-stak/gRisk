import pytest
from pydantic import ValidationError

from app.core.config import Settings

PROD_DATABASE_URL = "postgresql+asyncpg://grisk_app:strong-db-password@postgres:5432/grisk"
PROD_SECRET = "production-only-secret-key-with-at-least-32-bytes"


def test_production_rejects_weak_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            secret_key="short",
            database_url=PROD_DATABASE_URL,
            cors_origins="https://grisk.example.com",
        )


def test_production_rejects_default_database_credentials() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            secret_key=PROD_SECRET,
            cors_origins="https://grisk.example.com",
        )


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            secret_key=PROD_SECRET,
            database_url=PROD_DATABASE_URL,
            cors_origins="*",
        )


def test_production_rejects_insecure_cors_origin() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            secret_key=PROD_SECRET,
            database_url=PROD_DATABASE_URL,
            cors_origins="http://grisk.example.com",
        )


def test_production_accepts_explicit_secure_configuration() -> None:
    settings = Settings(
        environment="production",
        secret_key=PROD_SECRET,
        database_url=PROD_DATABASE_URL,
        cors_origins="https://grisk.example.com,https://portal.grisk.example.com",
    )
    assert settings.environment == "production"
    assert settings.cors_origin_list == [
        "https://grisk.example.com",
        "https://portal.grisk.example.com",
    ]
