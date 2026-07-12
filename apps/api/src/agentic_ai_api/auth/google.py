"""Google OAuth 2.0 authorization-code integration."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from agentic_ai_api.core.config import Settings

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


@dataclass(frozen=True, slots=True)
class GoogleProfile:
    """The minimum verified identity claims needed by this application."""

    subject: str
    email: str
    display_name: str


class GoogleOAuthClient:
    """Exchange an authorization code and retrieve verified Google user information."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def authorization_url(self, state: str) -> str:
        """Build the consent URL with OpenID scopes and anti-CSRF state."""
        if not self._settings.google_client_id:
            raise ValueError("Google OAuth is not configured")
        query = urlencode(
            {
                "client_id": self._settings.google_client_id,
                "redirect_uri": self._settings.google_redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "access_type": "offline",
                "prompt": "select_account",
            }
        )
        return f"{GOOGLE_AUTHORIZE_URL}?{query}"

    async def profile_from_code(self, code: str) -> GoogleProfile:
        """Exchange a code and require an email-verified OpenID user profile."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._settings.google_client_id,
                    "client_secret": self._settings.google_client_secret.get_secret_value(),
                    "redirect_uri": self._settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            if not isinstance(access_token, str):
                raise ValueError("Google token response did not include an access token")
            profile_response = await client.get(
                GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            profile_response.raise_for_status()
        profile = profile_response.json()
        if profile.get("email_verified") is not True:
            raise ValueError("Google account email is not verified")
        subject, email = profile.get("sub"), profile.get("email")
        if not isinstance(subject, str) or not isinstance(email, str):
            raise ValueError("Google user profile is missing required claims")
        name = profile.get("name")
        return GoogleProfile(subject=subject, email=email.lower(), display_name=name if isinstance(name, str) else email)
