"""Best-effort log redaction before using a local model.

Redaction is heuristic. Users must still review sensitive data before scanning.
"""

from __future__ import annotations

import re

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b([a-z][a-z0-9+.-]*://)([^\s/@:]+):([^\s/@]+)@", re.I), r"\1[USER]:[REDACTED]@"),
    (re.compile(r"\bAuthorization\s*[:=]\s*(?:Bearer|Basic)\s+[^\s,;\"']+", re.I), "Authorization: [REDACTED]"),
    (re.compile(r"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{15,}\b"), "[REDACTED-GITHUB-TOKEN]"),
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED-AWS-KEY]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+"), "[REDACTED-JWT]"),
    # Environment variables may be prefixed, e.g., DATABASE_PASSWORD, AWS_SECRET_ACCESS_KEY.
    (re.compile(r'(\b[A-Z][A-Z0-9_]*(?:PASSWORD|PASSWD|API_KEY|ACCESS_TOKEN|SECRET|PRIVATE_KEY)[A-Z0-9_]*\s*[:=]\s*)(?:"[^"]*"|[^\s,;]+)', re.I), r"\1[REDACTED]"),
    (re.compile(r'(?i)(["\']?\b(?:password|passwd|pwd|api[_-]?key|access[_-]?token|secret|client[_-]?secret|authorization)\b["\']?\s*[:=]\s*)"[^"]*"'), r'\1"[REDACTED]"'),
    (re.compile(r"(?i)(\b(?:password|passwd|pwd|api[_-]?key|access[_-]?token|secret|client[_-]?secret|authorization)\b\s*[:=]\s*)'[^']*'"), r"\1'[REDACTED]'"),
    (re.compile(r"(?i)(\b(?:password|passwd|pwd|api[_-]?key|access[_-]?token|secret|client[_-]?secret|authorization)\b\s*[:=]\s*)(?!\[REDACTED\])[^\s,;\"']+"), r"\1[REDACTED]"),
    (re.compile(r"\b[\w.+'-]+@[\w.-]+\.[a-zA-Z]{2,}\b"), "[REDACTED-EMAIL]"),
    (re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])"), "[REDACTED-IP]"),
)


def redact(text: str) -> str:
    """Remove common credentials and network identifiers, best effort."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
