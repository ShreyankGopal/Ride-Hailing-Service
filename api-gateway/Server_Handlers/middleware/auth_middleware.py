"""
auth_middleware.py — FastAPI dependency for JWT authentication.

Usage in a route:
    from Server_Handlers.middleware.auth_middleware import get_current_user

    @app.post("/some-route")
    async def some_route(user: dict = Depends(get_current_user)):
        rider_id = user.get("sub")
        ...
"""

import os
from typing import Any, Dict, Optional, Tuple

# pyrefly: ignore [missing-import]
import jwt
# pyrefly: ignore [missing-import]
from fastapi import HTTPException, Request

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"


def _decode_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Decode and validate a JWT token.

    Returns a tuple: (is_valid, payload, error_message)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True, payload, None
    except jwt.ExpiredSignatureError:
        return False, None, "Token has expired"
    except jwt.InvalidTokenError:
        return False, None, "Invalid token"


async def get_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI dependency that extracts and validates the JWT from the
    ``access_token`` HTTP-only cookie.

    Raises ``HTTPException(401)`` when the token is missing or invalid so
    FastAPI returns a proper JSON error response automatically.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing access token")

    is_valid, payload, error = _decode_token(token)
    if not is_valid or payload is None:
        raise HTTPException(status_code=401, detail=error or "Unauthorized")

    return payload
