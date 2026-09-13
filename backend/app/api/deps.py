from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import BusinessError
from app.core.security import AccessTokenError, decode_access_token
from app.db.session import get_db
from app.models.enums import MerchantStatus, UserRole, UserStatus
from app.models.user import Merchant, User
from app.repositories.merchant_repository import MerchantRepository
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)

DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_current_user(
    request: Request,
    credentials: BearerCredentials,
    session: DatabaseSession,
    settings: AppSettings,
) -> User:
    token = credentials.credentials if credentials is not None else None
    token = token or request.cookies.get(settings.auth_cookie_name)
    if token is None:
        raise BusinessError("NOT_AUTHENTICATED", "请先登录", status_code=401)

    try:
        claims = decode_access_token(token, settings)
    except AccessTokenError as exc:
        raise BusinessError(
            "INVALID_ACCESS_TOKEN",
            "登录凭据无效或已过期",
            status_code=401,
        ) from exc

    user = UserRepository(session).get(claims.user_id)
    if user is None:
        raise BusinessError("INVALID_ACCESS_TOKEN", "登录凭据无效", status_code=401)
    if user.status != UserStatus.ACTIVE:
        raise BusinessError("ACCOUNT_UNAVAILABLE", "账户已被暂停或禁用", status_code=403)
    if user.role != claims.role:
        raise BusinessError(
            "ROLE_CHANGED",
            "账户角色已变化，请重新登录",
            status_code=401,
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_user(
    request: Request,
    credentials: BearerCredentials,
    session: DatabaseSession,
    settings: AppSettings,
) -> User | None:
    token = credentials.credentials if credentials is not None else None
    token = token or request.cookies.get(settings.auth_cookie_name)
    if token is None:
        return None
    try:
        claims = decode_access_token(token, settings)
    except AccessTokenError:
        return None
    user = UserRepository(session).get(claims.user_id)
    if user is None or user.status != UserStatus.ACTIVE or user.role != claims.role:
        return None
    return user


OptionalCurrentUser = Annotated[User | None, Depends(get_optional_user)]


def require_roles(*allowed_roles: UserRole) -> Callable[[CurrentUser], User]:
    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise BusinessError("FORBIDDEN", "当前角色无权访问", status_code=403)
        return user

    return dependency


require_customer = require_roles(UserRole.CUSTOMER)
require_merchant = require_roles(UserRole.MERCHANT)
require_admin = require_roles(UserRole.ADMIN)

CustomerUser = Annotated[User, Depends(require_customer)]
MerchantUser = Annotated[User, Depends(require_merchant)]
AdminUser = Annotated[User, Depends(require_admin)]


def require_active_merchant(
    user: MerchantUser,
    session: DatabaseSession,
) -> Merchant:
    merchant = MerchantRepository(session).get_by_user_id(user.id)
    if merchant is None:
        raise BusinessError("MERCHANT_PROFILE_NOT_FOUND", "商家资料不存在", status_code=403)
    if merchant.status != MerchantStatus.ACTIVE:
        raise BusinessError("MERCHANT_NOT_ACTIVE", "商家尚未激活或已被冻结", status_code=403)
    return merchant


ActiveMerchant = Annotated[Merchant, Depends(require_active_merchant)]
