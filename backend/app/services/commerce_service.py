from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.models.cart import Cart, CartItem
from app.models.catalog import Inventory, InventoryTransaction, Product
from app.models.enums import (
    CartStatus,
    InventoryTransactionType,
    OrderPaymentStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ProductStatus,
    StoreStatus,
)
from app.models.order import Address, Order, OrderItem, Payment
from app.models.user import User
from app.repositories.commerce_repository import AddressRepository, CartRepository, OrderRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.merchant_repository import StoreRepository
from app.repositories.product_repository import ProductRepository


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ProductBrowseService:
    def __init__(self, session: Session) -> None:
        self.products = ProductRepository(session)
        self.inventory = InventoryRepository(session)
        self.stores = StoreRepository(session)

    def search(
        self,
        *,
        keyword: str | None,
        category_id: int | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        sort: str,
        offset: int,
        limit: int,
    ) -> tuple[list[tuple[Product, Inventory]], int]:
        products, total = self.products.search_active(
            keyword=keyword,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            sort=sort,
            offset=offset,
            limit=limit,
        )
        result = []
        for product in products:
            inventory = self.inventory.get(product.id)
            if inventory is not None:
                result.append((product, inventory))
        return result, total

    def get_active(self, product_id: int) -> tuple[Product, Inventory]:
        product = self.products.get(product_id)
        if product is None or product.status != ProductStatus.ACTIVE:
            raise BusinessError("PRODUCT_NOT_FOUND", "商品不存在或不可售", status_code=404)
        store = self.stores.get(product.store_id)
        if store is None or store.status != StoreStatus.ACTIVE:
            raise BusinessError("PRODUCT_NOT_FOUND", "商品不存在或不可售", status_code=404)
        inventory = self.inventory.get(product.id)
        if inventory is None:
            raise BusinessError("INVENTORY_NOT_FOUND", "库存记录不存在", status_code=409)
        return product, inventory


class CartService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.carts = CartRepository(session)
        self.products = ProductBrowseService(session)

    def get(self, user: User) -> tuple[Cart | None, list[tuple[CartItem, Product, Inventory]]]:
        cart = self.carts.get_active(user.id)
        if cart is None:
            return None, []
        return cart, self._item_details(cart)

    def add_item(self, user: User, product_id: int, quantity: int) -> Cart:
        product, inventory = self.products.get_active(product_id)
        cart = self._get_or_create_cart(user.id)
        if cart.store_id is not None and cart.store_id != product.store_id:
            raise BusinessError(
                "CART_STORE_CONFLICT",
                "一个购物车只能包含同一店铺的商品，请先结算或清空购物车",
                status_code=409,
            )
        item = self.carts.get_item_by_product(cart.id, product.id)
        requested_quantity = quantity + (item.quantity if item is not None else 0)
        if requested_quantity > inventory.quantity:
            raise BusinessError("INSUFFICIENT_STOCK", "商品库存不足", status_code=409)
        cart.store_id = product.store_id
        if item is None:
            self.session.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity))
        else:
            item.quantity = requested_quantity
        self.session.commit()
        self.session.refresh(cart)
        return cart

    def update_item(self, user: User, item_id: int, quantity: int) -> Cart:
        cart = self.carts.get_active(user.id)
        if cart is None:
            raise BusinessError("CART_NOT_FOUND", "购物车不存在", status_code=404)
        item = self.carts.get_item(cart.id, item_id)
        if item is None:
            raise BusinessError("CART_ITEM_NOT_FOUND", "购物车商品不存在", status_code=404)
        _, inventory = self.products.get_active(item.product_id)
        if quantity > inventory.quantity:
            raise BusinessError("INSUFFICIENT_STOCK", "商品库存不足", status_code=409)
        item.quantity = quantity
        self.session.commit()
        self.session.refresh(cart)
        return cart

    def delete_item(self, user: User, item_id: int) -> Cart:
        cart = self.carts.get_active(user.id)
        if cart is None:
            raise BusinessError("CART_NOT_FOUND", "购物车不存在", status_code=404)
        item = self.carts.get_item(cart.id, item_id)
        if item is None:
            raise BusinessError("CART_ITEM_NOT_FOUND", "购物车商品不存在", status_code=404)
        self.session.delete(item)
        self.session.flush()
        if not self.carts.list_items(cart.id):
            cart.store_id = None
        self.session.commit()
        self.session.refresh(cart)
        return cart

    def _get_or_create_cart(self, user_id: int) -> Cart:
        cart = self.carts.get_active(user_id)
        if cart is not None:
            return cart
        cart = Cart(user_id=user_id, status=CartStatus.ACTIVE)
        try:
            self.session.add(cart)
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            existing = self.carts.get_active(user_id)
            if existing is None:
                raise
            return existing
        return cart

    def _item_details(self, cart: Cart) -> list[tuple[CartItem, Product, Inventory]]:
        details = []
        for item in self.carts.list_items(cart.id):
            product = ProductRepository(self.session).get(item.product_id)
            inventory = InventoryRepository(self.session).get(item.product_id)
            if product is not None and inventory is not None:
                details.append((item, product, inventory))
        return details


