from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import MerchantStatus, StoreStatus


class MerchantApplicationCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=120)


class MerchantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    business_name: str
    status: MerchantStatus
    approved_at: datetime | None
    approved_by: int | None
    created_at: datetime


class MerchantStatusUpdate(BaseModel):
    status: MerchantStatus
    reason: str = Field(min_length=3, max_length=255)


class StoreCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name must not be null")
        return self


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: int
    name: str
    description: str | None
    status: StoreStatus
    created_at: datetime
    updated_at: datetime
