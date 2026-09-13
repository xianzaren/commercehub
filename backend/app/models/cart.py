from sqlalchemy import CheckConstraint, Computed, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.types import BIGINT_UNSIGNED
from app.models.enums import CartStatus


class Cart(TimestampMixin, Base):
    __tablename__ = "carts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE','CHECKED_OUT','ABANDONED')",
            name="valid_status",
        ),
        Index("uq_carts_one_active_user", "active_user_id", unique=True),
        Index("ix_carts_user_created", "user_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    store_id: Mapped[int | None] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), default=CartStatus.ACTIVE, nullable=False)
    active_user_id: Mapped[int | None] = mapped_column(
        BIGINT_UNSIGNED,
        Computed("CASE WHEN status = 'ACTIVE' THEN user_id ELSE NULL END", persisted=True),
        nullable=True,
    )


class CartItem(TimestampMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_quantity"),
        Index(
            "uq_cart_items_cart_product_variant",
            "cart_id",
            "product_id",
            "variant_key",
            unique=True,
        ),
        Index("ix_cart_items_cart_id", "cart_id"),
        Index("ix_cart_items_product", "product_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("carts.id", ondelete="CASCADE"),
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
    quantity: Mapped[int] = mapped_column(nullable=False)
