from __future__ import annotations

import re

_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|passwd|secret)\b(\s*[:=]\s*)([^\s,;]+)"
)
_SENSITIVE_QUERY_RE = re.compile(
    r"(?i)([?&](?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|secret)=)([^&\s]+)"
)
_SENSITIVE_BEARER_RE = re.compile(r"(?i)\b(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)")


def redact_sensitive_text(value: str | None) -> str | None:
    if value is None:
        return None

    redacted = _SENSITIVE_ASSIGNMENT_RE.sub(r"\1\2[REDACTED]", value)
    redacted = _SENSITIVE_QUERY_RE.sub(r"\1[REDACTED]", redacted)
    redacted = _SENSITIVE_BEARER_RE.sub(r"\1[REDACTED]", redacted)
    return redacted
