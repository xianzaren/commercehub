"""Regression cases use only the disposable MySQL test database."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_phase5_management import auth, login, seed_management_data

from app.db.session import get_db
from app.main import app
from app.models.catalog import Product
from app.models.order import Order, OrderItem, Payment
from app.models.user import Merchant
from app.repositories.management_repository import ManagementRepository
from app.services.management_service import MerchantManagementService

pytestmark = pytest.mark.integration


@pytest.fixture
def api_client(test_engine):
    def override():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_bug_001_revenue_uses_payment_time(test_engine):
    data = seed_management_data(test_engine)
    with Session(test_engine) as session:
        order = session.get(Order, data["paid_order_id"])
        order.created_at = datetime(2026, 1, 1, 12)
        payment = session.scalar(select(Payment).where(Payment.order_id == order.id))
        payment.paid_at = datetime(2026, 1, 2, 12)
        session.commit()
        repo = ManagementRepository(session)
        assert Decimal(
            str(
                repo.revenue_between(
                    datetime(2026, 1, 1), datetime(2026, 1, 2), store_id=data["store_id"]
                )
            )
        ) == Decimal("0")
        assert Decimal(
            str(
                repo.revenue_between(
                    datetime(2026, 1, 2), datetime(2026, 1, 3), store_id=data["store_id"]
                )
            )
        ) == Decimal("100")


def test_bug_002_product_rename_must_not_split_ranking(test_engine):
    data = seed_management_data(test_engine)
    with Session(test_engine) as session:
        product = session.get(Product, data["top_product_id"])
        original = session.get(Order, data["paid_order_id"])
        product.name = "Renamed product"
        order = Order(
            order_no=uuid4().hex,
            user_id=original.user_id,
            store_id=original.store_id,
            address_snapshot=original.address_snapshot,
            status="PAID",
            payment_status="PAID",
            subtotal=Decimal("50"),
            total_amount=Decimal("50"),
        )
        session.add(order)
        session.flush()
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                store_id=product.store_id,
                product_name_snapshot=product.name,
                sku_snapshot=product.sku,
                unit_price=Decimal("50"),
                quantity=1,
                subtotal=Decimal("50"),
            )
        )
        session.commit()
        rows = ManagementRepository(session).top_products(data["store_id"], 10)
        assert len(rows) == 1
        assert rows[0][1:3] == ("Renamed product", 3)
        assert rows[0][3] == Decimal("150")


def test_dashboard_boundaries_totals_and_isolation(api_client, test_engine):
    data = seed_management_data(test_engine)
    with Session(test_engine) as session:
        order = session.get(Order, data["paid_order_id"])
        # Two order lines must not double the order revenue in a join.
        order.total_amount = order.subtotal = Decimal("110")
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=data["low_product_id"],
                store_id=data["store_id"],
                product_name_snapshot="Second product",
                sku_snapshot="second",
                unit_price=Decimal("10"),
                quantity=1,
                subtotal=Decimal("10"),
            )
        )
        payment = session.scalar(select(Payment).where(Payment.order_id == order.id))
        payment.amount = Decimal("110")
        # UTC 16:00 is the start of the next Beijing day.
        payment.paid_at = datetime(2026, 1, 1, 16)
        session.commit()
    token = login(api_client, data["merchant_email"])
    url = "/api/merchant/analytics/dashboard?days=7&end_date=2026-01-08"
    result = api_client.get(url, headers=auth(token))
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["timezone"] == "Asia/Shanghai"
    assert len(body["daily"]) == 7
    assert body["daily"][0]["date"] == "2026-01-02"
    assert Decimal(body["totals"]["revenue"]) == Decimal("110")
    assert body["totals"]["order_count"] == 1
    assert body["totals"]["quantity_sold"] == 3
    assert body["daily"][0]["quantity_sold"] == 3
    assert all(Decimal(day["revenue"]) == 0 for day in body["daily"][1:])
    assert len(body["top_products"]) == 2
    assert sum(Decimal(p["revenue"]) for p in body["top_products"]) == Decimal("110")
    # Exclusive end: the same payment is not part of January 1.
    prior = api_client.get(
        "/api/merchant/analytics/dashboard?days=1&end_date=2026-01-01",
        headers=auth(token),
    ).json()
    assert Decimal(prior["totals"]["revenue"]) == 0
    filtered = api_client.get(url + f"&product_id={data['top_product_id']}", headers=auth(token))
    assert Decimal(filtered.json()["totals"]["revenue"]) == Decimal("100")
    assert filtered.json()["totals"]["quantity_sold"] == 2
    with Session(test_engine) as session:
        foreign_product = session.scalar(
            select(OrderItem.product_id).where(OrderItem.order_id == data["other_order_id"])
        )
        cancelled = session.get(Order, data["paid_order_id"])
        cancelled.status = "CANCELLED"
        session.commit()
    assert (
        api_client.get(url + f"&product_id={foreign_product}", headers=auth(token)).status_code
        == 404
    )
    assert Decimal(api_client.get(url, headers=auth(token)).json()["totals"]["revenue"]) == 0


def test_dashboard_auth_and_validation(api_client, test_engine):
    data = seed_management_data(test_engine)
    url = "/api/merchant/analytics/dashboard"
    assert api_client.get(url).status_code == 401
    customer = login(api_client, data["customer_email"])
    assert api_client.get(url, headers=auth(customer)).status_code == 403
    merchant = login(api_client, data["merchant_email"])
    for suffix in ("?days=0", "?days=91", "?product_id=0", "?end_date=bad"):
        assert api_client.get(url + suffix, headers=auth(merchant)).status_code == 422
    future = date.today() + timedelta(days=3)
    assert api_client.get(url + f"?end_date={future}", headers=auth(merchant)).status_code == 422


def test_summary_uses_beijing_day(test_engine, monkeypatch):
    data = seed_management_data(test_engine)
    monkeypatch.setattr("app.services.management_service.utcnow", lambda: datetime(2026, 1, 1, 17))
    with Session(test_engine) as session:
        payment = session.scalar(select(Payment).where(Payment.order_id == data["paid_order_id"]))
        payment.paid_at = datetime(2026, 1, 1, 16)
        session.commit()
        merchant = session.get(Merchant, data["merchant_id"])
        assert MerchantManagementService(session).analytics_summary(merchant)[
            "today_revenue"
        ] == Decimal("100")


def test_failed_attempts_refunds_and_previous_period(api_client, test_engine):
    data = seed_management_data(test_engine)
    with Session(test_engine) as session:
        paid = session.scalar(select(Payment).where(Payment.order_id == data["paid_order_id"]))
        paid.paid_at = datetime(2026, 1, 2, 0)
        session.add(
            Payment(
                order_id=paid.order_id,
                payment_no=uuid4().hex,
                idempotency_key=uuid4().hex,
                amount=Decimal("100"),
                method="MOCK_CARD",
                status="FAILED",
            )
        )
        session.commit()
    token = login(api_client, data["merchant_email"])
    url = "/api/merchant/analytics/dashboard?days=7&end_date=2026-01-15"
    result = api_client.get(url, headers=auth(token)).json()
    assert Decimal(result["totals"]["revenue"]) == 0
    assert Decimal(result["previous_totals"]["revenue"]) == Decimal("100")
    assert result["previous_totals"]["order_count"] == 1
    with Session(test_engine) as session:
        paid = session.scalar(
            select(Payment).where(
                Payment.order_id == data["paid_order_id"], Payment.status == "PAID"
            )
        )
        paid.status = "REFUNDED"
        session.commit()
    result = api_client.get(url, headers=auth(token)).json()
    assert Decimal(result["previous_totals"]["revenue"]) == 0
