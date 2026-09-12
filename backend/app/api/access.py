from fastapi import APIRouter

from app.api.deps import ActiveMerchant, AdminUser, CustomerUser

router = APIRouter(prefix="/api", tags=["access-check"])


@router.get("/customer/ping")
def customer_ping(user: CustomerUser) -> dict[str, int | str]:
    return {"status": "ok", "role": "CUSTOMER", "user_id": user.id}


@router.get("/merchant/ping")
def merchant_ping(merchant: ActiveMerchant) -> dict[str, int | str]:
    return {"status": "ok", "role": "MERCHANT", "merchant_id": merchant.id}


@router.get("/admin/ping")
def admin_ping(user: AdminUser) -> dict[str, int | str]:
    return {"status": "ok", "role": "ADMIN", "user_id": user.id}
