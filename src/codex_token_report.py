#!/usr/bin/env python3
from __future__ import annotations

import argparse
import heapq
import html
import json
import os
import re
import sys
from collections import defaultdict
from decimal import Decimal
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

FIELDS = [
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
]

MIX = [
    ("input_tokens", "input", "#22D3EE"),
    ("output_tokens", "output", "#FB7185"),
    ("reasoning_output_tokens", "reasoning", "#F59E0B"),
    ("cached_input_tokens", "cached", "#34D399"),
]

MODEL_COLORS = [
    "#22D3EE",
    "#FB7185",
    "#F59E0B",
    "#34D399",
    "#60A5FA",
    "#A78BFA",
    "#F97316",
    "#2DD4BF",
    "#E879F9",
    "#38BDF8",
]

I18N = {
    "zh": {
        "title": "Codex Token 用量",
        "subtitle": "基于本地 Codex CLI 日志的可视化报告",
        "range": "范围",
        "sessions": "会话数",
        "active_days": "活跃天数",
        "card_total": "总 token",
        "card_cached": "缓存与推理",
        "card_avg": "平均值",
        "card_cost": "估算成本 (USD)",
        "input": "输入",
        "output": "输出",
        "reasoning": "推理",
        "cached": "缓存",
        "cache_rate": "缓存率",
        "per_day": "每日",
        "per_session": "每会话",
        "pricing_source": "价格来源",
        "source_path": "日志路径",
        "from": "起始",
        "to": "结束",
        "apply": "应用",
        "last_7": "近 7 天",
        "last_30": "近 30 天",
        "last_90": "近 90 天",
        "all_time": "全部时间",
        "export": "导出",
        "import": "导入",
        "import_done": "已合并 {count} 个文件",
        "import_invalid": "导入文件格式不正确",
        "import_failed": "导入失败",
        "daily_chart": "每日总 token",
        "zoom_hint": "支持鼠标滚轮缩放",
        "mix_chart": "Token 构成",
        "hourly_chart": "小时分布",
        "model_mix": "模型占比",
        "top_days": "高峰日期",
        "top_spikes": "尖峰时刻",
        "model_table": "模型明细",
        "table_model": "模型",
        "table_tokens": "总 token",
        "table_input": "输入",
        "table_output": "输出",
        "table_cached": "缓存",
        "table_reasoning": "推理",
        "table_cost": "估算成本",
        "no_data": "无数据",
        "note_reasoning": "推理 token 按输出价格计费",
        "empty_banner": "该时间范围内没有 token 使用记录",
        "no_data": "无数据",
        "other": "其他",
        "total_label": "总计",
    },
    "en": {
        "title": "Codex Token Usage",
        "subtitle": "Visual report from local Codex CLI logs",
        "range": "Range",
        "sessions": "Sessions",
        "active_days": "Active days",
        "card_total": "Total tokens",
        "card_cached": "Cached and reasoning",
        "card_avg": "Averages",
        "card_cost": "Estimated cost (USD)",
        "input": "Input",
        "output": "Output",
        "reasoning": "Reasoning",
        "cached": "Cached",
        "cache_rate": "Cache rate",
        "per_day": "Per day",
        "per_session": "Per session",
        "pricing_source": "Pricing source",
        "source_path": "Log path",
        "from": "From",
        "to": "To",
        "apply": "Apply",
        "last_7": "Last 7d",
        "last_30": "Last 30d",
        "last_90": "Last 90d",
        "all_time": "All time",
        "export": "Export",
        "import": "Import",
        "import_done": "Merged {count} file(s)",
        "import_invalid": "Invalid import file",
        "import_failed": "Import failed",
        "daily_chart": "Daily total tokens",
        "zoom_hint": "Use mouse wheel to zoom",
        "mix_chart": "Token mix",
        "hourly_chart": "Hourly pattern",
        "model_mix": "Model share",
        "top_days": "Top days",
        "top_spikes": "Top spikes",
        "model_table": "Model breakdown",
        "table_model": "Model",
        "table_tokens": "Total tokens",
        "table_input": "Input",
        "table_output": "Output",
        "table_cached": "Cached",
        "table_reasoning": "Reasoning",
        "table_cost": "Estimated cost",
        "no_data": "No data",
        "note_reasoning": "Reasoning tokens billed as output",
        "empty_banner": "No token usage found in this range.",
        "no_data": "No data",
        "other": "Other",
        "total_label": "Total",
    },
}

def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Invalid date: {value}. Use YYYY-MM-DD.") from exc


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def to_local(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()


PAREN_SUFFIX_RE = re.compile(r"\s*[\(\（][^\)\）]*[\)\）]\s*")


def normalize_model_name(model: str | None) -> str:
    name = str(model or "").strip()
    if not name:
        return "unknown"
    head, sep, tail = name.partition(":")
    head = PAREN_SUFFIX_RE.sub(" ", head)
    head = re.sub(r"\s+", " ", head).strip()
    if not head:
        head = "unknown"
    if not sep:
        return head
    tail = tail.strip()
    if not tail:
        return head
    return f"{head}:{tail}"

def default_codex_root() -> Path:
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env)
    return Path.home() / ".codex"

PRICING_DEFAULT = {
    "tier": "standard",
    "currency": "USD",
    "source_url": "https://platform.openai.com/pricing",
    "source_date": "2025-12-27",
    "aliases": {
        "gpt-5.2-codex": "gpt-5.2",
        "gpt-5.3-codex": "gpt-5.2",
        "gpt-5.3-codex-latest": "gpt-5.2",
    },
    "prices": {
        "gpt-5.2": {"input": "1.75", "cached_input": "0.175", "output": "14.00"},
        "gpt-5.1": {"input": "1.25", "cached_input": "0.125", "output": "10.00"},
        "gpt-5": {"input": "1.25", "cached_input": "0.125", "output": "10.00"},
        "gpt-5-mini": {"input": "0.25", "cached_input": "0.025", "output": "2.00"},
        "gpt-5-nano": {"input": "0.05", "cached_input": "0.005", "output": "0.40"},
        "gpt-5.2-chat-latest": {"input": "1.75", "cached_input": "0.175", "output": "14.00"},
        "gpt-5.1-chat-latest": {"input": "1.25", "cached_input": "0.125", "output": "10.00"},
        "gpt-5-chat-latest": {"input": "1.25", "cached_input": "0.125", "output": "10.00"},
        "gpt-5.1-codex-max": {"input": "1.25", "cached_input": "0.125", "output": "10.00"},
        "gpt-5.1-codex": {"input": "1.25", "cached_input": "0.125", "output": "10.00"},
        "gpt-5-codex": {"input": "1.25", "cached_input": "0.125", "output": "10.00"},
        "gpt-5.1-codex-mini": {"input": "0.25", "cached_input": "0.025", "output": "2.00"},
        "codex-mini-latest": {"input": "1.50", "cached_input": "0.375", "output": "6.00"},
        "gpt-5.2-pro": {"input": "21.00", "cached_input": None, "output": "168.00"},
        "gpt-5-pro": {"input": "15.00", "cached_input": None, "output": "120.00"},
        "gpt-4.1": {"input": "2.00", "cached_input": "0.50", "output": "8.00"},
        "gpt-4.1-mini": {"input": "0.40", "cached_input": "0.10", "output": "1.60"},
        "gpt-4.1-nano": {"input": "0.10", "cached_input": "0.025", "output": "0.40"},
        "gpt-4o": {"input": "2.50", "cached_input": "1.25", "output": "10.00"},
        "gpt-4o-mini": {"input": "0.15", "cached_input": "0.075", "output": "0.60"},
        "gpt-4o-2024-05-13": {"input": "5.00", "cached_input": None, "output": "15.00"},
        "gpt-realtime": {"input": "4.00", "cached_input": "0.40", "output": "16.00"},
        "gpt-realtime-mini": {"input": "0.60", "cached_input": "0.06", "output": "2.40"},
        "gpt-4o-realtime-preview": {"input": "5.00", "cached_input": "2.50", "output": "20.00"},
        "gpt-4o-mini-realtime-preview": {"input": "0.60", "cached_input": "0.30", "output": "2.40"},
        "gpt-audio": {"input": "2.50", "cached_input": None, "output": "10.00"},
        "gpt-audio-mini": {"input": "0.60", "cached_input": None, "output": "2.40"},
        "o1": {"input": "15.00", "cached_input": "7.50", "output": "60.00"},
        "o1-pro": {"input": "150.00", "cached_input": None, "output": "600.00"},
        "o1-mini": {"input": "1.10", "cached_input": "0.55", "output": "4.40"},
        "o3": {"input": "2.00", "cached_input": "0.50", "output": "8.00"},
        "o3-pro": {"input": "20.00", "cached_input": None, "output": "80.00"},
        "o3-mini": {"input": "1.10", "cached_input": "0.55", "output": "4.40"},
        "o3-deep-research": {"input": "10.00", "cached_input": "2.50", "output": "40.00"},
        "o4-mini": {"input": "1.10", "cached_input": "0.275", "output": "4.40"},
        "o4-mini-deep-research": {"input": "2.00", "cached_input": "0.50", "output": "8.00"},
    },
}


