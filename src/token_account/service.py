from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .reporting import build_dashboard_payload, build_report_from_database, render_html
from .storage import db_session, fetch_sources, ingest_sync_events


class SyncEvent(BaseModel):
    event_id: str = Field(..., description="事件幂等键")
    session_id: str
    ts: str
    model: str
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0


class SyncPayload(BaseModel):
    source_id: str
    hostname: str
    sent_at: str
    events: list[SyncEvent]


class ServiceConfig(BaseModel):
    db_file: str
    pricing_file: str | None = None


def create_app(*, db_file: str | Path, pricing_file: str | Path | None = None) -> FastAPI:
    config = ServiceConfig(
        db_file=str(Path(db_file)),
        pricing_file=str(Path(pricing_file)) if pricing_file else None,
    )
    app = FastAPI(title="Codex Token Usage Service", version="1.0.0")
    app.state.config = config
    static_dir = Path(__file__).resolve().parent / "static"

    if (static_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        with db_session(app.state.config.db_file) as conn:
            data, summary, empty = build_report_from_database(
                conn,
                pricing_path=Path(app.state.config.pricing_file) if app.state.config.pricing_file else None,
                source_label=app.state.config.db_file,
            )
        return HTMLResponse(render_html(data, summary, empty))

    @app.get("/legacy", response_class=HTMLResponse)
    def legacy_index() -> HTMLResponse:
        with db_session(app.state.config.db_file) as conn:
            data, summary, empty = build_report_from_database(
                conn,
                pricing_path=Path(app.state.config.pricing_file) if app.state.config.pricing_file else None,
                source_label=app.state.config.db_file,
            )
        return HTMLResponse(render_html(data, summary, empty))

    @app.get("/api/dashboard")
    def api_dashboard(
        since: str | None = Query(default=None, description="起始日期，格式 YYYY-MM-DD"),
        until: str | None = Query(default=None, description="结束日期，格式 YYYY-MM-DD"),
    ) -> dict[str, Any]:
        try:
            with db_session(app.state.config.db_file) as conn:
                data, summary, empty = build_report_from_database(
                    conn,
                    since_text=since,
                    until_text=until,
                    pricing_path=Path(app.state.config.pricing_file) if app.state.config.pricing_file else None,
                    source_label=app.state.config.db_file,
                )
            return build_dashboard_payload(data, summary, empty)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/report")
    def api_report(
        since: str | None = Query(default=None, description="起始日期，格式 YYYY-MM-DD"),
        until: str | None = Query(default=None, description="结束日期，格式 YYYY-MM-DD"),
    ) -> dict[str, Any]:
        try:
            with db_session(app.state.config.db_file) as conn:
                data, _, _ = build_report_from_database(
                    conn,
                    since_text=since,
                    until_text=until,
                    pricing_path=Path(app.state.config.pricing_file) if app.state.config.pricing_file else None,
                    source_label=app.state.config.db_file,
                )
            return data
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/data.json")
    def data_json_alias(
        since: str | None = Query(default=None, description="起始日期，格式 YYYY-MM-DD"),
        until: str | None = Query(default=None, description="结束日期，格式 YYYY-MM-DD"),
    ) -> dict[str, Any]:
        try:
            with db_session(app.state.config.db_file) as conn:
                data, _, _ = build_report_from_database(
                    conn,
                    since_text=since,
                    until_text=until,
                    pricing_path=Path(app.state.config.pricing_file) if app.state.config.pricing_file else None,
                    source_label=app.state.config.db_file,
                )
            return data
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/health")
    def api_health() -> dict[str, Any]:
        with db_session(app.state.config.db_file) as conn:
            sources = fetch_sources(conn)
        return {
            "status": "ok",
            "db_file": app.state.config.db_file,
            "source_count": len(sources),
        }

    @app.get("/api/sources")
    def api_sources() -> dict[str, Any]:
        with db_session(app.state.config.db_file) as conn:
            sources = fetch_sources(conn)
        return {
            "count": len(sources),
            "sources": sources,
            "last_synced_at": (sources[0].get("last_sync_at") if sources else None),
        }

    @app.post("/api/sync/events")
    def api_sync_events(payload: SyncPayload) -> dict[str, Any]:
        events = [item.model_dump() for item in payload.events]
        with db_session(app.state.config.db_file) as conn:
            result = ingest_sync_events(
                conn,
                source_id=payload.source_id,
                hostname=payload.hostname,
                events=events,
            )
        result["sent_at"] = payload.sent_at
        return result

    return app
