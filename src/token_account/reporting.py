from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from .legacy_report import (
    FIELDS,
    build_day_series,
    fmt_int,
    fmt_money,
    fmt_pct,
    parse_date,
    parse_iso,
    render_html,
)
from .pricing import cost_for_record, load_pricing, normalize_model_name
from .storage import fetch_events, fetch_sources


def collect_usage_from_rows(rows: list[dict[str, Any]]):
    totals = {field: 0 for field in FIELDS}
    daily = defaultdict(lambda: {field: 0 for field in FIELDS})
    hourly = defaultdict(int)
    models = defaultdict(lambda: {field: 0 for field in FIELDS})
    daily_models = defaultdict(lambda: defaultdict(lambda: {field: 0 for field in FIELDS}))
    hourly_daily = defaultdict(lambda: [0] * 24)
    active_days = set()
    session_spans: dict[tuple[str, str], list[date]] = {}
    sessions_in_range = set()
    events: list[dict[str, Any]] = []

    for row in rows:
        ts = parse_iso(row.get("ts"))
        if ts is None:
            continue
        day = ts.date()
        model = normalize_model_name(row.get("model"))
        delta = {field: int(row.get(field, 0) or 0) for field in FIELDS}
        for field in FIELDS:
            totals[field] += delta[field]
            daily[day][field] += delta[field]
            models[model][field] += delta[field]
            daily_models[day][model][field] += delta[field]
        hourly[ts.hour] += delta["total_tokens"]
        hourly_daily[day][ts.hour] += delta["total_tokens"]
        active_days.add(day)

        session_key = (str(row.get("source_id") or "unknown"), str(row.get("session_id") or "unknown"))
        sessions_in_range.add(session_key)
        span = session_spans.get(session_key)
        if span is None:
            session_spans[session_key] = [day, day]
        else:
            if day < span[0]:
                span[0] = day
            if day > span[1]:
                span[1] = day

        if delta["total_tokens"] > 0:
            events.append(
                {
                    "ts": ts.strftime("%Y-%m-%d %H:%M"),
                    "day": day.isoformat(),
                    "model": model,
                    "value": delta["total_tokens"],
                    "input": delta["input_tokens"],
                    "cached": delta["cached_input_tokens"],
                    "output": delta["output_tokens"],
                    "reasoning": delta["reasoning_output_tokens"],
                    "total": delta["total_tokens"],
                    "source_id": row.get("source_id"),
                }
            )

    session_span_list = [
        {
            "start": span[0].isoformat(),
            "end": span[1].isoformat(),
        }
        for span in session_spans.values()
    ]
    return {
        "totals": totals,
        "daily": daily,
        "hourly": hourly,
        "models": models,
        "daily_models": daily_models,
        "hourly_daily": hourly_daily,
        "active_days": active_days,
        "events": events,
        "session_spans": session_span_list,
        "sessions": len(sessions_in_range),
    }


def _pricing_payload(prices: dict[str, dict[str, Decimal]], aliases: dict[str, str]) -> dict[str, Any]:
    return {
        "prices": {
            model: {
                "input": float(entry["input"]),
                "cached_input": float(entry["cached_input"]) if entry["cached_input"] is not None else None,
                "output": float(entry["output"]),
                "long_context_threshold": entry.get("long_context_threshold"),
                "long_context_input": float(entry["long_context_input"]) if entry.get("long_context_input") is not None else None,
                "long_context_cached_input": float(entry["long_context_cached_input"]) if entry.get("long_context_cached_input") is not None else None,
                "long_context_output": float(entry["long_context_output"]) if entry.get("long_context_output") is not None else None,
            }
            for model, entry in prices.items()
        },
        "aliases": aliases,
    }