def load_pricing(pricing_path: Path | None):
    doc = PRICING_DEFAULT
    if pricing_path and pricing_path.exists():
        try:
            doc = json.loads(pricing_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            doc = PRICING_DEFAULT
    else:
        local = Path("pricing.json")
        if local.exists():
            try:
                doc = json.loads(local.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                doc = PRICING_DEFAULT

    meta = {
        "tier": doc.get("tier", "standard"),
        "currency": doc.get("currency", "USD"),
        "source_url": doc.get("source_url", PRICING_DEFAULT["source_url"]),
        "source_date": doc.get("source_date", PRICING_DEFAULT["source_date"]),
    }
    prices = {}
    aliases = doc.get("aliases") or {}
    for model, entry in (doc.get("prices") or {}).items():
        if not entry:
            continue
        input_price = Decimal(str(entry.get("input", "0")))
        cached_raw = entry.get("cached_input")
        cached_price = None
        if cached_raw not in (None, "", "-"):
            cached_price = Decimal(str(cached_raw))
        output_price = Decimal(str(entry.get("output", "0")))
        prices[model] = {
            "input": input_price,
            "cached_input": cached_price,
            "output": output_price,
        }
    return prices, meta, aliases


def resolve_pricing(model: str, prices: dict, aliases: dict) -> dict | None:
    model = normalize_model_name(model)
    if model in aliases:
        alias_target = aliases.get(model)
        if alias_target in prices:
            return prices[alias_target]
    if model in prices:
        return prices[model]
    base = model.split(":")[0]
    if base in prices:
        return prices[base]
    for key in prices.keys():
        if base.startswith(key + "-"):
            return prices[key]
    if "gpt-5.3" in base:
        return prices.get("gpt-5.2") or prices.get("gpt-5")
    if "gpt-5.2" in base:
        return prices.get("gpt-5.2")
    if "gpt-5.1" in base:
        return prices.get("gpt-5.1")
    if base.startswith("gpt-5"):
        return prices.get("gpt-5")
    return None

def iter_session_files(root: Path):
    if not root.exists():
        return
    for path in root.rglob("*.jsonl"):
        yield path


def iter_token_deltas(path: Path):
    prev_total = None
    current_model = "unknown"
    try:
        handle = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_type = obj.get("type")
            if event_type == "turn_context":
                payload = obj.get("payload") or {}
                model = (
                    payload.get("model")
                    or payload.get("model_name")
                    or payload.get("model_id")
                )
                if model:
                    current_model = normalize_model_name(model)
                continue
            if event_type != "event_msg":
                continue
            payload = obj.get("payload", {})
            if payload.get("type") != "token_count":
                continue
            info = payload.get("info") or {}
            total = info.get("total_token_usage") or {}
            total_map = {k: int(total.get(k, 0) or 0) for k in FIELDS}
            if prev_total is None:
                delta = total_map
            else:
                delta = {k: max(0, total_map[k] - prev_total.get(k, 0)) for k in FIELDS}
            prev_total = total_map
            ts = parse_iso(obj.get("timestamp") or payload.get("timestamp"))
            if ts is None:
                continue
            yield ts, delta, current_model

def collect_usage(session_root: Path, since: date | None, until: date | None):
    totals = {k: 0 for k in FIELDS}
    daily = defaultdict(lambda: {k: 0 for k in FIELDS})
    hourly = defaultdict(int)
    models = defaultdict(lambda: {k: 0 for k in FIELDS})
    daily_models = defaultdict(lambda: defaultdict(lambda: {k: 0 for k in FIELDS}))
    hourly_daily = defaultdict(lambda: [0] * 24)
    active_days = set()
    sessions_in_range = set()
    session_spans = {}
    first_ts = None
    last_ts = None
    top_events = []
    events = []

    for path in iter_session_files(session_root) or []:
        file_has_range = False
        for ts, delta, model in iter_token_deltas(path) or []:
            local = to_local(ts)
            if local is None:
                continue
            day = local.date()
            in_range = True
            if since and day < since:
                in_range = False
            if until and day > until:
                in_range = False
            if not in_range:
                continue
            file_has_range = True
            for key in FIELDS:
                totals[key] += delta[key]
                daily[day][key] += delta[key]
                models[model][key] += delta[key]
                daily_models[day][model][key] += delta[key]
            hourly[local.hour] += delta["total_tokens"]
            hourly_daily[day][local.hour] += delta["total_tokens"]
            active_days.add(day)
            if first_ts is None or local < first_ts:
                first_ts = local
            if last_ts is None or local > last_ts:
                last_ts = local
            dtokens = delta["total_tokens"]
            if dtokens > 0:
                events.append(
                    {
                        "ts": local.strftime("%Y-%m-%d %H:%M"),
                        "day": day.isoformat(),
                        "value": dtokens,
                    }
                )
                heapq.heappush(top_events, (dtokens, local))
                if len(top_events) > 5:
                    heapq.heappop(top_events)
            span = session_spans.get(path)
            if span is None:
                session_spans[path] = [day, day]
            else:
                if day < span[0]:
                    span[0] = day
                if day > span[1]:
                    span[1] = day
        if file_has_range:
            sessions_in_range.add(path)

    top_events_sorted = sorted(top_events, key=lambda item: item[0], reverse=True)
    session_span_list = [
        {"start": span[0].isoformat(), "end": span[1].isoformat()}
        for span in session_spans.values()
    ]
    return {
        "totals": totals,
        "daily": daily,
        "hourly": hourly,
        "models": models,
        "daily_models": daily_models,
        "hourly_daily": hourly_daily,
        "session_spans": session_span_list,
        "active_days": active_days,
        "sessions": len(sessions_in_range),
        "first_ts": first_ts,
        "last_ts": last_ts,
        "top_events": top_events_sorted,
        "events": events,
    }

def build_day_series(daily, end_date: date, days: int):
    labels = []
    total = []
    inputs = []
    outputs = []
    reasoning = []
    cached = []
    days = max(1, days)
    for offset in range(days):
        day = end_date - timedelta(days=days - 1 - offset)
        labels.append(day.isoformat())
        record = daily.get(day, {k: 0 for k in FIELDS})
        total.append(record["total_tokens"])
        inputs.append(record["input_tokens"])
        outputs.append(record["output_tokens"])
        reasoning.append(record["reasoning_output_tokens"])
        cached.append(record["cached_input_tokens"])
    return {
        "labels": labels,
        "total": total,
        "input": inputs,
        "output": outputs,
        "reasoning": reasoning,
        "cached": cached,
    }


def fmt_int(value: int) -> str:
    n = int(value)
    abs_n = abs(n)
    if abs_n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}".rstrip("0").rstrip(".") + "B"
    if abs_n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    return f"{n:,}"


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def dollars_from_tokens(tokens: int, price_per_million: Decimal) -> Decimal:
    return (Decimal(tokens) / Decimal(1_000_000)) * price_per_million


def fmt_money(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    if value >= Decimal("1"):
        return f"${value:.2f}"
    return f"${value:.4f}"

def render_html(data: dict, summary: dict, empty: bool) -> str:
    top_days_html = summary.get("top_days_html", "")
    top_events_html = summary.get("top_events_html", "")
    empty_banner = ""
    data_json = json.dumps(data, separators=(",", ":"))
    i18n_json = json.dumps(I18N, ensure_ascii=False, separators=(",", ":"))     
    source_path = html.escape(summary.get("source_path", ""))
    template = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Codex Token Report</title>
<style>
:root {
  --background: #09090b;
  --surface: #0f1115;
  --surface-soft: #12161f;
  --surface-strong: #171c27;
  --text: #f4f4f5;
  --muted: #a1a1aa;
  --stroke: rgba(148, 163, 184, 0.22);
  --accent: #22d3ee;
  --accent-2: #fb7185;
  --accent-3: #34d399;
  --shadow: 0 22px 52px rgba(2, 6, 23, 0.5);
  --ring: rgba(34, 211, 238, 0.35);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background:
    radial-gradient(1200px 620px at 12% 0%, rgba(34, 211, 238, 0.18), transparent 58%),
    radial-gradient(1000px 580px at 92% 5%, rgba(251, 113, 133, 0.16), transparent 62%),
    linear-gradient(165deg, #09090b 0%, #0d111a 100%);
  color: var(--text);
  font-family: "IBM Plex Sans", "Noto Sans SC", "Segoe UI", sans-serif;
  line-height: 1.45;
}

.page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 34px 24px 56px;
}

.hero {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 12px;
}

.lang-toggle {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  padding: 4px;
  border: 1px solid var(--stroke);
  border-radius: 999px;
  background: rgba(15, 17, 21, 0.78);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.lang-toggle button {
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.04);
  color: var(--muted);
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.lang-toggle button.active {
  background: rgba(34, 211, 238, 0.2);
  color: #ecfeff;
  border-color: transparent;
  box-shadow: 0 0 0 1px var(--ring);
}

.title h1 {
  margin: 0 0 8px;
  font-size: clamp(30px, 5vw, 42px);
  letter-spacing: 0.5px;
  font-family: "Space Grotesk", "IBM Plex Sans", "Noto Sans SC", sans-serif;
  font-weight: 700;
  text-wrap: balance;
}

.title p {
  margin: 0;
  color: var(--muted);
  max-width: 680px;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.04);
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 13px;
  color: #d4d4d8;
  backdrop-filter: blur(6px);
}

.banner {
  margin-top: 18px;
  padding: 12px 14px;
  border: 1px dashed var(--stroke);
  background: rgba(251, 113, 133, 0.08);
  border-radius: 12px;
  color: #fecdd3;
}

.hidden {
  display: none;
}

.range-controls {
  margin: 18px 0 10px;
  padding: 14px 16px;
  border: 1px solid var(--stroke);
  background: linear-gradient(140deg, rgba(23, 28, 39, 0.84), rgba(15, 17, 21, 0.82));
  border-radius: 16px;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  box-shadow: var(--shadow);
}

.range-fields {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--muted);
}

.range-fields input {
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text);
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 12px;
}

