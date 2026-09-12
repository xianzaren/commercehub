from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.catalog import Category, Inventory, Product
from app.models.enums import (
    CategoryStatus,
    MerchantStatus,
    OrderPaymentStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ProductStatus,
    StoreStatus,
    UserRole,
    UserStatus,
)
from app.models.order import Order, OrderItem, Payment
from app.models.user import Merchant, Store, User


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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


def login(client: TestClient, email: str, password: str = "Resume123!") -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def seed_management_data(engine: Engine) -> dict[str, object]:
    suffix = uuid4().hex
    password = "Resume123!"
    with Session(engine) as session:
        admin = User(
            email=f"phase5-admin-{suffix}@example.com",
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        merchant_user = User(
            email=f"phase5-merchant-{suffix}@example.com",
            password_hash=hash_password(password),
            role=UserRole.MERCHANT,
            status=UserStatus.ACTIVE,
        )
        other_merchant_user = User(
            email=f"phase5-other-{suffix}@example.com",
            password_hash=hash_password(password),
            role=UserRole.MERCHANT,
            status=UserStatus.ACTIVE,
        )
        customer = User(
            email=f"phase5-customer-{suffix}@example.com",
            password_hash=hash_password(password),
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
        )
        session.add_all([admin, merchant_user, other_merchant_user, customer])
        session.flush()

        merchant = Merchant(
            user_id=merchant_user.id,
            business_name="Phase 5 Merchant",
            status=MerchantStatus.ACTIVE,
        )
        other_merchant = Merchant(
            user_id=other_merchant_user.id,
            business_name="Other Merchant",
            status=MerchantStatus.ACTIVE,
        )
        session.add_all([merchant, other_merchant])
        session.flush()
        store = Store(
            merchant_id=merchant.id,
            name="Phase 5 Store",
            status=StoreStatus.ACTIVE,
        )
        other_store = Store(
            merchant_id=other_merchant.id,
            name="Other Store",
            status=StoreStatus.ACTIVE,
        )
        category = Category(
            name="Phase 5 Category",
            slug=f"phase5-{suffix}",
            status=CategoryStatus.ACTIVE,
        )
        session.add_all([store, other_store, category])
        session.flush()

        top_product = Product(
            store_id=store.id,
            category_id=category.id,
            sku=f"TOP-{suffix[:10]}",
            name="Top Product",
            current_price=Decimal("50.00"),
            status=ProductStatus.ACTIVE,
        )
        low_product = Product(
            store_id=store.id,
            category_id=category.id,
            sku=f"LOW-{suffix[:10]}",
            name="Low Stock Product",
            current_price=Decimal("10.00"),
            status=ProductStatus.ACTIVE,
        )
        other_product = Product(
            store_id=other_store.id,
            category_id=category.id,
            sku=f"OTHER-{suffix[:10]}",
            name="Other Product",
            current_price=Decimal("20.00"),
            status=ProductStatus.ACTIVE,
        )
        session.add_all([top_product, low_product, other_product])
        session.flush()
        session.add_all(
            [
                Inventory(
                    product_id=top_product.id,
                    quantity=8,
                    version=1,
                    updated_at=utcnow(),
                ),
                Inventory(
                    product_id=low_product.id,
                    quantity=1,
                    version=1,
                    updated_at=utcnow(),
                ),
                Inventory(
                    product_id=other_product.id,
                    quantity=5,
                    version=1,
                    updated_at=utcnow(),
                ),
            ]
        )

        snapshot = {
            "recipient_name": "Phase 5 Customer",
            "phone": "13800138000",
            "province": "Shanghai",
            "city": "Shanghai",
            "district": "Pudong",
            "detail": "Management Test Road",
            "postal_code": "",
        }
        paid_order = Order(
            order_no=uuid4().hex,
            user_id=customer.id,
            store_id=store.id,
            address_snapshot=snapshot,
            status=OrderStatus.PAID,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            payment_status=OrderPaymentStatus.PAID,
        )
        pending_order = Order(
            order_no=uuid4().hex,
            user_id=customer.id,
            store_id=store.id,
            address_snapshot=snapshot,
            status=OrderStatus.PENDING_PAYMENT,
            subtotal=Decimal("10.00"),
            total_amount=Decimal("10.00"),
            payment_status=OrderPaymentStatus.UNPAID,
        )
        other_order = Order(
            order_no=uuid4().hex,
            user_id=customer.id,
            store_id=other_store.id,
            address_snapshot=snapshot,
            status=OrderStatus.PAID,
            subtotal=Decimal("20.00"),
            total_amount=Decimal("20.00"),
            payment_status=OrderPaymentStatus.PAID,
        )
        session.add_all([paid_order, pending_order, other_order])
        session.flush()
        session.add_all(
            [
                OrderItem(
                    order_id=paid_order.id,
                    product_id=top_product.id,
                    store_id=store.id,
                    product_name_snapshot=top_product.name,
                    sku_snapshot=top_product.sku,
                    unit_price=Decimal("50.00"),
                    quantity=2,
                    subtotal=Decimal("100.00"),
                ),
                OrderItem(
                    order_id=pending_order.id,
                    product_id=low_product.id,
                    store_id=store.id,
                    product_name_snapshot=low_product.name,
                    sku_snapshot=low_product.sku,
                    unit_price=Decimal("10.00"),
                    quantity=1,
                    subtotal=Decimal("10.00"),
                ),
                OrderItem(
                    order_id=other_order.id,
                    product_id=other_product.id,
                    store_id=other_store.id,
                    product_name_snapshot=other_product.name,
                    sku_snapshot=other_product.sku,
                    unit_price=Decimal("20.00"),
                    quantity=1,
                    subtotal=Decimal("20.00"),
                ),
                Payment(
                    order_id=paid_order.id,
                    payment_no=uuid4().hex,
                    idempotency_key=f"paid-{uuid4().hex}",
                    method=PaymentMethod.MOCK_CARD,
                    amount=Decimal("100.00"),
                    status=PaymentStatus.PAID,
                    paid_at=utcnow(),
                ),
                Payment(
                    order_id=pending_order.id,
                    payment_no=uuid4().hex,
                    idempotency_key=f"pending-{uuid4().hex}",
                    method=PaymentMethod.MOCK_WALLET,
                    amount=Decimal("10.00"),
                    status=PaymentStatus.PENDING,
                ),
                Payment(
                    order_id=other_order.id,
                    payment_no=uuid4().hex,
                    idempotency_key=f"other-{uuid4().hex}",
                    method=PaymentMethod.MOCK_CARD,
                    amount=Decimal("20.00"),
                    status=PaymentStatus.PAID,
                    paid_at=utcnow(),
                ),
            ]
        )
        session.commit()
        return {
            "admin_id": admin.id,
            "admin_email": admin.email,
            "merchant_email": merchant_user.email,
            "customer_id": customer.id,
            "customer_email": customer.email,
            "merchant_id": merchant.id,
            "store_id": store.id,
            "top_product_id": top_product.id,
            "low_product_id": low_product.id,
            "paid_order_id": paid_order.id,
            "pending_order_id": pending_order.id,
            "other_order_id": other_order.id,
        }


@pytest.mark.integration
def test_merchant_order_workflow_ownership_and_analytics(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    data = seed_management_data(test_engine)
    token = login(api_client, str(data["merchant_email"]))

    orders = api_client.get("/api/merchant/orders", headers=auth(token))
    assert orders.status_code == 200
    assert orders.json()["total"] == 2
    foreign_order = api_client.get(
        f"/api/merchant/orders/{data['other_order_id']}", headers=auth(token)
    )
    assert foreign_order.status_code == 403
    assert foreign_order.json()["error"]["code"] == "ORDER_NOT_OWNED"

    invalid = api_client.patch(
        f"/api/merchant/orders/{data['pending_order_id']}/status",
        headers=auth(token),
        json={"status": "PROCESSING"},
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_ORDER_TRANSITION"

    processing = api_client.patch(
        f"/api/merchant/orders/{data['paid_order_id']}/status",
        headers=auth(token),
        json={"status": "PROCESSING"},
    )
    shipped = api_client.patch(
        f"/api/merchant/orders/{data['paid_order_id']}/status",
        headers=auth(token),
        json={"status": "SHIPPED"},
    )
    assert processing.status_code == 200
    assert shipped.json()["status"] == "SHIPPED"

    summary = api_client.get("/api/merchant/analytics/summary", headers=auth(token))
    top = api_client.get("/api/merchant/analytics/top-products", headers=auth(token))
    low = api_client.get(
        "/api/merchant/analytics/low-stock",
        headers=auth(token),
        params={"threshold": 1},
    )
    assert summary.status_code == 200
    assert summary.json()["paid_order_count"] == 1
    assert summary.json()["total_revenue"] == "100.00"
    assert summary.json()["average_order_amount"] == "100.00"
    assert top.json()[0]["product_id"] == data["top_product_id"]
    assert top.json()[0]["quantity_sold"] == 2
    assert low.json()["total"] == 1
    assert low.json()["items"][0]["product_id"] == data["low_product_id"]


@pytest.mark.integration
def test_admin_management_audit_and_platform_summary(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    data = seed_management_data(test_engine)
    admin_token = login(api_client, str(data["admin_email"]))
    customer_token = login(api_client, str(data["customer_email"]))

    users = api_client.get(
        "/api/admin/users",
        headers=auth(admin_token),
        params={"role": "CUSTOMER", "keyword": str(data["customer_email"])},
    )
    merchants = api_client.get("/api/admin/merchants", headers=auth(admin_token))
    stores = api_client.get("/api/admin/stores", headers=auth(admin_token))
    products = api_client.get("/api/admin/products", headers=auth(admin_token))
    orders = api_client.get("/api/admin/orders", headers=auth(admin_token))
    assert users.status_code == 200 and users.json()["total"] == 1
    assert merchants.status_code == 200 and merchants.json()["total"] >= 2
    assert stores.status_code == 200 and stores.json()["total"] >= 2
    assert products.status_code == 200 and products.json()["total"] >= 3
    assert orders.status_code == 200 and orders.json()["total"] >= 3

    self_suspend = api_client.patch(
        f"/api/admin/users/{data['admin_id']}/status",
        headers=auth(admin_token),
        json={"status": "SUSPENDED", "reason": "must be rejected"},
    )
    assert self_suspend.status_code == 409
    assert self_suspend.json()["error"]["code"] == "CANNOT_SUSPEND_SELF"

    suspended = api_client.patch(
        f"/api/admin/users/{data['customer_id']}/status",
        headers=auth(admin_token),
        json={"status": "SUSPENDED", "reason": "security review"},
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "SUSPENDED"
    assert api_client.get("/api/auth/me", headers=auth(customer_token)).status_code == 403

    before = api_client.get(
        f"/api/products/{data['low_product_id']}"
    )
    deactivated = api_client.post(
        f"/api/admin/products/{data['low_product_id']}/force-deactivate",
        headers=auth(admin_token),
        json={"reason": "policy violation"},
    )
    after = api_client.get(f"/api/products/{data['low_product_id']}")
    assert before.status_code == 200
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"
    assert after.status_code == 404

    logs = api_client.get("/api/admin/audit-logs", headers=auth(admin_token))
    summary = api_client.get("/api/admin/analytics/summary", headers=auth(admin_token))
    actions = {item["action"] for item in logs.json()["items"]}
    assert {"USER_STATUS_CHANGED", "PRODUCT_FORCE_DEACTIVATED"} <= actions
    assert summary.status_code == 200
    assert summary.json()["paid_order_count"] >= 2
    assert Decimal(summary.json()["total_revenue"]) >= Decimal("120.00")

    with Session(test_engine) as session:
        product = session.get(Product, int(data["low_product_id"]))
        customer = session.get(User, int(data["customer_id"]))
        assert product is not None and product.status == ProductStatus.INACTIVE
        assert customer is not None and customer.status == UserStatus.SUSPENDED
