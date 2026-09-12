from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.enums import MerchantStatus, UserRole, UserStatus
from app.models.user import Merchant, User


@pytest.fixture
def api_client(test_engine: Engine) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def _register_and_login(client: TestClient, email: str, password: str = "Resume123!") -> str:
    register_response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return str(login_response.json()["access_token"])


@pytest.mark.integration
def test_register_login_me_and_logout(api_client: TestClient, test_engine: Engine) -> None:
    email = _email("customer")
    password = "Resume123!"
    token = _register_and_login(api_client, email, password)

    assert token.count(".") == 2
    assert "HttpOnly" in api_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    ).headers["set-cookie"]

    me_response = api_client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email
    assert me_response.json()["role"] == "CUSTOMER"

    with Session(test_engine) as session:
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None
        assert user.password_hash != password
        assert user.password_hash.startswith("$argon2id$")

    logout_response = api_client.post("/api/auth/logout")
    assert logout_response.status_code == 204
    assert api_client.get("/api/auth/me").status_code == 401


@pytest.mark.integration
def test_duplicate_registration_and_wrong_password(api_client: TestClient) -> None:
    email = _email("duplicate")
    _register_and_login(api_client, email)

    duplicate = api_client.post(
        "/api/auth/register",
        json={"email": email.upper(), "password": "Resume123!"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"

    wrong_password = api_client.post(
        "/api/auth/login",
        json={"email": email, "password": "Incorrect123!"},
    )
    assert wrong_password.status_code == 401
    assert wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.integration
def test_customer_cannot_access_admin_api(api_client: TestClient) -> None:
    token = _register_and_login(api_client, _email("rbac-customer"))
    response = api_client.get(
        "/api/admin/ping",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.integration
def test_suspension_invalidates_existing_token(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    email = _email("suspended")
    token = _register_and_login(api_client, email)

    with Session(test_engine) as session:
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None
        user.status = UserStatus.SUSPENDED
        session.commit()

    response = api_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_UNAVAILABLE"


@pytest.mark.integration
@pytest.mark.parametrize(
    ("merchant_status", "expected_status"),
    [(MerchantStatus.ACTIVE, 200), (MerchantStatus.PENDING, 403)],
)
def test_merchant_endpoint_requires_active_profile(
    api_client: TestClient,
    test_engine: Engine,
    merchant_status: MerchantStatus,
    expected_status: int,
) -> None:
    email = _email(f"merchant-{merchant_status.lower()}")
    password = "Resume123!"
    with Session(test_engine) as session:
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.MERCHANT,
            status=UserStatus.ACTIVE,
        )
        session.add(user)
        session.flush()
        session.add(
            Merchant(
                user_id=user.id,
                business_name=f"Merchant {merchant_status}",
                status=merchant_status,
            )
        )
        session.commit()

    login_response = api_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["access_token"]
    response = api_client.get(
        "/api/merchant/ping",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == expected_status


@pytest.mark.integration
def test_admin_role_can_access_admin_api(api_client: TestClient, test_engine: Engine) -> None:
    email = _email("admin")
    password = "Resume123!"
    with Session(test_engine) as session:
        session.add(
            User(
                email=email,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
            )
        )
        session.commit()

    login_response = api_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["access_token"]
    response = api_client.get(
        "/api/admin/ping",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"
