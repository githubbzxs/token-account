from __future__ import annotations

from pathlib import Path
from threading import Lock, Thread
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .reporting import build_dashboard_payload, build_report_from_database, render_html
from .storage import db_session, fetch_default_report_stamp, fetch_sources, ingest_sync_events


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


SHELL_SUMMARY = {
    "range_text": "--",
    "sessions": "--",
    "days_active": "--",
    "total_tokens": "--",
    "input_tokens": "--",
    "output_tokens": "--",
    "reasoning_tokens": "--",
    "cached_tokens": "--",
    "cache_rate": "--",
    "avg_per_day": "--",
    "avg_per_session": "--",
    "total_cost": "--",
    "generated_at": "",
    "source_path": "",
}


class DefaultReportCache:
    def __init__(self, config: ServiceConfig) -> None:
        self._config = config
        self._lock = Lock()
        self._default_report: tuple[dict[str, Any], dict[str, Any], bool] | None = None
        self._default_stamp = ""
        self._refreshing = False

    def _pricing_path(self) -> Path | None:
        if not self._config.pricing_file:
            return None
        return Path(self._config.pricing_file)

    def _build_default_report(self) -> tuple[tuple[dict[str, Any], dict[str, Any], bool], str]:
        with db_session(self._config.db_file) as conn:
            report = build_report_from_database(
                conn,
                pricing_path=self._pricing_path(),
                source_label=self._config.db_file,
            )
            stamp = fetch_default_report_stamp(conn)
        return report, stamp

    def _current_stamp(self) -> str:
        with db_session(self._config.db_file) as conn:
            return fetch_default_report_stamp(conn)

    def _store(self, report: tuple[dict[str, Any], dict[str, Any], bool], stamp: str) -> None:
        with self._lock:
            self._default_report = report
            self._default_stamp = stamp

    def _refresh_worker(self) -> None:
        try:
            report, stamp = self._build_default_report()
            self._store(report, stamp)
        finally:
            with self._lock:
                self._refreshing = False

    def schedule_refresh(self) -> bool:
        with self._lock:
            if self._refreshing:
                return False
            self._refreshing = True
        Thread(target=self._refresh_worker, daemon=True).start()
        return True

    def get_default(self) -> tuple[dict[str, Any], dict[str, Any], bool]:
        current_stamp = self._current_stamp()
        with self._lock:
            cached = self._default_report
            cached_stamp = self._default_stamp
        if cached is None:
            report, stamp = self._build_default_report()
            self._store(report, stamp)
            return report
        if cached_stamp != current_stamp:
            self.schedule_refresh()
        return cached


def create_app(*, db_file: str | Path, pricing_file: str | Path | None = None) -> FastAPI:
    config = ServiceConfig(
        db_file=str(Path(db_file)),
        pricing_file=str(Path(pricing_file)) if pricing_file else None,
    )
    app = FastAPI(title="Codex Token Usage Service", version="1.0.0")
    app.state.config = config
    app.state.default_report_cache = DefaultReportCache(config)

    @app.on_event("startup")
    def warm_default_report_cache() -> None:
        app.state.default_report_cache.get_default()

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        data, summary, empty = app.state.default_report_cache.get_default()
        return HTMLResponse(render_html(data, summary, empty))

    @app.get("/api/dashboard")
    def api_dashboard(
        since: str | None = Query(default=None, description="起始日期，格式 YYYY-MM-DD"),
        until: str | None = Query(default=None, description="结束日期，格式 YYYY-MM-DD"),
    ) -> dict[str, Any]:
        try:
            if since is None and until is None:
                data, summary, empty = app.state.default_report_cache.get_default()
                return build_dashboard_payload(data, summary, empty)
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
            if since is None and until is None:
                data, _, _ = app.state.default_report_cache.get_default()
                return data
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
            if since is None and until is None:
                data, _, _ = app.state.default_report_cache.get_default()
                return data
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
        app.state.default_report_cache.schedule_refresh()
        result["sent_at"] = payload.sent_at
        return result

    return app
