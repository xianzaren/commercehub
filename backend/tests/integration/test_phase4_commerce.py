from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.cart import Cart, CartItem
from app.models.catalog import Category, Inventory, InventoryTransaction, Product
from app.models.enums import (
    CartStatus,
    CategoryStatus,
    MerchantStatus,
    PaymentMethod,
    ProductStatus,
    StoreStatus,
    UserRole,
    UserStatus,
)
from app.models.order import Address, Order, OrderItem, Payment
from app.models.user import Merchant, Store, User
from app.services.commerce_service import CheckoutService


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


def create_catalog(
    engine: Engine,
    *,
    stock: int = 10,
    price: Decimal = Decimal("49.90"),
    name: str = "Phase 4 Product",
) -> tuple[int, int]:
    suffix = uuid4().hex
    with Session(engine) as session:
        merchant_user = User(
            email=f"merchant-{suffix}@example.com",
            password_hash=hash_password("Resume123!"),
            role=UserRole.MERCHANT,
            status=UserStatus.ACTIVE,
        )
        session.add(merchant_user)
        session.flush()
        merchant = Merchant(
            user_id=merchant_user.id,
            business_name=f"Business {suffix}",
            status=MerchantStatus.ACTIVE,
        )
        session.add(merchant)
        session.flush()
        store = Store(
            merchant_id=merchant.id,
            name=f"Store {suffix}",
            status=StoreStatus.ACTIVE,
        )
        category = Category(
            name=f"Category {suffix}",
            slug=f"phase4-{suffix}",
            status=CategoryStatus.ACTIVE,
        )
        session.add_all([store, category])
        session.flush()
        product = Product(
            store_id=store.id,
            category_id=category.id,
            sku=f"P4-{suffix[:12]}",
            name=name,
            current_price=price,
            status=ProductStatus.ACTIVE,
        )
        session.add(product)
        session.flush()
        session.add(
            Inventory(
                product_id=product.id,
                quantity=stock,
                version=0,
                updated_at=utcnow(),
            )
        )
        session.commit()
        return product.id, store.id


def create_customer(engine: Engine) -> tuple[int, str, str]:
    suffix = uuid4().hex
    email = f"customer-{suffix}@example.com"
    password = "Resume123!"
    with Session(engine) as session:
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
        )
        session.add(user)
        session.flush()
        address = Address(
            user_id=user.id,
            recipient_name="Test Customer",
            phone="13800138000",
            province="Shanghai",
            city="Shanghai",
            district="Pudong",
            detail="No. 1 Test Road",
            is_default=True,
        )
        session.add(address)
        session.commit()
        return user.id, email, password


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def prepare_cart(
    engine: Engine,
    user_id: int,
    product_id: int,
    store_id: int,
    quantity: int,
) -> int:
    with Session(engine) as session:
        cart = Cart(user_id=user_id, store_id=store_id, status=CartStatus.ACTIVE)
        session.add(cart)
        session.flush()
        session.add(CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity))
        address_id = session.scalar(select(Address.id).where(Address.user_id == user_id))
        session.commit()
        assert address_id is not None
        return address_id


