"""Common shopping defects: verify responses AND durable side effects."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_phase4_commerce import auth, create_catalog, create_customer, login

from app.db.session import get_db
from app.main import app
from app.models.catalog import Inventory, InventoryTransaction, Product, ProductVariant
from app.models.engagement import Favorite, SearchHistory
from app.models.order import Address, Order, Payment

pytestmark = pytest.mark.integration


@pytest.fixture
def client(test_engine):
    def override():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override
    try:
        # A server error must be an observable HTTP 500, not hide the response assertion.
        with TestClient(app, raise_server_exceptions=False) as api:
            yield api
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def shop(client, test_engine):
    product, store = create_catalog(test_engine, stock=5, price=Decimal("0.10"))
    user, email, password = create_customer(test_engine)
    headers = auth(login(client, email, password))
    address = client.get("/api/addresses", headers=headers).json()[0]["id"]
    return dict(product=product, store=store, user=user, headers=headers, address=address)


def add(client, shop, quantity=1, **extra):
    return client.post(
        "/api/cart/items",
        headers=shop["headers"],
        json={
            "product_id": shop["product"],
            "quantity": quantity,
            **extra,
        },
    )


def checkout(client, shop, **extra):
    return client.post(
        "/api/checkout",
        headers=shop["headers"],
        json={
            "address_id": shop["address"],
            "idempotency_key": uuid4().hex,
            **extra,
        },
    )


def pending(client, shop):
    assert add(client, shop, 3).status_code == 201
    response = checkout(client, shop)
    assert response.status_code == 201, response.text
    return response.json()


def pay(client, shop, order):
    return client.post(
        f"/api/orders/{order['id']}/pay",
        headers=shop["headers"],
        json={
            "method": "MOCK_CARD",
            "amount": order["total_amount"],
            "idempotency_key": uuid4().hex,
        },
    )


def assert_untouched(engine, shop, stock=5):
    with Session(engine) as session:
        assert session.get(Inventory, shop["product"]).quantity == stock
        assert (
            session.scalar(select(func.count(Order.id)).where(Order.user_id == shop["user"])) == 0
        )
        assert (
            session.scalar(
                select(func.count(InventoryTransaction.id)).where(
                    InventoryTransaction.product_id == shop["product"]
                )
            )
            == 0
        )


@pytest.mark.parametrize(
    "quantity", [0, -1, 10001, 1.5], ids=["zero", "negative", "too-large", "fraction"]
)
def test_invalid_cart_quantity_never_writes(client, test_engine, shop, quantity):
    assert add(client, shop, quantity).status_code == 422
    assert client.get("/api/cart", headers=shop["headers"]).json()["items"] == []
    assert_untouched(test_engine, shop)


def test_repeated_add_cannot_exceed_stock(client, test_engine, shop):
    assert add(client, shop, 3).status_code == 201
    result = add(client, shop, 3)
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    items = client.get("/api/cart", headers=shop["headers"]).json()["items"]
    assert len(items) == 1 and items[0]["quantity"] == 3
    assert_untouched(test_engine, shop)


@pytest.mark.parametrize("action", ["read", "pay", "cancel"])
def test_other_customer_cannot_touch_order(client, test_engine, shop, action):
    order = pending(client, shop)
    _, email, password = create_customer(test_engine)
    headers = auth(login(client, email, password))
    url = f"/api/orders/{order['id']}"
    if action == "read":
        response = client.get(url, headers=headers)
    elif action == "cancel":
        response = client.post(url + "/cancel", headers=headers)
    else:
        response = client.post(
            url + "/pay",
            headers=headers,
            json={
                "method": "MOCK_CARD",
                "amount": "0.30",
                "idempotency_key": uuid4().hex,
            },
        )
    assert response.status_code == 404, response.text
    with Session(test_engine) as session:
        assert session.get(Order, order["id"]).status == "PENDING_PAYMENT"
        assert session.get(Inventory, shop["product"]).quantity == 2
        assert (
            session.scalar(
                select(func.count(Payment.id)).where(
                    Payment.order_id == order["id"], Payment.status == "PAID"
                )
            )
            == 0
        )


@pytest.mark.parametrize("action", ["patch", "delete", "checkout"])
def test_foreign_address_is_not_usable(client, test_engine, shop, action):
    other, _, _ = create_customer(test_engine)
    with Session(test_engine) as session:
        foreign = session.scalar(select(Address.id).where(Address.user_id == other))
    assert add(client, shop).status_code == 201
    if action == "checkout":
        response = checkout(client, shop, address_id=foreign)
    elif action == "patch":
        response = client.patch(
            f"/api/addresses/{foreign}",
            headers=shop["headers"],
            json={"detail": "Unauthorized change"},
        )
    else:
        response = client.delete(f"/api/addresses/{foreign}", headers=shop["headers"])
    assert response.status_code == 404
    with Session(test_engine) as session:
        assert session.get(Address, foreign).detail == "No. 1 Test Road"
    assert_untouched(test_engine, shop)


def test_empty_checkout_has_no_side_effects(client, test_engine, shop):
    response = checkout(client, shop)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CART_EMPTY"
    assert_untouched(test_engine, shop)


@pytest.mark.parametrize("cause", ["stock-lost", "product-offline"])
def test_checkout_revalidates_cart_and_rolls_back(client, test_engine, shop, cause):
    assert add(client, shop, 3).status_code == 201
    with Session(test_engine) as session:
        if cause == "stock-lost":
            session.get(Inventory, shop["product"]).quantity = 1
        else:
            session.get(Product, shop["product"]).status = "INACTIVE"
        session.commit()
    response = checkout(client, shop)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "INSUFFICIENT_STOCK" if cause == "stock-lost" else "PRODUCT_NOT_AVAILABLE"
    )
    assert_untouched(test_engine, shop, stock=1 if cause == "stock-lost" else 5)
    assert client.get("/api/cart", headers=shop["headers"]).json()["items"][0]["quantity"] == 3


def test_decimal_totals_and_order_snapshot_survive_catalog_changes(client, test_engine, shop):
    order = pending(client, shop)
    assert Decimal(order["total_amount"]) == Decimal("0.30")
    with Session(test_engine) as session:
        product = session.get(Product, shop["product"])
        product.name = "Changed after purchase"
        product.current_price = Decimal("999.99")
        session.get(Address, shop["address"]).detail = "New delivery address"
        session.commit()
    saved = client.get(f"/api/orders/{order['id']}", headers=shop["headers"]).json()
    assert saved["items"] == order["items"]
    assert saved["address_snapshot"] == order["address_snapshot"]
    assert pay(client, shop, saved).status_code == 200


@pytest.mark.parametrize("paid", [False, True], ids=["unpaid", "paid-refund"])
def test_repeated_cancel_returns_stock_exactly_once(client, test_engine, shop, paid):
    order = pending(client, shop)
    if paid:
        assert pay(client, shop, order).status_code == 200
    url = f"/api/orders/{order['id']}/cancel"
    for _ in range(2):
        response = client.post(url, headers=shop["headers"])
        assert response.status_code == 200 and response.json()["status"] == "CANCELLED"
    assert pay(client, shop, order).status_code == 409
    with Session(test_engine) as session:
        assert session.get(Inventory, shop["product"]).quantity == 5
        changes = list(
            session.scalars(
                select(InventoryTransaction.quantity_change)
                .where(InventoryTransaction.product_id == shop["product"])
                .order_by(InventoryTransaction.id)
            )
        )
        assert changes == [-3, 3]
        assert (
            session.scalar(
                select(func.count(Payment.id)).where(
                    Payment.order_id == order["id"], Payment.status == "PAID"
                )
            )
            == 0
        )
        if paid:
            assert (
                session.scalar(
                    select(func.count(Payment.id)).where(
                        Payment.order_id == order["id"], Payment.status == "REFUNDED"
                    )
                )
                == 1
            )


def variants(engine, product):
    with Session(engine) as session:
        rows = [
            ProductVariant(
                product_id=product,
                sku=uuid4().hex,
                name=name,
                attributes={"颜色": name},
                price=Decimal("0.20"),
                status="ACTIVE",
                sort_order=i,
            )
            for i, name in enumerate(["红色", "橙色"])
        ]
        session.add_all(rows)
        session.commit()
        return [row.id for row in rows]


def test_sku_requires_selection_and_rejects_foreign_variant(client, test_engine, shop):
    variants(test_engine, shop["product"])
    foreign, _ = create_catalog(test_engine)
    foreign_variant = variants(test_engine, foreign)[0]
    assert add(client, shop).status_code == 422
    assert add(client, shop, variant_id=foreign_variant).status_code == 404
    assert_untouched(test_engine, shop)


def test_sku_shared_inventory_checked_on_add_and_update(client, test_engine, shop):
    first, second = variants(test_engine, shop["product"])
    assert add(client, shop, 3, variant_id=first).status_code == 201
    assert add(client, shop, 3, variant_id=second).status_code == 409
    result = add(client, shop, 2, variant_id=second)
    assert result.status_code == 201
    item_id = next(item["id"] for item in result.json()["items"] if item["variant_id"] == second)
    assert (
        client.patch(
            f"/api/cart/items/{item_id}", headers=shop["headers"], json={"quantity": 3}
        ).status_code
        == 409
    )
    order = checkout(client, shop)
    assert order.status_code == 201
    assert Decimal(order.json()["total_amount"]) == Decimal("1.00")
    with Session(test_engine) as session:
        assert session.get(Inventory, shop["product"]).quantity == 0


def test_offline_sku_cannot_checkout(client, test_engine, shop):
    variant = variants(test_engine, shop["product"])[0]
    assert add(client, shop, variant_id=variant).status_code == 201
    with Session(test_engine) as session:
        session.get(ProductVariant, variant).status = "INACTIVE"
        session.commit()
    response = checkout(client, shop)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VARIANT_NOT_AVAILABLE"
    assert_untouched(test_engine, shop)


def test_favorite_repeat_and_other_account_isolation(client, test_engine, shop):
    url = f"/api/favorites/{shop['product']}"
    for _ in range(2):
        assert client.post(url, headers=shop["headers"]).status_code == 200
    _, email, password = create_customer(test_engine)
    other = auth(login(client, email, password))
    assert client.get("/api/favorites/ids", headers=other).json() == []
    assert client.delete(url, headers=other).status_code == 200
    with Session(test_engine) as session:
        assert (
            session.scalar(select(func.count(Favorite.id)).where(Favorite.user_id == shop["user"]))
            == 1
        )
    for _ in range(2):
        assert client.delete(url, headers=shop["headers"]).status_code == 200
    assert client.get("/api/favorites/ids", headers=shop["headers"]).json() == []


def test_search_history_normalization_and_no_public_history(client, test_engine, shop):
    keyword = "probe" + uuid4().hex[:8]
    for value in [keyword.upper(), f"  {keyword}  ", "   "]:
        assert (
            client.get(
                "/api/products", headers=shop["headers"], params={"keyword": value}
            ).status_code
            == 200
        )
    # Anonymous search must not create a personal search history record.
    client.cookies.clear()
    assert client.get("/api/products", params={"keyword": keyword}).status_code == 200
    with Session(test_engine) as session:
        rows = list(
            session.scalars(select(SearchHistory).where(SearchHistory.user_id == shop["user"]))
        )
        assert len(rows) == 1
        assert rows[0].normalized_keyword == keyword and rows[0].search_count == 2
    assert client.get("/api/history/searches", headers=shop["headers"]).status_code == 404


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 101},
        {"min_price": "20", "max_price": "10"},
        {"keyword": "x" * 101},
    ],
    ids=["page-zero", "oversized-page", "reversed-price", "long-keyword"],
)
def test_invalid_search_is_rejected(client, params):
    assert client.get("/api/products", params=params).status_code == 422


def test_null_default_address_is_validation_error_not_server_error(client, test_engine, shop):
    response = client.patch(
        f"/api/addresses/{shop['address']}", headers=shop["headers"], json={"is_default": None}
    )
    assert response.status_code == 422, (
        f"Expected validation error, got {response.status_code}: {response.text}"
    )
    with Session(test_engine) as session:
        assert session.get(Address, shop["address"]).is_default is True


def test_duplicate_checkout_does_not_create_second_order(client, test_engine, shop):
    assert add(client, shop).status_code == 201
    key = uuid4().hex
    first = checkout(client, shop, idempotency_key=key)
    assert first.status_code == 201
    repeated = checkout(client, shop, idempotency_key=key)
    # Existing API may reject an emptied cart; both behaviors prevent double purchase.
    assert repeated.status_code in (200, 201, 409)
    if repeated.status_code != 409:
        assert repeated.json()["id"] == first.json()["id"]
    with Session(test_engine) as session:
        assert (
            session.scalar(select(func.count(Order.id)).where(Order.user_id == shop["user"])) == 1
        )
        assert session.get(Inventory, shop["product"]).quantity == 4
