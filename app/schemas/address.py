from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AddressCreate(BaseModel):
    address: str | None = Field(default=None, min_length=5, max_length=500)
    street: str | None = Field(default=None, min_length=2, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=120)
    pin: str | None = Field(default=None, pattern=r"^\d{6}$")
    label: str | None = Field(default=None, max_length=50)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def require_address(self):
        if self.address is None and not all((self.street, self.city, self.state)):
            raise ValueError("Provide address or all of street, city, and state")
        return self


class AddressUpdate(BaseModel):
    address: str | None = Field(default=None, min_length=5, max_length=500)
    street: str | None = Field(default=None, min_length=2, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=120)
    pin: str | None = Field(default=None, pattern=r"^\d{6}$")
    label: str | None = Field(default=None, max_length=50)

    model_config = ConfigDict(str_strip_whitespace=True)


class AddressRead(BaseModel):
    id: int
    label: str | None
    address: str
    street: str | None
    city: str | None
    state: str | None
    pin: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