@pytest.mark.integration
def test_product_search_filters_by_any_character_and_orders_by_relevance(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    strongest_id, _ = create_catalog(test_engine, name="翾翯翱主题灯")
    medium_id, _ = create_catalog(test_engine, name="翾翯桌垫")
    weakest_id, _ = create_catalog(test_engine, name="翾杯")

    response = api_client.get("/api/products", params={"keyword": "翾翯翱"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert [item["id"] for item in payload["items"]] == [strongest_id, medium_id, weakest_id]

    no_match = api_client.get("/api/products", params={"keyword": "龘靐齉"})
    assert no_match.status_code == 200
    assert no_match.json()["total"] == 0


@pytest.mark.integration
def test_customer_browse_cart_checkout_and_idempotent_payment(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    product_id, _ = create_catalog(
        test_engine,
        stock=5,
        price=Decimal("49.90"),
        name="Searchable Mechanical Keyboard",
    )
    _, email, password = create_customer(test_engine)
    token = login(api_client, email, password)

    search = api_client.get(
        "/api/products",
        params={"keyword": "Mechanical", "min_price": "40", "max_price": "60"},
    )
    assert search.status_code == 200
    assert search.json()["total"] == 1
    assert search.json()["items"][0]["id"] == product_id
    assert search.json()["items"][0]["category_name"].startswith("Category ")
    assert search.json()["items"][0]["store_name"].startswith("Store ")
    assert search.json()["items"][0]["tags"] == []
    assert search.json()["items"][0]["sales_count"] == 0
    product_detail = api_client.get(f"/api/products/{product_id}")
    assert product_detail.status_code == 200
    assert product_detail.json()["sales_count"] == 0

    cart = api_client.post(
        "/api/cart/items",
        headers=auth(token),
        json={"product_id": product_id, "quantity": 2},
    )
    assert cart.status_code == 201
    assert cart.json()["total_amount"] == "99.80"
    assert cart.json()["items"][0]["available_stock"] == 5

    address = api_client.post(
        "/api/addresses",
        headers=auth(token),
        json={
            "recipient_name": "Second Recipient",
            "phone": "13900139000",
            "province": "Beijing",
            "city": "Beijing",
            "district": "Haidian",
            "detail": "No. 2 Resume Road",
            "is_default": True,
        },
    )
    assert address.status_code == 201
    assert address.json()["is_default"] is True

    checkout_key = f"checkout-{uuid4().hex}"
    checkout = api_client.post(
        "/api/checkout",
        headers=auth(token),
        json={
            "address_id": address.json()["id"],
            "payment_method": "MOCK_CARD",
            "idempotency_key": checkout_key,
        },
    )
    assert checkout.status_code == 201
    order = checkout.json()
    assert order["status"] == "PENDING_PAYMENT"
    assert order["items"][0]["product_name_snapshot"] == "Searchable Mechanical Keyboard"
    assert order["payments"][0]["status"] == "PENDING"
    assert api_client.get(f"/api/products/{product_id}").json()["sales_count"] == 0

    payment_payload = {
        "method": "MOCK_CARD",
        "amount": "99.80",
        "idempotency_key": checkout_key,
        "simulate_failure": False,
    }
    paid = api_client.post(
        f"/api/orders/{order['id']}/pay",
        headers=auth(token),
        json=payment_payload,
    )
    repeated = api_client.post(
        f"/api/orders/{order['id']}/pay",
        headers=auth(token),
        json=payment_payload,
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "PAID"
    assert repeated.json()["id"] == paid.json()["id"]
    assert api_client.get(f"/api/products/{product_id}").json()["sales_count"] == 2

    with Session(test_engine) as session:
        inventory = session.get(Inventory, product_id)
        order_item = session.scalar(select(OrderItem).where(OrderItem.order_id == order["id"]))
        payment_count = session.scalar(
            select(func.count(Payment.id)).where(Payment.order_id == order["id"])
        )
        assert inventory is not None and inventory.quantity == 3
        assert order_item is not None and order_item.unit_price == Decimal("49.90")
        assert payment_count == 1


@pytest.mark.integration
def test_cart_rejects_other_store_and_cancel_restores_inventory(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    product_id, _ = create_catalog(test_engine, stock=3)
    other_product_id, _ = create_catalog(test_engine, stock=3)
    _, email, password = create_customer(test_engine)
    token = login(api_client, email, password)
    first = api_client.post(
        "/api/cart/items",
        headers=auth(token),
        json={"product_id": product_id, "quantity": 1},
    )
    assert first.status_code == 201
    conflict = api_client.post(
        "/api/cart/items",
        headers=auth(token),
        json={"product_id": other_product_id, "quantity": 1},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CART_STORE_CONFLICT"

    addresses = api_client.get("/api/addresses", headers=auth(token)).json()
    checkout = api_client.post(
        "/api/checkout",
        headers=auth(token),
        json={
            "address_id": addresses[0]["id"],
            "payment_method": "MOCK_WALLET",
            "idempotency_key": f"cancel-{uuid4().hex}",
        },
    )
    assert checkout.status_code == 201
    order_id = checkout.json()["id"]
    cancelled = api_client.post(f"/api/orders/{order_id}/cancel", headers=auth(token))
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    with Session(test_engine) as session:
        inventory = session.get(Inventory, product_id)
        changes = list(
            session.scalars(
                select(InventoryTransaction.quantity_change)
                .where(InventoryTransaction.reference_id == order_id)
                .order_by(InventoryTransaction.id)
            )
        )
        assert inventory is not None and inventory.quantity == 3
        assert changes == [-1, 1]


@pytest.mark.integration
def test_checkout_failure_rolls_back_everything(test_engine: Engine) -> None:
    product_id, store_id = create_catalog(test_engine, stock=4)
    user_id, _, _ = create_customer(test_engine)
    address_id = prepare_cart(test_engine, user_id, product_id, store_id, 2)

    with Session(test_engine) as session:
        user = session.get(User, user_id)
        assert user is not None
        with pytest.raises(RuntimeError, match="injected checkout failure"):
            CheckoutService(session).checkout(
                user,
                address_id,
                PaymentMethod.MOCK_CARD,
                f"rollback-{uuid4().hex}",
                fail_after_order_items=True,
            )

    with Session(test_engine) as session:
        inventory = session.get(Inventory, product_id)
        cart = session.scalar(
            select(Cart).where(Cart.user_id == user_id, Cart.status == CartStatus.ACTIVE)
        )
        order_count = session.scalar(select(func.count(Order.id)).where(Order.user_id == user_id))
        sale_count = session.scalar(
            select(func.count(InventoryTransaction.id)).where(
                InventoryTransaction.product_id == product_id,
                InventoryTransaction.type == "SALE",
            )
        )
        payment_count = session.scalar(
            select(func.count(Payment.id)).join(Order).where(Order.user_id == user_id)
        )
        order_item_count = session.scalar(
            select(func.count(OrderItem.id)).join(Order).where(Order.user_id == user_id)
        )
        assert inventory is not None and inventory.quantity == 4
        assert cart is not None
        assert order_count == 0
        assert sale_count == 0
        assert payment_count == 0
        assert order_item_count == 0


@pytest.mark.integration
def test_payment_failure_amount_validation_and_retry(
    api_client: TestClient,
    test_engine: Engine,
) -> None:
    product_id, store_id = create_catalog(test_engine, stock=2, price=Decimal("25.00"))
    user_id, email, password = create_customer(test_engine)
    address_id = prepare_cart(test_engine, user_id, product_id, store_id, 1)
    token = login(api_client, email, password)
    checkout = api_client.post(
        "/api/checkout",
        headers=auth(token),
        json={
            "address_id": address_id,
            "payment_method": "MOCK_CARD",
            "idempotency_key": f"initial-{uuid4().hex}",
        },
    )
    assert checkout.status_code == 201
    order_id = checkout.json()["id"]

    mismatch = api_client.post(
        f"/api/orders/{order_id}/pay",
        headers=auth(token),
        json={
            "method": "MOCK_CARD",
            "amount": "24.99",
            "idempotency_key": f"wrong-{uuid4().hex}",
        },
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "PAYMENT_AMOUNT_MISMATCH"

    failure_key = f"failure-{uuid4().hex}"
    failed_payload = {
        "method": "MOCK_WALLET",
        "amount": "25.00",
        "idempotency_key": failure_key,
        "simulate_failure": True,
    }
    failed = api_client.post(
        f"/api/orders/{order_id}/pay",
        headers=auth(token),
        json=failed_payload,
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "FAILED"

    failed_payload["simulate_failure"] = False
    repeated = api_client.post(
        f"/api/orders/{order_id}/pay",
        headers=auth(token),
        json=failed_payload,
    )
    assert repeated.status_code == 200
    assert repeated.json()["id"] == failed.json()["id"]
    assert repeated.json()["status"] == "FAILED"
    order = api_client.get(f"/api/orders/{order_id}", headers=auth(token))
    assert order.json()["status"] == "PENDING_PAYMENT"


@pytest.mark.integration
def test_two_customers_competing_for_last_item_only_one_succeeds(test_engine: Engine) -> None:
    product_id, store_id = create_catalog(test_engine, stock=1)
    first_user_id, _, _ = create_customer(test_engine)
    second_user_id, _, _ = create_customer(test_engine)
    first_address_id = prepare_cart(test_engine, first_user_id, product_id, store_id, 1)
    second_address_id = prepare_cart(test_engine, second_user_id, product_id, store_id, 1)
    barrier = Barrier(2)

    def attempt(user_id: int, address_id: int) -> str:
        with Session(test_engine) as session:
            user = session.get(User, user_id)
            assert user is not None
            barrier.wait(timeout=5)
            try:
                CheckoutService(session).checkout(
                    user,
                    address_id,
                    PaymentMethod.MOCK_CARD,
                    f"concurrent-{uuid4().hex}",
                )
            except BusinessError as exc:
                return exc.code
            return "SUCCESS"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda args: attempt(*args),
                [(first_user_id, first_address_id), (second_user_id, second_address_id)],
            )
        )

    assert sorted(results) == ["INSUFFICIENT_STOCK", "SUCCESS"]
    with Session(test_engine) as session:
        inventory = session.get(Inventory, product_id)
        order_count = session.scalar(
            select(func.count(Order.id)).where(Order.user_id.in_([first_user_id, second_user_id]))
        )
        sale_count = session.scalar(
            select(func.count(InventoryTransaction.id)).where(
                InventoryTransaction.product_id == product_id,
                InventoryTransaction.type == "SALE",
            )
        )
        assert inventory is not None and inventory.quantity == 0
        assert order_count == 1
        assert sale_count == 1
