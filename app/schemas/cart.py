from pydantic import AliasChoices, BaseModel, Field


class CartItemCreate(BaseModel):
    parent_id: int = Field(
        gt=0,
        validation_alias=AliasChoices("parentId", "parent_id"),
        serialization_alias="parentId",
    )
    variant_id: str = Field(min_length=1, max_length=255)
    quantity: int = Field(default=1, ge=1, le=99)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=99)
