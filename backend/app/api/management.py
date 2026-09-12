from datetime import datetime

from fastapi import APIRouter, Query

from app.api.deps import ActiveMerchant, AdminUser, DatabaseSession, MerchantUser
from app.models.enums import MerchantStatus, OrderStatus, ProductStatus, UserRole, UserStatus
from app.models.order import Order
from app.repositories.commerce_repository import OrderRepository
from app.schemas.commerce import OrderItemResponse, PaymentResponse
from app.schemas.management import (
    AdminMerchantPage,
    AdminMerchantResponse,
    AdminProductPage,
    AdminProductResponse,
    AdminStorePage,
    AdminStoreResponse,
    AuditLogPage,
    AuditLogResponse,
    ForceDeactivateRequest,
    LowStockPage,
    LowStockResponse,
    ManagedOrderPage,
    ManagedOrderResponse,
    MerchantAnalyticsSummary,
    OrderStatusUpdate,
    PlatformAnalyticsSummary,
    TopProductResponse,
    UserAdminPage,
    UserAdminResponse,
    UserStatusUpdate,
)
from app.services.management_service import AdminManagementService, MerchantManagementService

merchant_management_router = APIRouter(prefix="/api/merchant", tags=["merchant-management"])
admin_management_router = APIRouter(prefix="/api/admin", tags=["admin-management"])