class AddressService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.addresses = AddressRepository(session)

    def list(self, user: User) -> list[Address]:
        return self.addresses.list_owned(user.id)

    def create(self, user: User, values: dict[str, object]) -> Address:
        existing = self.addresses.list_owned(user.id)
        make_default = bool(values.get("is_default")) or not existing
        if make_default:
            self.addresses.unset_defaults(user.id)
        values["is_default"] = make_default
        address = Address(user_id=user.id, **values)
        self.session.add(address)
        self.session.commit()
        self.session.refresh(address)
        return address

    def update(self, user: User, address_id: int, changes: dict[str, object]) -> Address:
        address = self._get_owned(user, address_id)
        if changes.get("is_default") is True:
            self.addresses.unset_defaults(user.id, except_id=address.id)
        for field, value in changes.items():
            setattr(address, field, value)
        self.session.commit()
        self.session.refresh(address)
        return address

    def delete(self, user: User, address_id: int) -> None:
        address = self._get_owned(user, address_id)
        was_default = address.is_default
        self.session.delete(address)
        self.session.flush()
        remaining = self.addresses.list_owned(user.id)
        if was_default and remaining:
            remaining[0].is_default = True
        self.session.commit()

    def _get_owned(self, user: User, address_id: int) -> Address:
        address = self.addresses.get_owned(address_id, user.id)
        if address is None:
            raise BusinessError("ADDRESS_NOT_FOUND", "地址不存在", status_code=404)
        return address


class CheckoutService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.carts = CartRepository(session)
        self.addresses = AddressRepository(session)
        self.orders = OrderRepository(session)
        self.products = ProductRepository(session)
        self.inventory = InventoryRepository(session)
        self.stores = StoreRepository(session)

    def checkout(
        self,
        user: User,
        address_id: int,
        payment_method: PaymentMethod,
        idempotency_key: str,
        *,
        fail_after_order_items: bool = False,
    ) -> Order:
        try:
            address = self.addresses.get_owned(address_id, user.id)
            if address is None:
                raise BusinessError("ADDRESS_NOT_FOUND", "地址不存在", status_code=404)
            cart = self.carts.get_active(user.id, lock=True)
            if cart is None:
                raise BusinessError("CART_EMPTY", "购物车为空", status_code=409)
            cart_items = self.carts.list_items(cart.id)
            if not cart_items:
                raise BusinessError("CART_EMPTY", "购物车为空", status_code=409)
            store = self.stores.get(int(cart.store_id)) if cart.store_id is not None else None
            if store is None or store.status != StoreStatus.ACTIVE:
                raise BusinessError("STORE_NOT_ACTIVE", "店铺当前不可用", status_code=409)

            product_ids = sorted(item.product_id for item in cart_items)
            locked_inventory = self.inventory.lock_many(product_ids)
            inventory_by_product = {row.product_id: row for row in locked_inventory}
            product_by_id: dict[int, Product] = {}
            subtotal = Decimal("0.00")
            for item in cart_items:
                product = self.products.get(item.product_id)
                inventory = inventory_by_product.get(item.product_id)
                if (
                    product is None
                    or product.status != ProductStatus.ACTIVE
                    or product.store_id != cart.store_id
                ):
                    raise BusinessError(
                        "PRODUCT_NOT_AVAILABLE", "购物车中存在不可售商品", status_code=409
                    )
                if inventory is None or inventory.quantity < item.quantity:
                    raise BusinessError(
                        "INSUFFICIENT_STOCK",
                        f"商品 {product.name} 库存不足",
                        status_code=409,
                    )
                product_by_id[product.id] = product
                subtotal += product.current_price * item.quantity

            order = Order(
                order_no=uuid4().hex,
                user_id=user.id,
                store_id=int(cart.store_id),
                address_snapshot=self._address_snapshot(address),
                status=OrderStatus.PENDING_PAYMENT,
                subtotal=subtotal,
                total_amount=subtotal,
                payment_status=OrderPaymentStatus.UNPAID,
            )
            self.session.add(order)
            self.session.flush()
            for item in cart_items:
                product = product_by_id[item.product_id]
                line_subtotal = product.current_price * item.quantity
                self.session.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        store_id=product.store_id,
                        product_name_snapshot=product.name,
                        sku_snapshot=product.sku,
                        unit_price=product.current_price,
                        quantity=item.quantity,
                        subtotal=line_subtotal,
                    )
                )
            self.session.flush()
            if fail_after_order_items:
                raise RuntimeError("injected checkout failure")

            for item in cart_items:
                inventory = inventory_by_product[item.product_id]
                before = inventory.quantity
                inventory.quantity -= item.quantity
                inventory.version += 1
                inventory.updated_at = utcnow()
                self.session.add(
                    InventoryTransaction(
                        product_id=item.product_id,
                        type=InventoryTransactionType.SALE,
                        quantity_change=-item.quantity,
                        quantity_before=before,
                        quantity_after=inventory.quantity,
                        reference_type="ORDER",
                        reference_id=order.id,
                        created_by=user.id,
                        created_at=utcnow(),
                    )
                )
            self.session.add(
                Payment(
                    order_id=order.id,
                    payment_no=uuid4().hex,
                    idempotency_key=idempotency_key,
                    method=payment_method,
                    amount=order.total_amount,
                    status=PaymentStatus.PENDING,
                )
            )
            cart.status = CartStatus.CHECKED_OUT
            self.session.commit()
            self.session.refresh(order)
            return order
        except Exception:
            self.session.rollback()
            raise

    def _address_snapshot(self, address: Address) -> dict[str, str]:
        return {
            "recipient_name": address.recipient_name,
            "phone": address.phone,
            "province": address.province,
            "city": address.city,
            "district": address.district,
            "detail": address.detail,
            "postal_code": address.postal_code or "",
        }


