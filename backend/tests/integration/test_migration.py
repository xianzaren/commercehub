import sqlalchemy as sa
from sqlalchemy import Engine


def test_migration_creates_all_domain_tables(test_engine: Engine) -> None:
    inspector = sa.inspect(test_engine)
    tables = set(inspector.get_table_names())
    assert {
        "users",
        "merchants",
        "stores",
        "categories",
        "products",
        "inventory",
        "inventory_transactions",
        "carts",
        "cart_items",
        "addresses",
        "orders",
        "order_items",
        "payments",
        "product_prices",
        "product_images",
        "product_variants",
        "favorites",
        "product_views",
        "search_histories",
        "audit_logs",
    } <= tables


def test_mysql_session_uses_read_committed(test_engine: Engine) -> None:
    with test_engine.connect() as connection:
        level = connection.scalar(sa.text("SELECT @@transaction_isolation"))
    assert str(level).upper() == "READ-COMMITTED"
