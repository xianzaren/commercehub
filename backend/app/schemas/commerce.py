from datetime import datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import OrderPaymentStatus, OrderStatus, PaymentMethod, PaymentStatus
from app.schemas.pagination import Page


class PublicProductResponse(BaseModel):
    id: int
    store_id: int
    category_id: int
    category_name: str
    store_name: str
    sku: str
    name: str
    description: str | None
    tags: list[str]
    current_price: Decimal
    inventory_quantity: int
    sales_count: int
    created_at: datetime


class ProductSearchParams(BaseModel):
    keyword: str | None = Field(default=None, max_length=100)
    category_id: int | None = Field(default=None, gt=0)
    min_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    max_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    sort: Literal["price_asc", "price_desc", "newest", "oldest"] = "newest"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_price_range(self) -> Self:
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must not exceed max_price")
        return self


ProductPage = Page[PublicProductResponse]


class CartItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=10_000)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0, le=10_000)


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    sku: str
    unit_price: Decimal
    quantity: int
    available_stock: int
    subtotal: Decimal


class CartResponse(BaseModel):
    id: int | None
    store_id: int | None
    items: list[CartItemResponse]
    total_amount: Decimal


class AddressCreate(BaseModel):
    recipient_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=6, max_length=32)
    province: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=80)
    district: str = Field(min_length=1, max_length=80)
    detail: str = Field(min_length=2, max_length=255)
    postal_code: str | None = Field(default=None, max_length=20)
    is_default: bool = False


class AddressUpdate(BaseModel):
    recipient_name: str | None = Field(default=None, min_length=2, max_length=80)
    phone: str | None = Field(default=None, min_length=6, max_length=32)
    province: str | None = Field(default=None, min_length=1, max_length=80)
    city: str | None = Field(default=None, min_length=1, max_length=80)
    district: str | None = Field(default=None, min_length=1, max_length=80)
    detail: str | None = Field(default=None, min_length=2, max_length=255)
    postal_code: str | None = Field(default=None, max_length=20)
    is_default: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        required = {"recipient_name", "phone", "province", "city", "district", "detail"}
        for field in required & self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} must not be null")
        return self


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_name: str
    phone: str
    province: str
    city: str
    district: str
    detail: str
    postal_code: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class CheckoutRequest(BaseModel):
    address_id: int = Field(gt=0)
    payment_method: PaymentMethod = PaymentMethod.MOCK_CARD
    idempotency_key: str = Field(min_length=8, max_length=64)


class PaymentRequest(BaseModel):
    method: PaymentMethod
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    idempotency_key: str = Field(min_length=8, max_length=64)
    simulate_failure: bool = False


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    store_id: int
    product_name_snapshot: str
    sku_snapshot: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_no: str
    method: PaymentMethod
    amount: Decimal
    status: PaymentStatus
    idempotency_key: str
    paid_at: datetime | None
    created_at: datetime


class OrderResponse(BaseModel):
    id: int
    order_no: str
    store_id: int
    address_snapshot: dict[str, str]
    status: OrderStatus
    subtotal: Decimal
    total_amount: Decimal
    payment_status: OrderPaymentStatus
    items: list[OrderItemResponse]
    payments: list[PaymentResponse]
    created_at: datetime
    updated_at: datetime
