from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.types import BIGINT_UNSIGNED, UTC_DATETIME
from app.models.enums import MerchantStatus, StoreStatus, UserRole, UserStatus


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('CUSTOMER','MERCHANT','ADMIN')",
            name="valid_role",
        ),
        CheckConstraint(
            "status IN ('ACTIVE','SUSPENDED','DISABLED')",
            name="valid_status",
        ),
        Index("ix_users_role_status", "role", "status"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.CUSTOMER, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.ACTIVE, nullable=False)


class Merchant(TimestampMixin, Base):
    __tablename__ = "merchants"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','ACTIVE','SUSPENDED','CLOSED')",
            name="valid_status",
        ),
        CheckConstraint(
            "(approved_at IS NULL AND approved_by IS NULL) OR "
            "(approved_at IS NOT NULL AND approved_by IS NOT NULL)",
            name="approval_fields_together",
        ),
        Index("ix_merchants_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    business_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=MerchantStatus.PENDING, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(UTC_DATETIME, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class Store(TimestampMixin, Base):
    __tablename__ = "stores"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE','SUSPENDED','CLOSED')",
            name="valid_status",
        ),
        Index("ix_stores_status", "status"),
    )

    id: Mapped[int] = mapped_column(BIGINT_UNSIGNED, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("merchants.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=StoreStatus.ACTIVE, nullable=False)
