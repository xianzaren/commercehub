"""add catalog media, engagement records and product variants

Revision ID: e4c91f2a8b63
Revises: 9b0e2a71c4d8
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "e4c91f2a8b63"
down_revision: str | None = "9b0e2a71c4d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
        ),
        sa.Column(
            "updated_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
        ),
    ]


def upgrade() -> None:
    bigint = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
    money = sa.Numeric(12, 2)

    op.create_table(
        "product_images",
        sa.Column("id", bigint, autoincrement=True, nullable=False),
        sa.Column("product_id", bigint, nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("alt_text", sa.String(length=200), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("sort_order >= 0", name="ck_product_images_nonnegative_sort_order"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_images_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_images"),
    )
    op.create_index(
        "ix_product_images_product_sort",
        "product_images",
        ["product_id", "sort_order", "id"],
    )

    op.create_table(
        "product_variants",
        sa.Column("id", bigint, autoincrement=True, nullable=False),
        sa.Column("product_id", bigint, nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("price", money, nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("price > 0", name="ck_product_variants_positive_price"),
        sa.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE')",
            name="ck_product_variants_valid_status",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_product_variants_nonnegative_sort_order",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_variants_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_variants"),
    )
    op.create_index(
        "uq_product_variants_product_sku",
        "product_variants",
        ["product_id", "sku"],
        unique=True,
    )
    op.create_index(
        "ix_product_variants_product_status",
        "product_variants",
        ["product_id", "status", "sort_order"],
    )

    # MySQL may reuse the old unique index to enforce the cart_id foreign key.
    # Give that foreign key a dedicated supporting index before replacing it.
    op.create_index("ix_cart_items_cart_id", "cart_items", ["cart_id"])
    op.drop_index("uq_cart_items_cart_product", table_name="cart_items")
    op.add_column("cart_items", sa.Column("variant_id", bigint, nullable=True))
    op.add_column(
        "cart_items",
        sa.Column(
            "variant_key",
            bigint,
            sa.Computed("COALESCE(variant_id, 0)", persisted=True),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_cart_items_variant_id_product_variants",
        "cart_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "uq_cart_items_cart_product_variant",
        "cart_items",
        ["cart_id", "product_id", "variant_key"],
        unique=True,
    )

    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.drop_index("uq_order_items_order_product", table_name="order_items")
    op.add_column("order_items", sa.Column("variant_id", bigint, nullable=True))
    op.add_column(
        "order_items",
        sa.Column(
            "variant_key",
            bigint,
            sa.Computed("COALESCE(variant_id, 0)", persisted=True),
            nullable=False,
        ),
    )
    op.add_column(
        "order_items",
        sa.Column("variant_name_snapshot", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("variant_sku_snapshot", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_order_items_variant_id_product_variants",
        "order_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "uq_order_items_order_product_variant",
        "order_items",
        ["order_id", "product_id", "variant_key"],
        unique=True,
    )

    op.create_table(
        "favorites",
        sa.Column("id", bigint, autoincrement=True, nullable=False),
        sa.Column("user_id", bigint, nullable=False),
        sa.Column("product_id", bigint, nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_favorites_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_favorites_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_favorites"),
    )
    op.create_index("uq_favorites_user_product", "favorites", ["user_id", "product_id"], unique=True)
    op.create_index("ix_favorites_user_created", "favorites", ["user_id", "created_at", "id"])

    op.create_table(
        "product_views",
        sa.Column("id", bigint, autoincrement=True, nullable=False),
        sa.Column("user_id", bigint, nullable=False),
        sa.Column("product_id", bigint, nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("view_count > 0", name="ck_product_views_positive_view_count"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_product_views_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_views_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_views"),
    )
    op.create_index("uq_product_views_user_product", "product_views", ["user_id", "product_id"], unique=True)
    op.create_index("ix_product_views_user_updated", "product_views", ["user_id", "updated_at", "id"])

    op.create_table(
        "search_histories",
        sa.Column("id", bigint, autoincrement=True, nullable=False),
        sa.Column("user_id", bigint, nullable=False),
        sa.Column("keyword", sa.String(length=100), nullable=False),
        sa.Column("normalized_keyword", sa.String(length=100), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("search_count", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("search_count > 0", name="ck_search_histories_positive_search_count"),
        sa.CheckConstraint("result_count >= 0", name="ck_search_histories_nonnegative_result_count"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_search_histories_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_search_histories"),
    )
    op.create_index(
        "uq_search_histories_user_keyword",
        "search_histories",
        ["user_id", "normalized_keyword"],
        unique=True,
    )
    op.create_index(
        "ix_search_histories_user_updated",
        "search_histories",
        ["user_id", "updated_at", "id"],
    )


def downgrade() -> None:
    op.drop_table("search_histories")
    op.drop_table("product_views")
    op.drop_table("favorites")

    op.drop_index("uq_order_items_order_product_variant", table_name="order_items")
    op.drop_constraint(
        "fk_order_items_variant_id_product_variants",
        "order_items",
        type_="foreignkey",
    )
    op.drop_column("order_items", "variant_sku_snapshot")
    op.drop_column("order_items", "variant_name_snapshot")
    op.drop_column("order_items", "variant_key")
    op.drop_column("order_items", "variant_id")
    op.create_index(
        "uq_order_items_order_product",
        "order_items",
        ["order_id", "product_id"],
        unique=True,
    )
    op.drop_index("ix_order_items_order_id", table_name="order_items")

    op.drop_index("uq_cart_items_cart_product_variant", table_name="cart_items")
    op.drop_constraint(
        "fk_cart_items_variant_id_product_variants",
        "cart_items",
        type_="foreignkey",
    )
    op.drop_column("cart_items", "variant_key")
    op.drop_column("cart_items", "variant_id")
    op.create_index(
        "uq_cart_items_cart_product",
        "cart_items",
        ["cart_id", "product_id"],
        unique=True,
    )
    op.drop_index("ix_cart_items_cart_id", table_name="cart_items")

    op.drop_table("product_variants")
    op.drop_table("product_images")
