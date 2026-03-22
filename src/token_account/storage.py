from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect_db(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY,
            hostname TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            last_sync_at TEXT,
            total_events INTEGER NOT NULL DEFAULT 0,
            last_error TEXT
        );

        CREATE TABLE IF NOT EXISTS token_events (
            event_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            hostname TEXT NOT NULL,
            session_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            day TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            cached_input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            reasoning_output_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES sources(source_id)
        );

        CREATE TABLE IF NOT EXISTS sync_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            hostname TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            status TEXT NOT NULL,
            received_events INTEGER NOT NULL DEFAULT 0,
            inserted_events INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            FOREIGN KEY (source_id) REFERENCES sources(source_id)
        );

        CREATE INDEX IF NOT EXISTS idx_token_events_day ON token_events(day);
        CREATE INDEX IF NOT EXISTS idx_token_events_ts ON token_events(ts);
        CREATE INDEX IF NOT EXISTS idx_token_events_source_session ON token_events(source_id, session_id);
        CREATE INDEX IF NOT EXISTS idx_sync_runs_source_id ON sync_runs(source_id, finished_at DESC);
        """
    )
    conn.commit()


@contextmanager
def db_session(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    conn = connect_db(db_path)
    try:
        init_db(conn)
        yield conn
    finally:
        conn.close()


def upsert_source(conn: sqlite3.Connection, source_id: str, hostname: str) -> None:
    now = utc_now_iso()
    conn.execute(
        """
        INSERT INTO sources (source_id, hostname, first_seen_at, last_seen_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            hostname=excluded.hostname,
            last_seen_at=excluded.last_seen_at
        """,
        (source_id, hostname, now, now),
    )


def ingest_sync_events(
    conn: sqlite3.Connection,
    *,
    source_id: str,
    hostname: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    started_at = utc_now_iso()
    upsert_source(conn, source_id, hostname)
    created_at = utc_now_iso()
    inserted = 0
    status = "ok"
    error_message = None
    try:
        with conn:
            for event in events:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO token_events (
                        event_id, source_id, hostname, session_id, ts, day, model,
                        input_tokens, cached_input_tokens, output_tokens, reasoning_output_tokens,
                        total_tokens, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["event_id"],
                        source_id,
                        hostname,
                        event["session_id"],
                        event["ts"],
                        str(event["ts"])[:10],
                        event["model"],
                        int(event.get("input_tokens", 0) or 0),
                        int(event.get("cached_input_tokens", 0) or 0),
                        int(event.get("output_tokens", 0) or 0),
                        int(event.get("reasoning_output_tokens", 0) or 0),
                        int(event.get("total_tokens", 0) or 0),
                        created_at,
                    ),
                )
                inserted += cursor.rowcount or 0
            finished_at = utc_now_iso()
            conn.execute(
                """
                UPDATE sources
                SET hostname = ?,
                    last_seen_at = ?,
                    last_sync_at = ?,
                    total_events = total_events + ?,
                    last_error = NULL
                WHERE source_id = ?
                """,
                (hostname, finished_at, finished_at, inserted, source_id),
            )
            conn.execute(
                """
                INSERT INTO sync_runs (
                    source_id, hostname, started_at, finished_at, status,
                    received_events, inserted_events, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (source_id, hostname, started_at, finished_at, status, len(events), inserted, error_message),
            )
    except Exception as exc:
        status = "error"
        error_message = str(exc)
        finished_at = utc_now_iso()
        with conn:
            conn.execute(
                """
                UPDATE sources
                SET hostname = ?,
                    last_seen_at = ?,
                    last_error = ?
                WHERE source_id = ?
                """,
                (hostname, finished_at, error_message, source_id),
            )
            conn.execute(
                """
                INSERT INTO sync_runs (
                    source_id, hostname, started_at, finished_at, status,
                    received_events, inserted_events, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (source_id, hostname, started_at, finished_at, status, len(events), inserted, error_message),
            )
        raise
    return {
        "source_id": source_id,
        "hostname": hostname,
        "received_events": len(events),
        "inserted_events": inserted,
        "status": status,
        "finished_at": finished_at,
    }


def fetch_sources(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT source_id, hostname, first_seen_at, last_seen_at, last_sync_at, total_events, last_error
        FROM sources
        ORDER BY COALESCE(last_sync_at, last_seen_at) DESC, source_id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_event_bounds(conn: sqlite3.Connection) -> dict[str, str]:
    row = conn.execute(
        """
        SELECT MIN(day) AS start, MAX(day) AS end
        FROM token_events
        """
    ).fetchone()
    return {
        "start": str(row["start"] or ""),
        "end": str(row["end"] or ""),
    }


def fetch_events(
    conn: sqlite3.Connection,
    *,
    since: str | None = None,
    until: str | None = None,
) -> list[dict[str, Any]]:
    sql = """
        SELECT source_id, hostname, session_id, ts, day, model,
               input_tokens, cached_input_tokens, output_tokens,
               reasoning_output_tokens, total_tokens
        FROM token_events
    """
    params: list[Any] = []
    clauses: list[str] = []
    if since:
        clauses.append("day >= ?")
        params.append(since)
    if until:
        clauses.append("day <= ?")
        params.append(until)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY ts ASC, event_id ASC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]
