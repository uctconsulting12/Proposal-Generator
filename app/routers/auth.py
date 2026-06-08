"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import authenticate_user, create_access_token, create_user, require_user
from ..config import Settings
from ..schemas import LoginRequest, LoginResponse, MeResponse
from ..services import get_settings_dep

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=LoginResponse)
def signup(payload: LoginRequest, settings: Settings = Depends(get_settings_dep)) -> LoginResponse:
    """Create a new user profile."""
    user = create_user(settings, payload.email, payload.password)
    user_id = str(user["_id"])
    token = create_access_token(settings, user_id=user_id, email=payload.email)
    return LoginResponse(access_token=token, user_id=user_id, email=payload.email)


@router.post("/signin", response_model=LoginResponse)
def signin(payload: LoginRequest, settings: Settings = Depends(get_settings_dep)) -> LoginResponse:
    """Sign in an existing user profile."""
    user = authenticate_user(settings, payload.email, payload.password)
    user_id = str(user["_id"])
    token = create_access_token(settings, user_id=user_id, email=payload.email)
    return LoginResponse(access_token=token, user_id=user_id, email=payload.email)


@router.get("/me", response_model=MeResponse)
def me(user: dict[str, str] = Depends(require_user)) -> MeResponse:
    """Return token identity details."""
    return MeResponse(user_id=user["user_id"], email=user["email"])
