"""Authentication cryptography unit tests."""

from __future__ import annotations

from uuid import uuid4

from agentic_ai_api.auth.security import CredentialCipher, TokenService
from agentic_ai_api.core.config import Settings


def test_access_token_round_trip() -> None:
    """Access-token claims retain the user and refresh-session identity."""
    settings = Settings(
        app_env="test",
        jwt_secret_key="test-secret-that-is-long-enough-for-jwt-signing",
        jwt_issuer="test-issuer",
        jwt_audience="test-audience",
    )
    token_service = TokenService(settings)
    user_id, session_id = uuid4(), uuid4()

    claims = token_service.decode_access_token(token_service.issue_access_token(user_id, session_id))

    assert claims.user_id == user_id
    assert claims.session_id == session_id


def test_credential_cipher_round_trip() -> None:
    """Connector credentials are encrypted at rest and recover without mutation."""
    settings = Settings(
        app_env="test",
        encryption_key="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )

    ciphertext = CredentialCipher(settings).encrypt(b'{"access_token":"secret"}')

    assert ciphertext != b'{"access_token":"secret"}'
    assert CredentialCipher(settings).decrypt(ciphertext) == b'{"access_token":"secret"}'
