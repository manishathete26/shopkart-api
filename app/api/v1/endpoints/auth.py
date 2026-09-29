import logging
from datetime import timedelta, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_mail import FastMail, MessageSchema, MessageType
from jwt import InvalidTokenError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ....core.security import (
    ALGORITHM,
    OTP_EXPIRE_MINUTES,
    SECRET_KEY,
    create_access_token,
    create_otp,
    create_refresh_token,
    hash_otp,
    utc_now,
)
from ....db.session import get_db
from ....models.auth import OTPCode, RefreshSession, User
from ....schemas.auth import (
    CreateProfileRequest,
    EmailRequest,
    LogoutRequest,
    RefreshTokenRequest,
    SendOTPResponse,
    TokenPair,
    UserRead,
    VerifyOTPRequest,
)
from ....services.email import get_mail_config
from ...deps import get_current_user

router = APIRouter(prefix="/auth")

logger = logging.getLogger(__name__)


@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(
    payload: EmailRequest,
    db: Session = Depends(get_db),
):
    email = str(payload.email).strip().lower()

    mail_config = get_mail_config()
    otp = create_otp()

    db.execute(
        update(OTPCode)
        .where(
            OTPCode.email == email,
            OTPCode.is_used.is_(False),
        )
        .values(is_used=True)
    )

    otp_record = OTPCode(
        email=email,
        code_hash=hash_otp(email, otp),
        expires_at=utc_now() + timedelta(minutes=OTP_EXPIRE_MINUTES),
    )
    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)

    message = MessageSchema(
        recipients=[email],
        subject="ShopKart Verification OTP",
        body=(
            "<p>Your ShopKart verification OTP is:</p>"
            f"<h2>{otp}</h2>"
            f"<p>This OTP expires in {OTP_EXPIRE_MINUTES} minutes.</p>"
            "<p>Do not share this OTP with anyone.</p>"
        ),
        subtype=MessageType.html,
    )

    try:
        await FastMail(mail_config).send_message(message)
    except Exception as error:
        logger.exception("OTP email send failed for %s", email)

        otp_record.is_used = True
        db.commit()

        raise HTTPException(
            status_code=502,
            detail="OTP email could not be sent. Please try again.",
        ) from error

    return SendOTPResponse(
        message="OTP sent successfully to your email",
        expires_in_seconds=OTP_EXPIRE_MINUTES * 60,
    )


@router.post("/verify-otp", response_model=TokenPair)
def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()

    otp_record = db.scalar(
        select(OTPCode)
        .where(
            OTPCode.email == email,
            OTPCode.is_used.is_(False),
        )
        .order_by(OTPCode.id.desc())
    )

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="OTP is invalid or expired",
        )

    # SQLite may return this datetime without timezone information.
    expires_at = otp_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= utc_now():
        raise HTTPException(
            status_code=400,
            detail="OTP is invalid or expired",
        )

    if otp_record.attempts >= 5:
        raise HTTPException(
            status_code=429,
            detail="Too many OTP attempts",
        )

    if otp_record.code_hash != hash_otp(email, payload.otp):
        otp_record.attempts += 1
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP",
        )

    otp_record.is_used = True

    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email)
        db.add(user)

    db.commit()
    db.refresh(user)

    return token_pair_for(user, db)


@router.post("/create-profile", response_model=UserRead)
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


@router.post("/refresh", response_model=TokenPair)
def refresh_token(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    try:
        claims = jwt.decode(
            payload.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        if claims.get("type") != "refresh":
            raise InvalidTokenError

        user_id = int(claims["sub"])
        token_id = claims["jti"]

    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
        )

    session = db.scalar(
        select(RefreshSession).where(RefreshSession.token_id == token_id)
    )

    if not session or session.is_revoked:
        raise HTTPException(
            status_code=401,
            detail="Refresh token is expired or revoked",
        )

    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= utc_now():
        raise HTTPException(
            status_code=401,
            detail="Refresh token is expired or revoked",
        )

    # These lines are outside the expiry check.
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User is unavailable",
        )

    session.is_revoked = True
    db.commit()

    return token_pair_for(user, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
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


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

def token_pair_for(user: User, db: Session) -> TokenPair:
    refresh_token, token_id, expires_at = create_refresh_token(user.id)

    db.add(
        RefreshSession(
            user_id=user.id,
            token_id=token_id,
            expires_at=expires_at,
        )
    )
    db.commit()

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=refresh_token,
        profile_completed=user.profile_completed,
    )
