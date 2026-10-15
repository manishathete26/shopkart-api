from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class OrderItemRead(BaseModel):
    id: int
    product_id: int | None
    product_name: str
    variant_id: str
    variant: dict[str, Any]
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderRead(BaseModel):
    id: int
    status: str
    total_amount: Decimal
    shipping_address: str | None
    shipping_pin: str | None
    created_at: datetime
    items: list[OrderItemRead]


class OrderHistoryRead(BaseModel):
    count: int
    page: int
    page_size: int = Field(serialization_alias="pageSize")
    total_pages: int = Field(serialization_alias="totalPages")
    orders: list[OrderRead]

    model_config = {"populate_by_name": True}
