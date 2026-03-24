<div align="center">

# token-account

<p><strong>Persistent token usage service for Codex sessions</strong></p>

<p>
  <a href="./README.md">
    <img src="https://img.shields.io/badge/English-111827?style=flat" alt="English README" />
  </a>
  <a href="./README.zh-CN.md">
    <img src="https://img.shields.io/badge/%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-2563EB?style=flat" alt="简体中文文档" />
  </a>
</p>

<p>
  Turn one-shot Codex token reports into a small service with incremental sync, multi-device aggregation, and a live HTML dashboard.
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Pydantic-E92063?style=flat&logo=pydantic&logoColor=white" alt="Pydantic" />
  <img src="https://img.shields.io/badge/SQLite-0F80CC?style=flat&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Docker_Compose-1D63ED?style=flat&logo=docker&logoColor=white" alt="Docker Compose" />
</p>

</div>

## Demo

<p align="center">
  <a href="https://github.com/githubbzxs/token-account/releases/download/readme-media-assets/demo-ui.mp4">
    <img src="./docs/demo-video-preview.png" alt="token-account demo video preview" width="100%" />
  </a>
</p>

<p align="center"><sub>Click the preview image to open the demo video. The demo uses fabricated sample data.</sub></p>

## Overview

`token-account` converts the original static HTML script into a long-lived FastAPI service backed by SQLite.

It accepts incremental sync uploads from one or more machines, deduplicates events by `event_id`, stores source status, and keeps the legacy report UI available as a live dashboard page.

## Features

- Long-lived HTTP service for token usage reporting
- Incremental sync from local Codex session logs
- Idempotent event ingestion with `event_id` deduplication
- Aggregated reporting across multiple devices
- Dashboard APIs plus server-rendered legacy HTML report
- Local sync state tracking for efficient repeated uploads

## tech stack

<p>
  <img src="https://img.shields.io/badge/FastAPI-API-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI API" />
  <img src="https://img.shields.io/badge/Pydantic-Validation-E92063?style=flat&logo=pydantic&logoColor=white" alt="Pydantic Validation" />
  <img src="https://img.shields.io/badge/Uvicorn-ASGI-4051B5?style=flat" alt="Uvicorn ASGI" />
  <img src="https://img.shields.io/badge/SQLite-Storage-0F80CC?style=flat&logo=sqlite&logoColor=white" alt="SQLite Storage" />
  <img src="https://img.shields.io/badge/urllib.request-Sync_Client-4B5563?style=flat" alt="urllib.request Sync Client" />
  <img src="https://img.shields.io/badge/Server_Rendered_HTML-Legacy_Report-111827?style=flat" alt="Server Rendered HTML Legacy Report" />
</p>

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

## Acknowledgements

Thanks to the [Linux.do community](https://linux.do) for the ongoing discussion, sharing, and practical feedback around Codex workflows, self-hosted tooling, and deployment experience.

Projects like this benefit a lot from communities that openly exchange scripts, ideas, and real-world usage patterns.

## Security Note

The current service does not add authentication.

If you expose it to a public network, anyone who can reach the service can read report data, inspect source status, and submit sync payloads. Put it behind a reverse proxy, access control, or add an auth layer before wider exposure.
