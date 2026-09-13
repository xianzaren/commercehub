from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.engagement import Favorite, ProductView, SearchHistory


class EngagementRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def favorite_ids(self, user_id: int) -> list[int]:
        statement = (
            select(Favorite.product_id)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc(), Favorite.id.desc())
        )
        return list(self.session.scalars(statement))

    def is_favorite(self, user_id: int, product_id: int) -> bool:
        statement = select(Favorite.id).where(
            Favorite.user_id == user_id,
            Favorite.product_id == product_id,
        )
        return self.session.scalar(statement) is not None

    def add_favorite(self, user_id: int, product_id: int) -> None:
        if not self.is_favorite(user_id, product_id):
            self.session.add(Favorite(user_id=user_id, product_id=product_id))

    def delete_favorite(self, user_id: int, product_id: int) -> None:
        self.session.execute(
            delete(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.product_id == product_id,
            )
        )

    def viewed_product_ids(self, user_id: int, *, limit: int = 30) -> list[int]:
        statement = (
            select(ProductView.product_id)
            .where(ProductView.user_id == user_id)
            .order_by(ProductView.updated_at.desc(), ProductView.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def record_view(self, user_id: int, product_id: int) -> None:
        statement = select(ProductView).where(
            ProductView.user_id == user_id,
            ProductView.product_id == product_id,
        )
        view = self.session.scalar(statement)
        if view is None:
            self.session.add(ProductView(user_id=user_id, product_id=product_id, view_count=1))
        else:
            view.view_count += 1

    def record_search(self, user_id: int, keyword: str, result_count: int) -> None:
        normalized = keyword.strip().lower()
        if not normalized:
            return
        statement = select(SearchHistory).where(
            SearchHistory.user_id == user_id,
            SearchHistory.normalized_keyword == normalized,
        )
        history = self.session.scalar(statement)
        if history is None:
            self.session.add(
                SearchHistory(
                    user_id=user_id,
                    keyword=keyword.strip(),
                    normalized_keyword=normalized,
                    result_count=result_count,
                    search_count=1,
                )
            )
        else:
            history.keyword = keyword.strip()
            history.result_count = result_count
            history.search_count += 1
