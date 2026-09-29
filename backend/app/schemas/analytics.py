from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class SalesTotals(BaseModel):
    revenue: Decimal
    order_count: int
    quantity_sold: int
    average_order_amount: Decimal


class SalesDay(BaseModel):
    date: date
    revenue: Decimal
    order_count: int
    quantity_sold: int


class RankedProduct(BaseModel):
    product_id: int
    product_name: str
    quantity_sold: int
    revenue: Decimal


class ProductOption(BaseModel):
    id: int
    name: str


class MerchantDashboard(BaseModel):
    start_date: date
    end_date: date
    timezone: str
    generated_at: datetime
    totals: SalesTotals
    previous_totals: SalesTotals
    daily: list[SalesDay]
    top_products: list[RankedProduct]
    products: list[ProductOption]
    product_id: int | None
