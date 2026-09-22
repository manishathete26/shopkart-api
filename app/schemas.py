from pydantic import BaseModel, EmailStr, Field


class EmailRequest(BaseModel):
    email: EmailStr


class SendOTPResponse(BaseModel):
    message: str
    expires_in_seconds: int

class VerifyOTPRequest(EmailRequest):
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class CreateProfileRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    gender: str | None = Field(default=None, pattern="^(male|female|other)$")


class UserRead(BaseModel):
    id: int
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
