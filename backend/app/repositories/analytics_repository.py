"""Aggregate orders and items separately so multiple lines never inflate revenue."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import Product
from app.models.order import Order, OrderItem, Payment
from app.repositories.management_repository import PAID_ORDER_STATUSES


class AnalyticsRepository:
    def __init__(self, session: Session):
        self.session = session

    def products(self, store_id: int):
        return self.session.execute(
            select(Product.id, Product.name)
            .where(Product.store_id == store_id)
            .order_by(Product.name, Product.id)
        ).all()

    def aggregate(self, store_id: int, start: datetime, end: datetime, product_id: int | None):
        day = func.date(func.convert_tz(Payment.paid_at, "+00:00", "+08:00"))
        conditions = [
            Order.store_id == store_id,
            Order.payment_status == "PAID",
            Order.status.in_(PAID_ORDER_STATUSES),
            Payment.status == "PAID",
            Payment.paid_at >= start,
            Payment.paid_at < end,
        ]
        # uq_payments_one_paid_order guarantees at most one successful payment per order.
        orders = (
            select(
                day.label("day"),
                func.sum(Order.total_amount).label("revenue"),
                func.count(Order.id).label("order_count"),
            )
            .select_from(Order)
            .join(Payment, Payment.order_id == Order.id)
            .where(*conditions)
            .group_by(day)
        )
        item_base = (
            select()
            .select_from(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .join(Payment, Payment.order_id == Order.id)
            .where(*conditions, OrderItem.store_id == store_id)
        )
        if product_id is not None:
            item_base = item_base.where(OrderItem.product_id == product_id)
        items = item_base.with_only_columns(
            day.label("day"),
            func.sum(OrderItem.subtotal).label("revenue"),
            func.count(func.distinct(Order.id)).label("order_count"),
            func.sum(OrderItem.quantity).label("quantity_sold"),
        ).group_by(day)
        ranking = (
            item_base.join(Product, Product.id == OrderItem.product_id)
            .with_only_columns(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                func.sum(OrderItem.quantity).label("quantity_sold"),
                func.sum(OrderItem.subtotal).label("revenue"),
            )
            .group_by(Product.id, Product.name)
            .order_by(func.sum(OrderItem.quantity).desc(), Product.id)
            .limit(10)
        )
        return (
            self.session.execute(orders).mappings().all() if product_id is None else [],
            self.session.execute(items).mappings().all(),
            self.session.execute(ranking).mappings().all(),
        )
