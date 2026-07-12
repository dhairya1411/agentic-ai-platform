"""Constant-time webhook verification and canonical event hashing."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime


def payload_hash(body: bytes) -> str:
    """Return a stable payload digest for duplicate/audit detection."""
    return hashlib.sha256(body).hexdigest()


def verify_hmac(secret: str, signed: bytes, signature: str, prefix: str = "") -> bool:
    """Verify a provider signature without leaking comparison timing."""
    expected = prefix + hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_slack_signature(secret: str, timestamp: str, body: bytes, signature: str, now: datetime | None = None) -> bool:
    """Verify Slack v0 signature and reject replayable timestamps older than five minutes."""
    try:
        sent_at = int(timestamp)
    except ValueError:
        return False
    current = int((now or datetime.now(UTC)).timestamp())
    if abs(current - sent_at) > 300:
        return False
    return verify_hmac(secret, f"v0:{timestamp}:".encode() + body, signature, "v0=")


def verify_github_signature(secret: str, body: bytes, signature: str) -> bool:
    """Verify GitHub's sha256 webhook signature."""
    return verify_hmac(secret, body, signature, "sha256=")
