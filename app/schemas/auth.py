from pydantic import BaseModel, EmailStr, Field


class EmailRequest(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    full_name: str = Field(alias="fullName", min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    gender: int = Field(ge=0, le=2, description="0=male, 1=female, 2=others")
    address: str = Field(min_length=5, max_length=500)
    pin: str = Field(pattern=r"^\d{6}$")

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


class UserRead(BaseModel):
    id: int
    full_name: str | None
    email: EmailStr | None
    gender: int | None
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
