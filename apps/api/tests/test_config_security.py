import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_weak_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            secret_key="short",
            cors_origins="https://grisk.example.com",
        )


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            secret_key="production-only-secret-key-with-at-least-32-bytes",
            cors_origins="*",
        )


def test_production_accepts_explicit_secure_configuration() -> None:
    settings = Settings(
        environment="production",
        secret_key="production-only-secret-key-with-at-least-32-bytes",
        cors_origins="https://grisk.example.com,https://portal.grisk.example.com",
    )
    assert settings.environment == "production"
    assert settings.cors_origin_list == [
        "https://grisk.example.com",
        "https://portal.grisk.example.com",
    ]
