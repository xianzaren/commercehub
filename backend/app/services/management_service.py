from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.models.audit import AuditLog
from app.models.catalog import Product
from app.models.enums import OrderStatus, ProductStatus, UserStatus
from app.models.order import Order
from app.models.user import Merchant, Store, User
from app.repositories.commerce_repository import OrderRepository
from app.repositories.management_repository import ManagementRepository
from app.repositories.merchant_repository import StoreRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def as_decimal(value: object) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def as_utc_naive(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


class MerchantManagementService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.orders = OrderRepository(session)
        self.stores = StoreRepository(session)
        self.management = ManagementRepository(session)

    def list_orders(
        self,
        merchant: Merchant,
        *,
        status: OrderStatus | None,
        order_no: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Order], int]:
        store = self._store(merchant)
        return self.orders.list_for_store(
            store.id,
            status=status.value if status is not None else None,
            order_no=order_no,
            created_from=as_utc_naive(created_from),
            created_to=as_utc_naive(created_to),
            offset=offset,
            limit=limit,
        )

    def get_order(self, merchant: Merchant, order_id: int) -> Order:
        store = self._store(merchant)
        order = self.orders.get(order_id)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", "订单不存在", status_code=404)
        if order.store_id != store.id:
            raise BusinessError("ORDER_NOT_OWNED", "不能访问其他商家的订单", status_code=403)
        return order

    def update_order_status(
        self,
        merchant: Merchant,
        actor: User,
        order_id: int,
        new_status: OrderStatus,
    ) -> Order:
        store = self._store(merchant)
        existing = self.orders.get(order_id)
        if existing is None:
            raise BusinessError("ORDER_NOT_FOUND", "订单不存在", status_code=404)
        if existing.store_id != store.id:
            raise BusinessError("ORDER_NOT_OWNED", "不能操作其他商家的订单", status_code=403)
        order = self.orders.get_for_store(order_id, store.id, lock=True)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", "订单不存在", status_code=404)
        if order.status == new_status:
            return order
        allowed = {
            OrderStatus.PAID: OrderStatus.PROCESSING,
            OrderStatus.PROCESSING: OrderStatus.SHIPPED,
        }
        expected = allowed.get(OrderStatus(order.status))
        if expected != new_status:
            raise BusinessError(
                "INVALID_ORDER_TRANSITION",
                f"订单不能从 {order.status} 变更为 {new_status}",
                status_code=409,
            )
        old_status = order.status
        order.status = new_status
        self._audit(
            actor,
            "MERCHANT_ORDER_STATUS_CHANGED",
            "order",
            order.id,
            {"status": old_status},
            {"status": new_status},
        )
        self.session.commit()
        self.session.refresh(order)
        return order

    def analytics_summary(self, merchant: Merchant) -> dict[str, object]:
        store = self._store(merchant)
        now = utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today_start + timedelta(days=1)
        month_start = today_start.replace(day=1)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)
        count, total, average = self.management.sales_summary(store.id)
        return {
            "today_revenue": as_decimal(
                self.management.revenue_between(today_start, tomorrow, store_id=store.id)
            ),
            "month_revenue": as_decimal(
                self.management.revenue_between(month_start, next_month, store_id=store.id)
            ),
            "total_revenue": as_decimal(total),
            "paid_order_count": count,
            "average_order_amount": as_decimal(average),
        }

    def top_products(self, merchant: Merchant, limit: int) -> list[dict[str, object]]:
        store = self._store(merchant)
        return [
            {
                "product_id": product_id,
                "product_name": name,
                "quantity_sold": int(quantity),
                "revenue": as_decimal(revenue),
            }
            for product_id, name, quantity, revenue in self.management.top_products(
                store.id, limit
            )
        ]

    def low_stock(
        self,
        merchant: Merchant,
        threshold: int,
        *,
        offset: int,
        limit: int,
    ):
        store = self._store(merchant)
        return self.management.low_stock(
            store.id,
            threshold,
            offset=offset,
            limit=limit,
        )

    def _store(self, merchant: Merchant) -> Store:
        store = self.stores.get_by_merchant_id(merchant.id)
        if store is None:
            raise BusinessError("STORE_NOT_FOUND", "店铺不存在", status_code=404)
        return store

    def _audit(
        self,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: int,
        before: dict[str, object] | None,
        after: dict[str, object] | None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_user_id=actor.id,
                actor_role=actor.role,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_data=before,
                after_data=after,
                created_at=utcnow(),
            )
        )


class AdminManagementService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.management = ManagementRepository(session)
        self.users = UserRepository(session)
        self.products = ProductRepository(session)
        self.orders = OrderRepository(session)

    def update_user_status(
        self,
        user_id: int,
        new_status: UserStatus,
        reason: str,
        admin: User,
    ) -> User:
        if user_id == admin.id and new_status != UserStatus.ACTIVE:
            raise BusinessError("CANNOT_SUSPEND_SELF", "管理员不能停用自己的账户", status_code=409)
        user = self.users.lock(user_id)
        if user is None:
            raise BusinessError("USER_NOT_FOUND", "用户不存在", status_code=404)
        if user.status == new_status:
            return user
        old_status = user.status
        user.status = new_status
        self._audit(
            admin,
            "USER_STATUS_CHANGED",
            "user",
            user.id,
            {"status": old_status},
            {"status": new_status, "reason": reason.strip()},
        )
        self.session.commit()
        self.session.refresh(user)
        return user

    def force_deactivate_product(
        self,
        product_id: int,
        reason: str,
        admin: User,
    ) -> Product:
        product = self.products.get(product_id)
        if product is None:
            raise BusinessError("PRODUCT_NOT_FOUND", "商品不存在", status_code=404)
        if product.status == ProductStatus.DELETED:
            raise BusinessError("PRODUCT_DELETED", "商品已删除", status_code=409)
        if product.status == ProductStatus.INACTIVE:
            return product
        old_status = product.status
        product.status = ProductStatus.INACTIVE
        self._audit(
            admin,
            "PRODUCT_FORCE_DEACTIVATED",
            "product",
            product.id,
            {"status": old_status},
            {"status": product.status, "reason": reason.strip()},
        )
        self.session.commit()
        self.session.refresh(product)
        return product

    def platform_summary(self) -> dict[str, object]:
        counts = self.management.platform_counts()
        paid_count, total, average = self.management.sales_summary()
        return {
            "user_count": counts["users"],
            "merchant_count": counts["merchants"],
            "store_count": counts["stores"],
            "product_count": counts["products"],
            "order_count": counts["orders"],
            "paid_order_count": paid_count,
            "total_revenue": as_decimal(total),
            "average_order_amount": as_decimal(average),
        }

    def _audit(
        self,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: int,
        before: dict[str, object] | None,
        after: dict[str, object] | None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_user_id=actor.id,
                actor_role=actor.role,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_data=before,
                after_data=after,
                created_at=utcnow(),
            )
        )
