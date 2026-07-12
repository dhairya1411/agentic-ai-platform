"""JWT, opaque refresh-token, and connector-secret cryptographic primitives."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from cryptography.fernet import Fernet, InvalidToken

from agentic_ai_api.core.config import Settings


def utc_now() -> datetime:
    """Return a timezone-aware current UTC timestamp."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class AccessClaims:
    """Validated application access-token claims."""

    user_id: UUID
    session_id: UUID


class TokenService:
    """Issue and verify short-lived JWTs plus hashed opaque secrets."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._secret = settings.jwt_secret_key.get_secret_value()

    def issue_access_token(self, user_id: UUID, session_id: UUID) -> str:
        """Issue a bounded access token linked to one revocable refresh session."""
        now = utc_now()
        return jwt.encode(
            {
                "sub": str(user_id),
                "sid": str(session_id),
                "iss": self._settings.jwt_issuer,
                "aud": self._settings.jwt_audience,
                "iat": now,
                "exp": now + timedelta(minutes=self._settings.access_token_ttl_minutes),
            },
            self._secret,
            algorithm="HS256",
        )

    def decode_access_token(self, token: str) -> AccessClaims:
        """Validate token signature, issuer, audience, expiry, and required IDs."""
        payload = jwt.decode(
            token,
            self._secret,
            algorithms=["HS256"],
            audience=self._settings.jwt_audience,
            issuer=self._settings.jwt_issuer,
            options={"require": ["sub", "sid", "exp", "iat"]},
        )
        return AccessClaims(user_id=UUID(payload["sub"]), session_id=UUID(payload["sid"]))

    def new_opaque_token(self) -> str:
        """Create a high-entropy browser secret that is never stored raw."""
        return secrets.token_urlsafe(48)

    def token_hash(self, token: str) -> str:
        """Create a keyed, constant-time-comparable hash for an opaque secret."""
        return hmac.new(self._secret.encode(), token.encode(), hashlib.sha256).hexdigest()


class CredentialCipher:
    """Encrypt OAuth connector credentials before they enter PostgreSQL."""

    def __init__(self, settings: Settings) -> None:
        self._cipher = Fernet(settings.encryption_key.get_secret_value().encode())

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt a credential payload with authenticated encryption."""
        return self._cipher.encrypt(plaintext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt a credential payload or reject tampered ciphertext."""
        try:
            return self._cipher.decrypt(ciphertext)
        except InvalidToken as exc:
            raise ValueError("Credential ciphertext is invalid or has been tampered with") from exc
