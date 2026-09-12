from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem
from app.models.enums import CartStatus, PaymentStatus
from app.models.order import Address, Order, OrderItem, Payment


class CartRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active(self, user_id: int, *, lock: bool = False) -> Cart | None:
        statement = select(Cart).where(
            Cart.user_id == user_id,
            Cart.status == CartStatus.ACTIVE,
        )
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def list_items(self, cart_id: int) -> list[CartItem]:
        statement = select(CartItem).where(CartItem.cart_id == cart_id).order_by(CartItem.id)
        return list(self.session.scalars(statement))

    def get_item(self, cart_id: int, item_id: int) -> CartItem | None:
        statement = select(CartItem).where(
            CartItem.id == item_id,
            CartItem.cart_id == cart_id,
        )
        return self.session.scalar(statement)

    def get_item_by_product(self, cart_id: int, product_id: int) -> CartItem | None:
        statement = select(CartItem).where(
            CartItem.cart_id == cart_id,
            CartItem.product_id == product_id,
        )
        return self.session.scalar(statement)


class AddressRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_owned(self, address_id: int, user_id: int) -> Address | None:
        statement = select(Address).where(Address.id == address_id, Address.user_id == user_id)
        return self.session.scalar(statement)

    def list_owned(self, user_id: int) -> list[Address]:
        statement = (
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.id.desc())
        )
        return list(self.session.scalars(statement))

    def unset_defaults(self, user_id: int, *, except_id: int | None = None) -> None:
        statement = select(Address).where(Address.user_id == user_id, Address.is_default.is_(True))
        if except_id is not None:
            statement = statement.where(Address.id != except_id)
        for address in self.session.scalars(statement):
            address.is_default = False


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_owned(self, order_id: int, user_id: int, *, lock: bool = False) -> Order | None:
        statement = select(Order).where(Order.id == order_id, Order.user_id == user_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def get(self, order_id: int) -> Order | None:
        return self.session.get(Order, order_id)

    def get_for_store(self, order_id: int, store_id: int, *, lock: bool = False) -> Order | None:
        statement = select(Order).where(Order.id == order_id, Order.store_id == store_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def list_owned(self, user_id: int) -> list[Order]:
        statement = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
        )
        return list(self.session.scalars(statement))

    def list_for_store(
        self,
        store_id: int,
        *,
        status: str | None,
        order_no: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Order], int]:
        conditions = [Order.store_id == store_id]
        if status is not None:
            conditions.append(Order.status == status)
        if order_no:
            conditions.append(Order.order_no == order_no.strip())
        if created_from is not None:
            conditions.append(Order.created_at >= created_from)
        if created_to is not None:
            conditions.append(Order.created_at <= created_to)
        statement = (
            select(Order)
            .where(*conditions)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = select(func.count(Order.id)).where(*conditions)
        return list(self.session.scalars(statement)), int(self.session.scalar(count_statement) or 0)

    def list_all(
        self,
        *,
        status: str | None,
        order_no: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Order], int]:
        conditions = []
        if status is not None:
            conditions.append(Order.status == status)
        if order_no:
            conditions.append(Order.order_no == order_no.strip())
        statement = (
            select(Order)
            .where(*conditions)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = select(func.count(Order.id)).where(*conditions)
        return list(self.session.scalars(statement)), int(self.session.scalar(count_statement) or 0)

    def list_items(self, order_id: int) -> list[OrderItem]:
        return list(
            self.session.scalars(
                select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id)
            )
        )

    def list_payments(self, order_id: int) -> list[Payment]:
        return list(
            self.session.scalars(
                select(Payment)
                .where(Payment.order_id == order_id)
                .order_by(Payment.created_at.desc(), Payment.id.desc())
            )
        )

    def get_payment_by_key(self, order_id: int, idempotency_key: str) -> Payment | None:
        statement = select(Payment).where(
            Payment.order_id == order_id,
            Payment.idempotency_key == idempotency_key,
        )
        return self.session.scalar(statement)

    def get_paid_payment(self, order_id: int) -> Payment | None:
        statement = select(Payment).where(
            Payment.order_id == order_id,
            Payment.status == PaymentStatus.PAID,
        )
        return self.session.scalar(statement)
