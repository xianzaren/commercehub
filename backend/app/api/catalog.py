from fastapi import APIRouter, Response, status

from app.api.deps import ActiveMerchant, AdminUser, DatabaseSession, MerchantUser
from app.models.catalog import Product
from app.schemas.catalog import (
    CategoryCreate,
    CategoryResponse,
    InventoryAdjustRequest,
    InventoryResponse,
    InventoryRestockRequest,
    InventoryTransactionResponse,
    PriceChangeRequest,
    PriceHistoryResponse,
    ProductCreate,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
)
from app.services.catalog_service import CatalogService

catalog_router = APIRouter(prefix="/api/categories", tags=["catalog"])
admin_catalog_router = APIRouter(prefix="/api/admin/categories", tags=["admin-catalog"])
merchant_catalog_router = APIRouter(prefix="/api/merchant/products", tags=["merchant-products"])


def product_response(product: Product, service: CatalogService) -> ProductResponse:
    inventory = service.inventory_for(product.id)
    return ProductResponse(
        id=product.id,
        store_id=product.store_id,
        category_id=product.category_id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        tags=product.tags,
        current_price=product.current_price,
        status=product.status,
        inventory_quantity=inventory.quantity,
        created_at=product.created_at,
        updated_at=product.updated_at,
        deleted_at=product.deleted_at,
    )


@catalog_router.get("", response_model=list[CategoryResponse])
def list_categories(session: DatabaseSession) -> list[CategoryResponse]:
    categories = CatalogService(session).categories.list_active()
    return [CategoryResponse.model_validate(category) for category in categories]


@admin_catalog_router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    payload: CategoryCreate,
    admin: AdminUser,
    session: DatabaseSession,
) -> CategoryResponse:
    del admin
    category = CatalogService(session).create_category(
        payload.name,
        payload.slug,
        payload.parent_id,
    )
    return CategoryResponse.model_validate(category)


@merchant_catalog_router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    payload: ProductCreate,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> ProductResponse:
    service = CatalogService(session)
    product = service.create_product(merchant, **payload.model_dump())
    return product_response(product, service)


@merchant_catalog_router.get("", response_model=list[ProductResponse])
def list_products(
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> list[ProductResponse]:
    service = CatalogService(session)
    return [product_response(product, service) for product in service.list_products(merchant)]


@merchant_catalog_router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> ProductResponse:
    service = CatalogService(session)
    return product_response(service.get_product(product_id, merchant), service)


@merchant_catalog_router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> ProductResponse:
    service = CatalogService(session)
    product = service.update_product(
        product_id,
        merchant,
        payload.model_dump(exclude_unset=True),
    )
    return product_response(product, service)


@merchant_catalog_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> Response:
    CatalogService(session).soft_delete(product_id, merchant)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@merchant_catalog_router.post("/{product_id}/status", response_model=ProductResponse)
def set_product_status(
    product_id: int,
    payload: ProductStatusUpdate,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> ProductResponse:
    service = CatalogService(session)
    product = service.set_status(product_id, merchant, payload.status)
    return product_response(product, service)


@merchant_catalog_router.post("/{product_id}/price", response_model=ProductResponse)
def change_product_price(
    product_id: int,
    payload: PriceChangeRequest,
    user: MerchantUser,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> ProductResponse:
    service = CatalogService(session)
    product = service.change_price(product_id, merchant, user, payload.new_price)
    return product_response(product, service)


@merchant_catalog_router.get(
    "/{product_id}/prices",
    response_model=list[PriceHistoryResponse],
)
def list_product_prices(
    product_id: int,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> list[PriceHistoryResponse]:
    prices = CatalogService(session).list_prices(product_id, merchant)
    return [PriceHistoryResponse.model_validate(price) for price in prices]


@merchant_catalog_router.post("/{product_id}/inventory/restock", response_model=InventoryResponse)
def restock_inventory(
    product_id: int,
    payload: InventoryRestockRequest,
    user: MerchantUser,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> InventoryResponse:
    inventory = CatalogService(session).restock(
        product_id,
        merchant,
        user,
        payload.quantity,
        payload.reason,
    )
    return InventoryResponse.model_validate(inventory, from_attributes=True)


@merchant_catalog_router.post("/{product_id}/inventory/adjust", response_model=InventoryResponse)
def adjust_inventory(
    product_id: int,
    payload: InventoryAdjustRequest,
    user: MerchantUser,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> InventoryResponse:
    inventory = CatalogService(session).adjust_inventory(
        product_id,
        merchant,
        user,
        payload.quantity_change,
        payload.reason,
    )
    return InventoryResponse.model_validate(inventory, from_attributes=True)


@merchant_catalog_router.get(
    "/{product_id}/inventory/transactions",
    response_model=list[InventoryTransactionResponse],
)
def list_inventory_transactions(
    product_id: int,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> list[InventoryTransactionResponse]:
    transactions = CatalogService(session).list_inventory_transactions(product_id, merchant)
    return [
        InventoryTransactionResponse.model_validate(transaction) for transaction in transactions
    ]
