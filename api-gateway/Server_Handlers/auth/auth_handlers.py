import os
import datetime
import hashlib
from typing import Any, Dict

import flask
import jwt

from Server_Handlers.db_user_repository import create_user

# Secret and JWT configuration. In production, configure JWT_SECRET_KEY
# as an environment variable and keep it private.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60  # 1 hour


def _create_access_token(payload: Dict[str, Any], expires_in_seconds: int) -> str:
    """Create a signed JWT access token with an expiration time.

    Args:
        payload: Base payload data to embed in the token.
        expires_in_seconds: Lifetime of the token in seconds.

    Returns:
        Encoded JWT string.
    """
    to_encode = payload.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        seconds=expires_in_seconds
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _set_auth_cookie(response: flask.Response, token: str) -> None:
    """Attach the JWT as an HTTP-only cookie on the response.

    The cookie is configured for a 1 hour lifetime.
    """
    response.set_cookie(
        "access_token",
        token,
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        secure=False,  # Set to True when serving strictly over HTTPS.
        samesite="Lax",
        path="/",
    )


def signup_handler() -> flask.Response:
    """Handle user signup.

    Expected JSON body fields:
        - name
        - phone
        - role
        - password

    This function should contain all business logic related to
    user registration. At the moment it only demonstrates the flow
    and JWT cookie creation. You can plug in your gRPC / DB logic here.
    """
    print("Signup handler called")
    data = flask.request.get_json() or {}
    name = data.get("name")
    phone = data.get("phone")
    role = data.get("role")
    password = data.get("password")

    # Validate input presence before touching the database.
    if not all([name, phone, role, password]):
        return flask.jsonify({"error": "Missing required fields"}), 400

    # Hash the password before persisting it. For a production system,
    # consider using a stronger hashing algorithm such as bcrypt or argon2.
    # Here we use SHA-256 as a minimal example.
    password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

    # Persist the new user in the PostgreSQL database.
    user_id = create_user(name=name, phone=phone, role=role, password=password_hash)
    if user_id is None:
        return flask.jsonify({"error": "Failed to create user"}), 500

    token_payload = {
        "sub": str(user_id),
        "role": role,
    }
    token = _create_access_token(token_payload, ACCESS_TOKEN_EXPIRE_SECONDS)

    response_body = {
        "message": "Signup successful",
        "user_id": user_id,
        "role": role,
    }
    response = flask.jsonify(response_body)
    _set_auth_cookie(response, token)
    return response


def login_handler() -> flask.Response:
    """Handle user login.

    Expected JSON body fields:
        - phone
        - password

    This function should contain all business logic related to
    user authentication. At the moment it only demonstrates the flow
    and JWT cookie creation. You can plug in your gRPC / DB logic here.
    """
    print("Login handler called")
    data = flask.request.get_json() or {}
    phone = data.get("phone")
    password = data.get("password")

    if not all([phone, password]):
        return flask.jsonify({"error": "Missing phone or password"}), 400

    # TODO: Insert actual login validation here
    # Example (pseudo):
    # auth_result = ClientCalls.UserReg.login(phone, password)
    # if not auth_result.success:
    #     return flask.jsonify({"error": "Invalid credentials"}), 401

    # Assuming authentication is successful, determine user_id and role.
    user_id = phone
    role = "rider"  # TODO: derive actual role from auth_result.

    token_payload = {
        "sub": user_id,
        "role": role,
    }
    token = _create_access_token(token_payload, ACCESS_TOKEN_EXPIRE_SECONDS)

    response_body = {
        "message": "Login successful",
        "user_id": user_id,
        "role": role,
    }
    response = flask.jsonify(response_body)
    _set_auth_cookie(response, token)
    return response
