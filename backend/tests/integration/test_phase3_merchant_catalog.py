from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.catalog import Inventory, InventoryTransaction, Product, ProductPrice
from app.models.enums import ProductStatus, UserRole, UserStatus
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


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client: TestClient, prefix: str) -> tuple[int, str, str]:
    email = f"{prefix}-{uuid4().hex}@example.com"
    password = "Resume123!"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201
    token = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    return response.json()["id"], email, token


def create_admin(client: TestClient, engine: Engine) -> tuple[int, str]:
    email = f"admin-{uuid4().hex}@example.com"
    password = "Resume123!"
    with Session(engine) as session:
        admin = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(admin)
        session.commit()
        admin_id = admin.id
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return admin_id, response.json()["access_token"]


def approve_merchant(
    client: TestClient,
    engine: Engine,
    prefix: str,
) -> tuple[int, int, str]:
    user_id, email, customer_token = register_and_login(client, prefix)
    application = client.post(
        "/api/merchant/applications",
        headers=auth(customer_token),
        json={"business_name": f"{prefix} Business"},
    )
    assert application.status_code == 201
    merchant_id = application.json()["id"]
    _, admin_token = create_admin(client, engine)
    approved = client.post(
        f"/api/admin/merchant-applications/{merchant_id}/approve",
        headers=auth(admin_token),
    )
    assert approved.status_code == 200

    old_token_response = client.get("/api/auth/me", headers=auth(customer_token))
    assert old_token_response.status_code == 401
    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Resume123!"},
    )
    assert login.status_code == 200
    return user_id, merchant_id, login.json()["access_token"]


