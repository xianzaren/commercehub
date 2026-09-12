from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import Merchant, Store


class MerchantRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_user_id(self, user_id: int) -> Merchant | None:
        statement = select(Merchant).where(Merchant.user_id == user_id)
        return self.session.scalar(statement)

    def get(self, merchant_id: int) -> Merchant | None:
        return self.session.get(Merchant, merchant_id)

    def lock(self, merchant_id: int) -> Merchant | None:
        statement = select(Merchant).where(Merchant.id == merchant_id).with_for_update()
        return self.session.scalar(statement)

    def add(self, merchant: Merchant) -> Merchant:
        self.session.add(merchant)
        self.session.flush()
        return merchant

    def list_by_status(self, status: str | None = None) -> list[Merchant]:
        statement = select(Merchant).order_by(Merchant.created_at.desc(), Merchant.id.desc())
        if status is not None:
            statement = statement.where(Merchant.status == status)
        return list(self.session.scalars(statement))


class StoreRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, store_id: int) -> Store | None:
        return self.session.get(Store, store_id)

    def get_by_merchant_id(self, merchant_id: int) -> Store | None:
        statement = select(Store).where(Store.merchant_id == merchant_id)
        return self.session.scalar(statement)

    def add(self, store: Store) -> Store:
        self.session.add(store)
        self.session.flush()
        return store
