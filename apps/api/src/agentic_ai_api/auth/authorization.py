"""Reusable RBAC checks for future organization-scoped endpoints."""

from __future__ import annotations

from collections.abc import Iterable

from agentic_ai_api.core.errors import APIError

ROLE_ORDER: dict[str, int] = {"viewer": 10, "member": 20, "manager": 30, "admin": 40, "owner": 50}


def require_minimum_role(actual_role: str, accepted_roles: Iterable[str]) -> None:
    """Raise a consistent forbidden error unless a role is explicitly allowed."""
    allowed = set(accepted_roles)
    if actual_role not in allowed:
        raise APIError(status_code=403, code="forbidden", message="Insufficient organization permission.")
