from collections.abc import Iterator
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.catalog import Inventory, InventoryTransaction
from app.models.enums import UserRole, UserStatus
from app.models.order import Order, OrderItem
from app.models.user import User


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


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.integration
def test_customer_merchant_admin_complete_demo_flow(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    suffix = uuid4().hex
    password = "Resume123!"
    admin_email = f"e2e-admin-{suffix}@example.com"
    merchant_email = f"e2e-merchant-{suffix}@example.com"
    customer_email = f"e2e-customer-{suffix}@example.com"

    with Session(test_engine) as session:
        session.add(
            User(
                email=admin_email,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
            )
        )
        session.commit()
    admin_token = login(api_client, admin_email, password)

    merchant_registration = api_client.post(
        "/api/auth/register", json={"email": merchant_email, "password": password}
    )
    customer_registration = api_client.post(
        "/api/auth/register", json={"email": customer_email, "password": password}
    )
    assert merchant_registration.status_code == 201
    assert customer_registration.status_code == 201

    applicant_token = login(api_client, merchant_email, password)
    application = api_client.post(
        "/api/merchant/applications",
        headers=auth(applicant_token),
        json={"business_name": "Phase 7 E2E Merchant"},
    )
    assert application.status_code == 201
    approved = api_client.post(
        f"/api/admin/merchant-applications/{application.json()['id']}/approve",
        headers=auth(admin_token),
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "ACTIVE"
    merchant_token = login(api_client, merchant_email, password)

    category = api_client.post(
        "/api/admin/categories",
        headers=auth(admin_token),
        json={"name": "Phase 7 E2E", "slug": f"phase7-e2e-{suffix}"},
    )
    store = api_client.post(
        "/api/merchant/store",
        headers=auth(merchant_token),
        json={"name": "Phase 7 E2E Store", "description": "Complete browser demo flow"},
    )
    assert category.status_code == 201
    assert store.status_code == 201

    product = api_client.post(
        "/api/merchant/products",
        headers=auth(merchant_token),
        json={
            "category_id": category.json()["id"],
            "sku": f"E2E-{suffix[:12]}",
            "name": "Phase 7 Transaction Product",
            "description": "Created by the final end-to-end test",
            "current_price": "88.80",
        },
    )
    product_id = product.json()["id"]
    restock = api_client.post(
        f"/api/merchant/products/{product_id}/inventory/restock",
        headers=auth(merchant_token),
        json={"quantity": 5, "reason": "E2E initial stock"},
    )
    activated = api_client.post(
        f"/api/merchant/products/{product_id}/status",
        headers=auth(merchant_token),
        json={"status": "ACTIVE"},
    )
    assert product.status_code == 201
    assert restock.json()["quantity"] == 5
    assert activated.json()["status"] == "ACTIVE"

    customer_token = login(api_client, customer_email, password)
    address = api_client.post(
        "/api/addresses",
        headers=auth(customer_token),
        json={
            "recipient_name": "E2E Customer",
            "phone": "13800138000",
            "province": "Shanghai",
            "city": "Shanghai",
            "district": "Pudong",
            "detail": "No. 7 Transaction Road",
            "is_default": True,
        },
    )
    cart = api_client.post(
        "/api/cart/items",
        headers=auth(customer_token),
        json={"product_id": product_id, "quantity": 1},
    )
    checkout_key = f"phase7-checkout-{suffix}"
    checkout = api_client.post(
        "/api/checkout",
        headers=auth(customer_token),
        json={
            "address_id": address.json()["id"],
            "payment_method": "MOCK_CARD",
            "idempotency_key": checkout_key,
        },
    )
    assert address.status_code == 201
    assert cart.status_code == 201
    assert checkout.status_code == 201
    order_id = checkout.json()["id"]
    payment = api_client.post(
        f"/api/orders/{order_id}/pay",
        headers=auth(customer_token),
        json={
            "method": "MOCK_CARD",
            "amount": "88.80",
            "idempotency_key": checkout_key,
            "simulate_failure": False,
        },
    )
    assert payment.status_code == 200
    assert payment.json()["status"] == "PAID"

    merchant_orders = api_client.get("/api/merchant/orders", headers=auth(merchant_token))
    processing = api_client.patch(
        f"/api/merchant/orders/{order_id}/status",
        headers=auth(merchant_token),
        json={"status": "PROCESSING"},
    )
    shipped = api_client.patch(
        f"/api/merchant/orders/{order_id}/status",
        headers=auth(merchant_token),
        json={"status": "SHIPPED"},
    )
    assert merchant_orders.status_code == 200
    assert any(item["id"] == order_id for item in merchant_orders.json()["items"])
    assert processing.json()["status"] == "PROCESSING"
    assert shipped.json()["status"] == "SHIPPED"

    audit = api_client.get("/api/admin/audit-logs", headers=auth(admin_token))
    assert audit.status_code == 200
    actions = {item["action"] for item in audit.json()["items"]}
    assert {"MERCHANT_APPROVED", "MERCHANT_ORDER_STATUS_CHANGED"} <= actions

    with Session(test_engine) as session:
        inventory = session.get(Inventory, product_id)
        order = session.get(Order, order_id)
        item = session.scalar(select(OrderItem).where(OrderItem.order_id == order_id))
        transaction_types = set(
            session.scalars(
                select(InventoryTransaction.type).where(
                    InventoryTransaction.product_id == product_id
                )
            )
        )
        assert inventory is not None and inventory.quantity == 4
        assert order is not None and order.status == "SHIPPED"
        assert item is not None and item.unit_price == Decimal("88.80")
        assert {"RESTOCK", "SALE"} <= transaction_types
        assert session.scalar(
            select(AuditLog.id).where(
                AuditLog.action == "MERCHANT_ORDER_STATUS_CHANGED",
                AuditLog.entity_id == order_id,
            )
        ) is not None
