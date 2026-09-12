"""Print reproducible MySQL EXPLAIN ANALYZE evidence for portfolio review."""

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import build_engine

QUERIES = {
    "baseline_product_browse_without_composite_index": """
        SELECT id, name, current_price
        FROM products IGNORE INDEX (ix_products_browse)
        WHERE status = 'ACTIVE' AND category_id = :category_id
        ORDER BY created_at DESC, id DESC
        LIMIT 20
    """,
    "optimized_product_browse_with_composite_index": """
        SELECT id, name, current_price
        FROM products FORCE INDEX (ix_products_browse)
        WHERE status = 'ACTIVE' AND category_id = :category_id
        ORDER BY created_at DESC, id DESC
        LIMIT 20
    """,
    "merchant_order_queue": """
        SELECT id, order_no, total_amount, created_at
        FROM orders FORCE INDEX (ix_orders_store_status_created)
        WHERE store_id = :store_id AND status = 'PAID'
        ORDER BY created_at DESC, id DESC
        LIMIT 20
    """,
}


def main() -> None:
    engine = build_engine(get_settings().database_url)
    try:
        with engine.connect() as connection:
            version = connection.scalar(text("SELECT VERSION()"))
            category_id = connection.scalar(
                text("SELECT category_id FROM products WHERE status = 'ACTIVE' LIMIT 1")
            )
            store_id = connection.scalar(text("SELECT store_id FROM orders LIMIT 1"))
            if category_id is None or store_id is None:
                raise RuntimeError("Run the Phase 7 seed before EXPLAIN analysis")
            print(f"MySQL version: {version}")
            for name, query in QUERIES.items():
                print(f"\n[{name}]")
                result = connection.execute(
                    text(f"EXPLAIN ANALYZE {query}"),
                    {"category_id": category_id, "store_id": store_id},
                )
                for row in result:
                    print(row[0])
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
