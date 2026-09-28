import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from ..core.security import ALGORITHM, SECRET_KEY
from ..db.session import get_db
from ..models.auth import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/verify-otp")


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
