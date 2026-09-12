from fastapi import APIRouter, status

from app.api.deps import ActiveMerchant, AdminUser, CurrentUser, CustomerUser, DatabaseSession
from app.models.enums import MerchantStatus
from app.schemas.merchant import (
    MerchantApplicationCreate,
    MerchantResponse,
    MerchantStatusUpdate,
    StoreCreate,
    StoreResponse,
    StoreUpdate,
)
from app.services.merchant_service import MerchantService

merchant_router = APIRouter(prefix="/api/merchant", tags=["merchant"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin-merchants"])


@merchant_router.post(
    "/applications",
    response_model=MerchantResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_for_merchant(
    payload: MerchantApplicationCreate,
    user: CustomerUser,
    session: DatabaseSession,
) -> MerchantResponse:
    merchant = MerchantService(session).apply(user, payload.business_name)
    return MerchantResponse.model_validate(merchant)


@merchant_router.get("/application", response_model=MerchantResponse)
def get_own_application(user: CurrentUser, session: DatabaseSession) -> MerchantResponse:
    merchant = MerchantService(session).get_application(user)
    return MerchantResponse.model_validate(merchant)


@admin_router.get("/merchant-applications", response_model=list[MerchantResponse])
def list_merchant_applications(
    admin: AdminUser,
    session: DatabaseSession,
    application_status: MerchantStatus | None = None,
) -> list[MerchantResponse]:
    del admin
    merchants = MerchantService(session).list_applications(application_status)
    return [MerchantResponse.model_validate(merchant) for merchant in merchants]


@admin_router.post(
    "/merchant-applications/{merchant_id}/approve",
    response_model=MerchantResponse,
)
def approve_merchant_application(
    merchant_id: int,
    admin: AdminUser,
    session: DatabaseSession,
) -> MerchantResponse:
    merchant = MerchantService(session).approve(merchant_id, admin)
    return MerchantResponse.model_validate(merchant)


@admin_router.patch("/merchants/{merchant_id}/status", response_model=MerchantResponse)
def update_merchant_status(
    merchant_id: int,
    payload: MerchantStatusUpdate,
    admin: AdminUser,
    session: DatabaseSession,
) -> MerchantResponse:
    merchant = MerchantService(session).update_status(
        merchant_id,
        payload.status,
        payload.reason,
        admin,
    )
    return MerchantResponse.model_validate(merchant)


@merchant_router.post("/store", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
def create_store(
    payload: StoreCreate,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> StoreResponse:
    store = MerchantService(session).create_store(merchant, payload.name, payload.description)
    return StoreResponse.model_validate(store)


@merchant_router.get("/store", response_model=StoreResponse)
def get_store(merchant: ActiveMerchant, session: DatabaseSession) -> StoreResponse:
    store = MerchantService(session).get_store(merchant)
    return StoreResponse.model_validate(store)


@merchant_router.patch("/store", response_model=StoreResponse)
def update_store(
    payload: StoreUpdate,
    merchant: ActiveMerchant,
    session: DatabaseSession,
) -> StoreResponse:
    store = MerchantService(session).update_store(
        merchant,
        name=payload.name,
        description=payload.description,
        fields_set=payload.model_fields_set,
    )
    return StoreResponse.model_validate(store)