.range-controls button,
.file-button {
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.05);
  color: #e4e4e7;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.range-controls button:hover,
.file-button:hover {
  border-color: rgba(34, 211, 238, 0.5);
  background: rgba(34, 211, 238, 0.15);
}

.range-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.range-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.file-button {
  color: var(--text);
}

.file-button input {
  display: none;
}

.import-status {
  font-size: 12px;
  color: var(--muted);
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin: 24px 0 24px;
}

.card {
  background: linear-gradient(145deg, rgba(23, 28, 39, 0.92), rgba(18, 22, 31, 0.88));
  border: 1px solid var(--stroke);
  border-radius: 20px;
  padding: 16px 18px;
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
  animation: rise 0.8s ease both;
  animation-delay: var(--delay, 0s);
}

.card::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.07), transparent 65%);
  pointer-events: none;
}

.card .label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--muted);
}

.card .value {
  margin-top: 10px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.card .sub {
  margin-top: 8px;
  color: #b4b4bd;
  font-size: 13px;
  line-height: 1.4;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 18px;
}

.panel {
  background: linear-gradient(150deg, rgba(20, 24, 33, 0.94), rgba(16, 19, 27, 0.9));
  border: 1px solid var(--stroke);
  border-radius: 20px;
  padding: 18px;
  box-shadow: var(--shadow);
  animation: rise 0.9s ease both;
  animation-delay: var(--delay, 0s);
}

.panel h3 {
  margin: 0 0 12px;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.panel.wide {
  grid-column: span 2;
}

.chart {
  width: 100%;
  height: 240px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 14px;
  background: rgba(15, 17, 21, 0.75);
  overflow: hidden;
}

.chart.small {
  height: 200px;
}

.chart.zoomable {
  cursor: zoom-in;
}

.chart-tip {
  margin-top: 10px;
  font-size: 12px;
  color: var(--muted);
}

.legend {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 8px;
  font-size: 13px;
  color: var(--muted);
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.legend i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.list li {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px dashed rgba(148, 163, 184, 0.2);
  font-size: 13px;
}

.list li:last-child {
  border-bottom: none;
}

.note {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 10px;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.table th,
.table td {
  padding: 8px 6px;
  border-bottom: 1px dashed rgba(148, 163, 184, 0.2);
  text-align: left;
}

.table th {
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 11px;
  color: var(--muted);
}

.table td:last-child {
  text-align: right;
  font-weight: 600;
}

.muted {
  color: var(--muted);
}

.footer {
  margin-top: 24px;
  font-size: 12px;
  color: var(--muted);
  text-align: right;
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 900px) {
  .page {
    padding: 24px 14px 42px;
  }
  .hero {
    gap: 12px;
  }
  .panel.wide {
    grid-column: span 1;
  }
  .chart {
    height: 200px;
  }
  .chart.small {
    height: 180px;
  }
  .range-controls {
    gap: 10px;
  }
}
</style>
</head>
<body>
<div class="page">
  <div class="hero">
    <div class="title">
      <h1 data-i18n="title">Codex Token Usage</h1>
      <p data-i18n="subtitle">Local report from Codex CLI session logs</p>
    </div>
    <div class="meta">
      <div class="pill"><span data-i18n="range">Range</span>: <span id="range-text">__RANGE_TEXT__</span></div>
      <div class="pill"><span data-i18n="sessions">Sessions</span>: <span id="sessions-count">__SESSIONS__</span></div>
      <div class="pill"><span data-i18n="active_days">Active days</span>: <span id="active-days">__DAYS_ACTIVE__</span></div>
    </div>
    <div class="lang-toggle">
      <button type="button" data-lang="zh">中文</button>
      <button type="button" data-lang="en">EN</button>
    </div>
  </div>
  <div class="range-controls">
    <div class="range-fields">
      <label><span data-i18n="from">From</span> <input type="date" id="range-start"></label>
      <label><span data-i18n="to">To</span> <input type="date" id="range-end"></label>
      <button type="button" id="apply-range" data-i18n="apply">Apply</button>
    </div>
    <div class="range-buttons">
      <button type="button" data-range="7" data-i18n="last_7">Last 7d</button>
      <button type="button" data-range="30" data-i18n="last_30">Last 30d</button>
      <button type="button" data-range="90" data-i18n="last_90">Last 90d</button>
      <button type="button" data-range="all" data-i18n="all_time">All time</button>
    </div>
    <div class="range-actions">
      <button type="button" id="export-data" data-i18n="export">Export</button>
      <label class="file-button"><span data-i18n="import">Import</span>
        <input type="file" id="import-data" accept="application/json" multiple>
      </label>
      <span class="import-status" id="import-status"></span>
    </div>
  </div>
  __EMPTY_BANNER__
  <div class="banner hidden" id="range-banner" data-i18n="empty_banner">No token usage found in this range.</div>
  <div class="cards">
    <div class="card" style="--delay:0.05s">
      <div class="label" data-i18n="card_total">Total tokens</div>
      <div class="value" id="value-total">__TOTAL_TOKENS__</div>
      <div class="sub"><span data-i18n="input">Input</span> <span id="value-input">__INPUT_TOKENS__</span> | <span data-i18n="output">Output</span> <span id="value-output">__OUTPUT_TOKENS__</span></div>
    </div>
    <div class="card" style="--delay:0.1s">
      <div class="label" data-i18n="card_cached">Cached and reasoning</div>
      <div class="value" id="value-cached">__CACHED_TOKENS__</div>
      <div class="sub"><span data-i18n="reasoning">Reasoning</span> <span id="value-reasoning">__REASONING_TOKENS__</span> | <span data-i18n="cache_rate">Cache rate</span> <span id="value-cache-rate">__CACHE_RATE__</span></div>
    </div>
    <div class="card" style="--delay:0.15s">
      <div class="label" data-i18n="card_avg">Averages</div>
      <div class="value" id="value-avg-day">__AVG_PER_DAY__</div>
      <div class="sub"><span data-i18n="per_day">Per day</span> | <span data-i18n="per_session">Per session</span> <span id="value-avg-session">__AVG_PER_SESSION__</span></div>
    </div>
    <div class="card" style="--delay:0.2s">
      <div class="label" data-i18n="card_cost">Estimated cost (USD)</div>
      <div class="value" id="value-cost">__TOTAL_COST__</div>
      <div class="sub"><span data-i18n="pricing_source">Pricing source</span> <span id="value-pricing">__PRICING_SOURCE__</span></div>
    </div>
  </div>

  <div class="panel-grid">
    <div class="panel wide" style="--delay:0.25s">
      <h3 data-i18n="daily_chart">Daily total tokens</h3>
      <div id="chart-daily" class="chart zoomable"></div>
      <div class="chart-tip" data-i18n="zoom_hint">Use mouse wheel to zoom</div>
    </div>
    <div class="panel" style="--delay:0.3s">
      <h3 data-i18n="mix_chart">Token mix</h3>
      <div id="chart-mix" class="chart small"></div>
      <div id="legend-mix" class="legend"></div>
    </div>
    <div class="panel" style="--delay:0.33s">
      <h3 data-i18n="model_mix">Model share</h3>
      <div id="chart-models" class="chart small"></div>
      <div id="legend-models" class="legend"></div>
    </div>
    <div class="panel" style="--delay:0.37s">
      <h3 data-i18n="hourly_chart">Hourly pattern</h3>
      <div id="chart-hourly" class="chart small zoomable"></div>
      <div class="chart-tip" data-i18n="zoom_hint">Use mouse wheel to zoom</div>
    </div>
    <div class="panel" style="--delay:0.41s">
      <h3 data-i18n="top_days">Top days</h3>
      <ul class="list" id="list-top-days">
__TOP_DAYS__
      </ul>
    </div>
    <div class="panel" style="--delay:0.45s">
      <h3 data-i18n="top_spikes">Top spikes</h3>
      <ul class="list" id="list-top-spikes">
__TOP_EVENTS__
      </ul>
    </div>
    <div class="panel wide" style="--delay:0.5s">
      <h3 data-i18n="model_table">Model breakdown</h3>
      <div class="note" data-i18n="note_reasoning">Reasoning tokens billed as output</div>
      <table class="table">
        <thead>
          <tr>
            <th data-i18n="table_model">Model</th>
            <th data-i18n="table_tokens">Total tokens</th>
            <th data-i18n="table_input">Input</th>
            <th data-i18n="table_output">Output</th>
            <th data-i18n="table_cached">Cached</th>
            <th data-i18n="table_reasoning">Reasoning</th>
            <th data-i18n="table_cost">Estimated cost</th>
          </tr>
        </thead>
        <tbody id="table-models">
__MODEL_TABLE__
        </tbody>
      </table>
    </div>
  </div>

  <div class="footer">Generated __GENERATED_AT__</div>
</div>
<script>
const DATA = __DATA_JSON__;
const I18N = __I18N_JSON__;
let currentLang = "zh";
const CHART_AXIS_TEXT = "#94a3b8";
const CHART_AXIS_LINE = "rgba(148,163,184,0.28)";
const CHART_CENTER_TEXT = "#f4f4f5";

function formatNumber(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0";
  const absNum = Math.abs(num);
  if (absNum >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(1).replace(/\\.0$/, "")}B`;
  }
  if (absNum >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1).replace(/\\.0$/, "")}M`;
  }
  return new Intl.NumberFormat("en-US").format(num);
}

function applyI18n(lang) {
  currentLang = lang;
  const dict = I18N[lang] || I18N.en;
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.dataset.i18n;
    if (dict[key]) {
      el.textContent = dict[key];
    }
  });
  document.querySelectorAll(".lang-toggle button").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });
}

