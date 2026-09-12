from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.cart import Cart
from app.models.catalog import Category, Inventory, Product
from app.models.enums import CartStatus, ProductStatus
from app.models.user import Merchant, Store, User


def _catalog_graph(session: Session, suffix: str) -> tuple[User, Store, Product]:
    user = User(
        email=f"merchant-{suffix}@example.com",
        password_hash="not-a-real-hash",
    )
    session.add(user)
    session.flush()
    merchant = Merchant(user_id=user.id, business_name=f"Merchant {suffix}")
    session.add(merchant)
    session.flush()
    store = Store(merchant_id=merchant.id, name=f"Store {suffix}")
    category = Category(name=f"Category {suffix}", slug=f"category-{suffix}")
    session.add_all([store, category])
    session.flush()
    product = Product(
        store_id=store.id,
        category_id=category.id,
        sku=f"SKU-{suffix}",
        name=f"Product {suffix}",
        current_price=Decimal("19.90"),
        status=ProductStatus.DRAFT,
    )
    session.add(product)
    session.flush()
    return user, store, product


@pytest.mark.integration
def test_inventory_cannot_be_negative(test_engine: Engine) -> None:
    with Session(test_engine) as session:
        _, _, product = _catalog_graph(session, "negative-stock")
        session.add(
            Inventory(
                product_id=product.id,
                quantity=-1,
                version=0,
                updated_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        # PyMySQL maps MySQL error 3819 (CHECK violation) to OperationalError.
        with pytest.raises((IntegrityError, OperationalError)):
            session.flush()
        session.rollback()


@pytest.mark.integration
def test_store_sku_is_unique(test_engine: Engine) -> None:
    with Session(test_engine) as session:
        _, store, product = _catalog_graph(session, "duplicate-sku")
        duplicate = Product(
            store_id=store.id,
            category_id=product.category_id,
            sku=product.sku,
            name="Duplicate",
            current_price=Decimal("20.00"),
            status=ProductStatus.DRAFT,
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


@pytest.mark.integration
def test_only_one_active_cart_per_user(test_engine: Engine) -> None:
    with Session(test_engine) as session:
        user = User(email="cart-owner@example.com", password_hash="not-a-real-hash")
        session.add(user)
        session.flush()
        session.add(Cart(user_id=user.id, status=CartStatus.ACTIVE))
        session.flush()
        session.add(Cart(user_id=user.id, status=CartStatus.ACTIVE))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
