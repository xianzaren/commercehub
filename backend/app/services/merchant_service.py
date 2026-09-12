from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.models.audit import AuditLog
from app.models.enums import MerchantStatus, StoreStatus, UserRole
from app.models.user import Merchant, Store, User
from app.repositories.merchant_repository import MerchantRepository, StoreRepository
from app.repositories.user_repository import UserRepository


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MerchantService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.merchants = MerchantRepository(session)
        self.stores = StoreRepository(session)
        self.users = UserRepository(session)

    def apply(self, user: User, business_name: str) -> Merchant:
        existing = self.merchants.get_by_user_id(user.id)
        if existing is not None:
            raise BusinessError("MERCHANT_APPLICATION_EXISTS", "商家申请已存在", status_code=409)
        merchant = Merchant(
            user_id=user.id,
            business_name=business_name.strip(),
            status=MerchantStatus.PENDING,
        )
        try:
            self.merchants.add(merchant)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise BusinessError(
                "MERCHANT_APPLICATION_EXISTS", "商家申请已存在", status_code=409
            ) from exc
        self.session.refresh(merchant)
        return merchant

    def get_application(self, user: User) -> Merchant:
        merchant = self.merchants.get_by_user_id(user.id)
        if merchant is None:
            raise BusinessError("MERCHANT_APPLICATION_NOT_FOUND", "商家申请不存在", status_code=404)
        return merchant

    def list_applications(self, status: MerchantStatus | None) -> list[Merchant]:
        return self.merchants.list_by_status(status.value if status is not None else None)

    def approve(self, merchant_id: int, admin: User) -> Merchant:
        merchant = self.merchants.lock(merchant_id)
        if merchant is None:
            raise BusinessError("MERCHANT_NOT_FOUND", "商家不存在", status_code=404)
        if merchant.status != MerchantStatus.PENDING:
            raise BusinessError(
                "MERCHANT_APPLICATION_NOT_PENDING", "商家申请不是待审批状态", status_code=409
            )
        user = self.users.get(merchant.user_id)
        if user is None:
            raise BusinessError("MERCHANT_USER_NOT_FOUND", "商家账户不存在", status_code=409)

        before = {"status": merchant.status, "user_role": user.role}
        merchant.status = MerchantStatus.ACTIVE
        merchant.approved_at = utcnow()
        merchant.approved_by = admin.id
        user.role = UserRole.MERCHANT
        self._audit(
            admin,
            "MERCHANT_APPROVED",
            "merchant",
            merchant.id,
            before,
            {"status": merchant.status, "user_role": user.role},
        )
        self.session.commit()
        self.session.refresh(merchant)
        return merchant

    def update_status(
        self,
        merchant_id: int,
        new_status: MerchantStatus,
        reason: str,
        admin: User,
    ) -> Merchant:
        merchant = self.merchants.lock(merchant_id)
        if merchant is None:
            raise BusinessError("MERCHANT_NOT_FOUND", "商家不存在", status_code=404)
        if new_status == MerchantStatus.PENDING:
            raise BusinessError(
                "INVALID_MERCHANT_STATUS", "不能将商家恢复为待审批", status_code=409
            )
        if merchant.status == MerchantStatus.PENDING:
            raise BusinessError(
                "MERCHANT_APPLICATION_NOT_APPROVED",
                "待审批商家必须通过审批接口处理",
                status_code=409,
            )
        if merchant.status == MerchantStatus.CLOSED:
            raise BusinessError(
                "MERCHANT_ALREADY_CLOSED", "已关闭商家不能变更状态", status_code=409
            )
        if merchant.status == new_status:
            return merchant

        old_status = merchant.status
        merchant.status = new_status
        store = self.stores.get_by_merchant_id(merchant.id)
        if store is not None:
            if new_status == MerchantStatus.SUSPENDED:
                store.status = StoreStatus.SUSPENDED
            elif new_status == MerchantStatus.ACTIVE and store.status == StoreStatus.SUSPENDED:
                store.status = StoreStatus.ACTIVE
            elif new_status == MerchantStatus.CLOSED:
                store.status = StoreStatus.CLOSED
        self._audit(
            admin,
            "MERCHANT_STATUS_CHANGED",
            "merchant",
            merchant.id,
            {"status": old_status},
            {"status": new_status, "reason": reason.strip()},
        )
        self.session.commit()
        self.session.refresh(merchant)
        return merchant

    def create_store(self, merchant: Merchant, name: str, description: str | None) -> Store:
        if self.stores.get_by_merchant_id(merchant.id) is not None:
            raise BusinessError("STORE_ALREADY_EXISTS", "当前商家已经创建店铺", status_code=409)
        store = Store(
            merchant_id=merchant.id,
            name=name.strip(),
            description=description.strip() if description else None,
            status=StoreStatus.ACTIVE,
        )
        try:
            self.stores.add(store)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise BusinessError(
                "STORE_ALREADY_EXISTS", "当前商家已经创建店铺", status_code=409
            ) from exc
        self.session.refresh(store)
        return store

    def get_store(self, merchant: Merchant) -> Store:
        store = self.stores.get_by_merchant_id(merchant.id)
        if store is None:
            raise BusinessError("STORE_NOT_FOUND", "店铺不存在", status_code=404)
        return store

    def update_store(
        self,
        merchant: Merchant,
        *,
        name: str | None,
        description: str | None,
        fields_set: set[str],
    ) -> Store:
        store = self.get_store(merchant)
        if name is not None:
            store.name = name.strip()
        if "description" in fields_set:
            store.description = description.strip() if description else None
        self.session.commit()
        self.session.refresh(store)
        return store

    def _audit(
        self,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: int,
        before: dict[str, object] | None,
        after: dict[str, object] | None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_user_id=actor.id,
                actor_role=actor.role,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_data=before,
                after_data=after,
                created_at=utcnow(),
            )
        )
