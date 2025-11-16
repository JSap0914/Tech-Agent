"""
JWT authentication middleware for Tech Spec Agent API.
Validates JWT tokens from ANYON platform.
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, UUID4
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)

# Security scheme
security = HTTPBearer()


# ============= User Model =============

class User(BaseModel):
    """Authenticated user from JWT token."""

    user_id: UUID4
    email: str
    role: str  # admin, user, etc.
    permissions: list[str] = []


# ============= JWT Token Functions =============

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload

    except JWTError as e:
        logger.warning("JWT validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============= Authentication Dependency =============

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> User:
    """
    Dependency to extract and validate current user from JWT token.

    Args:
        credentials: HTTP Authorization header with Bearer token

    Returns:
        User object with user information

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    try:
        # Decode JWT token
        payload = decode_access_token(token)

        # Extract user information
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role", "user")
        permissions: list = payload.get("permissions", [])

        if user_id is None or email is None:
            logger.warning("JWT payload missing required fields")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create User object
        user = User(
            user_id=user_id,
            email=email,
            role=role,
            permissions=permissions
        )

        logger.info("User authenticated", user_id=str(user.user_id), role=user.role)
        return user

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============= Optional Authentication =============

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[User]:
    """
    Optional authentication dependency.
    Returns User if authenticated, None otherwise.

    Args:
        credentials: HTTP Authorization header (optional)

    Returns:
        User object if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ============= Role-Based Access Control =============

class RoleChecker:
    """Dependency for role-based access control."""

    def __init__(self, allowed_roles: list[str]):
        """
        Initialize role checker.

        Args:
            allowed_roles: List of roles allowed to access the endpoint
        """
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        """
        Check if user has required role.

        Args:
            user: Current authenticated user

        Returns:
            User object if authorized

        Raises:
            HTTPException: If user doesn't have required role
        """
        if user.role not in self.allowed_roles:
            logger.warning(
                "Access denied - insufficient permissions",
                user_id=str(user.user_id),
                role=user.role,
                required_roles=self.allowed_roles
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(self.allowed_roles)}"
            )

        return user


# ============= Permission-Based Access Control =============

class PermissionChecker:
    """Dependency for permission-based access control."""

    def __init__(self, required_permission: str):
        """
        Initialize permission checker.

        Args:
            required_permission: Permission required to access the endpoint
        """
        self.required_permission = required_permission

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        """
        Check if user has required permission.

        Args:
            user: Current authenticated user

        Returns:
            User object if authorized

        Raises:
            HTTPException: If user doesn't have required permission
        """
        if self.required_permission not in user.permissions:
            logger.warning(
                "Access denied - missing permission",
                user_id=str(user.user_id),
                permission=self.required_permission
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission: {self.required_permission}"
            )

        return user


# ============= Helper Functions =============

def verify_token_signature(token: str) -> bool:
    """
    Verify JWT token signature without decoding payload.

    Args:
        token: JWT token string

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return True
    except JWTError:
        return False


def extract_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from JWT token without full validation.
    Useful for logging/monitoring.

    Args:
        token: JWT token string

    Returns:
        User ID if present, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False}  # Don't verify expiration for extraction
        )
        return payload.get("sub")
    except JWTError:
        return None


# ============= Predefined Role Checkers =============

# Only admins can access
require_admin = RoleChecker(allowed_roles=["admin"])

# Admins and managers can access
require_admin_or_manager = RoleChecker(allowed_roles=["admin", "manager"])

# Any authenticated user can access (but must be authenticated)
require_authenticated = Depends(get_current_user)
