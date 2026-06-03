# AI-Powered Server Monitoring and Alert System

Flask application that collects server metrics (CPU, memory, disk, network), detects anomalies with Isolation Forest, raises threshold-based alerts, and provides a Bootstrap 5 dashboard with live Chart.js graphs, CSV/PDF reports, and dark mode.

## Features

- Real-time metrics collection via `psutil` (background scheduler)
- ML anomaly detection (scikit-learn Isolation Forest)
- Configurable alert thresholds and email simulation
- Web UI: dashboard, alerts, logs, reports
- CSV and PDF export
- SQLite by default; MySQL via `DATABASE_URL`

## Quick start

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
python seed_data.py            # optional demo data
python app.py
```

Open http://127.0.0.1:5000

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | `development`, `testing`, `production` |
| `SECRET_KEY` | (dev default) | Required in production |
| `ADMIN_USERNAME` | `admin` | Admin login username |
| `ADMIN_PASSWORD` | `admin` | Admin login password (required in production) |
| `METRICS_RETENTION_DAYS` | `30` | Auto-delete data older than N days |
| `MONITORING_INTERVAL` | `5` | Seconds between metric samples |
| `DATABASE_URL` | SQLite in `database/` | e.g. `mysql+pymysql://user:pass@host/db` |
| `DISK_PATH` | `C:\` (Windows) or `/` | Path for disk usage |
| `MAIL_SIMULATION_MODE` | `true` | Log emails instead of sending |

## Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```

## Project layout

```
app.py                 # Application entry
config.py              # Settings
models/                # SQLAlchemy models
routes/                # Blueprints (dashboard, metrics, alerts, logs, reports)
services/              # Collector, ML, alerts, reports, email
templates/             # Jinja2 UI
static/                # CSS and JavaScript
seed_data.py           # Sample data
docker/                # Dockerfile and compose
```

## Authentication

Sign in at `/login` with `ADMIN_USERNAME` / `ADMIN_PASSWORD`. Alert acknowledge/resolve and CSV/PDF exports require an active session.

## Health check

- `GET /health` — application, database, and scheduler status (no auth; returns 503 if degraded)

## API (selected)

- `GET /api/dashboard/summary` — current metrics and status
- `GET /api/metrics/history?hours=1` — time series for charts
- `GET /api/alerts` — paginated alerts
- `GET /api/logs` — paginated audit logs
- `GET /api/reports/csv?hours=24` — CSV download
- `GET /api/reports/pdf?hours=24` — PDF download

## License

MIT
