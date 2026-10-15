from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AddressCreate(BaseModel):
    address: str = Field(min_length=5, max_length=500)
    pin: str | None = Field(default=None, pattern=r"^\d{6}$")
    label: str | None = Field(default=None, max_length=50)


class AddressUpdate(BaseModel):
    address: str | None = Field(default=None, min_length=5, max_length=500)
    pin: str | None = Field(default=None, pattern=r"^\d{6}$")
    label: str | None = Field(default=None, max_length=50)


class AddressRead(BaseModel):
    id: int
    label: str | None
    address: str
    pin: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
