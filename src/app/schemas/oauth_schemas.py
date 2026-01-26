from __future__ import annotations

from pydantic import BaseModel, Field, EmailStr


class OAuthToken(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None


class OAuthUserInfo(BaseModel):
    provider: str
    provider_user_id: str
    email: EmailStr
    full_name: str
    orcid_id: str | None = None


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


class OAuthAuthorizationResponse(BaseModel):
    authorization_url: str


class OAuthLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user_id: str
    email: str


class OAuthLinkRequest(BaseModel):
    code: str
    state: str
    provider: str = Field(..., pattern="^(google|microsoft|orcid)$")


class OAuthLinkResponse(BaseModel):
    message: str
    provider: str
    provider_email: str