function labelFor(key) {
  const dict = I18N[currentLang] || I18N.en;
  return dict[key] || key;
}

function formatI18n(key, vars) {
  const dict = I18N[currentLang] || I18N.en;
  let text = dict[key] || key;
  if (!vars) return text;
  Object.keys(vars).forEach(k => {
    text = text.replace(`{${k}}`, vars[k]);
  });
  return text;
}

function lineChart(el, labels, values, color) {
  const width = 860;
  const height = 240;
  const pad = { l: 32, r: 16, t: 16, b: 32 };
  const max = Math.max(...values, 1);
  const xStep = values.length > 1 ? (width - pad.l - pad.r) / (values.length - 1) : 0;
  const baseY = height - pad.b;

  const points = values.map((v, i) => {
    const x = pad.l + i * xStep;
    const y = pad.t + (height - pad.t - pad.b) * (1 - v / max);
    return [x, y];
  });

  const line = points.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(" ");
  const area = `${line} L ${pad.l + (values.length - 1) * xStep} ${baseY} L ${pad.l} ${baseY} Z`;

  const uid = "grad" + Math.random().toString(36).slice(2);
  const svg = `
    <svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" preserveAspectRatio="none">
      <defs>
        <linearGradient id="${uid}" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.35"></stop>
          <stop offset="100%" stop-color="${color}" stop-opacity="0"></stop>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"></rect>
      <path d="${area}" fill="url(#${uid})"></path>
      <path d="${line}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round"></path>
      <line x1="${pad.l}" x2="${width - pad.r}" y1="${baseY}" y2="${baseY}" stroke="${CHART_AXIS_LINE}" />
      <text x="${pad.l}" y="${height - 8}" fill="${CHART_AXIS_TEXT}" font-size="11">${labels[0] || ""}</text>
      <text x="${width - pad.r - 80}" y="${height - 8}" fill="${CHART_AXIS_TEXT}" font-size="11">${labels[labels.length - 1] || ""}</text>
      <text x="${pad.l}" y="${pad.t + 12}" fill="${CHART_AXIS_TEXT}" font-size="11">${formatNumber(max)}</text>
    </svg>
  `;
  el.innerHTML = svg;
}

function barChart(el, labels, values, color) {
  const width = 640;
  const height = 220;
  const pad = { l: 24, r: 16, t: 16, b: 26 };
  const max = Math.max(...values, 1);
  const barWidth = (width - pad.l - pad.r) / values.length;

  let bars = "";
  values.forEach((v, i) => {
    const x = pad.l + i * barWidth;
    const h = ((height - pad.t - pad.b) * v) / max;
    const y = height - pad.b - h;
    const w = Math.max(2, barWidth - 2);
    bars += `<rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${w.toFixed(2)}" height="${h.toFixed(2)}" rx="3" fill="${color}"></rect>`;
  });
  const svg = `
    <svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" preserveAspectRatio="none">
      <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"></rect>
      <line x1="${pad.l}" x2="${width - pad.r}" y1="${height - pad.b}" y2="${height - pad.b}" stroke="${CHART_AXIS_LINE}" />
      ${bars}
      <text x="${pad.l}" y="${pad.t + 12}" fill="${CHART_AXIS_TEXT}" font-size="11">${formatNumber(max)}</text>
    </svg>
  `;
  el.innerHTML = svg;
}

function donutChart(el, legendEl, segments) {
  const size = 220;
  const r = 78;
  const c = 2 * Math.PI * r;
  const total = segments.reduce((sum, seg) => sum + seg.value, 0);
  const denom = total || 1;
  let offset = 0;

  let rings = "";
  segments.forEach(seg => {
    const portion = seg.value / denom;
    const dash = portion * c;
    rings += `<circle cx="110" cy="110" r="${r}" fill="transparent" stroke="${seg.color}" stroke-width="18" stroke-dasharray="${dash} ${c - dash}" stroke-dashoffset="${-offset}" transform="rotate(-90 110 110)" />`;
    offset += dash;
  });
  const svg = `
    <svg viewBox="0 0 ${size} ${size}" width="100%" height="100%">
      <circle cx="110" cy="110" r="${r}" fill="transparent" stroke="rgba(30,42,40,0.08)" stroke-width="18"></circle>
      ${rings}
      <text x="110" y="108" text-anchor="middle" font-size="14" fill="${CHART_AXIS_TEXT}">${labelFor("total_label")}</text>
      <text x="110" y="130" text-anchor="middle" font-size="18" fill="${CHART_CENTER_TEXT}">${formatNumber(total)}</text>
    </svg>
  `;
  el.innerHTML = svg;

  legendEl.innerHTML = segments.map(seg => {
    return `<span><i style="background:${seg.color}"></i>${seg.label}: ${formatNumber(seg.value)}</span>`;
  }).join("");
}

