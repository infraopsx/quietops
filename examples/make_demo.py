"""Generate a fully synthetic repeatable Docker Compose incident fixture."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

start = datetime(2026, 10, 20, 1, 0, tzinfo=timezone.utc)
rows = []
for i in range(240):
    timestamp = (start + timedelta(seconds=15 * i)).isoformat().replace("+00:00", "Z")
    if i % 17 == 0:
        service, text = "postgres", 'FATAL: password authentication failed for user "app"'
    elif i % 13 == 0:
        service, text = "nginx", f'ERROR connect() failed (111: Connection refused) while connecting to upstream; client: 198.51.100.{i % 200 + 1}; status: 502'
    elif i % 11 == 0:
        service, text = "api", 'ERROR connection timeout during database query; password=super-secret-demo-value'
    elif i % 7 == 0:
        service, text = "worker", 'WARNING retrying background queue delivery after timeout'
    elif i % 5 == 0:
        service, text = "api", 'ERROR database URL: postgres://demo_user:demo_pw@postgres:5432/demo'
    else:
        service, text = "api", 'INFO request completed in 14ms'
    rows.append(f"{service} | {timestamp} {text}")
Path(__file__).with_name("docker-incident.log").write_text("\n".join(rows) + "\n", encoding="utf-8")
print("Generated synthetic sample with", len(rows), "lines")