def build_report_document(
    rows: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    *,
    since: date | None,
    until: date | None,
    pricing_path: Path | None = None,
    source_label: str = "SQLite",
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    usage = collect_usage_from_rows(rows)
    active_days = usage["active_days"]
    empty = not active_days

    range_start = since or (min(active_days) if active_days else date.today())
    range_end = until or (max(active_days) if active_days else date.today())
    range_days = (range_end - range_start).days + 1

    daily_series = build_day_series(usage["daily"], range_end, max(1, range_days))
    hourly_values = [usage["hourly"].get(hour, 0) for hour in range(24)]
    hour_labels = [f"{hour:02d}" for hour in range(24)]

    prices, _, aliases = load_pricing(pricing_path)
    totals = usage["totals"]
    total_tokens = totals["total_tokens"]
    input_tokens = totals["input_tokens"]
    output_tokens = totals["output_tokens"]
    reasoning_tokens = totals["reasoning_output_tokens"]
    cached_tokens = totals["cached_input_tokens"]
    cache_rate = cached_tokens / input_tokens if input_tokens else 0

    total_cost = Decimal("0")
    for row in rows:
        cost = cost_for_record(str(row.get("model") or ""), row, prices, aliases)
        if cost is not None:
            total_cost += cost

    daily_models_serialized: dict[str, Any] = {}
    for day, model_map in usage["daily_models"].items():
        day_key = day.isoformat()
        daily_models_serialized[day_key] = {}
        for model, rec in model_map.items():
            daily_models_serialized[day_key][model] = {
                "input_tokens": rec["input_tokens"],
                "cached_input_tokens": rec["cached_input_tokens"],
                "output_tokens": rec["output_tokens"],
                "reasoning_output_tokens": rec["reasoning_output_tokens"],
                "total_tokens": rec["total_tokens"],
            }

    hourly_daily_serialized = {
        day.isoformat(): values
        for day, values in usage["hourly_daily"].items()
    }

    last_synced_at = ""
    if sources:
        candidates = [item.get("last_sync_at") or item.get("last_seen_at") for item in sources if item.get("last_sync_at") or item.get("last_seen_at")]
        if candidates:
            last_synced_at = max(candidates)

    generated_dt = parse_iso(last_synced_at) if last_synced_at else None
    if generated_dt is None and rows:
        generated_dt = parse_iso(rows[-1].get("ts"))
    if generated_dt is None:
        generated_dt = datetime.now()
    generated_at = generated_dt.strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "range": {
            "start": range_start.isoformat(),
            "end": range_end.isoformat(),
            "days": range_days,
        },
        "daily": daily_series,
        "daily_models": daily_models_serialized,
        "hourly": {"labels": hour_labels, "total": hourly_values},
        "hourly_daily": hourly_daily_serialized,
        "session_spans": usage["session_spans"],
        "events": usage["events"],
        "pricing": _pricing_payload(prices, aliases),
        "sources": sources,
        "meta": {
            "generated_at": generated_at,
            "source_path": source_label,
            "source_count": len(sources),
            "last_synced_at": last_synced_at,
            "data_stamp": f"{last_synced_at}:{len(rows)}:{range_start.isoformat()}:{range_end.isoformat()}",
        },
    }

    summary = {
        "range_text": f"{range_start.isoformat()} to {range_end.isoformat()}",
        "sessions": fmt_int(usage["sessions"]),
        "days_active": fmt_int(len(active_days)),
        "total_tokens": fmt_int(total_tokens),
        "input_tokens": fmt_int(input_tokens),
        "output_tokens": fmt_int(output_tokens),
        "reasoning_tokens": fmt_int(reasoning_tokens),
        "cached_tokens": fmt_int(cached_tokens),
        "cache_rate": fmt_pct(cache_rate),
        "avg_per_day": fmt_int(int(round(total_tokens / len(active_days)))) if active_days else "0",
        "avg_per_session": fmt_int(int(round(total_tokens / usage["sessions"]))) if usage["sessions"] else "0",
        "total_cost": fmt_money(total_cost),
        "generated_at": generated_at,
        "source_path": source_label,
    }
    return data, summary, empty


def build_report_from_database(
    conn,
    *,
    since_text: str | None = None,
    until_text: str | None = None,
    pricing_path: Path | None = None,
    source_label: str = "SQLite",
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    since = parse_date(since_text) if since_text else None
    until = parse_date(until_text) if until_text else None
    if since and until and since > until:
        raise ValueError("since must be earlier than until")
    rows = fetch_events(conn, since=since.isoformat() if since else None, until=until.isoformat() if until else None)
    sources = fetch_sources(conn)
    return build_report_document(rows, sources, since=since, until=until, pricing_path=pricing_path, source_label=source_label)


__all__ = [
    "build_report_document",
    "build_report_from_database",
    "render_html",
]
