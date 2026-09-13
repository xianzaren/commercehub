from sqlalchemy import CheckConstraint

from app import models  # noqa: F401
from app.db.base import Base

EXPECTED_TABLES = {
    "addresses",
    "audit_logs",
    "cart_items",
    "carts",
    "categories",
    "favorites",
    "inventory",
    "inventory_transactions",
    "merchants",
    "order_items",
    "orders",
    "payments",
    "product_images",
    "product_prices",
    "product_variants",
    "product_views",
    "products",
    "search_histories",
    "stores",
    "users",
}


def test_metadata_contains_expected_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_inventory_has_nonnegative_check() -> None:
    checks = {
        constraint.name
        for constraint in Base.metadata.tables["inventory"].constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_inventory_nonnegative_quantity" in checks


def test_conditional_unique_columns_are_computed() -> None:
    carts = Base.metadata.tables["carts"]
    payments = Base.metadata.tables["payments"]
    assert carts.c.active_user_id.computed is not None
    assert payments.c.paid_order_id.computed is not None
