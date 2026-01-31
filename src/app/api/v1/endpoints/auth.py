from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.auth_schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.rate_limiter import RateLimiter
from app.services.token_service import (
    blacklist_refresh_token,
    extract_user_id_from_payload,
    generate_password_reset_token,
    generate_token_pair,
    is_token_blacklisted,
    validate_and_decode_token,
)
from app.services.user_auth_service import (
    authenticate_user_credentials,
    create_user_account,
    get_user_by_id,
    mark_email_verified,
    update_user_password,
)

router = APIRouter()

rate_limiter = RateLimiter(
    max_attempts=5,
    window_seconds=900,
    key_prefix="auth:login:"
)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    return await create_user_account(request, db)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    await rate_limiter.check_rate_limit(request.email)
    user = await authenticate_user_credentials(request.email, request.password, db)
    return await generate_token_pair(user.id, user.email)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    from app.core.exceptions import InvalidToken

    if await is_token_blacklisted(request.refresh_token):
        raise InvalidToken()

    payload = validate_and_decode_token(request.refresh_token, "refresh")
    user_id = extract_user_id_from_payload(payload)

    user = await get_user_by_id(user_id, db)
    if not user or not user.is_active:
        raise InvalidToken()

    await blacklist_refresh_token(request.refresh_token)
    return await generate_token_pair(user.id, user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(
    refresh_token: str,
    current_user: Annotated[User, Depends(get_current_user)]
) -> Response:
    await blacklist_refresh_token(refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify-email", response_model=UserResponse)
async def verify_email(
    request: VerifyEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    payload = validate_and_decode_token(request.token, "email_verification")
    user_id = extract_user_id_from_payload(payload)
    return await mark_email_verified(user_id, db)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, str]:
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user:
        generate_password_reset_token(user.id)

    return {"message": "If email exists, password reset link has been sent"}


@router.post("/reset-password", response_model=UserResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    payload = validate_and_decode_token(request.token, "password_reset")
    user_id = extract_user_id_from_payload(payload)
    return await update_user_password(user_id, request.new_password, db)
