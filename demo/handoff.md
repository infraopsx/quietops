# QuietOps incident handoff

> **Read-only analysis.** AI suggestions are hypotheses, not verified diagnoses. No server configuration was changed. All model input is redacted best-effort; review your logs before processing.

- Analyzed lines: **240** / 240
- Symptom lines: **110**
- Unique signatures found: **5**
- Top signatures shown to operator: **5**
- Reduction in lines needing initial review: **97.9%** (signature summary vs. raw lines; not a measured human time saving)
- Lines with redaction or ANSI removal: **68**

## AI briefing

**Not run.** This is a deterministic preview; no model-generated diagnosis is shown.

## Grouped log evidence (redacted)

### E01 · ERROR · 32 occurrences

```text
api | 2026-10-20T01:01:15Z ERROR database URL: postgres://[USER]:[REDACTED]@postgres:5432/demo
api | 2026-10-20T01:02:30Z ERROR database URL: postgres://[USER]:[REDACTED]@postgres:5432/demo
```

### E02 · ERROR · 27 occurrences

```text
worker | 2026-10-20T01:01:45Z WARNING retrying background queue delivery after timeout
worker | 2026-10-20T01:03:30Z WARNING retrying background queue delivery after timeout
```

### E03 · ERROR · 19 occurrences

```text
api | 2026-10-20T01:02:45Z ERROR connection timeout during database query; password=[REDACTED]
api | 2026-10-20T01:05:30Z ERROR connection timeout during database query; password=[REDACTED]
```

### E04 · ERROR · 17 occurrences

```text
nginx | 2026-10-20T01:03:15Z ERROR connect() failed (111: Connection refused) while connecting to upstream; client: [REDACTED-IP]; status: 502
nginx | 2026-10-20T01:06:30Z ERROR connect() failed (111: Connection refused) while connecting to upstream; client: [REDACTED-IP]; status: 502
```

### E05 · ERROR · 15 occurrences

```text
postgres | 2026-10-20T01:00:00Z FATAL: password authentication failed for user "app"
postgres | 2026-10-20T01:04:15Z FATAL: password authentication failed for user "app"
```
