"""
Authentication module for Tech Spec Agent.

Provides JWT token generation, validation, and user authentication
for both HTTP API endpoints and WebSocket connections.
"""

from .jwt import (
    create_access_token,
    decode_access_token,
    get_current_user_from_ws_token,
    get_current_user_from_header,
    TokenData,
    User
)

__all__ = [
    "create_access_token",
    "decode_access_token",
    "get_current_user_from_ws_token",
    "get_current_user_from_header",
    "TokenData",
    "User"
]
