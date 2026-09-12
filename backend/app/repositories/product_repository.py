from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.catalog import Category, Product, ProductPrice
from app.models.user import Store


class CategoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, category_id: int) -> Category | None:
        return self.session.get(Category, category_id)

    def get_by_slug(self, slug: str) -> Category | None:
        return self.session.scalar(select(Category).where(Category.slug == slug))

    def add(self, category: Category) -> Category:
        self.session.add(category)
        self.session.flush()
        return category

    def list_active(self) -> list[Category]:
        statement = select(Category).where(Category.status == "ACTIVE").order_by(Category.id)
        return list(self.session.scalars(statement))


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, product_id: int) -> Product | None:
        return self.session.get(Product, product_id)

    def get_owned(self, product_id: int, merchant_id: int) -> Product | None:
        statement = (
            select(Product)
            .join(Store, Product.store_id == Store.id)
            .where(Product.id == product_id)
            .where(Store.merchant_id == merchant_id)
        )
        return self.session.scalar(statement)

    def add(self, product: Product) -> Product:
        self.session.add(product)
        self.session.flush()
        return product

    def list_owned(self, merchant_id: int, *, include_deleted: bool = False) -> list[Product]:
        statement = (
            select(Product)
            .join(Store, Product.store_id == Store.id)
            .where(Store.merchant_id == merchant_id)
            .order_by(Product.id.desc())
        )
        if not include_deleted:
            statement = statement.where(Product.status != "DELETED")
        return list(self.session.scalars(statement))

    def list_prices(self, product_id: int) -> list[ProductPrice]:
        statement = (
            select(ProductPrice)
            .where(ProductPrice.product_id == product_id)
            .order_by(ProductPrice.changed_at.desc(), ProductPrice.id.desc())
        )
        return list(self.session.scalars(statement))

    def search_active(
        self,
        *,
        keyword: str | None,
        category_id: int | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        sort: str,
        offset: int,
        limit: int,
    ) -> tuple[list[Product], int]:
        conditions = [Product.status == "ACTIVE", Store.status == "ACTIVE"]
        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(or_(Product.name.like(pattern), Product.description.like(pattern)))
        if category_id is not None:
            conditions.append(Product.category_id == category_id)
        if min_price is not None:
            conditions.append(Product.current_price >= min_price)
        if max_price is not None:
            conditions.append(Product.current_price <= max_price)

        order_by = {
            "price_asc": (Product.current_price.asc(), Product.id.asc()),
            "price_desc": (Product.current_price.desc(), Product.id.desc()),
            "newest": (Product.created_at.desc(), Product.id.desc()),
            "oldest": (Product.created_at.asc(), Product.id.asc()),
        }[sort]
        statement = (
            select(Product)
            .join(Store, Product.store_id == Store.id)
            .where(*conditions)
            .order_by(*order_by)
            .offset(offset)
            .limit(limit)
        )
        count_statement = (
            select(func.count(Product.id))
            .select_from(Product)
            .join(Store, Product.store_id == Store.id)
            .where(*conditions)
        )
        return list(self.session.scalars(statement)), int(self.session.scalar(count_statement) or 0)
