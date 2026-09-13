from decimal import Decimal

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.orm import Session

from app.models.catalog import Category, Inventory, Product, ProductPrice
from app.models.enums import OrderStatus
from app.models.order import Order, OrderItem
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
    SALE_COUNTED_STATUSES = (
        OrderStatus.PAID,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.COMPLETED,
    )

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
    ) -> tuple[list[tuple[Product, Inventory, str, str, int]], int]:
        conditions = [Product.status == "ACTIVE", Store.status == "ACTIVE"]
        relevance = None
        normalized_keyword = keyword.strip().lower() if keyword else ""
        if normalized_keyword:
            def escape_like(value: str) -> str:
                return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

            searchable_name = func.lower(Product.name)
            searchable_description = func.lower(func.coalesce(Product.description, ""))
            full_pattern = f"%{escape_like(normalized_keyword)}%"
            distinct_characters = list(
                dict.fromkeys(
                    character for character in normalized_keyword if not character.isspace()
                )
            )
            character_matches = []
            relevance = literal(0)

            for character in distinct_characters:
                character_pattern = f"%{escape_like(character)}%"
                name_match = searchable_name.like(character_pattern, escape="\\")
                description_match = searchable_description.like(character_pattern, escape="\\")
                character_matches.append(or_(name_match, description_match))
                relevance += case((name_match, 4), (description_match, 1), else_=0)

            conditions.append(or_(*character_matches))
            relevance += case(
                (searchable_name == normalized_keyword, 1000),
                (searchable_name.like(f"{escape_like(normalized_keyword)}%", escape="\\"), 500),
                (searchable_name.like(full_pattern, escape="\\"), 250),
                (searchable_description.like(full_pattern, escape="\\"), 100),
                else_=0,
            )
        if category_id is not None:
            conditions.append(Product.category_id == category_id)
        if min_price is not None:
            conditions.append(Product.current_price >= min_price)
        if max_price is not None:
            conditions.append(Product.current_price <= max_price)

        secondary_order_by = {
            "price_asc": (Product.current_price.asc(), Product.id.asc()),
            "price_desc": (Product.current_price.desc(), Product.id.desc()),
            "newest": (Product.created_at.desc(), Product.id.desc()),
            "oldest": (Product.created_at.asc(), Product.id.asc()),
        }[sort]
        order_by = (
            (relevance.desc(), *secondary_order_by)
            if relevance is not None
            else secondary_order_by
        )
        sales_totals = (
            select(
                OrderItem.product_id.label("product_id"),
                func.sum(OrderItem.quantity).label("sales_count"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.status.in_(self.SALE_COUNTED_STATUSES))
            .group_by(OrderItem.product_id)
            .subquery()
        )
        statement = (
            select(
                Product,
                Inventory,
                Category.name,
                Store.name,
                func.coalesce(sales_totals.c.sales_count, 0),
            )
            .join(Store, Product.store_id == Store.id)
            .join(Category, Product.category_id == Category.id)
            .join(Inventory, Inventory.product_id == Product.id)
            .outerjoin(sales_totals, sales_totals.c.product_id == Product.id)
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
        rows = [
            (product, inventory, category_name, store_name, int(sales_count))
            for product, inventory, category_name, store_name, sales_count in self.session.execute(
                statement
            )
        ]
        return rows, int(self.session.scalar(count_statement) or 0)

    def sales_count(self, product_id: int) -> int:
        statement = (
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .join(Order, Order.id == OrderItem.order_id)
            .where(OrderItem.product_id == product_id)
            .where(Order.status.in_(self.SALE_COUNTED_STATUSES))
        )
        return int(self.session.scalar(statement) or 0)
