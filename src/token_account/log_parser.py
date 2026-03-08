from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path
from typing import Any

from .legacy_report import FIELDS, default_codex_root, iter_token_deltas, normalize_model_name, to_local


def default_sessions_root(codex_home: str | Path | None = None) -> Path:
    if codex_home:
        return Path(codex_home) / "sessions"
    return default_codex_root() / "sessions"


def default_source_id() -> str:
    host = socket.gethostname().strip().lower() or "codex-host"
    safe = []
    for ch in host:
        if ch.isalnum() or ch in {"-", "_", "."}:
            safe.append(ch)
        else:
            safe.append("-")
    return "".join(safe).strip("-._") or "codex-host"


def iter_session_files(root: Path):
    if not root.exists():
        return
    for path in sorted(root.rglob("*.jsonl")):
        yield path


def build_event_id(source_id: str, session_id: str, ts_iso: str, model: str, delta: dict[str, int]) -> str:
    raw = json.dumps(
        {
            "source_id": source_id,
            "session_id": session_id,
            "ts": ts_iso,
            "model": model,
            "delta": {field: int(delta.get(field, 0) or 0) for field in FIELDS},
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def session_id_from_path(path: Path, session_root: Path) -> str:
    try:
        return path.relative_to(session_root).as_posix()
    except ValueError:
        return path.name


def file_fingerprint(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {
        "size": int(stat.st_size),
        "mtime_ns": int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))),
    }


def file_changed(path: Path, state_entry: dict[str, Any] | None) -> bool:
    if not state_entry:
        return True
    current = file_fingerprint(path)
    return current.get("size") != state_entry.get("size") or current.get("mtime_ns") != state_entry.get("mtime_ns")


def normalize_delta(delta: dict[str, int]) -> dict[str, int]:
    out = {field: max(0, int(delta.get(field, 0) or 0)) for field in FIELDS}
    if out["total_tokens"] <= 0 and any(out[field] > 0 for field in FIELDS if field != "total_tokens"):
        out["total_tokens"] = (
            out["input_tokens"]
            + out["cached_input_tokens"]
            + out["output_tokens"]
            + out["reasoning_output_tokens"]
        )
    return out


def extract_events_from_file(path: Path, session_root: Path, source_id: str, hostname: str) -> list[dict[str, Any]]:
    session_id = session_id_from_path(path, session_root)
    events: list[dict[str, Any]] = []
    for ts, delta, model in iter_token_deltas(path) or []:
        local = to_local(ts)
        if local is None:
            continue
        normalized = normalize_delta(delta)
        if not any(normalized.values()):
            continue
        model_name = normalize_model_name(model)
        ts_iso = local.isoformat()
        events.append(
            {
                "event_id": build_event_id(source_id, session_id, ts_iso, model_name, normalized),
                "session_id": session_id,
                "ts": ts_iso,
                "model": model_name,
                "input_tokens": normalized["input_tokens"],
                "cached_input_tokens": normalized["cached_input_tokens"],
                "output_tokens": normalized["output_tokens"],
                "reasoning_output_tokens": normalized["reasoning_output_tokens"],
                "total_tokens": normalized["total_tokens"],
                "hostname": hostname,
            }
        )
    return events


def scan_sync_events(
    session_root: Path,
    source_id: str,
    hostname: str,
    previous_state: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, int]]:
    previous_files = (previous_state or {}).get("files") or {}
    current_files: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    scanned = 0
    changed = 0

    for path in iter_session_files(session_root) or []:
        scanned += 1
        session_key = session_id_from_path(path, session_root)
        fingerprint = file_fingerprint(path)
        current_files[session_key] = fingerprint
        if not file_changed(path, previous_files.get(session_key)):
            continue
        changed += 1
        events.extend(extract_events_from_file(path, session_root, source_id, hostname))

    next_state = {
        "source_id": source_id,
        "hostname": hostname,
        "session_root": str(session_root),
        "files": current_files,
    }
    stats = {
        "scanned_files": scanned,
        "changed_files": changed,
        "event_count": len(events),
    }
    return events, next_state, stats
