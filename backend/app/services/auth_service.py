from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import BusinessError
from app.core.security import (
    create_access_token,
    hash_password,
    password_hash_needs_update,
    verify_password,
)
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.repositories.user_repository import UserRepository

DUMMY_PASSWORD_HASH = hash_password("CommerceHubDummyPassword123!")


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)

    def register(self, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        if self.users.exists_by_email(normalized_email):
            raise BusinessError(
                "EMAIL_ALREADY_REGISTERED",
                "该邮箱已注册",
                status_code=409,
            )

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
        )
        try:
            self.users.add(user)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise BusinessError(
                "EMAIL_ALREADY_REGISTERED",
                "该邮箱已注册",
                status_code=409,
            ) from exc
        self.session.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> tuple[User, str]:
        user = self.users.get_by_email(email)
        candidate_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        password_is_valid = verify_password(password, candidate_hash)
        if user is None or not password_is_valid:
            raise BusinessError(
                "INVALID_CREDENTIALS",
                "邮箱或密码错误",
                status_code=401,
            )
        if user.status != UserStatus.ACTIVE:
            raise BusinessError(
                "ACCOUNT_UNAVAILABLE",
                "账户已被暂停或禁用",
                status_code=403,
            )

        if password_hash_needs_update(user.password_hash):
            user.password_hash = hash_password(password)
            self.session.commit()

        token = create_access_token(user.id, user.role, self.settings)
        return user, token
