"""Phase 2 packaging smoke tests."""


def test_package_is_importable() -> None:
    """The worker package can be resolved by the configured source layout."""
    import agentic_ai_worker

    assert agentic_ai_worker.__doc__ is not None
