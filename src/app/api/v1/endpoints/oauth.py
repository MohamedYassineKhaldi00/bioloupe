from __future__ import annotations

import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.core.config import get_settings
from app.core.exceptions import InvalidOAuthState, InvalidRequest
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.db.base import get_db
from app.models.user import User
from app.schemas.oauth_schemas import (
    OAuthAuthorizationResponse,
    OAuthLoginResponse,
    OAuthLinkResponse,
)
from app.services import oauth_service, oauth_state_service

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/{provider}/authorize", response_model=OAuthAuthorizationResponse)
async def get_authorization_url(
    provider: str = Path(..., pattern="^(google|microsoft|orcid)$")
) -> OAuthAuthorizationResponse:
    settings = get_settings()
    state = await oauth_state_service.generate_oauth_state()
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/oauth/{provider}/callback"

    auth_url = oauth_service.get_authorization_url(provider, redirect_uri, state)
    return OAuthAuthorizationResponse(authorization_url=auth_url)


async def _create_user_from_oauth(
    db: AsyncSession, user_info: oauth_service.OAuthUserInfo
) -> User:
    user = User(
        email=user_info.email,
        full_name=user_info.full_name,
        hashed_password=hash_password(str(uuid.uuid4())),
        is_verified=True,
        is_active=True,
        orcid_id=user_info.orcid_id,
    )
    db.add(user)
    await db.flush()

    await oauth_service.link_oauth_account(
        db,
        user.id,
        user_info.provider,
        user_info.provider_user_id,
        user_info.email,
    )
    await db.commit()
    await db.refresh(user)
    return user


async def _handle_oauth_login(
    db: AsyncSession, user_info: oauth_service.OAuthUserInfo
) -> OAuthLoginResponse:
    user = await oauth_service.find_user_by_oauth(
        db, user_info.provider, user_info.provider_user_id
    )

    if not user:
        user = await oauth_service.find_user_by_email(db, user_info.email)
        if user:
            await oauth_service.link_oauth_account(
                db,
                user.id,
                user_info.provider,
                user_info.provider_user_id,
                user_info.email,
            )
            await db.commit()
        else:
            user = await _create_user_from_oauth(db, user_info)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    access_token = create_access_token(str(user.id), user.email)
    refresh_token = create_refresh_token(str(user.id))

    return OAuthLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        email=user.email,
    )


@router.get("/{provider}/callback", response_model=OAuthLoginResponse)
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> OAuthLoginResponse:
    if not await oauth_state_service.validate_oauth_state(state):
        raise InvalidOAuthState()

    settings = get_settings()
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/oauth/{provider}/callback"

    token = await oauth_service.exchange_code_for_token(provider, code, redirect_uri)
    user_info = await oauth_service.get_user_info(provider, token.access_token)

    return await _handle_oauth_login(db, user_info)


@router.post("/{provider}/link", response_model=OAuthLinkResponse)
async def link_oauth_account(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> OAuthLinkResponse:
    if not await oauth_state_service.validate_oauth_state(state):
        raise InvalidOAuthState()

    settings = get_settings()
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/oauth/{provider}/callback"

    token = await oauth_service.exchange_code_for_token(provider, code, redirect_uri)
    user_info = await oauth_service.get_user_info(provider, token.access_token)

    existing_user = await oauth_service.find_user_by_oauth(
        db, user_info.provider, user_info.provider_user_id
    )
    if existing_user and existing_user.id != current_user.id:
        raise InvalidRequest("This OAuth account is already linked to another user")

    await oauth_service.link_oauth_account(
        db,
        current_user.id,
        user_info.provider,
        user_info.provider_user_id,
        user_info.email,
    )
    await db.commit()

    return OAuthLinkResponse(
        message=f"Successfully linked {provider} account",
        provider=provider,
        provider_email=user_info.email,
    )
