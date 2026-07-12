"""Phase 2 packaging smoke tests."""


def test_package_is_importable() -> None:
    """The API package can be resolved by the configured source layout."""
    import agentic_ai_api

    assert agentic_ai_api.__doc__ is not None
