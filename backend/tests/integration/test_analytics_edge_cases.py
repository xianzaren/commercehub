"""Calendar, status matrix, historical pricing, ranking and tenant boundaries."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_phase5_management import auth, login, seed_management_data

from app.db.session import get_db
from app.main import app
from app.models.catalog import Product
from app.models.order import Order, Payment
from app.models.user import Merchant

pytestmark = pytest.mark.integration


@pytest.fixture
def scenario(test_engine):
    def override():
        with Session(test_engine) as session:
            yield session

    data = seed_management_data(test_engine)
    with Session(test_engine) as session:
        payment = session.scalar(select(Payment).where(Payment.order_id == data["paid_order_id"]))
        payment.paid_at = datetime(2024, 2, 29, 0)
        session.commit()
    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            yield client, auth(login(client, data["merchant_email"])), data
    finally:
        app.dependency_overrides.clear()


def dashboard(scenario, **params):
    client, headers, _ = scenario
    response = client.get(
        "/api/merchant/analytics/dashboard",
        headers=headers,
        params={"days": 7, "end_date": "2024-03-01", **params},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert sum(Decimal(row["revenue"]) for row in body["daily"]) == Decimal(
        body["totals"]["revenue"]
    )
    assert sum(row["order_count"] for row in body["daily"]) == body["totals"]["order_count"]
    assert sum(row["quantity_sold"] for row in body["daily"]) == body["totals"]["quantity_sold"]
    return body


@pytest.mark.parametrize(
    "status,included",
    [
        ("PAID", True),
        ("PROCESSING", True),
        ("SHIPPED", True),
        ("COMPLETED", True),
        ("CANCELLED", False),
        ("PENDING_PAYMENT", False),
    ],
)
def test_order_status_matrix(scenario, test_engine, status, included):
    with Session(test_engine) as session:
        session.get(Order, scenario[2]["paid_order_id"]).status = status
        session.commit()
    body = dashboard(scenario)
    assert Decimal(body["totals"]["revenue"]) == (100 if included else 0)
    assert body["totals"]["quantity_sold"] == (2 if included else 0)
    assert len(body["top_products"]) == (1 if included else 0)


@pytest.mark.parametrize("status", ["PENDING", "FAILED", "REFUNDED"])
def test_non_successful_payment_excluded_everywhere(scenario, test_engine, status):
    with Session(test_engine) as session:
        payment = session.scalar(
            select(Payment).where(Payment.order_id == scenario[2]["paid_order_id"])
        )
        payment.status = status
        session.commit()
    body = dashboard(scenario)
    assert Decimal(body["totals"]["revenue"]) == 0
    assert body["totals"]["order_count"] == 0
    assert body["top_products"] == []


@pytest.mark.parametrize(
    "days,end",
    [(1, "2024-02-29"), (7, "2024-03-01"), (30, "2024-01-05"), (90, "2024-03-01")],
    ids=["leap-day", "month-boundary", "year-boundary", "max-range"],
)
def test_calendar_days_are_contiguous_without_duplicates(scenario, days, end):
    body = dashboard(scenario, days=days, end_date=end)
    expected = [
        (date.fromisoformat(end) - timedelta(days=i)).isoformat() for i in reversed(range(days))
    ]
    assert [row["date"] for row in body["daily"]] == expected
    assert body["start_date"] == expected[0] and body["end_date"] == expected[-1]
    assert Decimal(body["totals"]["revenue"]) == (0 if end == "2024-01-05" else 100)


def test_catalog_price_change_and_soft_delete_do_not_erase_history(scenario, test_engine):
    with Session(test_engine) as session:
        product = session.get(Product, scenario[2]["top_product_id"])
        product.current_price = Decimal("9999.99")
        product.name = "新名称，旧成交价格"
        product.status = "DELETED"
        product.deleted_at = datetime(2024, 3, 1)
        session.commit()
    body = dashboard(scenario, product_id=scenario[2]["top_product_id"])
    assert Decimal(body["totals"]["revenue"]) == 100
    assert Decimal(body["totals"]["average_order_amount"]) == 100
    assert body["top_products"][0]["product_name"] == "新名称，旧成交价格"
    assert body["top_products"][0]["quantity_sold"] == 2


def test_foreign_store_parameter_cannot_change_scope(scenario, test_engine):
    with Session(test_engine) as session:
        foreign = session.get(Order, scenario[2]["other_order_id"])
        foreign_store = foreign.store_id
        payment = session.scalar(select(Payment).where(Payment.order_id == foreign.id))
        payment.paid_at = datetime(2024, 2, 29, 0)
        session.commit()
    body = dashboard(scenario, store_id=foreign_store)
    assert Decimal(body["totals"]["revenue"]) == 100
    assert {row["id"] for row in body["products"]} == {
        scenario[2]["top_product_id"],
        scenario[2]["low_product_id"],
    }


def test_existing_token_stops_working_after_merchant_suspension(scenario, test_engine):
    client, headers, data = scenario
    with Session(test_engine) as session:
        session.get(Merchant, data["merchant_id"]).status = "SUSPENDED"
        session.commit()
    response = client.get("/api/merchant/analytics/dashboard", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "MERCHANT_NOT_ACTIVE"


def test_zero_sales_owned_product_has_zero_metrics_not_store_metrics(scenario):
    body = dashboard(scenario, product_id=scenario[2]["low_product_id"])
    assert Decimal(body["totals"]["revenue"]) == 0
    assert Decimal(body["totals"]["average_order_amount"]) == 0
    assert body["totals"]["order_count"] == 0
    assert body["top_products"] == []
