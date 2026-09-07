from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_round_trip() -> None:
    password = "Correct-Horse-Battery-Staple-42"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_round_trip() -> None:
    subject = "8e3f5977-1abc-4bb2-b329-b2e7c37ab03a"
    token = create_access_token(subject, expires_minutes=5)

    assert decode_access_token(token) == subject


def test_invalid_access_token_is_rejected() -> None:
    try:
        decode_access_token("not-a-valid-jwt")
    except TokenError:
        return
    raise AssertionError("Invalid token should raise TokenError")
