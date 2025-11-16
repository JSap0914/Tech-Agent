"""
JWT authentication helpers for WebSocket and API endpoints.

Provides token generation, validation, and user extraction for secure WebSocket connections.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Query
from pydantic import BaseModel
import structlog

from src.config import settings

logger = structlog.get_logger()


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: str
    email: Optional[str] = None
    exp: Optional[datetime] = None


class User(BaseModel):
    """User model for authentication."""
    id: str
    email: str
    is_active: bool = True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Payload data to encode (must include 'sub' with user_id)
        expires_delta: Token expiration time (default: 24 hours)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm="HS256"
    )

    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate JWT access token.

    Args:
        token: JWT token string

    Returns:
        TokenData with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"]
        )

        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("jwt_decode_failed", reason="missing_subject")
            raise credentials_exception

        token_data = TokenData(
            user_id=user_id,
            email=payload.get("email"),
            exp=payload.get("exp")
        )

        logger.debug("jwt_decoded_successfully", user_id=user_id)
        return token_data

    except JWTError as e:
        logger.warning("jwt_decode_error", error=str(e))
        raise credentials_exception


async def get_current_user_from_ws_token(token: str) -> User:
    """
    Extract and validate user from WebSocket JWT token.

    Args:
        token: JWT token from WebSocket query parameter

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found

    Usage:
        @router.websocket("/ws/{session_id}")
        async def endpoint(websocket: WebSocket, token: str = Query(...)):
            user = await get_current_user_from_ws_token(token)
            ...
    """
    token_data = decode_access_token(token)

    # In a real application, you would fetch user from database here
    # For now, we create a User object from token data
    user = User(
        id=token_data.user_id,
        email=token_data.email or f"{token_data.user_id}@example.com",
        is_active=True
    )

    logger.info("websocket_user_authenticated", user_id=user.id)
    return user


async def get_current_user_from_header(authorization: str) -> User:
    """
    Extract and validate user from Authorization header.

    Args:
        authorization: Authorization header value ("Bearer {token}")

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid

    Usage:
        @router.get("/api/endpoint")
        async def endpoint(authorization: str = Header(...)):
            user = await get_current_user_from_header(authorization)
            ...
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )

    token = authorization.replace("Bearer ", "")
    token_data = decode_access_token(token)

    user = User(
        id=token_data.user_id,
        email=token_data.email or f"{token_data.user_id}@example.com",
        is_active=True
    )

    return user
