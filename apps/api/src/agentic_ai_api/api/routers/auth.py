"""OAuth login, refresh-session lifecycle, and current-identity endpoints."""

from __future__ import annotations

from datetime import timedelta

import jwt
import httpx
from fastapi import APIRouter, Cookie, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_ai_api.api.dependencies import get_app_settings, get_session
from agentic_ai_api.auth.google import GoogleOAuthClient
from agentic_ai_api.auth.security import AccessClaims, TokenService, utc_now
from agentic_ai_api.core.config import Settings
from agentic_ai_api.core.errors import APIError
from agentic_ai_api.domain.models import AuthSession, ExternalIdentity, OAuthLoginState, User

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer_scheme = HTTPBearer(auto_error=False)
REFRESH_COOKIE = "agentic_ai_refresh"


class AuthorizationStartResponse(BaseModel):
    authorization_url: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    status: str


async def get_current_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_app_settings),
    session: AsyncSession = Depends(get_session),
) -> AccessClaims:
    """Validate a bearer token and confirm its linked refresh session remains active."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise APIError(status_code=401, code="unauthenticated", message="Bearer token is required.")
    try:
        claims = TokenService(settings).decode_access_token(credentials.credentials)
    except (jwt.PyJWTError, ValueError) as exc:
        raise APIError(status_code=401, code="unauthenticated", message="Access token is invalid or expired.") from exc
    auth_session = await session.get(AuthSession, claims.session_id)
    if (
        auth_session is None
        or auth_session.user_id != claims.user_id
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= utc_now()
    ):
        raise APIError(status_code=401, code="unauthenticated", message="Access session is no longer active.")
    return claims


def set_refresh_cookie(response: Response, refresh_token: str, settings: Settings) -> None:
    """Store the opaque refresh token in a constrained HttpOnly browser cookie."""
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth",
    )


@router.post("/google/start", response_model=AuthorizationStartResponse)
async def start_google_login(
    settings: Settings = Depends(get_app_settings), session: AsyncSession = Depends(get_session)
) -> AuthorizationStartResponse:
    """Create one-time OAuth state before returning the Google consent URL."""
    token_service = TokenService(settings)
    raw_state = token_service.new_opaque_token()
    session.add(
        OAuthLoginState(
            state_hash=token_service.token_hash(raw_state),
            expires_at=utc_now() + timedelta(minutes=10),
        )
    )
    try:
        authorization_url = GoogleOAuthClient(settings).authorization_url(raw_state)
    except ValueError as exc:
        raise APIError(status_code=503, code="oauth_unavailable", message=str(exc)) from exc
    return AuthorizationStartResponse(authorization_url=authorization_url)


@router.get("/google/callback", response_model=TokenResponse)
async def complete_google_login(
    code: str,
    state: str,
    response: Response,
    settings: Settings = Depends(get_app_settings),
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Consume OAuth state, link the Google account, and issue a browser session."""
    token_service = TokenService(settings)
    state_record = await session.scalar(
        select(OAuthLoginState)
        .where(OAuthLoginState.state_hash == token_service.token_hash(state))
        .with_for_update()
    )
    if state_record is None or state_record.consumed_at is not None or state_record.expires_at <= utc_now():
        raise APIError(status_code=401, code="invalid_oauth_state", message="OAuth login state is invalid or expired.")
    state_record.consumed_at = utc_now()
    try:
        profile = await GoogleOAuthClient(settings).profile_from_code(code)
    except (httpx.HTTPError, ValueError) as exc:
        raise APIError(status_code=401, code="oauth_exchange_failed", message="Google login could not be verified.") from exc

    identity = await session.scalar(
        select(ExternalIdentity).where(
            ExternalIdentity.provider == "google", ExternalIdentity.provider_subject == profile.subject
        )
    )
    if identity is None:
        user = await session.scalar(select(User).where(User.email == profile.email))
        if user is None:
            user = User(email=profile.email, display_name=profile.display_name, status="active")
            session.add(user)
            await session.flush()
        identity = ExternalIdentity(user_id=user.id, provider="google", provider_subject=profile.subject)
        session.add(identity)
    else:
        user = await session.get(User, identity.user_id)
        if user is None or user.status != "active":
            raise APIError(status_code=401, code="account_inactive", message="This account is not active.")

    await session.flush()
    refresh_token = token_service.new_opaque_token()
    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=token_service.token_hash(refresh_token),
        expires_at=utc_now() + timedelta(days=settings.refresh_token_ttl_days),
    )
    session.add(auth_session)
    await session.flush()
    set_refresh_cookie(response, refresh_token, settings)
    return TokenResponse(
        access_token=token_service.issue_access_token(user.id, auth_session.id),
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    settings: Settings = Depends(get_app_settings),
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Rotate a browser refresh secret and issue a new short-lived access token."""
    if refresh_token is None:
        raise APIError(status_code=401, code="unauthenticated", message="Refresh session is required.")
    token_service = TokenService(settings)
    auth_session = await session.scalar(
        select(AuthSession).where(AuthSession.refresh_token_hash == token_service.token_hash(refresh_token)).with_for_update()
    )
    if auth_session is None or auth_session.revoked_at is not None or auth_session.expires_at <= utc_now():
        raise APIError(status_code=401, code="unauthenticated", message="Refresh session is invalid or expired.")
    new_refresh_token = token_service.new_opaque_token()
    auth_session.refresh_token_hash = token_service.token_hash(new_refresh_token)
    auth_session.last_used_at = utc_now()
    set_refresh_cookie(response, new_refresh_token, settings)
    return TokenResponse(
        access_token=token_service.issue_access_token(auth_session.user_id, auth_session.id),
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    claims: AccessClaims = Depends(get_current_claims),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Revoke the current refresh session and delete its browser cookie."""
    auth_session = await session.get(AuthSession, claims.session_id)
    if auth_session is not None:
        auth_session.revoked_at = utc_now()
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=CurrentUserResponse)
async def current_user(
    claims: AccessClaims = Depends(get_current_claims), session: AsyncSession = Depends(get_session)
) -> CurrentUserResponse:
    """Return the authenticated user's global profile without leaking tenant records."""
    user = await session.get(User, claims.user_id)
    if user is None:
        raise APIError(status_code=401, code="unauthenticated", message="User account no longer exists.")
    return CurrentUserResponse(id=str(user.id), email=user.email, display_name=user.display_name, status=user.status)
