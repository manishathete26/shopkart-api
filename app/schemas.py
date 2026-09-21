from pydantic import BaseModel, EmailStr, Field, field_validator


class MobileNumberRequest(BaseModel):
    mobile_number: str = Field(description="E.164 number, e.g. +919876543210")

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, value: str) -> str:
        normalized = value.replace(" ", "").replace("-", "")
        if not normalized.startswith("+") or not normalized[1:].isdigit() or not 8 <= len(normalized[1:]) <= 15:
            raise ValueError("mobile_number must be a valid E.164 number")
        return normalized


class SendOTPResponse(BaseModel):
    message: str
    expires_in_seconds: int
    development_otp: str | None = None


class VerifyOTPRequest(MobileNumberRequest):
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class CreateProfileRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    gender: str | None = Field(default=None, pattern="^(male|female|other)$")


class UserRead(BaseModel):
    id: int
    mobile_number: str
    full_name: str | None
    email: EmailStr | None
    gender: str | None
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