const MODEL_COLORS = [
  "#22D3EE",
  "#FB7185",
  "#F59E0B",
  "#34D399",
  "#60A5FA",
  "#A78BFA",
  "#F97316",
  "#2DD4BF",
  "#E879F9",
  "#38BDF8",
];

const MIX_COLORS = (() => {
  const out = {};
  (DATA.mix || []).forEach(seg => {
    out[seg.label_key] = seg.color;
  });
  return out;
})();

let labelIndex = new Map(
  ((DATA.daily && DATA.daily.labels) ? DATA.daily.labels : []).map((d, i) => [d, i])
);

function rebuildLabelIndex() {
  labelIndex = new Map(
    ((DATA.daily && DATA.daily.labels) ? DATA.daily.labels : []).map((d, i) => [d, i])
  );
}

let currentRange = {
  start: (DATA.range && DATA.range.start) || "",
  end: (DATA.range && DATA.range.end) || "",
};

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, ch => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function parseISODate(iso) {
  const [y, m, d] = String(iso).split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

function formatISODate(date) {
  return date.toISOString().slice(0, 10);
}

function addDaysISO(iso, days) {
  const date = parseISODate(iso);
  date.setUTCDate(date.getUTCDate() + days);
  return formatISODate(date);
}

function clampISO(iso, minISO, maxISO) {
  if (!iso) return minISO;
  if (iso < minISO) return minISO;
  if (iso > maxISO) return maxISO;
  return iso;
}

function sumSlice(values, startIdx, endIdx) {
  let sum = 0;
  for (let i = startIdx; i <= endIdx; i++) {
    sum += values[i] || 0;
  }
  return sum;
}

function countActiveDays(values, startIdx, endIdx) {
  let count = 0;
  for (let i = startIdx; i <= endIdx; i++) {
    if ((values[i] || 0) > 0) count++;
  }
  return count;
}

function sessionsInRange(startISO, endISO) {
  const spans = DATA.session_spans || [];
  let count = 0;
  spans.forEach(span => {
    if (span.start <= endISO && span.end >= startISO) {
      count++;
    }
  });
  return count;
}

function normalizeModelName(model) {
  const raw = String(model || "").trim();
  if (!raw) return "unknown";
  const parts = raw.split(":");
  const head = (parts.shift() || "").replace(/\\s*[\\(（][^\\)）]*[\\)）]\\s*/g, " ").replace(/\\s+/g, " ").trim();
  const base = head || "unknown";
  const tail = parts.join(":").trim();
  return tail ? `${base}:${tail}` : base;
}

function aggregateModels(dayLabels) {
  const out = {};
  const dailyModels = DATA.daily_models || {};
  dayLabels.forEach(day => {
    const dayMap = dailyModels[day];
    if (!dayMap) return;
    Object.keys(dayMap).forEach(model => {
      const modelKey = normalizeModelName(model);
      const rec = dayMap[model] || {};
      if (!out[modelKey]) {
        out[modelKey] = {
          input_tokens: 0,
          cached_input_tokens: 0,
          output_tokens: 0,
          reasoning_output_tokens: 0,
          total_tokens: 0,
        };
      }
      out[modelKey].input_tokens += rec.input_tokens || 0;
      out[modelKey].cached_input_tokens += rec.cached_input_tokens || 0;
      out[modelKey].output_tokens += rec.output_tokens || 0;
      out[modelKey].reasoning_output_tokens += rec.reasoning_output_tokens || 0;
      out[modelKey].total_tokens += rec.total_tokens || 0;
    });
  });
  return out;
}

function resolvePricing(model) {
  const pricing = (DATA.pricing && DATA.pricing.prices) || {};
  const aliases = (DATA.pricing && DATA.pricing.aliases) || {};
  const resolveAlias = (value) => {
    let name = value;
    const seen = new Set();
    while (aliases[name] && !seen.has(name)) {
      seen.add(name);
      name = aliases[name];
    }
    return name;
  };

  const modelName = resolveAlias(normalizeModelName(model));
  if (pricing[modelName]) return pricing[modelName];

  const base = modelName.split(":")[0];
  const baseName = resolveAlias(base);
  if (pricing[baseName]) return pricing[baseName];

  for (const key of Object.keys(pricing)) {
    if (baseName.startsWith(`${key}-`)) return pricing[key];
  }

  if (baseName.includes("gpt-5.3")) return pricing["gpt-5.2"] || pricing["gpt-5"] || null;
  if (baseName.includes("gpt-5.2")) return pricing["gpt-5.2"] || null;
  if (baseName.includes("gpt-5.1")) return pricing["gpt-5.1"] || null;
  if (baseName.startsWith("gpt-5")) return pricing["gpt-5"] || null;
  return null;
}

function costUSD(rec, pricing) {
  if (!pricing) return null;
  const cachedPrice = pricing.cached_input != null ? pricing.cached_input : pricing.input;
  const outputTotal = (rec.output_tokens || 0) + (rec.reasoning_output_tokens || 0);
  return (
    ((rec.input_tokens || 0) / 1_000_000) * (pricing.input || 0) +
    ((rec.cached_input_tokens || 0) / 1_000_000) * (cachedPrice || 0) +
    (outputTotal / 1_000_000) * (pricing.output || 0)
  );
}

function formatMoneyUSD(value) {
  if (value == null || !Number.isFinite(value)) return "n/a";
  if (value >= 1) return `$${value.toFixed(2)}`;
  return `$${value.toFixed(4)}`;
}

function renderTokenMix(inputTokens, outputTokens, reasoningTokens, cachedTokens) {
  donutChart(
    document.getElementById("chart-mix"),
    document.getElementById("legend-mix"),
    [
      { label: labelFor("input"), value: inputTokens, color: MIX_COLORS.input || "#1B7F79" },
      { label: labelFor("output"), value: outputTokens, color: MIX_COLORS.output || "#C45A3C" },
      { label: labelFor("reasoning"), value: reasoningTokens, color: MIX_COLORS.reasoning || "#D4A373" },
      { label: labelFor("cached"), value: cachedTokens, color: MIX_COLORS.cached || "#506B64" },
    ]
  );
}

function renderModelMix(modelItems) {
  const top = modelItems.slice(0, 6);
  const other = modelItems.slice(6).reduce((sum, item) => sum + item.rec.total_tokens, 0);
  const segments = [];
  top.forEach((item, idx) => {
    if (item.rec.total_tokens <= 0) return;
    segments.push({
      label: item.model,
      value: item.rec.total_tokens,
      color: MODEL_COLORS[idx % MODEL_COLORS.length],
    });
  });
  if (other > 0) {
    segments.push({
      label: labelFor("other"),
      value: other,
      color: "#999999",
    });
  }
  donutChart(
    document.getElementById("chart-models"),
    document.getElementById("legend-models"),
    segments
  );
}

function normalizeImportedData(raw) {
  if (!raw) return null;
  if (raw.data && raw.data.daily && raw.data.daily.labels) return raw.data;
  if (raw.daily && raw.daily.labels) return raw;
  return null;
}

function mergeDailyInto(dayMap, data) {
  const daily = data.daily || {};
  const labels = daily.labels || [];
  const totals = daily.total || [];
  const inputs = daily.input || [];
  const outputs = daily.output || [];
  const reasoning = daily.reasoning || [];
  const cached = daily.cached || [];
  labels.forEach((day, idx) => {
    if (!dayMap[day]) {
      dayMap[day] = { total: 0, input: 0, output: 0, reasoning: 0, cached: 0 };
    }
    dayMap[day].total += totals[idx] || 0;
    dayMap[day].input += inputs[idx] || 0;
    dayMap[day].output += outputs[idx] || 0;
    dayMap[day].reasoning += reasoning[idx] || 0;
    dayMap[day].cached += cached[idx] || 0;
  });
}

