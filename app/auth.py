"""MongoDB-backed user authentication and JWT helpers."""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo import MongoClient

from .config import Settings
from .services import get_settings_dep

_bearer = HTTPBearer(auto_error=False)


def _users_collection(settings: Settings):
    client = MongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    col = db["users"]
    col.create_index("email", unique=True)
    return col


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    _, expected = _hash_password(password, salt=salt)
    return hmac.compare_digest(expected, digest_hex)


def create_user(settings: Settings, email: str, password: str) -> dict[str, Any]:
    users = _users_collection(settings)
    normalized = email.strip().lower()
    user = users.find_one({"email": normalized})
    if user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )
    salt_hex, digest_hex = _hash_password(password)
    users.insert_one(
        {
            "email": normalized,
            "password_salt": salt_hex,
            "password_hash": digest_hex,
            "created_at": datetime.now(timezone.utc),
            "last_login_at": datetime.now(timezone.utc),
        }
    )
    user = users.find_one({"email": normalized})
    if user is None:
        raise HTTPException(status_code=500, detail="Failed to create user")
    return user


def authenticate_user(settings: Settings, email: str, password: str) -> dict[str, Any]:
    users = _users_collection(settings)
    normalized = email.strip().lower()
    user = users.find_one({"email": normalized})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
        )
    if not _verify_password(password, str(user["password_salt"]), str(user["password_hash"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
        )
    users.update_one({"_id": user["_id"]}, {"$set": {"last_login_at": datetime.now(timezone.utc)}})
    return user


def create_access_token(settings: Settings, user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_exp_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings_dep),
) -> dict[str, str]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing 'Authorization: Bearer <token>' header.",
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    user_id = str(payload.get("sub", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    if not user_id or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return {"user_id": user_id, "email": email}
