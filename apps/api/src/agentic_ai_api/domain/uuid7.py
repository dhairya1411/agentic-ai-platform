"""Dependency-free UUIDv7 generation compatible with Python 3.12."""

from __future__ import annotations

import secrets
import time
from uuid import UUID


def uuid7() -> UUID:
    """Create a time-sortable UUIDv7 using the RFC 9562 bit layout."""
    timestamp_ms = int(time.time_ns() // 1_000_000)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    value = (timestamp_ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return UUID(int=value)
