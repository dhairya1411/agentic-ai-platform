"""UUIDv7 identifier tests."""

from __future__ import annotations

from agentic_ai_api.domain.uuid7 import uuid7


def test_uuid7_has_expected_version_and_variant() -> None:
    """Generated IDs use the RFC 9562 version and RFC variant bits."""
    identifier = uuid7()

    assert identifier.version == 7
    assert identifier.variant == "specified in RFC 4122"
