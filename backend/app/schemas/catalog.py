from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import CategoryStatus, ProductStatus


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)
    parent_id: int | None = Field(default=None, gt=0)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None
    name: str
    slug: str
    status: CategoryStatus


class ProductCreate(BaseModel):
    category_id: int = Field(gt=0)
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    current_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip().upper()


class ProductUpdate(BaseModel):
    category_id: int | None = Field(default=None, gt=0)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        for field in ("category_id", "sku", "name"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} must not be null")
        return self


class ProductStatusUpdate(BaseModel):
    status: ProductStatus


class PriceChangeRequest(BaseModel):
    new_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class InventoryRestockRequest(BaseModel):
    quantity: int = Field(gt=0, le=1_000_000)
    reason: str | None = Field(default=None, max_length=255)


class InventoryAdjustRequest(BaseModel):
    quantity_change: int = Field(ge=-1_000_000, le=1_000_000)
    reason: str = Field(min_length=3, max_length=255)

    @field_validator("quantity_change")
    @classmethod
    def nonzero_change(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity_change must not be zero")
        return value


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    category_id: int
    sku: str
    name: str
    description: str | None
    current_price: Decimal
    status: ProductStatus
    inventory_quantity: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class PriceHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    old_price: Decimal
    new_price: Decimal
    changed_by: int
    changed_at: datetime


class InventoryResponse(BaseModel):
    product_id: int
    quantity: int
    version: int
    updated_at: datetime


class InventoryTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    type: str
    quantity_change: int
    quantity_before: int
    quantity_after: int
    reason: str | None
    created_by: int | None
    created_at: datetime
