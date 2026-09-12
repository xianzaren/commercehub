import pytest

from app.core.config import Settings
from app.core.security import (
    AccessTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole


def test_password_is_hashed_and_verifiable() -> None:
    password = "Resume123!"
    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2id$")
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_round_trip() -> None:
    settings = Settings()
    token = create_access_token(42, UserRole.CUSTOMER, settings)
    claims = decode_access_token(token, settings)

    assert claims.user_id == 42
    assert claims.role is UserRole.CUSTOMER
    assert claims.jti


def test_tampered_token_is_rejected() -> None:
    settings = Settings()
    token = create_access_token(42, UserRole.CUSTOMER, settings)

    with pytest.raises(AccessTokenError):
        decode_access_token(f"{token}tampered", settings)


def test_expired_token_is_rejected() -> None:
    settings = Settings(jwt_access_token_minutes=-1)
    token = create_access_token(42, UserRole.CUSTOMER, settings)

    with pytest.raises(AccessTokenError):
        decode_access_token(token, settings)
