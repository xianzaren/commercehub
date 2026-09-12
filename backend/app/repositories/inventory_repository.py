from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Inventory, InventoryTransaction


class InventoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, product_id: int) -> Inventory | None:
        return self.session.get(Inventory, product_id)

    def lock(self, product_id: int) -> Inventory | None:
        statement = select(Inventory).where(Inventory.product_id == product_id).with_for_update()
        return self.session.scalar(statement)

    def list_transactions(self, product_id: int) -> list[InventoryTransaction]:
        statement = (
            select(InventoryTransaction)
            .where(InventoryTransaction.product_id == product_id)
            .order_by(InventoryTransaction.created_at.desc(), InventoryTransaction.id.desc())
        )
        return list(self.session.scalars(statement))

    def lock_many(self, product_ids: list[int]) -> list[Inventory]:
        ordered_ids = sorted(set(product_ids))
        statement = (
            select(Inventory)
            .where(Inventory.product_id.in_(ordered_ids))
            .order_by(Inventory.product_id)
            .with_for_update()
        )
        return list(self.session.scalars(statement))