function mergeDailyModelsInto(target, data) {
  const source = data.daily_models || {};
  Object.keys(source).forEach(day => {
    const dayMap = source[day] || {};
    const outDay = target[day] || (target[day] = {});
    Object.keys(dayMap).forEach(model => {
      const rec = dayMap[model] || {};
      const modelKey = normalizeModelName(model);
      const outRec = outDay[modelKey] || (outDay[modelKey] = {
        input_tokens: 0,
        cached_input_tokens: 0,
        output_tokens: 0,
        reasoning_output_tokens: 0,
        total_tokens: 0,
      });
      outRec.input_tokens += rec.input_tokens || 0;
      outRec.cached_input_tokens += rec.cached_input_tokens || 0;
      outRec.output_tokens += rec.output_tokens || 0;
      outRec.reasoning_output_tokens += rec.reasoning_output_tokens || 0;
      outRec.total_tokens += rec.total_tokens || 0;
    });
  });
}

function mergeHourlyDailyInto(target, data) {
  const source = data.hourly_daily || {};
  Object.keys(source).forEach(day => {
    const hours = source[day] || [];
    const out = target[day] || (target[day] = new Array(24).fill(0));
    for (let i = 0; i < 24; i++) {
      out[i] += hours[i] || 0;
    }
  });
}

function buildMergedData(datasets) {
  const dayMap = {};
  const dailyModels = {};
  const hourlyDaily = {};
  const events = [];
  const spans = [];

  datasets.forEach(data => {
    if (!data || !data.daily || !data.daily.labels) return;
    mergeDailyInto(dayMap, data);
    mergeDailyModelsInto(dailyModels, data);
    mergeHourlyDailyInto(hourlyDaily, data);
    (data.events || []).forEach(ev => events.push(ev));
    (data.session_spans || []).forEach(span => spans.push(span));
  });

  const labels = Object.keys(dayMap).sort();
  const daily = {
    labels,
    total: [],
    input: [],
    output: [],
    reasoning: [],
    cached: [],
  };
  labels.forEach(day => {
    const rec = dayMap[day];
    daily.total.push(rec.total);
    daily.input.push(rec.input);
    daily.output.push(rec.output);
    daily.reasoning.push(rec.reasoning);
    daily.cached.push(rec.cached);
  });

  return {
    daily,
    daily_models: dailyModels,
    hourly_daily: hourlyDaily,
    events,
    session_spans: spans,
    range: {
      start: labels[0] || "",
      end: labels[labels.length - 1] || "",
      days: labels.length,
    },
  };
}

function mergeImportedData(datasets) {
  const merged = buildMergedData(datasets);
  if (!merged.daily.labels.length) return false;
  DATA.daily = merged.daily;
  DATA.daily_models = merged.daily_models;
  DATA.hourly_daily = merged.hourly_daily;
  DATA.events = merged.events;
  DATA.session_spans = merged.session_spans;
  DATA.range = merged.range;
  rebuildLabelIndex();
  syncRangeControls(DATA.range.start, DATA.range.end);
  applyRange(DATA.range.start, DATA.range.end);
  return true;
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error("read failed"));
    reader.readAsText(file);
  });
}

function setupImportExport() {
  const exportBtn = document.getElementById("export-data");
  const importInput = document.getElementById("import-data");
  const statusEl = document.getElementById("import-status");

  if (exportBtn) {
    exportBtn.addEventListener("click", () => {
      const payload = {
        version: 1,
        exported_at: new Date().toISOString(),
        data: DATA,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      const day = new Date().toISOString().slice(0, 10);
      link.download = `codex-token-export-${day}.json`;
      link.href = URL.createObjectURL(blob);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    });
  }

  if (importInput) {
    importInput.addEventListener("change", async () => {
      const files = Array.from(importInput.files || []);
      if (!files.length) return;
      if (statusEl) statusEl.textContent = "";
      const imported = [];
      let invalidCount = 0;
      for (const file of files) {
        try {
          const text = await readFileAsText(file);
          const raw = JSON.parse(text);
          const data = normalizeImportedData(raw);
          if (data) {
            imported.push(data);
          } else {
            invalidCount += 1;
          }
        } catch (err) {
          invalidCount += 1;
        }
      }
      importInput.value = "";
      if (!imported.length) {
        if (statusEl) statusEl.textContent = formatI18n("import_invalid");
        return;
      }
      const mergedOk = mergeImportedData([DATA, ...imported]);
      if (!mergedOk) {
        if (statusEl) statusEl.textContent = formatI18n("import_failed");
        return;
      }
      if (statusEl) statusEl.textContent = formatI18n("import_done", { count: imported.length });
    });
  }
}

function applyRange(startISO, endISO) {
  const minISO = (DATA.range && DATA.range.start) || "";
  const maxISO = (DATA.range && DATA.range.end) || "";
  if (!minISO || !maxISO || !DATA.daily || !DATA.daily.labels) return;

  startISO = clampISO(startISO, minISO, maxISO);
  endISO = clampISO(endISO, minISO, maxISO);
  if (startISO > endISO) {
    const tmp = startISO;
    startISO = endISO;
    endISO = tmp;
  }
  currentRange = { start: startISO, end: endISO };

  const startIdx = labelIndex.has(startISO) ? labelIndex.get(startISO) : 0;
  const endIdx = labelIndex.has(endISO) ? labelIndex.get(endISO) : (DATA.daily.labels.length - 1);

  const labels = DATA.daily.labels.slice(startIdx, endIdx + 1);
  const totals = DATA.daily.total.slice(startIdx, endIdx + 1);

  const totalTokens = sumSlice(DATA.daily.total, startIdx, endIdx);
  const inputTokens = sumSlice(DATA.daily.input, startIdx, endIdx);
  const outputTokens = sumSlice(DATA.daily.output, startIdx, endIdx);
  const reasoningTokens = sumSlice(DATA.daily.reasoning, startIdx, endIdx);
  const cachedTokens = sumSlice(DATA.daily.cached, startIdx, endIdx);

  const activeDays = countActiveDays(DATA.daily.total, startIdx, endIdx);
  const sessions = sessionsInRange(startISO, endISO);
  const avgPerDay = activeDays ? Math.round(totalTokens / activeDays) : 0;
  const avgPerSession = sessions ? Math.round(totalTokens / sessions) : 0;
  const cacheRate = inputTokens ? (cachedTokens / inputTokens) : 0;

  const banner = document.getElementById("range-banner");
  if (banner) {
    banner.classList.toggle("hidden", totalTokens > 0);
  }

  const startInput = document.getElementById("range-start");
  const endInput = document.getElementById("range-end");
  if (startInput) startInput.value = startISO;
  if (endInput) endInput.value = endISO;

  const rangeText = document.getElementById("range-text");
  if (rangeText) rangeText.textContent = `${startISO} to ${endISO}`;
  const sessionsEl = document.getElementById("sessions-count");
  if (sessionsEl) sessionsEl.textContent = formatNumber(sessions);
  const activeDaysEl = document.getElementById("active-days");
  if (activeDaysEl) activeDaysEl.textContent = formatNumber(activeDays);

  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };
  setText("value-total", formatNumber(totalTokens));
  setText("value-input", formatNumber(inputTokens));
  setText("value-output", formatNumber(outputTokens));
  setText("value-cached", formatNumber(cachedTokens));
  setText("value-reasoning", formatNumber(reasoningTokens));
  setText("value-cache-rate", `${(cacheRate * 100).toFixed(1)}%`);
  setText("value-avg-day", formatNumber(avgPerDay));
  setText("value-avg-session", formatNumber(avgPerSession));

  lineChart(document.getElementById("chart-daily"), labels, totals, "#22D3EE");
  renderTokenMix(inputTokens, outputTokens, reasoningTokens, cachedTokens);

  const hourly = new Array(24).fill(0);
  const hourlyDaily = DATA.hourly_daily || {};
  labels.forEach(day => {
    const arr = hourlyDaily[day];
    if (!arr) return;
    for (let h = 0; h < 24; h++) hourly[h] += arr[h] || 0;
  });
  barChart(document.getElementById("chart-hourly"), (DATA.hourly && DATA.hourly.labels) || [], hourly, "#FB7185");

  const topDayItems = [];
  for (let i = startIdx; i <= endIdx; i++) {
    const value = DATA.daily.total[i] || 0;
    if (value > 0) topDayItems.push({ day: DATA.daily.labels[i], value });
  }
  topDayItems.sort((a, b) => b.value - a.value);
  const topDaysEl = document.getElementById("list-top-days");
  if (topDaysEl) {
    if (topDayItems.length === 0) {
      topDaysEl.innerHTML = `<li class="muted" data-i18n="no_data">No data</li>`;
    } else {
      topDaysEl.innerHTML = topDayItems.slice(0, 5).map(item => {
        return `<li><span>${escapeHTML(item.day)}</span><span>${formatNumber(item.value)}</span></li>`;
      }).join("");
    }
  }

  const spikes = (DATA.events || []).filter(ev => ev.day >= startISO && ev.day <= endISO);
  spikes.sort((a, b) => (b.value || 0) - (a.value || 0));
  const spikesEl = document.getElementById("list-top-spikes");
  if (spikesEl) {
    if (spikes.length === 0) {
      spikesEl.innerHTML = `<li class="muted" data-i18n="no_data">No data</li>`;
    } else {
      spikesEl.innerHTML = spikes.slice(0, 5).map(ev => {
        return `<li><span>${escapeHTML(ev.ts)}</span><span>${formatNumber(ev.value || 0)}</span></li>`;
      }).join("");
    }
  }

  const modelTotals = aggregateModels(labels);
  const modelItems = Object.keys(modelTotals).map(model => ({ model, rec: modelTotals[model] }));
  modelItems.sort((a, b) => (b.rec.total_tokens || 0) - (a.rec.total_tokens || 0));
  renderModelMix(modelItems);

  let totalCost = 0;
  let anyPriced = false;
  const tableRows = [];
  modelItems.slice(0, 10).forEach(item => {
    const pricing = resolvePricing(item.model);
    const cost = costUSD(item.rec, pricing);
    if (cost != null) {
      totalCost += cost;
      anyPriced = true;
    }
    tableRows.push(
      "<tr>" +
      `<td>${escapeHTML(item.model)}</td>` +
      `<td>${formatNumber(item.rec.total_tokens || 0)}</td>` +
      `<td>${formatNumber(item.rec.input_tokens || 0)}</td>` +
      `<td>${formatNumber(item.rec.output_tokens || 0)}</td>` +
      `<td>${formatNumber(item.rec.cached_input_tokens || 0)}</td>` +
      `<td>${formatNumber(item.rec.reasoning_output_tokens || 0)}</td>` +
      `<td>${cost != null ? formatMoneyUSD(cost) : "n/a"}</td>` +
      "</tr>"
    );
  });

  const tableEl = document.getElementById("table-models");
  if (tableEl) {
    if (tableRows.length === 0) {
      tableEl.innerHTML = `<tr><td class="muted" data-i18n="no_data">No data</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>`;
    } else {
      tableEl.innerHTML = tableRows.join("");
    }
  }

  setText("value-cost", anyPriced ? formatMoneyUSD(totalCost) : "n/a");

  applyI18n(currentLang);
}

