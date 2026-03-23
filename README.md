# token-account

[中文文档](./README.zh-CN.md)

`token-account` is a persistent token usage service for Codex sessions.

It turns the original one-shot static HTML report into a small FastAPI service backed by SQLite, accepts incremental sync uploads from one or more machines, and keeps the legacy report UI available as a live dashboard page.

## Features

- Run a long-lived HTTP service for token usage reporting
- Ingest incremental events from local Codex session logs
- Deduplicate events by `event_id`
- Merge usage from multiple devices into one report
- Serve both dashboard APIs and the legacy HTML report
- Keep sync state locally for efficient repeated uploads

## tech stack

- API: `FastAPI`, `Pydantic`, `Uvicorn`
- Storage: `SQLite`, `sqlite3`
- Sync client: `urllib.request`, local JSON state
- Reporting UI: server-rendered HTML, legacy report renderer
- Packaging and deployment: `Python 3.11+`, `Docker`, `Docker Compose`

## Project Structure

```text
src/token_account/
  cli.py                  CLI entry for serve / sync / sync-loop
  service.py              FastAPI routes and service wiring
  syncer.py               Incremental sync client
  storage.py              SQLite schema and ingestion
  reporting.py            Report aggregation and payload building
  legacy_report.py        Legacy HTML report renderer
src/codex_token_report.py Thin executable entrypoint
Dockerfile                Container image
docker-compose.yml        Compose service definition
pricing.json              Optional pricing overrides
```

## Quick Start

1. Install dependencies.

```bash
pip install -r requirements.txt
```

2. Start the service.

```bash
python3 src/codex_token_report.py serve --host 0.0.0.0 --port 8000 --db-file data/token-account.db
```

3. Sync local Codex events once.

```bash
python3 src/codex_token_report.py sync --service-url http://127.0.0.1:8000
```

4. Keep syncing in the background.

```bash
python3 src/codex_token_report.py sync-loop --service-url http://127.0.0.1:8000 --interval 60
```

Default URLs after the service starts:

- Report page: `http://127.0.0.1:8000/`
- Dashboard API: `http://127.0.0.1:8000/api/dashboard`
- Report API: `http://127.0.0.1:8000/api/report`
- Sources API: `http://127.0.0.1:8000/api/sources`
- Health API: `http://127.0.0.1:8000/api/health`

On Windows, you can also double-click `open-report.bat` to start the local service in the background and open the browser automatically.

## CLI Commands

### `serve`

Start the FastAPI service.

Common options:

- `--host`: bind address, default `127.0.0.1`
- `--port`: bind port, default `8000`
- `--db-file`: SQLite file path, default `data/token-account.db`
- `--pricing-file`: optional pricing override file

### `sync`

Scan local `.codex/sessions` data and push normalized token events to the service.

Common options:

- `--service-url`: service base URL, default `http://127.0.0.1:8000`
- `--codex-home`: custom `.codex` root
- `--sessions-root`: direct path to the `sessions` directory
- `--state-file`: local sync state file
- `--source-id`: source device identifier
- `--hostname`: source host name
- `--batch-size`: upload batch size, default `1000`
- `--timeout`: HTTP timeout in seconds, default `30`

### `sync-loop`

Run `sync` repeatedly for daemon, scheduler, or `systemd` usage.

Extra option:

- `--interval`: sync interval in seconds, default `60`

## Data Model

- Events are stored individually and deduplicated by `event_id`
- Device metadata is preserved in the `sources` table
- Sync runs are recorded for troubleshooting and status display
- The HTML report polls fresh report data periodically from the service

## Docker Compose

The repository includes `Dockerfile` and `docker-compose.yml`.

Default container command:

```bash
python src/codex_token_report.py serve --host 0.0.0.0 --port 8000 --db-file /data/token-account.db
```

Start it with:

```bash
docker compose up -d --build
```

The local `./data` directory is mounted to `/data` for SQLite persistence.

## Security Note

The current service does not add authentication.

If you expose it to a public network, anyone who can reach the service can read report data, inspect source status, and submit sync payloads. Put it behind a reverse proxy, access control, or add an auth layer before wider exposure.
