from pydantic import BaseModel, Field


class WishlistAddRequest(BaseModel):
    product_id: int = Field(gt=0)
