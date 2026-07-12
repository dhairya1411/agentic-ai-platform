"""Conservative redaction for data leaving the platform and entering logs."""

from __future__ import annotations

import re


class Redactor:
    """Replace common credentials and direct identifiers with stable placeholders."""

    _patterns = (
        (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), "[REDACTED_OPENAI_KEY]"),
        (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "[REDACTED_SLACK_TOKEN]"),
        (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
        (re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/-]{16,}"), r"\1[REDACTED_TOKEN]"),
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    )

    def redact(self, text: str) -> str:
        """Return text with high-risk credential and email patterns removed."""
        for pattern, replacement in self._patterns:
            text = pattern.sub(replacement, text)
        return text