def create_category(client: TestClient, engine: Engine) -> int:
    _, admin_token = create_admin(client, engine)
    slug = f"category-{uuid4().hex}"
    response = client.post(
        "/api/admin/categories",
        headers=auth(admin_token),
        json={"name": "Phase 3 Category", "slug": slug},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_store_and_product(
    client: TestClient,
    token: str,
    category_id: int,
    prefix: str,
) -> int:
    store = client.post(
        "/api/merchant/store",
        headers=auth(token),
        json={"name": f"{prefix} Store", "description": "Resume demo store"},
    )
    assert store.status_code == 201
    product = client.post(
        "/api/merchant/products",
        headers=auth(token),
        json={
            "category_id": category_id,
            "sku": f"{prefix}-{uuid4().hex[:8]}",
            "name": f"{prefix} Product",
            "description": "Phase 3 test product",
            "tags": ["热卖", "包邮"],
            "current_price": "99.90",
        },
    )
    assert product.status_code == 201
    assert product.json()["status"] == "DRAFT"
    assert product.json()["inventory_quantity"] == 0
    assert product.json()["tags"] == ["热卖", "包邮"]
    return product.json()["id"]


@pytest.mark.integration
def test_merchant_application_approval_store_and_audit(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    user_id, merchant_id, token = approve_merchant(api_client, test_engine, "approval")
    store = api_client.post(
        "/api/merchant/store",
        headers=auth(token),
        json={"name": "Approved Merchant Store", "description": "Initial"},
    )
    assert store.status_code == 201
    assert store.json()["merchant_id"] == merchant_id

    updated = api_client.patch(
        "/api/merchant/store",
        headers=auth(token),
        json={"description": "Updated description"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated description"

    with Session(test_engine) as session:
        user = session.get(User, user_id)
        merchant = session.get(Merchant, merchant_id)
        audit_count = session.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.action == "MERCHANT_APPROVED",
                AuditLog.entity_id == merchant_id,
            )
        )
        assert user is not None and user.role == UserRole.MERCHANT
        assert merchant is not None and merchant.approved_by is not None
        assert audit_count == 1


@pytest.mark.integration
def test_product_inventory_price_status_and_soft_delete(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    user_id, _, token = approve_merchant(api_client, test_engine, "catalog")
    category_id = create_category(api_client, test_engine)
    product_id = create_store_and_product(api_client, token, category_id, "CAT")

    no_stock = api_client.post(
        f"/api/merchant/products/{product_id}/status",
        headers=auth(token),
        json={"status": "ACTIVE"},
    )
    assert no_stock.status_code == 409
    assert no_stock.json()["error"]["code"] == "PRODUCT_OUT_OF_STOCK"

    restocked = api_client.post(
        f"/api/merchant/products/{product_id}/inventory/restock",
        headers=auth(token),
        json={"quantity": 10, "reason": "initial stock"},
    )
    assert restocked.status_code == 200
    assert restocked.json()["quantity"] == 10
    adjusted = api_client.post(
        f"/api/merchant/products/{product_id}/inventory/adjust",
        headers=auth(token),
        json={"quantity_change": -2, "reason": "damaged items"},
    )
    assert adjusted.status_code == 200
    assert adjusted.json()["quantity"] == 8

    negative = api_client.post(
        f"/api/merchant/products/{product_id}/inventory/adjust",
        headers=auth(token),
        json={"quantity_change": -9, "reason": "invalid correction"},
    )
    assert negative.status_code == 409
    assert negative.json()["error"]["code"] == "INSUFFICIENT_INVENTORY"

    price = api_client.post(
        f"/api/merchant/products/{product_id}/price",
        headers=auth(token),
        json={"new_price": "109.80"},
    )
    assert price.status_code == 200
    assert price.json()["current_price"] == "109.80"
    activated = api_client.post(
        f"/api/merchant/products/{product_id}/status",
        headers=auth(token),
        json={"status": "ACTIVE"},
    )
    assert activated.status_code == 200

    transactions = api_client.get(
        f"/api/merchant/products/{product_id}/inventory/transactions",
        headers=auth(token),
    )
    prices = api_client.get(
        f"/api/merchant/products/{product_id}/prices",
        headers=auth(token),
    )
    assert [item["quantity_change"] for item in transactions.json()] == [-2, 10]
    assert len(prices.json()) == 1
    assert prices.json()[0]["changed_by"] == user_id

    deleted = api_client.delete(
        f"/api/merchant/products/{product_id}", headers=auth(token)
    )
    assert deleted.status_code == 204
    assert api_client.get("/api/merchant/products", headers=auth(token)).json() == []

    with Session(test_engine) as session:
        product = session.get(Product, product_id)
        inventory = session.get(Inventory, product_id)
        transaction_count = session.scalar(
            select(func.count(InventoryTransaction.id)).where(
                InventoryTransaction.product_id == product_id
            )
        )
        price_count = session.scalar(
            select(func.count(ProductPrice.id)).where(ProductPrice.product_id == product_id)
        )
        assert product is not None and product.status == ProductStatus.DELETED
        assert product.deleted_at is not None
        assert inventory is not None and inventory.quantity == 8 and inventory.version == 2
        assert transaction_count == 2
        assert price_count == 1


@pytest.mark.integration
def test_merchant_cannot_access_another_merchants_product(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    _, _, owner_token = approve_merchant(api_client, test_engine, "owner")
    _, _, attacker_token = approve_merchant(api_client, test_engine, "attacker")
    category_id = create_category(api_client, test_engine)
    product_id = create_store_and_product(api_client, owner_token, category_id, "OWN")
    api_client.post(
        "/api/merchant/store",
        headers=auth(attacker_token),
        json={"name": "Attacker Store"},
    )

    response = api_client.post(
        f"/api/merchant/products/{product_id}/inventory/restock",
        headers=auth(attacker_token),
        json={"quantity": 1, "reason": "cross-store attempt"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PRODUCT_NOT_OWNED"

    with Session(test_engine) as session:
        inventory = session.get(Inventory, product_id)
        assert inventory is not None and inventory.quantity == 0


@pytest.mark.integration
def test_admin_suspension_blocks_merchant_and_store(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    _, merchant_id, token = approve_merchant(api_client, test_engine, "suspend")
    api_client.post(
        "/api/merchant/store",
        headers=auth(token),
        json={"name": "Suspension Store"},
    )
    _, admin_token = create_admin(api_client, test_engine)
    response = api_client.patch(
        f"/api/admin/merchants/{merchant_id}/status",
        headers=auth(admin_token),
        json={"status": "SUSPENDED", "reason": "policy review"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "SUSPENDED"

    blocked = api_client.get("/api/merchant/store", headers=auth(token))
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "MERCHANT_NOT_ACTIVE"
