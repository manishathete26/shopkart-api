from pydantic import BaseModel, Field


class WishlistAddRequest(BaseModel):
    product_id: int = Field(gt=0)
    variant_id: str = Field(min_length=1, max_length=255)
