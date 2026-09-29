from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.models.user import Merchant
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.merchant_repository import StoreRepository

BEIJING = timezone(timedelta(hours=8))


def total_days(rows):
    revenue = sum((row["revenue"] for row in rows), Decimal("0.00"))
    count = sum(row["order_count"] for row in rows)
    return {
        "revenue": revenue,
        "order_count": count,
        "quantity_sold": sum(row["quantity_sold"] for row in rows),
        "average_order_amount": (revenue / count if count else Decimal(0)).quantize(Decimal(".01")),
    }


class AnalyticsService:
    def __init__(self, session: Session):
        self.repository = AnalyticsRepository(session)
        self.stores = StoreRepository(session)

    def dashboard(
        self, merchant: Merchant, days: int, end_date: date | None, product_id: int | None
    ):
        now = datetime.now(UTC)
        today = now.astimezone(BEIJING).date()
        end_date = end_date or today
        if end_date > today or end_date < date(2000, 1, 1) or not 1 <= days <= 90:
            raise BusinessError(
                "INVALID_ANALYTICS_RANGE", "请选择有效日期和 1 至 90 天的区间", status_code=422
            )
        store = self.stores.get_by_merchant_id(merchant.id)
        if store is None:
            raise BusinessError("STORE_NOT_FOUND", "店铺不存在", status_code=404)
        products = [{"id": row.id, "name": row.name} for row in self.repository.products(store.id)]
        if product_id is not None and not any(p["id"] == product_id for p in products):
            raise BusinessError("PRODUCT_NOT_FOUND", "商品不存在", status_code=404)
        start_date = end_date - timedelta(days=days - 1)
        start = datetime.combine(start_date, datetime.min.time()) - timedelta(hours=8)
        end = start + timedelta(days=days)

        def period(period_start, period_end):
            orders, items, ranking = self.repository.aggregate(
                store.id,
                period_start,
                period_end,
                product_id,
            )
            by_day = {str(row["day"]): row for row in (items if product_id else orders)}
            quantities = {str(row["day"]): row["quantity_sold"] for row in items}
            first_day = (period_start + timedelta(hours=8)).date()
            daily = []
            for index in range(days):
                day = first_day + timedelta(days=index)
                row = by_day.get(str(day), {})
                daily.append(
                    {
                        "date": day,
                        "revenue": Decimal(str(row.get("revenue", 0))),
                        "order_count": int(row.get("order_count", 0)),
                        "quantity_sold": int(quantities.get(str(day), 0)),
                    }
                )
            return daily, ranking

        daily, ranking = period(start, end)
        previous, _ = period(start - timedelta(days=days), start)
        return {
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "Asia/Shanghai",
            "generated_at": now,
            "product_id": product_id,
            "products": products,
            "daily": daily,
            "totals": total_days(daily),
            "previous_totals": total_days(previous),
            "top_products": [dict(row) for row in ranking],
        }
