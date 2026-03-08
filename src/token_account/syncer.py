from __future__ import annotations

import json
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

from .log_parser import default_sessions_root, default_source_id, scan_sync_events


DEFAULT_SERVICE_URL = "http://127.0.0.1:8000"


def default_state_path(codex_home: str | Path | None = None) -> Path:
    base = Path(codex_home) if codex_home else Path.home() / ".codex"
    return base / "token-account-sync-state.json"


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def chunked(items: list[dict[str, Any]], size: int):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"同步失败：HTTP {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"同步失败：{exc.reason}") from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"同步失败：服务返回非 JSON 内容：{body[:200]}") from exc


def run_sync_once(
    *,
    service_url: str,
    sessions_root: str | Path | None,
    codex_home: str | Path | None,
    state_file: str | Path | None,
    source_id: str | None,
    hostname: str | None,
    batch_size: int,
    timeout: int,
) -> dict[str, Any]:
    session_root = Path(sessions_root) if sessions_root else default_sessions_root(codex_home)
    state_path = Path(state_file) if state_file else default_state_path(codex_home)
    source_key = source_id or default_source_id()
    host_name = hostname or socket.gethostname()

    previous_state = load_state(state_path)
    events, next_state, stats = scan_sync_events(session_root, source_key, host_name, previous_state)
    if not events:
        next_state["last_synced_at"] = datetime.now(timezone.utc).isoformat()
        save_state(state_path, next_state)
        return {
            "service_url": service_url,
            "session_root": str(session_root),
            "state_file": str(state_path),
            "source_id": source_key,
            "hostname": host_name,
            "received_events": 0,
            "inserted_events": 0,
            **stats,
        }

    total_inserted = 0
    endpoint = service_url.rstrip("/") + "/api/sync/events"
    sent_at = datetime.now(timezone.utc).isoformat()
    for batch in chunked(events, max(1, batch_size)):
        response = post_json(
            endpoint,
            {
                "source_id": source_key,
                "hostname": host_name,
                "sent_at": sent_at,
                "events": batch,
            },
            timeout,
        )
        total_inserted += int(response.get("inserted_events", 0) or 0)

    next_state["last_synced_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state_path, next_state)
    return {
        "service_url": service_url,
        "session_root": str(session_root),
        "state_file": str(state_path),
        "source_id": source_key,
        "hostname": host_name,
        "received_events": len(events),
        "inserted_events": total_inserted,
        **stats,
    }


def run_sync_loop(
    *,
    service_url: str,
    sessions_root: str | Path | None,
    codex_home: str | Path | None,
    state_file: str | Path | None,
    source_id: str | None,
    hostname: str | None,
    batch_size: int,
    timeout: int,
    interval: int,
) -> None:
    while True:
        started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            result = run_sync_once(
                service_url=service_url,
                sessions_root=sessions_root,
                codex_home=codex_home,
                state_file=state_file,
                source_id=source_id,
                hostname=hostname,
                batch_size=batch_size,
                timeout=timeout,
            )
            print(
                f"[{started}] 同步完成：收到 {result['received_events']} 条，写入 {result['inserted_events']} 条，"
                f"扫描 {result['scanned_files']} 个文件，命中 {result['changed_files']} 个变更文件。"
            )
        except Exception as exc:
            print(f"[{started}] 同步失败：{exc}")
        time.sleep(max(5, interval))
