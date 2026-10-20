"""Extract and group log symptoms without executing the logs as instructions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import re

from .redact import redact

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_TIMESTAMP = re.compile(
    r"\b\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:[.,]\d+)?(?:Z|[+-]\d\d:?\d\d)?\b"
)
_TIME_ONLY = re.compile(r"\b\d\d:\d\d:\d\d(?:[.,]\d+)?\b")
_UUID = re.compile(r"\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b", re.I)
_LONG_HEX = re.compile(r"\b[0-9a-f]{12,}\b", re.I)
_NUMBER = re.compile(r"\b\d{4,}\b")
_SPACE = re.compile(r"\s+")
# Logs that include these words are treated as symptoms, not arbitrary output.
_ERROR = re.compile(r"(?i)\b(?:error|exception|failed|failure|fatal|panic|critical|timeout|timed out|refused|unhealthy|killed|oomkilled|crashloopbackoff|denied|502|503|504|back-off|no route to host)\b")
_WARNING = re.compile(r"(?i)\b(?:warn(?:ing)?|retry(?:ing)?|degraded|slow|backoff|not ready)\b")
_PREFIX = re.compile(r"^\s*([\w.-]{1,50})\s*\|\s*")
_LEVEL = re.compile(r"(?i)\b(ERROR|WARN(?:ING)?|FATAL|CRITICAL|INFO|DEBUG)\b\s*[:\-]?\s*")


@dataclass(frozen=True)
class Event:
    id: str
    severity: str
    count: int
    signature: str
    samples: tuple[str, ...]
    first_line: int


@dataclass(frozen=True)
class Digest:
    total_lines: int
    examined_lines: int
    symptom_lines: int
    unique_events: int
    events: tuple[Event, ...]
    redacted_line_count: int


def _normalize(line: str) -> str:
    text = _ANSI.sub("", line).strip()
    # Preserve the service label, but erase changing timestamps / IDs.
    text = _TIMESTAMP.sub("<time>", text)
    text = _TIME_ONLY.sub("<time>", text)
    text = _UUID.sub("<uuid>", text)
    text = _LONG_HEX.sub("<id>", text)
    text = _NUMBER.sub("<n>", text)
    return _SPACE.sub(" ", text).strip()[:240]


def analyze(raw: str, *, max_lines: int = 8000, max_events: int = 12) -> Digest:
    if max_lines < 1 or max_events < 1:
        raise ValueError("max_lines and max_events must be positive")
    lines = raw.splitlines()
    selected = lines[:max_lines]
    grouped: dict[str, dict] = defaultdict(lambda: {"count": 0, "samples": [], "first_line": 0, "severity": "warning"})
    symptom_lines = 0
    redacted_lines = 0
    for number, original in enumerate(selected, 1):
        line = redact(_ANSI.sub("", original))
        if line != original:
            redacted_lines += 1
        # Respect an explicit WARNING log level even when the message mentions
        # "timeout" or "failed"; those words alone must not relabel it ERROR.
        level_match = _LEVEL.search(line)
        level = level_match.group(1).upper() if level_match else ""
        if level in ("WARN", "WARNING"):
            severity = "warning"
        elif level in ("ERROR", "FATAL", "CRITICAL"):
            severity = "error"
        elif _ERROR.search(line):
            severity = "error"
        elif _WARNING.search(line):
            severity = "warning"
        else:
            continue
        symptom_lines += 1
        # Avoid sending very long log lines or model-injection bait downstream.
        line = line[:500]
        signature = _normalize(line)
        if not signature:
            continue
        item = grouped[signature]
        if not item["first_line"]:
            item["first_line"] = number
        item["count"] += 1
        if severity == "error":
            item["severity"] = "error"
        if len(item["samples"]) < 2:
            item["samples"].append(line)

    ranked = sorted(grouped.items(), key=lambda kv: (-kv[1]["count"], kv[1]["first_line"]))
    chosen = ranked[:max_events]
    events = tuple(
        Event(
            id=f"E{index:02d}",
            severity=data["severity"],
            count=data["count"],
            signature=signature,
            samples=tuple(data["samples"]),
            first_line=data["first_line"],
        )
        for index, (signature, data) in enumerate(chosen, 1)
    )
    return Digest(
        total_lines=len(lines),
        examined_lines=len(selected),
        symptom_lines=symptom_lines,
        unique_events=len(grouped),
        events=events,
        redacted_line_count=redacted_lines,
    )
