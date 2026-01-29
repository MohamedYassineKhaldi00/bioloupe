from __future__ import annotations

import uuid
from urllib.parse import urlencode
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...app.core.config import get_settings
from ...app.core.exceptions import InvalidRequest
from ...app.models.oauth_account import OAuthAccount
from ...app.models.user import User
from ...app.schemas.oauth_schemas import OAuthToken, OAuthUserInfo


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"

ORCID_AUTH_URL = "https://orcid.org/oauth/authorize"
ORCID_TOKEN_URL = "https://orcid.org/oauth/token"
ORCID_USERINFO_URL = "https://pub.orcid.org/v3.0"


def _get_provider_config(provider: str) -> tuple[str, str, str, str, str]:
    settings = get_settings()

    if provider == "google":
        return (
            GOOGLE_AUTH_URL,
            GOOGLE_TOKEN_URL,
            GOOGLE_USERINFO_URL,
            settings.google_client_id or "",
            settings.google_client_secret or "",
        )
    elif provider == "microsoft":
        return (
            MICROSOFT_AUTH_URL,
            MICROSOFT_TOKEN_URL,
            MICROSOFT_USERINFO_URL,
            settings.microsoft_client_id or "",
            settings.microsoft_client_secret or "",
        )
    elif provider == "orcid":
        return (
            ORCID_AUTH_URL,
            ORCID_TOKEN_URL,
            ORCID_USERINFO_URL,
            settings.orcid_client_id or "",
            settings.orcid_client_secret or "",
        )
    else:
        raise InvalidRequest(f"Unsupported OAuth provider: {provider}")


def get_authorization_url(provider: str, redirect_uri: str, state: str) -> str:
    auth_url, _, _, client_id, _ = _get_provider_config(provider)

    if not client_id:
        raise InvalidRequest(f"{provider} OAuth is not configured")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
    }

    if provider == "google":
        params["scope"] = "openid email profile"
        params["access_type"] = "offline"
    elif provider == "microsoft":
        params["scope"] = "openid email profile User.Read"
        params["response_mode"] = "query"
    elif provider == "orcid":
        params["scope"] = "/authenticate"

    return f"{auth_url}?{urlencode(params)}"


async def exchange_code_for_token(
    provider: str, code: str, redirect_uri: str
) -> OAuthToken:
    _, token_url, _, client_id, client_secret = _get_provider_config(provider)

    if not client_id or not client_secret:
        raise InvalidRequest(f"{provider} OAuth is not configured")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()

    return OAuthToken(
        access_token=token_data["access_token"],
        token_type=token_data.get("token_type", "Bearer"),
        expires_in=token_data.get("expires_in"),
        refresh_token=token_data.get("refresh_token"),
        scope=token_data.get("scope"),
    )


async def _fetch_google_user_info(access_token: str) -> OAuthUserInfo:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = response.json()

    return OAuthUserInfo(
        provider="google",
        provider_user_id=data["id"],
        email=data["email"],
        full_name=data.get("name", ""),
    )


async def _fetch_microsoft_user_info(access_token: str) -> OAuthUserInfo:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            MICROSOFT_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = response.json()

    return OAuthUserInfo(
        provider="microsoft",
        provider_user_id=data["id"],
        email=data["mail"] or data.get("userPrincipalName", ""),
        full_name=data.get("displayName", ""),
    )


async def _fetch_orcid_user_info(access_token: str, orcid_id: str) -> OAuthUserInfo:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ORCID_USERINFO_URL}/{orcid_id}/person",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()

    given_name = data.get("name", {}).get("given-names", {}).get("value", "")
    family_name = data.get("name", {}).get("family-name", {}).get("value", "")
    full_name = f"{given_name} {family_name}".strip()

    emails = data.get("emails", {}).get("email", [])
    primary_email = next(
        (e["email"] for e in emails if e.get("primary")), emails[0]["email"] if emails else ""
    )

    return OAuthUserInfo(
        provider="orcid",
        provider_user_id=orcid_id,
        email=primary_email,
        full_name=full_name or "ORCID User",
        orcid_id=orcid_id,
    )


async def get_user_info(provider: str, access_token: str) -> OAuthUserInfo:
    if provider == "google":
        return await _fetch_google_user_info(access_token)
    elif provider == "microsoft":
        return await _fetch_microsoft_user_info(access_token)
    elif provider == "orcid":
        orcid_id = await _extract_orcid_id(access_token)
        return await _fetch_orcid_user_info(access_token, orcid_id)
    else:
        raise InvalidRequest(f"Unsupported provider: {provider}")


async def _extract_orcid_id(access_token: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://orcid.org/oauth/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = response.json()
        return data["sub"]


async def find_user_by_oauth(
    db: AsyncSession, provider: str, provider_user_id: str
) -> User | None:
    result = await db.execute(
        select(User)
        .join(OAuthAccount)
        .where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )
    return result.scalar_one_or_none()


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def link_oauth_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    provider_user_id: str,
    provider_email: str,
) -> OAuthAccount:
    existing = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.user_id == user_id, OAuthAccount.provider == provider
        )
    )
    if existing.scalar_one_or_none():
        raise InvalidRequest(f"User already has a {provider} account linked")

    oauth_account = OAuthAccount(
        user_id=user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=provider_email,
    )
    db.add(oauth_account)
    await db.flush()
    return oauth_account
