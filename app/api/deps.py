import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from ..core.security import ALGORITHM, SECRET_KEY
from ..db.session import get_db
from ..models.auth import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _user_from_credentials(credentials, db)


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Return the authenticated user when a valid bearer token is provided."""
    if credentials is None:
        return None

    return _user_from_credentials(credentials, db)


def _user_from_credentials(
    credentials: HTTPAuthorizationCredentials,
    db: Session,
) -> User:
    token = credentials.credentials

    try:
        claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if claims.get("type") != "access":
            raise InvalidTokenError

        user_id = int(claims["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