def managed_order_response(order: Order, orders: OrderRepository) -> ManagedOrderResponse:
    return ManagedOrderResponse(
        id=order.id,
        order_no=order.order_no,
        user_id=order.user_id,
        store_id=order.store_id,
        address_snapshot=order.address_snapshot,
        status=order.status,
        subtotal=order.subtotal,
        total_amount=order.total_amount,
        payment_status=order.payment_status,
        items=[
            OrderItemResponse.model_validate(item) for item in orders.list_items(order.id)
        ],
        payments=[
            PaymentResponse.model_validate(payment) for payment in orders.list_payments(order.id)
        ],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@merchant_management_router.get("/orders", response_model=ManagedOrderPage)
def list_merchant_orders(
    merchant: ActiveMerchant,
    session: DatabaseSession,
    order_status: OrderStatus | None = None,
    order_no: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ManagedOrderPage:
    service = MerchantManagementService(session)
    orders, total = service.list_orders(
        merchant,
        status=order_status,
        order_no=order_no,
        created_from=created_from,
        created_to=created_to,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return ManagedOrderPage(
        items=[managed_order_response(order, service.orders) for order in orders],
        page=page,
        page_size=page_size,
        total=total,
    )


@merchant_management_router.get("/orders/{order_id}", response_model=ManagedOrderResponse)
def get_merchant_order(
    order_id: int,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> ManagedOrderResponse:
    service = MerchantManagementService(session)
    return managed_order_response(service.get_order(merchant, order_id), service.orders)


@merchant_management_router.patch(
    "/orders/{order_id}/status",
    response_model=ManagedOrderResponse,
)
def update_merchant_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    user: MerchantUser,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> ManagedOrderResponse:
    service = MerchantManagementService(session)
    order = service.update_order_status(merchant, user, order_id, payload.status)
    return managed_order_response(order, service.orders)


@merchant_management_router.get(
    "/analytics/summary",
    response_model=MerchantAnalyticsSummary,
)
def merchant_analytics_summary(
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> MerchantAnalyticsSummary:
    return MerchantAnalyticsSummary.model_validate(
        MerchantManagementService(session).analytics_summary(merchant)
    )


@merchant_management_router.get(
    "/analytics/top-products",
    response_model=list[TopProductResponse],
)
def merchant_top_products(
    merchant: ActiveMerchant,
    session: DatabaseSession,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[TopProductResponse]:
    rows = MerchantManagementService(session).top_products(merchant, limit)
    return [TopProductResponse.model_validate(row) for row in rows]


@merchant_management_router.get("/analytics/low-stock", response_model=LowStockPage)
def merchant_low_stock(
    merchant: ActiveMerchant,
    session: DatabaseSession,
    threshold: int = Query(default=5, ge=0, le=1_000_000),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> LowStockPage:
    rows, total = MerchantManagementService(session).low_stock(
        merchant,
        threshold,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return LowStockPage(
        items=[
            LowStockResponse(
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                status=product.status,
                quantity=inventory.quantity,
            )
            for product, inventory in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@admin_management_router.get("/users", response_model=UserAdminPage)
def list_admin_users(
    admin: AdminUser,
    session: DatabaseSession,
    role: UserRole | None = None,
    user_status: UserStatus | None = None,
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> UserAdminPage:
    del admin
    service = AdminManagementService(session)
    users, total = service.management.list_users(
        role=role.value if role is not None else None,
        status=user_status.value if user_status is not None else None,
        keyword=keyword,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return UserAdminPage(
        items=[UserAdminResponse.model_validate(user) for user in users],
        page=page,
        page_size=page_size,
        total=total,
    )


@admin_management_router.patch("/users/{user_id}/status", response_model=UserAdminResponse)
def update_admin_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    admin: AdminUser,
    session: DatabaseSession,
) -> UserAdminResponse:
    user = AdminManagementService(session).update_user_status(
        user_id,
        payload.status,
        payload.reason,
        admin,
    )
    return UserAdminResponse.model_validate(user)


@admin_management_router.get("/merchants", response_model=AdminMerchantPage)
def list_admin_merchants(
    admin: AdminUser,
    session: DatabaseSession,
    merchant_status: MerchantStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AdminMerchantPage:
    del admin
    service = AdminManagementService(session)
    merchants, total = service.management.list_merchants(
        status=merchant_status.value if merchant_status is not None else None,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return AdminMerchantPage(
        items=[AdminMerchantResponse.model_validate(merchant) for merchant in merchants],
        page=page,
        page_size=page_size,
        total=total,
    )


@admin_management_router.get("/stores", response_model=AdminStorePage)
def list_admin_stores(
    admin: AdminUser,
    session: DatabaseSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AdminStorePage:
    del admin
    service = AdminManagementService(session)
    stores, total = service.management.list_stores(
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return AdminStorePage(
        items=[AdminStoreResponse.model_validate(store) for store in stores],
        page=page,
        page_size=page_size,
        total=total,
    )


@admin_management_router.get("/products", response_model=AdminProductPage)
def list_admin_products(
    admin: AdminUser,
    session: DatabaseSession,
    product_status: ProductStatus | None = None,
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AdminProductPage:
    del admin
    service = AdminManagementService(session)
    products, total = service.management.list_products(
        status=product_status.value if product_status is not None else None,
        keyword=keyword,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return AdminProductPage(
        items=[AdminProductResponse.model_validate(product) for product in products],
        page=page,
        page_size=page_size,
        total=total,
    )


@admin_management_router.post(
    "/products/{product_id}/force-deactivate",
    response_model=AdminProductResponse,
)
def force_deactivate_product(
    product_id: int,
    payload: ForceDeactivateRequest,
    admin: AdminUser,
    session: DatabaseSession,
) -> AdminProductResponse:
    product = AdminManagementService(session).force_deactivate_product(
        product_id,
        payload.reason,
        admin,
    )
    return AdminProductResponse.model_validate(product)


@admin_management_router.get("/orders", response_model=ManagedOrderPage)
def list_admin_orders(
    admin: AdminUser,
    session: DatabaseSession,
    order_status: OrderStatus | None = None,
    order_no: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ManagedOrderPage:
    del admin
    service = AdminManagementService(session)
    orders, total = service.orders.list_all(
        status=order_status.value if order_status is not None else None,
        order_no=order_no,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return ManagedOrderPage(
        items=[managed_order_response(order, service.orders) for order in orders],
        page=page,
        page_size=page_size,
        total=total,
    )


@admin_management_router.get("/audit-logs", response_model=AuditLogPage)
def list_admin_audit_logs(
    admin: AdminUser,
    session: DatabaseSession,
    action: str | None = None,
    actor_user_id: int | None = Query(default=None, gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AuditLogPage:
    del admin
    service = AdminManagementService(session)
    logs, total = service.management.list_audit_logs(
        action=action,
        actor_user_id=actor_user_id,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return AuditLogPage(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        page=page,
        page_size=page_size,
        total=total,
    )


@admin_management_router.get(
    "/analytics/summary",
    response_model=PlatformAnalyticsSummary,
)
def admin_analytics_summary(
    admin: AdminUser,
    session: DatabaseSession,
) -> PlatformAnalyticsSummary:
    del admin
    return PlatformAnalyticsSummary.model_validate(
        AdminManagementService(session).platform_summary()
    )