function syncRangeControls(minISO, maxISO) {
  const startInput = document.getElementById("range-start");
  const endInput = document.getElementById("range-end");
  if (!startInput || !endInput || !minISO || !maxISO) return;
  startInput.min = minISO;
  startInput.max = maxISO;
  endInput.min = minISO;
  endInput.max = maxISO;
  startInput.value = minISO;
  endInput.value = maxISO;
}

function setupRangeControls() {
  const startInput = document.getElementById("range-start");
  const endInput = document.getElementById("range-end");
  const applyBtn = document.getElementById("apply-range");
  const minISO = (DATA.range && DATA.range.start) || "";
  const maxISO = (DATA.range && DATA.range.end) || "";
  if (!startInput || !endInput || !applyBtn || !minISO || !maxISO) return;
  syncRangeControls(minISO, maxISO);

  applyBtn.addEventListener("click", () => {
    applyRange(startInput.value, endInput.value);
  });

  document.querySelectorAll("[data-range]").forEach(btn => {
    btn.addEventListener("click", () => {
      const value = btn.dataset.range;
      if (value === "all") {
        applyRange(minISO, maxISO);
        return;
      }
      const days = parseInt(value, 10);
      if (!days) return;
      const end = maxISO;
      let start = addDaysISO(end, -(days - 1));
      if (start < minISO) start = minISO;
      applyRange(start, end);
    });
  });
}

function setupDailyChartZoom() {
  const bindZoom = (chartEl) => {
    if (!chartEl) return;
    chartEl.addEventListener("wheel", (event) => {
      event.preventDefault();
      const labels = (DATA.daily && DATA.daily.labels) || [];
      if (!labels.length) return;

      const startIdx = labelIndex.has(currentRange.start) ? labelIndex.get(currentRange.start) : 0;
      const endIdx = labelIndex.has(currentRange.end) ? labelIndex.get(currentRange.end) : labels.length - 1;
      const visible = Math.max(1, endIdx - startIdx + 1);

      const nextVisible = event.deltaY > 0
        ? Math.min(labels.length, Math.round(visible * 1.2))
        : Math.max(1, Math.round(visible * 0.8));
      if (nextVisible === visible) return;

      const rect = chartEl.getBoundingClientRect();
      const ratioRaw = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0.5;
      const ratio = Math.min(1, Math.max(0, ratioRaw));
      const anchor = Math.round(startIdx + (visible - 1) * ratio);

      let nextStart = Math.round(anchor - (nextVisible - 1) * ratio);
      let nextEnd = nextStart + nextVisible - 1;

      if (nextStart < 0) {
        nextStart = 0;
        nextEnd = nextVisible - 1;
      }
      if (nextEnd >= labels.length) {
        nextEnd = labels.length - 1;
        nextStart = Math.max(0, nextEnd - nextVisible + 1);
      }
      applyRange(labels[nextStart], labels[nextEnd]);
    }, { passive: false });
  };

  bindZoom(document.getElementById("chart-daily"));
  bindZoom(document.getElementById("chart-hourly"));
}

