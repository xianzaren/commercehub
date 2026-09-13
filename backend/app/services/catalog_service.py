from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.models.catalog import Category, Inventory, InventoryTransaction, Product, ProductPrice
from app.models.enums import (
    CategoryStatus,
    InventoryTransactionType,
    ProductStatus,
    StoreStatus,
)
from app.models.user import Merchant, User
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.merchant_repository import StoreRepository
from app.repositories.product_repository import CategoryRepository, ProductRepository


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CatalogService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.categories = CategoryRepository(session)
        self.products = ProductRepository(session)
        self.inventory = InventoryRepository(session)
        self.stores = StoreRepository(session)

    def create_category(
        self, name: str, slug: str, parent_id: int | None = None
    ) -> Category:
        normalized_slug = slug.strip().lower()
        if self.categories.get_by_slug(normalized_slug) is not None:
            raise BusinessError("CATEGORY_SLUG_EXISTS", "分类标识已存在", status_code=409)
        if parent_id is not None and self.categories.get(parent_id) is None:
            raise BusinessError("PARENT_CATEGORY_NOT_FOUND", "父分类不存在", status_code=404)
        category = Category(
            name=name.strip(),
            slug=normalized_slug,
            parent_id=parent_id,
            status=CategoryStatus.ACTIVE,
        )
        try:
            self.categories.add(category)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise BusinessError("CATEGORY_SLUG_EXISTS", "分类标识已存在", status_code=409) from exc
        self.session.refresh(category)
        return category

    def create_product(
        self,
        merchant: Merchant,
        *,
        category_id: int,
        sku: str,
        name: str,
        description: str | None,
        tags: list[str],
        current_price: Decimal,
    ) -> Product:
        store = self._active_store(merchant)
        category = self.categories.get(category_id)
        if category is None or category.status != CategoryStatus.ACTIVE:
            raise BusinessError("CATEGORY_NOT_AVAILABLE", "商品分类不存在或不可用", status_code=409)
        product = Product(
            store_id=store.id,
            category_id=category_id,
            sku=sku,
            name=name.strip(),
            description=description.strip() if description else None,
            tags=tags,
            current_price=current_price,
            status=ProductStatus.DRAFT,
        )
        try:
            self.products.add(product)
            self.session.add(
                Inventory(product_id=product.id, quantity=0, version=0, updated_at=utcnow())
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise BusinessError("PRODUCT_SKU_EXISTS", "店铺内 SKU 已存在", status_code=409) from exc
        self.session.refresh(product)
        return product

    def list_products(self, merchant: Merchant) -> list[Product]:
        return self.products.list_owned(merchant.id)

    def get_product(self, product_id: int, merchant: Merchant) -> Product:
        product = self.products.get(product_id)
        if product is None:
            raise BusinessError("PRODUCT_NOT_FOUND", "商品不存在", status_code=404)
        owned = self.products.get_owned(product_id, merchant.id)
        if owned is None:
            raise BusinessError("PRODUCT_NOT_OWNED", "不能操作其他商家的商品", status_code=403)
        return owned

    def update_product(
        self,
        product_id: int,
        merchant: Merchant,
        changes: dict[str, object],
    ) -> Product:
        product = self.get_product(product_id, merchant)
        self._not_deleted(product)
        if "category_id" in changes:
            category = self.categories.get(int(changes["category_id"]))
            if category is None or category.status != CategoryStatus.ACTIVE:
                raise BusinessError(
                    "CATEGORY_NOT_AVAILABLE", "商品分类不存在或不可用", status_code=409
                )
        for field, value in changes.items():
            if field in {"sku", "name"} and isinstance(value, str):
                value = value.strip()
            if field == "description" and isinstance(value, str):
                value = value.strip() or None
            setattr(product, field, value)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise BusinessError("PRODUCT_SKU_EXISTS", "店铺内 SKU 已存在", status_code=409) from exc
        self.session.refresh(product)
        return product

    def set_status(
        self, product_id: int, merchant: Merchant, new_status: ProductStatus
    ) -> Product:
        product = self.get_product(product_id, merchant)
        self._not_deleted(product)
        if new_status not in {ProductStatus.ACTIVE, ProductStatus.INACTIVE, ProductStatus.DRAFT}:
            raise BusinessError("INVALID_PRODUCT_STATUS", "不支持该商品状态变更", status_code=409)
        if new_status == ProductStatus.ACTIVE:
            self._active_store(merchant)
            inventory = self.inventory.get(product.id)
            if inventory is None or inventory.quantity <= 0:
                raise BusinessError("PRODUCT_OUT_OF_STOCK", "库存大于零后才能上架", status_code=409)
        product.status = new_status
        self.session.commit()
        self.session.refresh(product)
        return product

    def soft_delete(self, product_id: int, merchant: Merchant) -> None:
        product = self.get_product(product_id, merchant)
        if product.status == ProductStatus.DELETED:
            return
        product.status = ProductStatus.DELETED
        product.deleted_at = utcnow()
        self.session.commit()

    def change_price(
        self,
        product_id: int,
        merchant: Merchant,
        actor: User,
        new_price: Decimal,
    ) -> Product:
        product = self.get_product(product_id, merchant)
        self._not_deleted(product)
        if product.current_price == new_price:
            raise BusinessError("PRICE_UNCHANGED", "新价格与当前价格相同", status_code=409)
        old_price = product.current_price
        product.current_price = new_price
        self.session.add(
            ProductPrice(
                product_id=product.id,
                old_price=old_price,
                new_price=new_price,
                changed_by=actor.id,
                changed_at=utcnow(),
            )
        )
        self.session.commit()
        self.session.refresh(product)
        return product

    def list_prices(self, product_id: int, merchant: Merchant) -> list[ProductPrice]:
        self.get_product(product_id, merchant)
        return self.products.list_prices(product_id)

    def restock(
        self,
        product_id: int,
        merchant: Merchant,
        actor: User,
        quantity: int,
        reason: str | None,
    ) -> Inventory:
        return self._change_inventory(
            product_id,
            merchant,
            actor,
            quantity,
            InventoryTransactionType.RESTOCK,
            reason,
        )

    def adjust_inventory(
        self,
        product_id: int,
        merchant: Merchant,
        actor: User,
        quantity_change: int,
        reason: str,
    ) -> Inventory:
        return self._change_inventory(
            product_id,
            merchant,
            actor,
            quantity_change,
            InventoryTransactionType.ADJUSTMENT,
            reason,
        )

    def list_inventory_transactions(
        self, product_id: int, merchant: Merchant
    ) -> list[InventoryTransaction]:
        self.get_product(product_id, merchant)
        return self.inventory.list_transactions(product_id)

    def inventory_for(self, product_id: int) -> Inventory:
        inventory = self.inventory.get(product_id)
        if inventory is None:
            raise BusinessError("INVENTORY_NOT_FOUND", "库存记录不存在", status_code=409)
        return inventory

    def _change_inventory(
        self,
        product_id: int,
        merchant: Merchant,
        actor: User,
        quantity_change: int,
        transaction_type: InventoryTransactionType,
        reason: str | None,
    ) -> Inventory:
        product = self.get_product(product_id, merchant)
        self._not_deleted(product)
        inventory = self.inventory.lock(product.id)
        if inventory is None:
            raise BusinessError("INVENTORY_NOT_FOUND", "库存记录不存在", status_code=409)
        before = inventory.quantity
        after = before + quantity_change
        if after < 0:
            self.session.rollback()
            raise BusinessError("INSUFFICIENT_INVENTORY", "库存调整后不能为负数", status_code=409)
        inventory.quantity = after
        inventory.version += 1
        inventory.updated_at = utcnow()
        self.session.add(
            InventoryTransaction(
                product_id=product.id,
                type=transaction_type,
                quantity_change=quantity_change,
                quantity_before=before,
                quantity_after=after,
                reason=reason.strip() if reason else None,
                created_by=actor.id,
                created_at=utcnow(),
            )
        )
        self.session.commit()
        self.session.refresh(inventory)
        return inventory

    def _active_store(self, merchant: Merchant):
        store = self.stores.get_by_merchant_id(merchant.id)
        if store is None:
            raise BusinessError("STORE_NOT_FOUND", "请先创建店铺", status_code=409)
        if store.status != StoreStatus.ACTIVE:
            raise BusinessError("STORE_NOT_ACTIVE", "店铺当前不可用", status_code=409)
        return store

    @staticmethod
    def _not_deleted(product: Product) -> None:
        if product.status == ProductStatus.DELETED:
            raise BusinessError("PRODUCT_DELETED", "商品已删除", status_code=409)