class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.orders = OrderRepository(session)
        self.inventory = InventoryRepository(session)

    def list(self, user: User) -> list[Order]:
        return self.orders.list_owned(user.id)

    def get(self, user: User, order_id: int) -> Order:
        order = self.orders.get_owned(order_id, user.id)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", "订单不存在", status_code=404)
        return order

    def pay(
        self,
        user: User,
        order_id: int,
        method: PaymentMethod,
        amount: Decimal,
        idempotency_key: str,
        simulate_failure: bool,
    ) -> Payment:
        try:
            order = self.orders.get_owned(order_id, user.id, lock=True)
            if order is None:
                raise BusinessError("ORDER_NOT_FOUND", "订单不存在", status_code=404)
            if amount != order.total_amount:
                raise BusinessError(
                    "PAYMENT_AMOUNT_MISMATCH", "支付金额与订单金额不一致", status_code=409
                )
            if order.status == OrderStatus.CANCELLED:
                raise BusinessError("ORDER_CANCELLED", "已取消订单不能支付", status_code=409)
            paid = self.orders.get_paid_payment(order.id)
            if paid is not None:
                return paid
            if order.status != OrderStatus.PENDING_PAYMENT:
                raise BusinessError("ORDER_NOT_PAYABLE", "当前订单状态不能支付", status_code=409)

            payment = self.orders.get_payment_by_key(order.id, idempotency_key)
            if payment is not None:
                if payment.method != method or payment.amount != amount:
                    raise BusinessError(
                        "IDEMPOTENCY_KEY_REUSED",
                        "幂等键已用于不同的支付参数",
                        status_code=409,
                    )
                if payment.status != PaymentStatus.PENDING:
                    return payment
            else:
                payment = Payment(
                    order_id=order.id,
                    payment_no=uuid4().hex,
                    idempotency_key=idempotency_key,
                    method=method,
                    amount=amount,
                    status=PaymentStatus.PENDING,
                )
                self.session.add(payment)

            if simulate_failure:
                payment.status = PaymentStatus.FAILED
            else:
                payment.status = PaymentStatus.PAID
                payment.paid_at = utcnow()
                order.status = OrderStatus.PAID
                order.payment_status = OrderPaymentStatus.PAID
            self.session.commit()
            self.session.refresh(payment)
            return payment
        except Exception:
            self.session.rollback()
            raise

    def cancel(self, user: User, order_id: int) -> Order:
        try:
            order = self.orders.get_owned(order_id, user.id, lock=True)
            if order is None:
                raise BusinessError("ORDER_NOT_FOUND", "订单不存在", status_code=404)
            if order.status == OrderStatus.CANCELLED:
                return order
            if order.status not in {OrderStatus.PENDING_PAYMENT, OrderStatus.PAID}:
                raise BusinessError(
                    "ORDER_NOT_CANCELLABLE", "当前订单状态不能取消", status_code=409
                )
            items = self.orders.list_items(order.id)
            inventory_rows = self.inventory.lock_many([item.product_id for item in items])
            inventory_by_product = {row.product_id: row for row in inventory_rows}
            for item in items:
                inventory = inventory_by_product.get(item.product_id)
                if inventory is None:
                    raise BusinessError("INVENTORY_NOT_FOUND", "库存记录不存在", status_code=409)
                before = inventory.quantity
                inventory.quantity += item.quantity
                inventory.version += 1
                inventory.updated_at = utcnow()
                self.session.add(
                    InventoryTransaction(
                        product_id=item.product_id,
                        type=InventoryTransactionType.RETURN,
                        quantity_change=item.quantity,
                        quantity_before=before,
                        quantity_after=inventory.quantity,
                        reference_type="ORDER",
                        reference_id=order.id,
                        created_by=user.id,
                        created_at=utcnow(),
                    )
                )
            for payment in self.orders.list_payments(order.id):
                if payment.status == PaymentStatus.PAID:
                    payment.status = PaymentStatus.REFUNDED
                elif payment.status == PaymentStatus.PENDING:
                    payment.status = PaymentStatus.FAILED
            order.status = OrderStatus.CANCELLED
            order.payment_status = OrderPaymentStatus.UNPAID
            self.session.commit()
            self.session.refresh(order)
            return order
        except Exception:
            self.session.rollback()
            raise
