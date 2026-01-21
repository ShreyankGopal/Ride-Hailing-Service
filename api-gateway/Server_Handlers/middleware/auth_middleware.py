from functools import wraps
from typing import Callable, Optional, Tuple, Dict, Any

import os

import flask
import jwt

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


def get_current_user_from_request(request: flask.Request) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Extract and validate the JWT token from the incoming request.

    The token is expected to be present in the `access_token` cookie.
    """
    token = request.cookies.get("access_token")
    if not token:
        return False, None, "Missing access token"

    return _decode_token(token)


def auth_required(fn: Callable) -> Callable:
    """Decorator to protect routes that require authentication.

    Usage example in a route (in app.py):

        @app.route("/protected", methods=["GET"])
        @auth_required
        def protected_endpoint():
            user = flask.g.current_user
            return flask.jsonify({"message": "ok", "user": user})
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        is_valid, payload, error = get_current_user_from_request(flask.request)
        if not is_valid or payload is None:
            return flask.jsonify({"error": error or "Unauthorized"}), 401

        # Attach the user payload to flask.g for downstream use.
        flask.g.current_user = payload
        return fn(*args, **kwargs)

    return wrapper
