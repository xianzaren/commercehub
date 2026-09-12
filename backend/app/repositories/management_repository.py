from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.catalog import Inventory, Product
from app.models.enums import OrderPaymentStatus, OrderStatus, ProductStatus
from app.models.order import Order, OrderItem
from app.models.user import Merchant, Store, User

PAID_ORDER_STATUSES = (
    OrderStatus.PAID,
    OrderStatus.PROCESSING,
    OrderStatus.SHIPPED,
    OrderStatus.COMPLETED,
)


class ManagementRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_users(
        self,
        *,
        role: str | None,
        status: str | None,
        keyword: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[User], int]:
        conditions = []
        if role is not None:
            conditions.append(User.role == role)
        if status is not None:
            conditions.append(User.status == status)
        if keyword:
            conditions.append(User.email.like(f"%{keyword.strip()}%"))
        statement = (
            select(User)
            .where(*conditions)
            .order_by(User.created_at.desc(), User.id.desc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = select(func.count(User.id)).where(*conditions)
        return list(self.session.scalars(statement)), int(self.session.scalar(count_statement) or 0)

    def list_merchants(
        self,
        *,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Merchant], int]:
        conditions = [Merchant.status == status] if status is not None else []
        statement = (
            select(Merchant)
            .where(*conditions)
            .order_by(Merchant.created_at.desc(), Merchant.id.desc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = select(func.count(Merchant.id)).where(*conditions)
        return list(self.session.scalars(statement)), int(
            self.session.scalar(count_statement) or 0
        )

    def list_stores(self, *, offset: int, limit: int) -> tuple[list[Store], int]:
        statement = (
            select(Store)
            .order_by(Store.created_at.desc(), Store.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return (
            list(self.session.scalars(statement)),
            int(self.session.scalar(select(func.count(Store.id))) or 0),
        )

    def list_products(
        self,
        *,
        status: str | None,
        keyword: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Product], int]:
        conditions = []
        if status is not None:
            conditions.append(Product.status == status)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(or_(Product.name.like(pattern), Product.sku.like(pattern)))
        statement = (
            select(Product)
            .where(*conditions)
            .order_by(Product.created_at.desc(), Product.id.desc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = select(func.count(Product.id)).where(*conditions)
        return list(self.session.scalars(statement)), int(self.session.scalar(count_statement) or 0)

    def list_audit_logs(
        self,
        *,
        action: str | None,
        actor_user_id: int | None,
        offset: int,
        limit: int,
    ) -> tuple[list[AuditLog], int]:
        conditions = []
        if action:
            conditions.append(AuditLog.action == action.strip())
        if actor_user_id is not None:
            conditions.append(AuditLog.actor_user_id == actor_user_id)
        statement = (
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = select(func.count(AuditLog.id)).where(*conditions)
        return list(self.session.scalars(statement)), int(self.session.scalar(count_statement) or 0)

    def sales_summary(self, store_id: int | None = None) -> tuple[int, object, object]:
        conditions = [
            Order.payment_status == OrderPaymentStatus.PAID,
            Order.status.in_(PAID_ORDER_STATUSES),
        ]
        if store_id is not None:
            conditions.append(Order.store_id == store_id)
        statement = select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), 0),
            func.coalesce(func.avg(Order.total_amount), 0),
        ).where(*conditions)
        row = self.session.execute(statement).one()
        return int(row[0]), row[1], row[2]

    def revenue_between(
        self,
        start: datetime,
        end: datetime,
        *,
        store_id: int | None = None,
    ) -> object:
        conditions = [
            Order.payment_status == OrderPaymentStatus.PAID,
            Order.status.in_(PAID_ORDER_STATUSES),
            Order.created_at >= start,
            Order.created_at < end,
        ]
        if store_id is not None:
            conditions.append(Order.store_id == store_id)
        return self.session.scalar(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(*conditions)
        )

    def top_products(self, store_id: int, limit: int) -> list[tuple[int, str, int, object]]:
        statement = (
            select(
                OrderItem.product_id,
                OrderItem.product_name_snapshot,
                func.sum(OrderItem.quantity).label("quantity_sold"),
                func.sum(OrderItem.subtotal).label("revenue"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.store_id == store_id,
                Order.payment_status == OrderPaymentStatus.PAID,
                Order.status.in_(PAID_ORDER_STATUSES),
            )
            .group_by(OrderItem.product_id, OrderItem.product_name_snapshot)
            .order_by(func.sum(OrderItem.quantity).desc(), OrderItem.product_id)
            .limit(limit)
        )
        return [tuple(row) for row in self.session.execute(statement).all()]

    def low_stock(
        self,
        store_id: int,
        threshold: int,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[tuple[Product, Inventory]], int]:
        conditions = [
            Product.store_id == store_id,
            Product.status != ProductStatus.DELETED,
            Inventory.quantity <= threshold,
        ]
        statement = (
            select(Product, Inventory)
            .join(Inventory, Inventory.product_id == Product.id)
            .where(*conditions)
            .order_by(Inventory.quantity.asc(), Product.id.asc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = (
            select(func.count(Product.id))
            .join(Inventory, Inventory.product_id == Product.id)
            .where(*conditions)
        )
        return list(self.session.execute(statement).all()), int(
            self.session.scalar(count_statement) or 0
        )

    def platform_counts(self) -> dict[str, int]:
        return {
            "users": int(self.session.scalar(select(func.count(User.id))) or 0),
            "merchants": int(self.session.scalar(select(func.count(Merchant.id))) or 0),
            "stores": int(self.session.scalar(select(func.count(Store.id))) or 0),
            "products": int(self.session.scalar(select(func.count(Product.id))) or 0),
            "orders": int(self.session.scalar(select(func.count(Order.id))) or 0),
        }
