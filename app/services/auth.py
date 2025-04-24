import jwt
from datetime import datetime, timedelta, timezone
from config import get_jwt_token_cred
from datetime import datetime, timezone
from typing import Any, Dict
import jwt
from jwt import PyJWTError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from typing import Annotated
from app.db.crud import get_user_by_email
from app.db.schemas import TokenData, UserOut
from app.db import database
from jwt.exceptions import InvalidTokenError




JWT_CRED = get_jwt_token_cred()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="log_in")


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token.

    Args:
        data (dict): The payload to encode in the token. Typically includes user identifier.
        expires_delta (timedelta, optional): Token expiration duration. Defaults to 15 minutes.

    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_CRED.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, JWT_CRED.SECRET_KEY, algorithm=JWT_CRED.ALGORITHM)
    return encoded_jwt



def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            JWT_CRED.SECRET_KEY,
            algorithms=[JWT_CRED.ALGORITHM],
        )
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        return payload
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token",
        )



async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
     db: Session = Depends(database.get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception

    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user



async def get_current_active_user(
    current_user: Annotated[UserOut, Depends(get_current_user)],
):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user