window.addEventListener("load", () => {
  const stored = localStorage.getItem("codex_report_lang");
  const langGuess = (navigator.language || "en").startsWith("zh") ? "zh" : "en";
  const fallback = stored || langGuess;
  applyI18n(fallback);
  setupRangeControls();
  setupDailyChartZoom();
  setupImportExport();
  const startInput = document.getElementById("range-start");
  const endInput = document.getElementById("range-end");
  applyRange(
    (startInput && startInput.value) || (DATA.range && DATA.range.start) || "",
    (endInput && endInput.value) || (DATA.range && DATA.range.end) || ""
  );
  document.querySelectorAll(".lang-toggle button").forEach(btn => {
    btn.addEventListener("click", () => {
      const lang = btn.dataset.lang;
      localStorage.setItem("codex_report_lang", lang);
      applyI18n(lang);
      applyRange(currentRange.start, currentRange.end);
    });
  });
});
</script>
</body>
</html>
"""
    replacements = {
        "RANGE_TEXT": html.escape(summary.get("range_text", "")),
        "SESSIONS": html.escape(summary.get("sessions", "")),
        "DAYS_ACTIVE": html.escape(summary.get("days_active", "")),
        "TOTAL_TOKENS": html.escape(summary.get("total_tokens", "")),
        "INPUT_TOKENS": html.escape(summary.get("input_tokens", "")),
        "OUTPUT_TOKENS": html.escape(summary.get("output_tokens", "")),
        "CACHED_TOKENS": html.escape(summary.get("cached_tokens", "")),
        "REASONING_TOKENS": html.escape(summary.get("reasoning_tokens", "")),
        "CACHE_RATE": html.escape(summary.get("cache_rate", "")),
        "AVG_PER_DAY": html.escape(summary.get("avg_per_day", "")),
        "AVG_PER_SESSION": html.escape(summary.get("avg_per_session", "")),
        "TOTAL_COST": html.escape(summary.get("total_cost", "")),
        "PRICING_SOURCE": html.escape(summary.get("pricing_source", "")),
        "SOURCE_PATH": source_path,
        "TOP_DAYS": top_days_html or "        <li class=\"muted\" data-i18n=\"no_data\">No data</li>",
        "TOP_EVENTS": top_events_html or "        <li class=\"muted\" data-i18n=\"no_data\">No data</li>",
        "MODEL_TABLE": summary.get("model_table_html", "") or "          <tr><td class=\"muted\" data-i18n=\"no_data\">No data</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>",
        "GENERATED_AT": html.escape(summary.get("generated_at", "")),
        "EMPTY_BANNER": empty_banner,
        "DATA_JSON": data_json,
        "I18N_JSON": i18n_json,
    }
    for key, value in replacements.items():
        template = template.replace(f"__{key}__", value)
    return template

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a local Codex token usage report from session logs."
    )
    parser.add_argument("--codex-home", help="Path to .codex directory.")
    parser.add_argument("--sessions-root", help="Path to sessions directory.")
    parser.add_argument("--since", help="Start date YYYY-MM-DD.")
    parser.add_argument("--until", help="End date YYYY-MM-DD.")
    parser.add_argument("--days", type=int, help="Limit to last N days when no dates set.")
    parser.add_argument("--out", default="report", help="Output directory for report.")
    parser.add_argument("--pricing-file", help="Path to pricing json.")
    parser.add_argument("--json", action="store_true", help="Write data.json alongside report.")
    parser.add_argument("--open", action="store_true", help="Open report in default browser.")
    args = parser.parse_args()
    try:
        since = parse_date(args.since) if args.since else None
        until = parse_date(args.until) if args.until else None
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if since and until and since > until:
        print("since must be earlier than until", file=sys.stderr)
        return 2
    if args.days is not None and args.days <= 0:
        print("days must be positive", file=sys.stderr)
        return 2

    if args.sessions_root:
        session_root = Path(args.sessions_root)
    else:
        codex_root = Path(args.codex_home) if args.codex_home else default_codex_root()
        session_root = codex_root / "sessions"
    pricing_path = Path(args.pricing_file) if args.pricing_file else None
    prices, pricing_meta, aliases = load_pricing(pricing_path)
    usage = collect_usage(session_root, since, until)

    if args.days and since is None and until is None and usage["active_days"]:
        last_day = max(usage["active_days"])
        since = last_day - timedelta(days=args.days - 1)
        usage = collect_usage(session_root, since, until)

    active_days = usage["active_days"]
    empty = not active_days
    range_start = since or (min(active_days) if active_days else date.today())
    range_end = until or (max(active_days) if active_days else date.today())
    range_days = (range_end - range_start).days + 1
    chart_days = max(1, range_days)
    daily_series = build_day_series(usage["daily"], range_end, chart_days)

    hourly_values = [usage["hourly"].get(h, 0) for h in range(24)]
    hour_labels = [f"{h:02d}" for h in range(24)]

    totals = usage["totals"]
    total_tokens = totals["total_tokens"]
    input_tokens = totals["input_tokens"]
    output_tokens = totals["output_tokens"]
    reasoning_tokens = totals["reasoning_output_tokens"]
    cached_tokens = totals["cached_input_tokens"]
    cache_rate = cached_tokens / input_tokens if input_tokens else 0

    days_active = len(active_days)
    avg_per_day = total_tokens / days_active if days_active else 0
    sessions = usage["sessions"]
    avg_per_session = total_tokens / sessions if sessions else 0

    top_days = sorted(
        ((day, rec["total_tokens"]) for day, rec in usage["daily"].items()),
        key=lambda item: item[1],
        reverse=True,
    )
    top_days = [item for item in top_days if item[1] > 0][:5]
    top_days_html = "\n".join(
        f"        <li><span>{day.isoformat()}</span><span>{fmt_int(total)}</span></li>"
        for day, total in top_days
    )

    top_events = usage["top_events"]
    top_events_html = "\n".join(
        f"        <li><span>{ts.strftime('%Y-%m-%d %H:%M')}</span><span>{fmt_int(total)}</span></li>"
        for total, ts in top_events
    )

    model_totals = usage["models"]
    model_items = sorted(
        ((model, rec) for model, rec in model_totals.items()),
        key=lambda item: item[1]["total_tokens"],
        reverse=True,
    )
    model_costs = {}
    total_cost = Decimal("0")
    for model, rec in model_items:
        pricing = resolve_pricing(model, prices, aliases)
        if not pricing:
            continue
        cached_price = pricing["cached_input"] or pricing["input"]
        output_total = rec["output_tokens"] + rec["reasoning_output_tokens"]
        cost = (
            dollars_from_tokens(rec["input_tokens"], pricing["input"])
            + dollars_from_tokens(rec["cached_input_tokens"], cached_price)
            + dollars_from_tokens(output_total, pricing["output"])
        )
        model_costs[model] = cost
        total_cost += cost

    model_table_rows = []
    for model, rec in model_items[:10]:
        model_table_rows.append(
            "<tr>"
            f"<td>{html.escape(model)}</td>"
            f"<td>{fmt_int(rec['total_tokens'])}</td>"
            f"<td>{fmt_int(rec['input_tokens'])}</td>"
            f"<td>{fmt_int(rec['output_tokens'])}</td>"
            f"<td>{fmt_int(rec['cached_input_tokens'])}</td>"
            f"<td>{fmt_int(rec['reasoning_output_tokens'])}</td>"
            f"<td>{fmt_money(model_costs.get(model))}</td>"
            "</tr>"
        )
    model_table_html = "\n".join(model_table_rows)

    model_mix = []
    top_mix = model_items[:6]
    other_tokens = sum(rec["total_tokens"] for _, rec in model_items[6:])
    for idx, (model, rec) in enumerate(top_mix):
        if rec["total_tokens"] <= 0:
            continue
        model_mix.append(
            {
                "label": model,
                "value": rec["total_tokens"],
                "color": MODEL_COLORS[idx % len(MODEL_COLORS)],
            }
        )
    if other_tokens > 0:
        model_mix.append(
            {
                "label": "Other",
                "label_key": "other",
                "value": other_tokens,
                "color": "#999999",
            }
        )
    daily_models_serialized = {}
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

    hourly_daily_serialized = {}
    for day, hours in usage["hourly_daily"].items():
        hourly_daily_serialized[day.isoformat()] = hours

    pricing_js = {
        "prices": {
            model: {
                "input": float(entry["input"]),
                "cached_input": float(entry["cached_input"]) if entry["cached_input"] else None,
                "output": float(entry["output"]),
            }
            for model, entry in prices.items()
        },
        "aliases": aliases,
    }

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
        "mix": [
            {"label_key": label_key, "value": totals[key], "color": color}
            for key, label_key, color in MIX
        ],
        "model_mix": model_mix,
        "pricing": pricing_js,
    }

    summary = {
        "range_text": f"{range_start.isoformat()} to {range_end.isoformat()}",
        "sessions": fmt_int(sessions),
        "days_active": fmt_int(days_active),
        "total_tokens": fmt_int(total_tokens),
        "input_tokens": fmt_int(input_tokens),
        "output_tokens": fmt_int(output_tokens),
        "reasoning_tokens": fmt_int(reasoning_tokens),
        "cached_tokens": fmt_int(cached_tokens),
        "cache_rate": fmt_pct(cache_rate),
        "avg_per_day": fmt_int(int(round(avg_per_day))),
        "avg_per_session": fmt_int(int(round(avg_per_session))),
        "total_cost": fmt_money(total_cost),
        "pricing_source": f"{pricing_meta['tier']} {pricing_meta['currency']} | {pricing_meta['source_url']} ({pricing_meta['source_date']})",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_path": str(session_root),
        "top_days_html": top_days_html,
        "top_events_html": top_events_html,
        "model_table_html": model_table_html,
    }

    html_text = render_html(data, summary, empty)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "index.html"
    index_path.write_text(html_text, encoding="utf-8")

    if args.json:
        data_path = out_dir / "data.json"
        data_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"Report written to {index_path}")
    if args.open:
        if hasattr(os, "startfile"):
            try:
                os.startfile(index_path)
            except Exception as exc:
                print(f"Could not open report: {exc}", file=sys.stderr)
        else:
            print("open is only supported on Windows", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
