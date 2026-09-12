from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jwt import InvalidTokenError

from app.core.config import Settings
from app.models.enums import UserRole

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: int
    role: UserRole
    jti: str
    expires_at: datetime


class AccessTokenError(ValueError):
    pass


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def password_hash_needs_update(password_hash: str) -> bool:
    try:
        return password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def create_access_token(user_id: int, role: UserRole | str, settings: Settings) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.jwt_access_token_minutes)
    payload = {
        "sub": str(user_id),
        "role": str(role),
        "jti": uuid4().hex,
        "iat": now,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "role", "jti", "iat", "exp", "iss", "aud"]},
        )
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
        return AccessTokenClaims(
            user_id=int(payload["sub"]),
            role=UserRole(payload["role"]),
            jti=str(payload["jti"]),
            expires_at=expires_at,
        )
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise AccessTokenError("Invalid or expired access token") from exc
