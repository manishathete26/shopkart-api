from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterAddress(BaseModel):
    street: str = Field(min_length=2, max_length=255)
    city: str = Field(min_length=2, max_length=120)
    state: str = Field(min_length=2, max_length=120)

    model_config = ConfigDict(str_strip_whitespace=True)


class EmailRequest(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    full_name: str = Field(alias="fullName", min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    gender: int | None = Field(
        default=None,
        ge=0,
        le=2,
        description="0=male, 1=female, 2=others",
    )
    # Keep accepting the former string form while supporting structured addresses.
    address: RegisterAddress | str
    pin: str = Field(pattern=r"^\d{6}$")

    @field_validator("address", mode="before")
    @classmethod
    def validate_legacy_address(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if len(value) < 5:
                raise ValueError("Address must contain at least 5 characters")
        return value

    @field_validator("gender", mode="before")
    @classmethod
    def empty_gender_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    model_config = {"populate_by_name": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class SendOTPResponse(BaseModel):
    message: str
    expires_in_seconds: int


class VerifyOTPRequest(EmailRequest):
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class CreateProfileRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    gender: int | None = Field(default=None, ge=0, le=2, description="0=male, 1=female, 2=others")


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120, alias="fullName")
    gender: int | None = Field(default=None, ge=0, le=2, description="0=male, 1=female, 2=others")
    phone_number: str | None = Field(
        default=None,
        alias="phoneNumber",
        pattern=r"^\+?[0-9]{7,15}$",
    )

    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)


class UserRead(BaseModel):
    id: int
    full_name: str | None
    email: EmailStr | None
    gender: int | None
    phone_number: str | None
    profile_completed: bool
    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    profile_completed: bool


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
