import logging
import os
from datetime import timedelta
import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import OTPCode, RefreshSession, User
from .schemas import (
    CreateProfileRequest,
    EmailRequest,
    LogoutRequest,
    RefreshTokenRequest,
    SendOTPResponse,
    TokenPair,
    UserRead,
    VerifyOTPRequest,
)
from .security import (
    ALGORITHM,
    OTP_EXPIRE_MINUTES,
    SECRET_KEY,
    create_access_token,
    create_otp,
    create_refresh_token,
    hash_otp,
    utc_now,
)

load_dotenv()

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)
app = FastAPI(title="ShopKart Authentication API", version="1.0.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/verify-otp")


def get_mail_config() -> ConnectionConfig:
    """Build Gmail SMTP configuration from environment variables."""
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    from_email = os.getenv("MAIL_FROM")
    server = os.getenv("MAIL_SERVER")
    port = os.getenv("MAIL_PORT")

    if not all((username, password, from_email, server, port)):
        raise HTTPException(status_code=500, detail="Email service is not configured.")

    try:
        mail_port = int(port)
    except ValueError as error:
        raise HTTPException(status_code=500, detail="Email service is not configured.") from error

    return ConnectionConfig(
        MAIL_USERNAME=username,
        MAIL_PASSWORD=password,
        MAIL_FROM=from_email,
        MAIL_PORT=mail_port,
        MAIL_SERVER=server,
        MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "true").lower() == "true",
        MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "false").lower() == "true",
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


def token_pair_for(user: User, db: Session) -> TokenPair:
    refresh_token, token_id, expires_at = create_refresh_token(user.id)
    db.add(RefreshSession(user_id=user.id, token_id=token_id, expires_at=expires_at))
    db.commit()
    return TokenPair(access_token=create_access_token(user.id), refresh_token=refresh_token, profile_completed=user.profile_completed)


@app.post("/auth/send-otp", response_model=SendOTPResponse)
async def send_otp(payload: EmailRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    otp = create_otp()
    mail_config = get_mail_config()
    db.execute(
        update(OTPCode)
        .where(OTPCode.email == email, OTPCode.is_used.is_(False))
        .values(is_used=True)
    )

    otp_record = OTPCode(
        email=email,
        code_hash=hash_otp(email, otp),
        expires_at=utc_now() + timedelta(minutes=OTP_EXPIRE_MINUTES),
    )
    db.add(otp_record)
    db.commit()

    try:
        message = MessageSchema(
            recipients=[email],
            subject="ShopKart Verification OTP",
            body=f"""
                <p>Your ShopKart verification OTP is:</p>
                <h2>{otp}</h2>
                <p>This OTP expires in {OTP_EXPIRE_MINUTES} minutes.</p>
                <p>Do not share this OTP with anyone.</p>
            """,
            subtype=MessageType.html,
        )
        await FastMail(mail_config).send_message(message)
    except Exception:
        logger.exception("OTP email send failed for %s", email)

        # Email send fail झाल्यास OTP invalid करा
        otp_record.is_used = True
        db.commit()

        raise HTTPException(
            status_code=500,
            detail="OTP email could not be sent. Please try again.",
        )

    return SendOTPResponse(
        message="OTP sent successfully to your email",
        expires_in_seconds=OTP_EXPIRE_MINUTES * 60,
    )


@app.post("/auth/verify-otp", response_model=TokenPair)
def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()

    otp_record = db.scalar(
        select(OTPCode)
        .where(OTPCode.email == email, OTPCode.is_used.is_(False))
        .order_by(OTPCode.id.desc())
    )

    if not otp_record or otp_record.expires_at < utc_now():
        raise HTTPException(status_code=400, detail="OTP is invalid or expired")

    if otp_record.attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many OTP attempts")

    if otp_record.code_hash != hash_otp(email, payload.otp):
        otp_record.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp_record.is_used = True

    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email)
        db.add(user)

    db.commit()
    db.refresh(user)

    return token_pair_for(user, db)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    error = HTTPException(status_code=401, detail="Invalid access token", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if claims.get("type") != "access":
            raise error
        user_id = int(claims["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise error
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise error
    return user


@app.post("/auth/create-profile", response_model=UserRead)
def create_profile(
    payload: CreateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.full_name = payload.full_name
    current_user.gender = payload.gender
    current_user.profile_completed = True

    db.commit()
    db.refresh(current_user)

    return current_user


@app.post("/auth/refresh", response_model=TokenPair)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        claims = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if claims.get("type") != "refresh":
            raise InvalidTokenError
        user_id, token_id = int(claims["sub"]), claims["jti"]
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_id == token_id))
    if not session or session.is_revoked or session.expires_at < utc_now():
        raise HTTPException(status_code=401, detail="Refresh token is expired or revoked")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is unavailable")
    session.is_revoked = True
    db.commit()
    return token_pair_for(user, db)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    try:
        claims = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if claims.get("type") != "refresh":
            raise InvalidTokenError
        token_id = claims["jti"]
    except (InvalidTokenError, KeyError):
        raise HTTPException(status_code=400, detail="Invalid refresh token")
    session = db.scalar(select(RefreshSession).where(RefreshSession.token_id == token_id))
    if session:
        session.is_revoked = True
        db.commit()


@app.get("/auth/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
