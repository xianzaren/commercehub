from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CustomerUser, DatabaseSession
from app.models.cart import Cart, CartItem
from app.models.catalog import Inventory, Product
from app.models.order import Order
from app.schemas.commerce import (
    AddressCreate,
    AddressResponse,
    AddressUpdate,
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartResponse,
    CheckoutRequest,
    OrderItemResponse,
    OrderResponse,
    PaymentRequest,
    PaymentResponse,
    ProductPage,
    ProductSearchParams,
    PublicProductResponse,
)
from app.services.commerce_service import (
    AddressService,
    CartService,
    CheckoutService,
    OrderService,
    ProductBrowseService,
)

product_router = APIRouter(prefix="/api/products", tags=["products"])
customer_router = APIRouter(prefix="/api", tags=["customer-commerce"])


def public_product_response(
    product: Product,
    inventory: Inventory,
    category_name: str,
    store_name: str,
    sales_count: int,
) -> PublicProductResponse:
    return PublicProductResponse(
        id=product.id,
        store_id=product.store_id,
        category_id=product.category_id,
        category_name=category_name,
        store_name=store_name,
        sku=product.sku,
        name=product.name,
        description=product.description,
        tags=product.tags,
        current_price=product.current_price,
        inventory_quantity=inventory.quantity,
        sales_count=sales_count,
        created_at=product.created_at,
    )


def cart_response(
    cart: Cart | None,
    details: list[tuple[CartItem, Product, Inventory]],
) -> CartResponse:
    items = [
        CartItemResponse(
            id=item.id,
            product_id=product.id,
            product_name=product.name,
            sku=product.sku,
            unit_price=product.current_price,
            quantity=item.quantity,
            available_stock=inventory.quantity,
            subtotal=product.current_price * item.quantity,
        )
        for item, product, inventory in details
    ]
    return CartResponse(
        id=cart.id if cart is not None else None,
        store_id=cart.store_id if cart is not None else None,
        items=items,
        total_amount=sum((item.subtotal for item in items), Decimal("0.00")),
    )


def order_response(order: Order, service: OrderService) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        order_no=order.order_no,
        store_id=order.store_id,
        address_snapshot=order.address_snapshot,
        status=order.status,
        subtotal=order.subtotal,
        total_amount=order.total_amount,
        payment_status=order.payment_status,
        items=[
            OrderItemResponse.model_validate(item)
            for item in service.orders.list_items(order.id)
        ],
        payments=[
            PaymentResponse.model_validate(payment)
            for payment in service.orders.list_payments(order.id)
        ],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@product_router.get("", response_model=ProductPage)
def search_products(
    params: Annotated[ProductSearchParams, Query()],
    session: DatabaseSession,
) -> ProductPage:
    service = ProductBrowseService(session)
    products, total = service.search(
        keyword=params.keyword,
        category_id=params.category_id,
        min_price=params.min_price,
        max_price=params.max_price,
        sort=params.sort,
        offset=(params.page - 1) * params.page_size,
        limit=params.page_size,
    )
    return ProductPage(
        items=[public_product_response(*item) for item in products],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@product_router.get("/{product_id}", response_model=PublicProductResponse)
def get_product(product_id: int, session: DatabaseSession) -> PublicProductResponse:
    product = ProductBrowseService(session).get_active_details(product_id)
    return public_product_response(*product)


@customer_router.get("/cart", response_model=CartResponse)
def get_cart(user: CustomerUser, session: DatabaseSession) -> CartResponse:
    return cart_response(*CartService(session).get(user))


@customer_router.post(
    "/cart/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_cart_item(
    payload: CartItemCreate,
    user: CustomerUser,
    session: DatabaseSession,
) -> CartResponse:
    service = CartService(session)
    service.add_item(user, payload.product_id, payload.quantity)
    return cart_response(*service.get(user))


@customer_router.patch("/cart/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    item_id: int,
    payload: CartItemUpdate,
    user: CustomerUser,
    session: DatabaseSession,
) -> CartResponse:
    service = CartService(session)
    service.update_item(user, item_id, payload.quantity)
    return cart_response(*service.get(user))


@customer_router.delete("/cart/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart_item(
    item_id: int,
    user: CustomerUser,
    session: DatabaseSession,
) -> Response:
    CartService(session).delete_item(user, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@customer_router.get("/addresses", response_model=list[AddressResponse])
def list_addresses(user: CustomerUser, session: DatabaseSession) -> list[AddressResponse]:
    addresses = AddressService(session).list(user)
    return [AddressResponse.model_validate(address) for address in addresses]


@customer_router.post(
    "/addresses",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_address(
    payload: AddressCreate,
    user: CustomerUser,
    session: DatabaseSession,
) -> AddressResponse:
    address = AddressService(session).create(user, payload.model_dump())
    return AddressResponse.model_validate(address)


@customer_router.patch("/addresses/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: int,
    payload: AddressUpdate,
    user: CustomerUser,
    session: DatabaseSession,
) -> AddressResponse:
    address = AddressService(session).update(
        user,
        address_id,
        payload.model_dump(exclude_unset=True),
    )
    return AddressResponse.model_validate(address)


@customer_router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: int,
    user: CustomerUser,
    session: DatabaseSession,
) -> Response:
    AddressService(session).delete(user, address_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@customer_router.post(
    "/checkout",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def checkout(
    payload: CheckoutRequest,
    user: CustomerUser,
    session: DatabaseSession,
) -> OrderResponse:
    order = CheckoutService(session).checkout(
        user,
        payload.address_id,
        payload.payment_method,
        payload.idempotency_key,
    )
    return order_response(order, OrderService(session))


@customer_router.get("/orders", response_model=list[OrderResponse])
def list_orders(user: CustomerUser, session: DatabaseSession) -> list[OrderResponse]:
    service = OrderService(session)
    return [order_response(order, service) for order in service.list(user)]


@customer_router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    user: CustomerUser,
    session: DatabaseSession,
) -> OrderResponse:
    service = OrderService(session)
    return order_response(service.get(user, order_id), service)


@customer_router.post("/orders/{order_id}/pay", response_model=PaymentResponse)
def pay_order(
    order_id: int,
    payload: PaymentRequest,
    user: CustomerUser,
    session: DatabaseSession,
) -> PaymentResponse:
    payment = OrderService(session).pay(
        user,
        order_id,
        payload.method,
        payload.amount,
        payload.idempotency_key,
        payload.simulate_failure,
    )
    return PaymentResponse.model_validate(payment)


@customer_router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    user: CustomerUser,
    session: DatabaseSession,
) -> OrderResponse:
    service = OrderService(session)
    return order_response(service.cancel(user, order_id), service)
