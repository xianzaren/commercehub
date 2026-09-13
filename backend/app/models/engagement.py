from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.types import BIGINT_UNSIGNED


class Favorite(TimestampMixin, Base):
    __tablename__ = "favorites"
    __table_args__ = (
        Index("uq_favorites_user_product", "user_id", "product_id", unique=True),
        Index("ix_favorites_user_created", "user_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )


class ProductView(TimestampMixin, Base):
    __tablename__ = "product_views"
    __table_args__ = (
        CheckConstraint("view_count > 0", name="positive_view_count"),
        Index("uq_product_views_user_product", "user_id", "product_id", unique=True),
        Index("ix_product_views_user_updated", "user_id", "updated_at", "id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    view_count: Mapped[int] = mapped_column(default=1, nullable=False)


class SearchHistory(TimestampMixin, Base):
    __tablename__ = "search_histories"
    __table_args__ = (
        CheckConstraint("search_count > 0", name="positive_search_count"),
        CheckConstraint("result_count >= 0", name="nonnegative_result_count"),
        Index("uq_search_histories_user_keyword", "user_id", "normalized_keyword", unique=True),
        Index("ix_search_histories_user_updated", "user_id", "updated_at", "id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    result_count: Mapped[int] = mapped_column(default=0, nullable=False)
    search_count: Mapped[int] = mapped_column(default=1, nullable=False)
