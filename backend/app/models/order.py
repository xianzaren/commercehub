from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, CheckConstraint, Computed, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.types import BIGINT_UNSIGNED, MONEY, UTC_DATETIME
from app.models.enums import OrderPaymentStatus, OrderStatus, PaymentMethod, PaymentStatus


class Address(TimestampMixin, Base):
    __tablename__ = "addresses"
    __table_args__ = (Index("ix_addresses_user", "user_id", "id"),)

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recipient_name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    province: Mapped[str] = mapped_column(String(80), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    district: Mapped[str] = mapped_column(String(80), nullable=False)
    detail: Mapped[str] = mapped_column(String(255), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING_PAYMENT','PAID','PROCESSING','SHIPPED','COMPLETED','CANCELLED')",
            name="valid_status",
        ),
        CheckConstraint("payment_status IN ('UNPAID','PAID')", name="valid_payment_status"),
        CheckConstraint("subtotal >= 0", name="nonnegative_subtotal"),
        CheckConstraint("total_amount >= 0", name="nonnegative_total"),
        Index("ix_orders_user_created", "user_id", "created_at", "id"),
        Index("ix_orders_store_status_created", "store_id", "status", "created_at", "id"),
        Index("ix_orders_status_created", "status", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    store_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
    )
    address_snapshot: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        default=OrderStatus.PENDING_PAYMENT,
        nullable=False,
    )
    subtotal: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    payment_status: Mapped[str] = mapped_column(
        String(20),
        default=OrderPaymentStatus.UNPAID,
        nullable=False,
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("unit_price > 0", name="positive_unit_price"),
        CheckConstraint("quantity > 0", name="positive_quantity"),
        CheckConstraint("subtotal > 0", name="positive_subtotal"),
        Index(
            "uq_order_items_order_product_variant",
            "order_id",
            "product_id",
            "variant_key",
            unique=True,
        ),
        Index("ix_order_items_order_id", "order_id"),
        Index("ix_order_items_store_product", "store_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    variant_id: Mapped[int | None] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    variant_key: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        Computed("COALESCE(variant_id, 0)", persisted=True),
        nullable=False,
    )
    store_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    sku_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    variant_name_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    variant_sku_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(MONEY, nullable=False)


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("method IN ('MOCK_CARD','MOCK_WALLET')", name="valid_method"),
        CheckConstraint(
            "status IN ('PENDING','PAID','FAILED','REFUNDED')",
            name="valid_status",
        ),
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint(
            "(status = 'PAID' AND paid_at IS NOT NULL) OR status <> 'PAID'",
            name="paid_at_required_when_paid",
        ),
        Index("uq_payments_order_idempotency", "order_id", "idempotency_key", unique=True),
        Index("uq_payments_one_paid_order", "paid_order_id", unique=True),
        Index("ix_payments_order_created", "order_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payment_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    method: Mapped[str] = mapped_column(
        String(20),
        default=PaymentMethod.MOCK_CARD,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    paid_order_id: Mapped[int | None] = mapped_column(
        BIGINT_UNSIGNED,
        Computed("CASE WHEN status = 'PAID' THEN order_id ELSE NULL END", persisted=True),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
