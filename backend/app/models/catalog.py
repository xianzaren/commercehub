from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.types import BIGINT_UNSIGNED, MONEY, UTC_DATETIME
from app.models.enums import CategoryStatus, InventoryTransactionType, ProductStatus


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="valid_status"),
        Index("ix_categories_parent_status", "parent_id", "status"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default=CategoryStatus.ACTIVE, nullable=False)


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("current_price > 0", name="positive_price"),
        CheckConstraint(
            "status IN ('DRAFT','ACTIVE','INACTIVE','DELETED')",
            name="valid_status",
        ),
        Index("uq_products_store_sku", "store_id", "sku", unique=True),
        Index("ix_products_browse", "status", "category_id", "created_at", "id"),
        Index("ix_products_store_status", "store_id", "status", "id"),
        Index("ix_products_active_price", "status", "current_price", "id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
    )
    category_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    current_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=ProductStatus.DRAFT, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)


class ProductImage(TimestampMixin, Base):
    __tablename__ = "product_images"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="nonnegative_sort_order"),
        Index("ix_product_images_product_sort", "product_id", "sort_order", "id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ProductVariant(TimestampMixin, Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint("price > 0", name="positive_price"),
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="valid_status"),
        CheckConstraint("sort_order >= 0", name="nonnegative_sort_order"),
        Index("uq_product_variants_product_sku", "product_id", "sku", unique=True),
        Index("ix_product_variants_product_status", "product_id", "status", "sort_order"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    attributes: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)


class ProductPrice(Base):
    __tablename__ = "product_prices"
    __table_args__ = (
        CheckConstraint("old_price > 0", name="positive_old_price"),
        CheckConstraint("new_price > 0", name="positive_new_price"),
        CheckConstraint("old_price <> new_price", name="prices_different"),
        Index("ix_product_prices_product_changed", "product_id", "changed_at", "id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    old_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    new_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    changed_by: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (CheckConstraint("quantity >= 0", name="nonnegative_quantity"),)

    product_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    version: Mapped[int] = mapped_column(BIGINT_UNSIGNED, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('RESTOCK','SALE','ADJUSTMENT','RETURN','RELEASE')",
            name="valid_type",
        ),
        CheckConstraint("quantity_change <> 0", name="nonzero_change"),
        CheckConstraint("quantity_before >= 0", name="nonnegative_before"),
        CheckConstraint("quantity_after >= 0", name="nonnegative_after"),
        Index("ix_inventory_tx_product_created", "product_id", "created_at", "id"),
        Index("ix_inventory_tx_reference", "reference_type", "reference_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        String(20),
        default=InventoryTransactionType.ADJUSTMENT,
        nullable=False,
    )
    quantity_change: Mapped[int] = mapped_column(nullable=False)
    quantity_before: Mapped[int] = mapped_column(nullable=False)
    quantity_after: Mapped[int] = mapped_column(nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reference_id: Mapped[int | None] = mapped_column(BIGINT_UNSIGNED, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(UTC_DATETIME, nullable=False)
