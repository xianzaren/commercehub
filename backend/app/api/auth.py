from fastapi import APIRouter, Response, status

from app.api.deps import AppSettings, CurrentUser, DatabaseSession
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> UserResponse:
    user = AuthService(session, settings).register(str(payload.email), payload.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: DatabaseSession,
    settings: AppSettings,
) -> LoginResponse:
    user, access_token = AuthService(session, settings).authenticate(
        str(payload.email),
        payload.password,
    )
    max_age = settings.jwt_access_token_minutes * 60
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=access_token,
        max_age=max_age,
        httponly=True,
        secure=settings.app_env not in {"development", "test"},
        samesite="lax",
        path="/",
    )
    return LoginResponse(
        access_token=access_token,
        expires_in=max_age,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, settings: AppSettings) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.app_env not in {"development", "test"},
        httponly=True,
        samesite="lax",
    )
