from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    MerchantStatus,
    OrderPaymentStatus,
    OrderStatus,
    ProductStatus,
    StoreStatus,
    UserRole,
    UserStatus,
)
from app.schemas.commerce import OrderItemResponse, PaymentResponse
from app.schemas.pagination import Page


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class ManagedOrderResponse(BaseModel):
    id: int
    order_no: str
    user_id: int
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


ManagedOrderPage = Page[ManagedOrderResponse]


class MerchantAnalyticsSummary(BaseModel):
    today_revenue: Decimal
    month_revenue: Decimal
    total_revenue: Decimal
    paid_order_count: int
    average_order_amount: Decimal


class TopProductResponse(BaseModel):
    product_id: int
    product_name: str
    quantity_sold: int
    revenue: Decimal


class LowStockResponse(BaseModel):
    product_id: int
    sku: str
    name: str
    status: ProductStatus
    quantity: int


LowStockPage = Page[LowStockResponse]


class UserAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime


UserAdminPage = Page[UserAdminResponse]


class UserStatusUpdate(BaseModel):
    status: UserStatus
    reason: str = Field(min_length=3, max_length=255)


class AdminMerchantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    business_name: str
    status: MerchantStatus
    approved_at: datetime | None
    approved_by: int | None
    created_at: datetime
    updated_at: datetime


AdminMerchantPage = Page[AdminMerchantResponse]


class AdminStoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: int
    name: str
    description: str | None
    status: StoreStatus
    created_at: datetime
    updated_at: datetime


AdminStorePage = Page[AdminStoreResponse]


class AdminProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    category_id: int
    sku: str
    name: str
    current_price: Decimal
    status: ProductStatus
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


AdminProductPage = Page[AdminProductResponse]


class ForceDeactivateRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int
    actor_role: UserRole
    action: str
    entity_type: str
    entity_id: int
    before_data: dict[str, object] | None
    after_data: dict[str, object] | None
    created_at: datetime


AuditLogPage = Page[AuditLogResponse]


class PlatformAnalyticsSummary(BaseModel):
    user_count: int
    merchant_count: int
    store_count: int
    product_count: int
    order_count: int
    paid_order_count: int
    total_revenue: Decimal
    average_order_amount: Decimal
