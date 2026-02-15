#!/usr/bin/env python3
from __future__ import annotations

import argparse
import heapq
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
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

I18N = {
    "zh": {
        "title": "Codex Token Usage",
        "range": "范围",
        "sessions": "会话数",
        "active_days": "活跃天数",
        "card_total": "总 token",
        "card_cached": "缓存与推理",
        "card_avg": "平均值",
        "card_cost": "估算成本",
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
        "last_1": "1D",
        "last_2": "2D",
        "last_7": "1W",
        "last_30": "1M",
        "last_90": "3M",
        "all_time": "ALL",
        "export": "导出",
        "import": "导入",
        "import_done": "已合并 {count} 个文件",
        "import_invalid": "导入文件格式不正确",
        "import_failed": "导入失败",
        "daily_chart": "每小时总 token",
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
        "table_cost": "估算成本",
        "no_data": "无数据",
        "empty_banner": "该时间范围内没有 token 使用记录",
        "no_data": "无数据",
        "other": "其他",
        "total_label": "总计",
        "share_card_title": "今日分享图",
        "share_hint": "自动同步最新数据，可下载或分享今日图片",
        "share_copy": "一键复制",
        "share_copied": "图片已准备好",
        "share_copy_failed": "生成图片失败",
        "share_template": "范围 {range}\\n总计 {total}\\n输入 {input} | 输出 {output}\\n推理 {reasoning} | 缓存 {cached} | 缓存率 {cache_rate}\\n会话 {sessions} | 活跃 {active_days} 天\\n日均 {avg_day} | 会话均值 {avg_session}\\n估算成本 {cost}",
        "share_download": "下载图片",
        "share_native": "分享图片",
        "today_usage": "今天用量",
        "share_native_unsupported": "浏览器不支持直接分享，已改为下载",
        "auto_sync": "自动同步最新数据",
        "share_downloaded": "图片已下载",
        "share_copied_image": "图片已复制，可直接粘贴发送",
        "calendar_clear": "清除",
        "calendar_today": "今天",
    },
    "en": {
        "title": "Codex Token Usage",
        "range": "Range",
        "sessions": "Sessions",
        "active_days": "Active days",
        "card_total": "Total tokens",
        "card_cached": "Cached and reasoning",
        "card_avg": "Averages",
        "card_cost": "Estimated cost",
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
        "last_1": "1D",
        "last_2": "2D",
        "last_7": "1W",
        "last_30": "1M",
        "last_90": "3M",
        "all_time": "ALL",
        "export": "Export",
        "import": "Import",
        "import_done": "Merged {count} file(s)",
        "import_invalid": "Invalid import file",
        "import_failed": "Import failed",
        "daily_chart": "Hourly total tokens",
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
        "table_cost": "Estimated cost",
        "no_data": "No data",
        "empty_banner": "No token usage found in this range.",
        "no_data": "No data",
        "other": "Other",
        "total_label": "Total",
        "share_card_title": "Today's share card",
        "share_hint": "Auto-sync latest data, download or share today's image",
        "share_copy": "Copy",
        "share_copied": "Image ready",
        "share_copy_failed": "Image generation failed",
        "share_template": "Range {range}\\nTotal {total}\\nInput {input} | Output {output}\\nReasoning {reasoning} | Cached {cached} | Cache rate {cache_rate}\\nSessions {sessions} | Active days {active_days}\\nPer day {avg_day} | Per session {avg_session}\\nEstimated cost {cost}",
        "share_download": "Download image",
        "share_native": "Share image",
        "today_usage": "Today's usage",
        "share_native_unsupported": "Direct share is unavailable, downloaded instead",
        "auto_sync": "Auto-sync latest data",
        "share_downloaded": "Image downloaded",
        "share_copied_image": "Image copied, paste to share",
        "calendar_clear": "Clear",
        "calendar_today": "Today",
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
                        "input": delta["input_tokens"],
                        "cached": delta["cached_input_tokens"],
                        "output": delta["output_tokens"],
                        "reasoning": delta["reasoning_output_tokens"],
                        "total": delta["total_tokens"],
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
    if abs_n >= 1_000:
        return f"{n / 1_000:.1f}".rstrip("0").rstrip(".") + "K"
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
    empty_banner = ""
    data_json = json.dumps(data, separators=(",", ":"))
    i18n_json = json.dumps(I18N, ensure_ascii=False, separators=(",", ":"))     
    source_path = html.escape(summary.get("source_path", ""))
    template = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Codex Token Usage</title>
<style>
@import url('https://cdn.jsdelivr.net/npm/lxgw-wenkai-webfont@1.7.0/style.css');

:root {
  --background: #0a0a0a;
  --surface: #111113;
  --surface-soft: #141418;
  --surface-strong: #1a1b20;
  --text: #f8fafc;
  --muted: #a1a1aa;
  --stroke: rgba(148, 163, 184, 0.16);
  --accent: #B026FF;
  --accent-cyan: #00F0FF;
  --accent-rgb: 176, 38, 255;
  --accent-cyan-rgb: 0, 240, 255;
  --bg-glow-a: rgba(176, 38, 255, 0.20);
  --bg-glow-b: rgba(0, 240, 255, 0.16);
  --bg-glow-c: rgba(176, 38, 255, 0.08);
  --bg-base-start: #06070d;
  --bg-base-mid: #090d16;
  --bg-base-end: #05060a;
  --page-border: rgba(150, 156, 190, 0.24);
  --page-bg-start: rgba(14, 14, 24, 0.94);
  --page-bg-end: rgba(8, 10, 18, 0.96);
  --page-glow: rgba(176, 38, 255, 0.18);
  --page-outline: rgba(188, 198, 255, 0.18);
  --page-inner-glow: rgba(176, 38, 255, 0.08);
  --page-outer-glow: rgba(0, 240, 255, 0.10);
  --segment-start: #B026FF;
  --segment-end: #00F0FF;
  --chart-line-start: #B026FF;
  --chart-line-end: #00F0FF;
  --chart-area-start: rgba(176, 38, 255, 0.55);
  --chart-area-mid: rgba(0, 240, 255, 0.22);
  --chart-area-end: rgba(0, 240, 255, 0);
  --tooltip-border: rgba(176, 38, 255, 0.45);
  --axis-pointer: rgba(0, 240, 255, 0.7);
  --shadow: 0 22px 52px rgba(0, 0, 0, 0.62);
  --ring: rgba(176, 38, 255, 0.28);
  --font-zh: "LXGW WenKai", "LXGW WenKai GB", "霞鹜文楷", "霞鹜文楷 GB 屏幕阅读版", "LXGW WenKai Screen", "PingFang SC", "Microsoft YaHei", serif;
  --font-en: "LXGW WenKai", "LXGW WenKai GB", "霞鹜文楷", "霞鹜文楷 GB 屏幕阅读版", "LXGW WenKai Screen", "Segoe UI", "Helvetica Neue", Arial, serif;
  --app-font: var(--font-en);
  --swift-duration-fast: 900ms;
  --swift-duration-normal: 2000ms;
  --swift-ease-standard: cubic-bezier(0.2, 0.8, 0.2, 1);
  --swift-ease-spring: cubic-bezier(0.22, 0.8, 0.22, 1.02);
}

* {
  box-sizing: border-box;
}

html[lang="zh"] {
  --app-font: var(--font-zh);
}

html[lang="en"] {
  --app-font: var(--font-en);
}

html[data-theme="bronze"] {
  --accent: #B89C7A;
  --accent-cyan: #E3C89A;
  --accent-rgb: 184, 156, 122;
  --accent-cyan-rgb: 227, 200, 154;
  --bg-glow-a: rgba(120, 92, 58, 0.20);
  --bg-glow-b: rgba(94, 79, 63, 0.16);
  --bg-glow-c: rgba(168, 152, 132, 0.07);
  --bg-base-start: #080706;
  --bg-base-mid: #0b0a09;
  --bg-base-end: #050505;
  --page-border: rgba(226, 220, 210, 0.30);
  --page-bg-start: rgba(18, 15, 12, 0.92);
  --page-bg-end: rgba(10, 8, 7, 0.95);
  --page-glow: rgba(214, 202, 186, 0.20);
  --page-outline: rgba(240, 233, 223, 0.24);
  --page-inner-glow: rgba(186, 170, 150, 0.14);
  --page-outer-glow: rgba(230, 219, 205, 0.16);
  --segment-start: #A27C4A;
  --segment-end: #D7B98A;
  --chart-line-start: #B89C7A;
  --chart-line-end: #E3C89A;
  --chart-area-start: rgba(184, 156, 122, 0.40);
  --chart-area-mid: rgba(227, 200, 154, 0.18);
  --chart-area-end: rgba(227, 200, 154, 0);
  --tooltip-border: rgba(184, 156, 122, 0.45);
  --axis-pointer: rgba(227, 200, 154, 0.72);
  --ring: rgba(184, 156, 122, 0.26);
}

body {
  margin: 0;
  min-height: 100vh;
  padding: 0 0 28px;
  background:
    radial-gradient(1200px 720px at 12% 2%, var(--bg-glow-a), transparent 62%),
    radial-gradient(980px 640px at 88% 8%, var(--bg-glow-b), transparent 66%),
    linear-gradient(178deg, var(--bg-base-start) 0%, var(--bg-base-mid) 52%, var(--bg-base-end) 100%);
  color: var(--text);
  font-family: var(--app-font);
  line-height: 1.45;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}

.page {
  position: relative;
  max-width: 1280px;
  margin: 24px auto 0;
  padding: 24px 18px 38px;
  border-radius: 24px;
  border: none;
  background: linear-gradient(170deg, var(--page-bg-start), var(--page-bg-end));
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.05),
    0 0 24px rgba(0, 0, 0, 0.30);
  overflow: hidden;
}

.page::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: inherit;
  border: none;
  box-shadow:
    inset 0 0 18px var(--page-inner-glow);
}

.page::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 22px;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(8, 10, 18, 0), rgba(5, 6, 10, 0.92));
}

.hero {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 12px;
}

.hero-tools {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
}

.theme-dot-toggle {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  border: 1.5px solid rgba(var(--accent-rgb), 0.88);
  background: transparent;
  box-shadow: none;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.22s ease, box-shadow 0.22s ease;
}

.theme-dot-toggle:hover {
  transform: scale(1.03);
  border-color: rgba(var(--accent-cyan-rgb), 0.78);
  box-shadow: 0 0 0 1px rgba(var(--accent-cyan-rgb), 0.18);
}

.theme-dot-toggle:focus-visible {
  outline: none;
  border-color: rgba(var(--accent-rgb), 0.95);
  box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.2);
}

.theme-dot-toggle.is-bronze {
  transform: scale(1.06);
  box-shadow: 0 0 0 1px rgba(var(--accent-rgb), 0.2);
}

.title h1 {
  margin: 0 0 8px;
  font-size: clamp(30px, 5vw, 42px);
  letter-spacing: 0.5px;
  font-family: var(--app-font);
  font-weight: 700;
  text-wrap: balance;
}

.title p {
  margin: 0;
  color: var(--muted);
  max-width: 900px;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.03);
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

html.theme-ready body,
html.theme-ready .page,
html.theme-ready .page::before,
html.theme-ready .page::after,
html.theme-ready .range-controls,
html.theme-ready .range-date-trigger,
html.theme-ready .range-segmented,
html.theme-ready .range-action-btn,
html.theme-ready .file-button,
html.theme-ready .theme-dot-toggle,
html.theme-ready .card,
html.theme-ready .panel,
html.theme-ready .chart {
  transition:
    color 280ms ease,
    border-color 320ms ease,
    background-color 320ms ease,
    background-image 320ms ease,
    box-shadow 320ms ease;
}

html.theme-switching body,
html.theme-switching .page,
html.theme-switching .page::before,
html.theme-switching .page::after,
html.theme-switching .range-controls,
html.theme-switching .range-date-trigger,
html.theme-switching .range-segmented,
html.theme-switching .range-action-btn,
html.theme-switching .file-button,
html.theme-switching .theme-dot-toggle,
html.theme-switching .card,
html.theme-switching .panel,
html.theme-switching .chart {
  animation: themeSwap 460ms var(--swift-ease-standard);
}

.range-controls {
  --range-selector-width: 260px;
  --range-selector-height: 36px;
  margin: 16px 0 8px;
  padding: 6px 12px;
  border: 1px solid var(--stroke);
  background: linear-gradient(140deg, rgba(26, 27, 32, 0.9), rgba(17, 17, 19, 0.88));
  border-radius: 14px;
  display: grid;
  grid-template-columns: var(--range-selector-width) var(--range-selector-width) auto;
  align-items: center;
  column-gap: 10px;
  row-gap: 10px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.range-fields {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--range-selector-width);
  min-height: var(--range-selector-height);
  min-width: 0;
}

.range-fields input[type="hidden"] {
  display: none;
}

.range-date-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  border: 1px solid var(--stroke);
  background: linear-gradient(140deg, rgba(36, 38, 46, 0.94), rgba(24, 26, 33, 0.94));
  color: #eef2ff;
  border-radius: 999px;
  font-size: 14px;
  line-height: 1;
  letter-spacing: 0.2px;
  cursor: pointer;
  width: 100%;
  height: var(--range-selector-height);
  padding: 0 14px;
  min-width: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.07);
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.range-date-trigger:hover {
  border-color: rgba(var(--accent-cyan-rgb), 0.5);
  background: linear-gradient(140deg, rgba(42, 45, 56, 0.96), rgba(27, 29, 37, 0.96));
}

.range-date-trigger:focus-visible {
  outline: none;
  border-color: rgba(var(--accent-rgb), 0.58);
  box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.18);
}

#range-date-label {
  display: block;
  width: 100%;
  text-align: center;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  line-height: 1;
  text-overflow: ellipsis;
  overflow: hidden;
}

.calendar-popover {
  position: fixed;
  z-index: 999;
  width: min(320px, calc(100vw - 20px));
  border: 1px solid var(--stroke);
  border-radius: 16px;
  background: linear-gradient(150deg, rgba(26, 27, 32, 0.98), rgba(16, 17, 21, 0.96));
  box-shadow: 0 22px 44px rgba(0, 0, 0, 0.45);
  padding: 12px;
}

.calendar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  gap: 8px;
}

.calendar-title {
  font-size: 15px;
  font-weight: 700;
  color: #f3f4f6;
  letter-spacing: 0.2px;
}

.calendar-nav-btn {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.04);
  color: #e4e4e7;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

.calendar-nav-btn:hover {
  border-color: rgba(var(--accent-cyan-rgb), 0.5);
  background: rgba(var(--accent-cyan-rgb), 0.15);
}

.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
  margin-bottom: 6px;
}

.calendar-weekdays span {
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  padding: 4px 0;
}

.calendar-days {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
}

.calendar-day-btn {
  border: 1px solid transparent;
  background: transparent;
  color: #e4e4e7;
  border-radius: 9px;
  min-height: 34px;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  cursor: pointer;
}

.calendar-day-btn:hover:not(:disabled) {
  border-color: rgba(var(--accent-cyan-rgb), 0.4);
  background: rgba(var(--accent-cyan-rgb), 0.14);
}

.calendar-day-btn.is-outside {
  color: #64748b;
}

.calendar-day-btn.is-today {
  border-color: rgba(var(--accent-rgb), 0.72);
}

.calendar-day-btn.is-selected {
  border-color: rgba(var(--accent-rgb), 0.86);
  background: rgba(var(--accent-rgb), 0.28);
  color: #ecfeff;
}

.calendar-day-btn.is-in-range {
  border-color: rgba(var(--accent-cyan-rgb), 0.25);
  background: rgba(var(--accent-cyan-rgb), 0.14);
}

.calendar-day-btn.is-range-start,
.calendar-day-btn.is-range-end {
  border-color: rgba(var(--accent-rgb), 0.88);
  background: rgba(var(--accent-rgb), 0.3);
  color: #ecfeff;
}

.calendar-day-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.calendar-actions {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.calendar-actions button {
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.04);
  color: #e4e4e7;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
}

.calendar-actions button:hover {
  border-color: rgba(var(--accent-cyan-rgb), 0.5);
  background: rgba(var(--accent-cyan-rgb), 0.15);
}

.range-action-btn,
.file-button {
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.04);
  color: #e4e4e7;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.range-action-btn:hover,
.file-button:hover {
  border-color: rgba(var(--accent-cyan-rgb), 0.5);
  background: rgba(var(--accent-cyan-rgb), 0.15);
}

.range-buttons {
  display: flex;
  flex: 0 0 var(--range-selector-width);
  justify-content: center;
  width: var(--range-selector-width);
  min-height: var(--range-selector-height);
  min-width: 0;
}

.range-segmented {
  position: relative;
  display: inline-flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 1px;
  box-sizing: border-box;
  padding: 2px;
  border-radius: 999px;
  border: 1px solid var(--stroke);
  background: rgba(44, 46, 56, 0.92);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
  width: 100%;
  height: var(--range-selector-height);
  max-width: none;
  overflow: hidden;
}

.range-segmented-slider {
  position: absolute;
  top: 2px;
  bottom: 2px;
  left: 0;
  width: 0;
  border-radius: 999px;
  background: linear-gradient(120deg, var(--segment-start), var(--segment-end));
  box-shadow: 0 5px 14px rgba(0, 0, 0, 0.34);
  opacity: 0;
  transform: translateX(0);
  will-change: transform, width, opacity;
  transition:
    transform 0.66s cubic-bezier(0.18, 0.88, 0.26, 1),
    width 0.54s cubic-bezier(0.2, 0.92, 0.24, 1),
    opacity 0.24s ease;
  z-index: 0;
}

.range-segmented-slider::after {
  content: "";
  position: absolute;
  inset: 1px;
  border-radius: inherit;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.02));
  pointer-events: none;
}

.range-segmented button {
  position: relative;
  z-index: 1;
  flex: 1 1 0;
  min-width: 0;
  min-height: calc(var(--range-selector-height) - 4px);
  border: none;
  background: transparent;
  color: #b6bac6;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 13px;
  line-height: 1;
  font-weight: 600;
  letter-spacing: 0.2px;
  cursor: pointer;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
  transition: color 0.22s ease;
}

.range-segmented button:hover {
  color: #f8fafc;
}

.range-segmented button.is-active {
  color: #ffffff;
}

.range-actions {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  align-items: center;
  justify-self: end;
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin: 24px 0 24px;
  align-items: stretch;
}

.card {
  background: linear-gradient(145deg, rgba(26, 27, 32, 0.94), rgba(20, 20, 24, 0.9));
  border: 1px solid var(--stroke);
  border-radius: 20px;
  padding: 14px 16px;
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
  animation: rise 0.8s ease both;
  animation-delay: var(--delay, 0s);
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.metric-card {
  min-height: 124px;
  justify-content: flex-start;
}

.card::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.05), transparent 65%);
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
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
}

.text-fade-anim,
.metric-value-anim,
.i18n-switch-anim {
  animation: textFadeOnly 360ms ease both;
  will-change: opacity;
}

.card .sub {
  margin-top: 8px;
  color: #b4b4bd;
  font-size: 13px;
  line-height: 1.4;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 18px;
}

.panel {
  background: linear-gradient(150deg, rgba(26, 27, 32, 0.94), rgba(20, 20, 24, 0.9));
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
  background: rgba(17, 17, 19, 0.82);
  overflow: hidden;
}

.chart.small {
  height: 200px;
}

.chart.zoomable {
  cursor: grab;
  user-select: none;
  touch-action: pan-y;
}

.chart.zoomable.is-panning {
  cursor: grabbing;
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
  border-bottom: 1px dashed rgba(148, 163, 184, 0.16);
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
  border-bottom: 1px dashed rgba(148, 163, 184, 0.16);
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
    grid-template-columns: 1fr;
    gap: 10px;
  }
  .range-fields {
    width: 100%;
  }
  .range-buttons {
    width: 100%;
    flex-basis: auto;
  }
  .range-actions {
    justify-self: start;
    flex-wrap: wrap;
  }
}

@media (max-width: 1280px) {
  .cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1180px) and (min-width: 901px) {
  .range-controls {
    --range-selector-width: 236px;
    grid-template-columns: var(--range-selector-width) var(--range-selector-width) auto;
  }
  .range-fields {
    width: var(--range-selector-width);
  }
}

@media (max-width: 760px) {
  .cards {
    grid-template-columns: minmax(0, 1fr);
  }
  .metric-card {
    min-height: 108px;
  }
}

@keyframes textFadeOnly {
  0% {
    opacity: 0.72;
  }
  100% {
    opacity: 1;
  }
}

@keyframes themeSwap {
  0% {
    opacity: 0.72;
  }
  68% {
    opacity: 1;
  }
  100% {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .text-fade-anim,
  .metric-value-anim,
  .i18n-switch-anim,
  html.theme-switching body,
  html.theme-switching .page,
  html.theme-switching .page::before,
  html.theme-switching .page::after,
  html.theme-switching .range-controls,
  html.theme-switching .range-date-trigger,
  html.theme-switching .range-segmented,
  html.theme-switching .range-action-btn,
  html.theme-switching .file-button,
  html.theme-switching .theme-dot-toggle,
  html.theme-switching .card,
  html.theme-switching .panel,
  html.theme-switching .chart {
    animation: none !important;
    transition: none !important;
  }
  .range-segmented-slider {
    transition: none !important;
  }
  html.theme-ready body,
  html.theme-ready .page,
  html.theme-ready .page::before,
  html.theme-ready .page::after,
  html.theme-ready .range-controls,
  html.theme-ready .range-date-trigger,
  html.theme-ready .range-segmented,
  html.theme-ready .range-action-btn,
  html.theme-ready .file-button,
  html.theme-ready .theme-dot-toggle,
  html.theme-ready .card,
  html.theme-ready .panel,
  html.theme-ready .chart {
    transition: none !important;
  }
}
</style>
</head>
<body>
<div class="page">
  <div class="hero">
    <div class="title">
      <h1 data-i18n="title">Codex Token Usage</h1>
    </div>
    <div class="hero-tools">
      <button type="button" id="theme-dot-toggle" class="theme-dot-toggle" aria-label="Switch color theme">
      </button>
    </div>
  </div>
  <div class="range-controls">
    <div class="range-fields">
      <button type="button" id="range-date-trigger" class="range-date-trigger" aria-haspopup="dialog" aria-expanded="false">
        <span id="range-date-label">2000/01/01 - 01/01</span>
      </button>
      <input type="hidden" id="range-start">
      <input type="hidden" id="range-end">
    </div>
    <div class="range-buttons range-segmented" id="quick-range-segmented">
      <span class="range-segmented-slider" id="quick-range-slider" aria-hidden="true"></span>
      <button type="button" data-range="1" data-i18n="last_1">1D</button>
      <button type="button" data-range="2" data-i18n="last_2">2D</button>
      <button type="button" data-range="7" data-i18n="last_7">1W</button>
      <button type="button" data-range="30" data-i18n="last_30">1M</button>
      <button type="button" data-range="90" data-i18n="last_90">3M</button>
      <button type="button" data-range="all" data-i18n="all_time">ALL</button>
    </div>
    <div class="range-actions">
      <button type="button" id="export-data" class="range-action-btn" data-i18n="export">Export</button>
      <label class="file-button"><span data-i18n="import">Import</span>
        <input type="file" id="import-data" accept="application/json" multiple>
      </label>
      <span class="import-status" id="import-status"></span>
    </div>
  </div>
  <div id="calendar-popover" class="calendar-popover hidden" aria-hidden="true">
    <div class="calendar-head">
      <button type="button" id="calendar-prev" class="calendar-nav-btn" aria-label="Previous month">&lsaquo;</button>
      <div class="calendar-title" id="calendar-title">January 2000</div>
      <button type="button" id="calendar-next" class="calendar-nav-btn" aria-label="Next month">&rsaquo;</button>
    </div>
    <div class="calendar-weekdays" id="calendar-weekdays"></div>
    <div class="calendar-days" id="calendar-days"></div>
    <div class="calendar-actions">
      <button type="button" id="calendar-clear" data-i18n="calendar_clear">Clear</button>
      <button type="button" id="calendar-today" data-i18n="calendar_today">Today</button>
    </div>
  </div>
  __EMPTY_BANNER__
  <div class="banner hidden" id="range-banner" data-i18n="empty_banner">No token usage found in this range.</div>
  <div class="cards">
    <div class="card metric-card" style="--delay:0.05s">
      <div class="label" data-i18n="card_total">Total tokens</div>
      <div class="value" id="value-total">__TOTAL_TOKENS__</div>
      <div class="sub"><span data-i18n="input">Input</span> <span id="value-input">__INPUT_TOKENS__</span> | <span data-i18n="output">Output</span> <span id="value-output">__OUTPUT_TOKENS__</span></div>
    </div>
    <div class="card metric-card" style="--delay:0.1s">
      <div class="label" data-i18n="card_cost">Estimated cost</div>
      <div class="value" id="value-cost">__TOTAL_COST__</div>
    </div>
  </div>

  <div class="panel-grid">
    <div class="panel wide" style="--delay:0.25s">
      <h3 data-i18n="daily_chart">Hourly total tokens</h3>
      <div id="chart-daily" class="chart"></div>
    </div>
  </div>

</div>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js"></script>
<script>
const DATA = __DATA_JSON__;
const I18N = __I18N_JSON__;
let currentLang = "en";
const CHART_AXIS_TEXT = "#94a3b8";
const CHART_AXIS_LINE = "rgba(148,163,184,0.28)";
const ZOOM_IN_FACTOR = 0.72;
const ZOOM_OUT_FACTOR = 1.25;
const MIN_WINDOW_PERCENT = 0.05;
const DAY_MS = 86_400_000;
const WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_LABELS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
let dailyChartInstance = null;
let chartResizeBound = false;
let chartWheelZoomBound = false;
let quickRangeResizeBound = false;
const THEME_STORAGE_KEY = "token-report-theme";
let themeSwitchTimer = null;
const calendarState = {
  open: false,
  minISO: "",
  maxISO: "",
  viewYear: 0,
  viewMonth: 0,
  draftStartISO: "",
  draftEndISO: "",
  selectingPhase: "start",
};

function prefersReducedMotion() {
  return Boolean(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
}

function triggerSwapAnimation(el, className) {
  if (!el || prefersReducedMotion()) return;
  el.classList.remove(className);
  const applyClass = () => {
    el.classList.add(className);
  };
  if (window.requestAnimationFrame) {
    window.requestAnimationFrame(applyClass);
    return;
  }
  setTimeout(applyClass, 0);
}

function setAnimatedText(el, text, options) {
  if (!el) return false;
  const opts = options || {};
  const nextText = String(text ?? "");
  const prevText = el.dataset.animatedText != null
    ? el.dataset.animatedText
    : (el.dataset.metricText != null ? el.dataset.metricText : (el.textContent || ""));
  if (prevText === nextText) {
    if (opts.syncAriaLabel) {
      el.setAttribute("aria-label", nextText);
    }
    return false;
  }
  el.textContent = nextText;
  el.dataset.animatedText = nextText;
  el.dataset.metricText = nextText;
  if (opts.syncAriaLabel) {
    el.setAttribute("aria-label", nextText);
  }
  const shouldAnimate = opts.animate !== false;
  if (shouldAnimate) {
    triggerSwapAnimation(el, opts.className || "text-fade-anim");
  }
  return true;
}

function updateLangToggleState() {
  // 语言切换控件已移除，保留函数以兼容调用。
}

function formatNumber(value) {
  return formatCompactNumber(value);
}

function formatCompactNumber(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0";
  const absNum = Math.abs(num);
  if (absNum >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(1).replace(/\\.0$/, "")}B`;
  }
  if (absNum >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1).replace(/\\.0$/, "")}M`;
  }
  if (absNum >= 1_000) {
    return `${(num / 1_000).toFixed(1).replace(/\\.0$/, "")}K`;
  }
  return new Intl.NumberFormat("en-US").format(num);
}

function formatChartNumber(value) {
  return formatCompactNumber(value);
}

function clampPercent(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return 0;
  if (num < 0) return 0;
  if (num > 100) return 100;
  return num;
}

function normalizeISO(value) {
  const raw = String(value || "").trim().replace(/\\//g, "-");
  if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(raw)) return "";
  return raw;
}

function toDisplayISO(value) {
  const iso = normalizeISO(value);
  return iso ? iso.replace(/-/g, "/") : "";
}

function getRangeInputValue(input) {
  if (!input) return "";
  return normalizeISO(input.dataset.iso || input.value || "");
}

function setRangeInputValue(input, value) {
  if (!input) return;
  const iso = normalizeISO(value);
  input.dataset.iso = iso;
  input.value = toDisplayISO(iso);
  input.setAttribute("aria-label", iso || "");
}

function formatRangeButtonLabel(startISO, endISO) {
  const start = normalizeISO(startISO);
  const end = normalizeISO(endISO);
  if (!start || !end) return "--/--/-- - --/--";
  const startText = toDisplayISO(start);
  const endText = start.slice(0, 4) === end.slice(0, 4) ? end.slice(5).replace(/-/g, "/") : toDisplayISO(end);
  return `${startText} - ${endText}`;
}

function updateRangeDateButton(startISO, endISO) {
  const trigger = document.getElementById("range-date-trigger");
  const label = document.getElementById("range-date-label");
  const text = formatRangeButtonLabel(startISO, endISO);
  if (label) setAnimatedText(label, text, { animate: true });
  if (trigger) trigger.setAttribute("aria-label", text);
}

function normalizeTheme(value) {
  return value === "bronze" ? "bronze" : "neon";
}

function readStoredTheme() {
  try {
    return normalizeTheme(window.localStorage.getItem(THEME_STORAGE_KEY) || "");
  } catch (_) {
    return "neon";
  }
}

function persistTheme(theme) {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch (_) {
    // ignore
  }
}

function updateThemeDotToggle(theme) {
  const btn = document.getElementById("theme-dot-toggle");
  if (!btn) return;
  const isBronze = theme === "bronze";
  btn.classList.toggle("is-bronze", isBronze);
  const nextThemeLabel = isBronze ? "Neon" : "Bronze";
  btn.setAttribute("aria-label", `Switch to ${nextThemeLabel} theme`);
}

function getThemePalette() {
  const style = window.getComputedStyle(document.documentElement);
  const read = (name, fallback) => {
    const value = style.getPropertyValue(name).trim();
    return value || fallback;
  };
  return {
    lineStart: read("--chart-line-start", "#B026FF"),
    lineEnd: read("--chart-line-end", "#00F0FF"),
    areaStart: read("--chart-area-start", "rgba(176, 38, 255, 0.55)"),
    areaMid: read("--chart-area-mid", "rgba(0, 240, 255, 0.22)"),
    areaEnd: read("--chart-area-end", "rgba(0, 240, 255, 0)"),
    tooltipBorder: read("--tooltip-border", "rgba(176, 38, 255, 0.45)"),
    axisPointer: read("--axis-pointer", "rgba(0, 240, 255, 0.7)"),
  };
}

function playThemeSwitchMotion() {
  if (prefersReducedMotion()) return;
  const root = document.documentElement;
  root.classList.remove("theme-switching");
  const addClass = () => {
    root.classList.add("theme-switching");
  };
  if (window.requestAnimationFrame) {
    window.requestAnimationFrame(addClass);
  } else {
    setTimeout(addClass, 0);
  }
  if (themeSwitchTimer != null) {
    window.clearTimeout(themeSwitchTimer);
  }
  themeSwitchTimer = window.setTimeout(() => {
    root.classList.remove("theme-switching");
    themeSwitchTimer = null;
  }, 540);
}

function applyTheme(theme, options) {
  const opts = options || {};
  const currentTheme = normalizeTheme(document.documentElement.dataset.theme || "neon");
  const nextTheme = normalizeTheme(theme);
  document.documentElement.dataset.theme = nextTheme;
  updateThemeDotToggle(nextTheme);
  if (opts.animate !== false && currentTheme !== nextTheme) {
    playThemeSwitchMotion();
  }
  if (opts.persist !== false) {
    persistTheme(nextTheme);
  }
  if (opts.refreshChart !== false && currentRange.start && currentRange.end) {
    applyRangePreview(currentRange.start, currentRange.end);
  }
}

function quickRangePresetFor(startISO, endISO, minISO, maxISO) {
  if (!startISO || !endISO || !minISO || !maxISO) return "";
  if (startISO === minISO && endISO === maxISO) return "all";
  if (endISO !== maxISO) return "";
  const presetDays = [1, 2, 7, 30, 90];
  for (const days of presetDays) {
    let expectedStart = addDaysISO(maxISO, -(days - 1));
    if (expectedStart < minISO) expectedStart = minISO;
    if (startISO === expectedStart) {
      return String(days);
    }
  }
  return "";
}

function updateQuickRangeSlider() {
  const segmented = document.getElementById("quick-range-segmented");
  const slider = document.getElementById("quick-range-slider");
  if (!segmented || !slider) return;
  const activeBtn = segmented.querySelector("button.is-active");
  if (!(activeBtn instanceof HTMLElement)) {
    slider.style.opacity = "0";
    slider.style.width = "0";
    slider.style.transform = "translateX(0)";
    return;
  }
  const offsetX = Math.max(0, activeBtn.offsetLeft);
  const activeWidth = Math.max(0, activeBtn.offsetWidth);
  slider.style.opacity = "1";
  slider.style.width = `${activeWidth.toFixed(2)}px`;
  slider.style.transform = `translate3d(${offsetX.toFixed(2)}px, 0, 0)`;
}

function setQuickRangeActive(preset) {
  const segmented = document.getElementById("quick-range-segmented");
  if (!segmented) return;
  segmented.querySelectorAll("button[data-range]").forEach((btn) => {
    btn.classList.toggle("is-active", Boolean(preset) && btn.dataset.range === preset);
  });
  updateQuickRangeSlider();
}

function updateQuickRangeState(startISO, endISO) {
  const minISO = (DATA.range && DATA.range.start) || "";
  const maxISO = (DATA.range && DATA.range.end) || "";
  const preset = quickRangePresetFor(startISO, endISO, minISO, maxISO);
  setQuickRangeActive(preset);
}

function closeCalendarPopover() {
  const popover = document.getElementById("calendar-popover");
  const trigger = document.getElementById("range-date-trigger");
  if (!popover) return;
  calendarState.open = false;
  calendarState.selectingPhase = "start";
  popover.classList.add("hidden");
  popover.setAttribute("aria-hidden", "true");
  if (trigger) trigger.setAttribute("aria-expanded", "false");
}

function positionCalendarPopover() {
  const popover = document.getElementById("calendar-popover");
  const trigger = document.getElementById("range-date-trigger");
  if (!popover || !trigger || !calendarState.open) return;
  const rect = trigger.getBoundingClientRect();
  const gap = 8;
  const margin = 10;
  const popW = popover.offsetWidth || 320;
  const popH = popover.offsetHeight || 320;
  let left = rect.left;
  let top = rect.bottom + gap;
  if (left + popW + margin > window.innerWidth) {
    left = Math.max(margin, window.innerWidth - popW - margin);
  }
  if (top + popH + margin > window.innerHeight) {
    top = Math.max(margin, rect.top - popH - gap);
  }
  popover.style.left = `${Math.round(left)}px`;
  popover.style.top = `${Math.round(top)}px`;
}

function renderCalendarDays() {
  const titleEl = document.getElementById("calendar-title");
  const daysEl = document.getElementById("calendar-days");
  if (!titleEl || !daysEl) return;
  const year = calendarState.viewYear;
  const month = calendarState.viewMonth;
  let selectedStart = normalizeISO(calendarState.draftStartISO);
  let selectedEnd = normalizeISO(calendarState.draftEndISO);
  if (selectedStart && selectedEnd && selectedStart > selectedEnd) {
    const tmp = selectedStart;
    selectedStart = selectedEnd;
    selectedEnd = tmp;
  }
  const todayISO = toLocalISODate(new Date());
  const monthName = MONTH_LABELS[month] || "";
  setAnimatedText(titleEl, `${monthName} ${year}`, { animate: true });
  const monthStart = new Date(Date.UTC(year, month, 1));
  const startOffset = monthStart.getUTCDay();
  const gridStart = new Date(Date.UTC(year, month, 1 - startOffset));
  let htmlDays = "";
  for (let i = 0; i < 42; i++) {
    const d = new Date(gridStart.getTime() + i * DAY_MS);
    const iso = formatISODate(d);
    const isOutside = d.getUTCMonth() !== month;
    const isRangeStart = iso === selectedStart;
    const isRangeEnd = iso === selectedEnd;
    const isSelected = isRangeStart || isRangeEnd;
    const isInRange = Boolean(selectedStart && selectedEnd && iso > selectedStart && iso < selectedEnd);
    const isToday = iso === todayISO;
    const isDisabled = (calendarState.minISO && iso < calendarState.minISO) || (calendarState.maxISO && iso > calendarState.maxISO);
    const classes = [
      "calendar-day-btn",
      isOutside ? "is-outside" : "",
      isSelected ? "is-selected" : "",
      isRangeStart ? "is-range-start" : "",
      isRangeEnd ? "is-range-end" : "",
      isInRange ? "is-in-range" : "",
      isToday ? "is-today" : "",
    ].filter(Boolean).join(" ");
    const disabledAttr = isDisabled ? " disabled" : "";
    const dayText = String(d.getUTCDate());
    htmlDays += `<button type="button" class="${classes}" data-iso="${iso}"${disabledAttr}>${dayText}</button>`;
  }
  daysEl.innerHTML = htmlDays;
}

function shiftCalendarMonth(step) {
  let month = calendarState.viewMonth + step;
  let year = calendarState.viewYear;
  if (month < 0) {
    month = 11;
    year -= 1;
  } else if (month > 11) {
    month = 0;
    year += 1;
  }
  calendarState.viewYear = year;
  calendarState.viewMonth = month;
  renderCalendarDays();
}

function applyCalendarRange(startISO, endISO) {
  const startInput = document.getElementById("range-start");
  const endInput = document.getElementById("range-end");
  if (!startInput || !endInput) return;
  setRangeInputValue(startInput, startISO);
  setRangeInputValue(endInput, endISO);
  applyRange(startISO, endISO);
}

function openCalendarPopover() {
  const popover = document.getElementById("calendar-popover");
  const trigger = document.getElementById("range-date-trigger");
  const startInput = document.getElementById("range-start");
  const endInput = document.getElementById("range-end");
  if (!popover || !trigger || !startInput || !endInput) return;
  const minISO = normalizeISO((DATA.range && DATA.range.start) || "");
  const maxISO = normalizeISO((DATA.range && DATA.range.end) || "");
  let startISO = getRangeInputValue(startInput) || minISO || maxISO || toLocalISODate(new Date());
  let endISO = getRangeInputValue(endInput) || startISO;
  if (startISO > endISO) {
    const tmp = startISO;
    startISO = endISO;
    endISO = tmp;
  }
  let selectedDate = parseISODate(startISO);
  if (!Number.isFinite(selectedDate.getTime())) {
    selectedDate = parseISODate(toLocalISODate(new Date()));
  }
  calendarState.open = true;
  calendarState.minISO = minISO;
  calendarState.maxISO = maxISO;
  calendarState.viewYear = selectedDate.getUTCFullYear();
  calendarState.viewMonth = selectedDate.getUTCMonth();
  calendarState.draftStartISO = startISO;
  calendarState.draftEndISO = endISO;
  calendarState.selectingPhase = "start";
  renderCalendarDays();
  popover.classList.remove("hidden");
  popover.setAttribute("aria-hidden", "false");
  trigger.setAttribute("aria-expanded", "true");
  positionCalendarPopover();
}

function applyI18n(lang, options) {
  const opts = options || {};
  const source = opts.source || "system";
  const shouldAnimate = opts.animate !== false && source === "user";
  currentLang = lang;
  const dict = I18N[lang] || I18N.en;
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.dataset.i18n;
    const nextText = dict[key];
    if (nextText && el.textContent !== nextText) {
      setAnimatedText(el, nextText, {
        animate: shouldAnimate,
        className: "i18n-switch-anim",
      });
    }
  });
  updateLangToggleState(lang, shouldAnimate);
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

function toLocalISODate(d) {
  const date = d || new Date();
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function animateMetricValue(el, text) {
  setAnimatedText(el, text, {
    animate: true,
    className: "metric-value-anim",
    syncAriaLabel: true,
  });
}

function setDisplayText(id, value, animate) {
  const el = document.getElementById(id);
  if (!el) return;
  const text = String(value ?? "");
  const useAnimation = typeof animate === "object" ? animate.animate !== false : animate !== false;
  setAnimatedText(el, text, {
    animate: useAnimation,
    className: "metric-value-anim",
    syncAriaLabel: true,
  });
}

function readDailyValue(dayISO, key) {
  const labels = (DATA.daily && DATA.daily.labels) || [];
  const idx = labels.indexOf(dayISO);
  if (idx < 0) return 0;
  const arr = (DATA.daily && DATA.daily[key]) || [];
  return Number(arr[idx] || 0);
}

let latestDataStamp = (DATA.meta && DATA.meta.generated_at) || "";
let syncInFlight = false;

function getDataStamp(doc) {
  if (doc && doc.meta && doc.meta.generated_at) return String(doc.meta.generated_at);
  const start = doc && doc.range ? doc.range.start : "";
  const end = doc && doc.range ? doc.range.end : "";
  const count = doc && doc.daily && Array.isArray(doc.daily.labels) ? doc.daily.labels.length : 0;
  return `${start}:${end}:${count}`;
}

function applyLatestData(nextData) {
  if (!nextData || !nextData.range || !nextData.daily || !Array.isArray(nextData.daily.labels)) {
    return false;
  }
  DATA.range = nextData.range;
  DATA.daily = nextData.daily;
  DATA.daily_models = nextData.daily_models || {};
  DATA.hourly = nextData.hourly || { labels: [], total: [] };
  DATA.hourly_daily = nextData.hourly_daily || {};
  DATA.session_spans = nextData.session_spans || [];
  DATA.events = nextData.events || [];
  DATA.pricing = nextData.pricing || DATA.pricing;
  DATA.meta = nextData.meta || {};
  rebuildLabelIndex();
  rebuildHourEventMap();

  const minISO = (DATA.range && DATA.range.start) || "";
  const maxISO = (DATA.range && DATA.range.end) || "";
  if (!minISO || !maxISO) return true;
  syncRangeControls(minISO, maxISO);
  const desiredStart = clampISO(currentRange.start || minISO, minISO, maxISO);
  const desiredEnd = clampISO(currentRange.end || maxISO, minISO, maxISO);
  applyRange(desiredStart, desiredEnd);
  return true;
}

async function syncLatestData() {
  if (window.location.protocol === "file:") return false;
  if (syncInFlight) return false;
  syncInFlight = true;
  try {
    const response = await fetch(`data.json?ts=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return false;
    const incoming = await response.json();
    const incomingStamp = getDataStamp(incoming);
    if (incomingStamp === latestDataStamp) return false;
    const ok = applyLatestData(incoming);
    if (ok) {
      latestDataStamp = incomingStamp;
    }
    return ok;
  } catch (err) {
    return false;
  } finally {
    syncInFlight = false;
  }
}

function setupAutoSync() {
  syncLatestData();
  window.setInterval(() => {
    syncLatestData();
  }, 15000);
  window.addEventListener("focus", () => {
    syncLatestData();
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      syncLatestData();
    }
  });
}

function lineChart(el, labels, values) {
  if (!el) return;
  const chartLabels = Array.isArray(labels) ? labels : [];
  const chartValues = Array.isArray(values) ? values.map(v => Number(v || 0)) : [];
  const xAxisLabelMode = pickXAxisLabelMode(chartLabels);
  if (!window.echarts) {
    el.innerHTML = "";
    return;
  }
  if (!dailyChartInstance || dailyChartInstance.isDisposed() || dailyChartInstance.getDom() !== el) {
    if (dailyChartInstance && !dailyChartInstance.isDisposed()) {
      dailyChartInstance.dispose();
    }
    dailyChartInstance = window.echarts.init(el, null, { renderer: "canvas" });
  }
  if (!chartResizeBound) {
    window.addEventListener("resize", () => {
      if (dailyChartInstance && !dailyChartInstance.isDisposed()) {
        dailyChartInstance.resize();
      }
    });
    chartResizeBound = true;
  }
  if (!chartWheelZoomBound) {
    el.addEventListener(
      "wheel",
      (event) => {
        if (!dailyChartInstance || dailyChartInstance.isDisposed()) return;
        event.preventDefault();
        event.stopPropagation();
        const option = dailyChartInstance.getOption();
        const dz = (option.dataZoom || [])[0] || {};
        const currentStart = clampPercent(dz.start != null ? dz.start : 0);
        const currentEnd = clampPercent(dz.end != null ? dz.end : 100);
        const currentWindow = Math.max(MIN_WINDOW_PERCENT, currentEnd - currentStart);
        const rect = el.getBoundingClientRect();
        const ratioRaw = (event.clientX - rect.left) / Math.max(1, rect.width);
        const anchorRatio = Math.min(1, Math.max(0, ratioRaw));
        const anchor = currentStart + currentWindow * anchorRatio;
        const zoomFactor = event.deltaY < 0 ? ZOOM_IN_FACTOR : ZOOM_OUT_FACTOR;
        const nextWindow = Math.min(100, Math.max(MIN_WINDOW_PERCENT, currentWindow * zoomFactor));
        let nextStart = anchor - nextWindow / 2;
        let nextEnd = anchor + nextWindow / 2;
        if (nextStart < 0) {
          nextStart = 0;
          nextEnd = nextWindow;
        }
        if (nextEnd > 100) {
          nextEnd = 100;
          nextStart = 100 - nextWindow;
        }
        dailyChartInstance.dispatchAction({
          type: "dataZoom",
          dataZoomIndex: 0,
          start: clampPercent(nextStart),
          end: clampPercent(nextEnd),
        });
      },
      { passive: false, capture: true }
    );
    chartWheelZoomBound = true;
  }
  if (!chartValues.length) {
    dailyChartInstance.clear();
    return;
  }
  const animateChartUpdate = hasInitialMetricsRender && !prefersReducedMotion();
  const windowSize = chartValues.length > 200 ? Math.max(MIN_WINDOW_PERCENT, (200 / chartValues.length) * 100) : 100;
  const zoomStart = Math.max(0, (100 - windowSize) / 2);
  const zoomEnd = Math.min(100, zoomStart + windowSize);
  const palette = getThemePalette();
  const chartOption = {
    backgroundColor: "transparent",
    animation: animateChartUpdate,
    animationDuration: animateChartUpdate ? 260 : 0,
    animationDurationUpdate: animateChartUpdate ? 320 : 0,
    animationEasing: "cubicOut",
    animationEasingUpdate: "cubicOut",
    grid: { left: 48, right: 26, top: 16, bottom: 56 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(10,10,10,0.92)",
      borderColor: palette.tooltipBorder,
      borderWidth: 1,
      textStyle: { color: "#f8fafc" },
      axisPointer: { type: "line", lineStyle: { color: palette.axisPointer, width: 1 } },
      valueFormatter: (value) => formatChartNumber(value),
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: chartLabels,
      axisLabel: {
        color: CHART_AXIS_TEXT,
        hideOverlap: true,
        formatter: (value) => formatXAxisLabel(value, xAxisLabelMode),
      },
      axisLine: { lineStyle: { color: CHART_AXIS_LINE } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: CHART_AXIS_TEXT,
        formatter: (value) => formatChartNumber(value),
      },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.10)" } },
    },
    dataZoom: [
      {
        type: "inside",
        xAxisIndex: 0,
        start: zoomStart,
        end: zoomEnd,
        zoomOnMouseWheel: false,
        moveOnMouseMove: true,
        moveOnMouseWheel: false,
      },
    ],
    series: [
      {
        type: "line",
        data: chartValues,
        showSymbol: false,
        smooth: 0.46,
        lineStyle: {
          width: 1.4,
          color: new window.echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: palette.lineStart },
            { offset: 1, color: palette.lineEnd },
          ]),
          opacity: 0.78,
        },
        areaStyle: {
          color: new window.echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: palette.lineStart },
            { offset: 0.38, color: palette.areaStart },
            { offset: 0.62, color: palette.areaMid },
            { offset: 1, color: palette.areaEnd },
          ]),
        },
        emphasis: { focus: "series" },
      },
    ],
  };
  dailyChartInstance.setOption(chartOption, {
    notMerge: false,
    lazyUpdate: true,
  });
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
let hasInitialMetricsRender = false;
const HOUR_MS = 3_600_000;
const MAX_CHART_POINTS = 1600;
let hourEventMap = new Map();

function parseHourMs(ts) {
  if (!ts) return null;
  const iso = String(ts).replace(" ", "T");
  const ms = Date.parse(iso);
  if (!Number.isFinite(ms)) return null;
  return Math.floor(ms / HOUR_MS) * HOUR_MS;
}

function rebuildHourEventMap() {
  const next = new Map();
  (DATA.events || []).forEach(ev => {
    if (!ev || !ev.ts) return;
    const hourMs = parseHourMs(ev.ts);
    if (hourMs == null) return;
    const totalValue = ev.total != null ? ev.total : ev.value;
    next.set(hourMs, (next.get(hourMs) || 0) + Number(totalValue || 0));
  });
  hourEventMap = next;
}

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

function pad2(value) {
  return String(value).padStart(2, "0");
}

function formatHourLabel(dateObj) {
  return `${dateObj.getFullYear()}-${pad2(dateObj.getMonth() + 1)}-${pad2(dateObj.getDate())} ${pad2(dateObj.getHours())}:00`;
}

function parseHourLabel(label) {
  const raw = String(label || "").trim();
  const m = raw.match(/^(\\d{4})-(\\d{2})-(\\d{2})\\s+(\\d{2}):(\\d{2})$/);
  if (!m) return null;
  const year = Number(m[1]);
  const month = Number(m[2]);
  const day = Number(m[3]);
  const hour = Number(m[4]);
  const minute = Number(m[5]);
  const dt = new Date(year, month - 1, day, hour, minute, 0, 0);
  if (Number.isNaN(dt.getTime())) return null;
  return dt;
}

function pickXAxisLabelMode(labels) {
  if (!Array.isArray(labels) || labels.length < 2) {
    return "hour";
  }
  const first = parseHourLabel(labels[0]);
  const last = parseHourLabel(labels[labels.length - 1]);
  if (!first || !last) {
    return "hour";
  }
  const spanHours = Math.abs(last.getTime() - first.getTime()) / HOUR_MS;
  return spanHours <= 24 ? "hour" : "day";
}

function formatXAxisLabel(label, mode) {
  const dt = parseHourLabel(label);
  if (!dt) return label;
  if (mode === "day") {
    return `${pad2(dt.getMonth() + 1)}-${pad2(dt.getDate())}`;
  }
  return `${pad2(dt.getHours())}:${pad2(dt.getMinutes())}`;
}

function buildHourlySeries(startISO, endISO) {
  const labels = [];
  const totals = [];
  if (!startISO || !endISO) return { labels, totals };
  const startMs = new Date(`${startISO}T00:00:00`).getTime();
  const endMs = new Date(`${endISO}T23:00:00`).getTime();
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || startMs > endMs) {
    return { labels, totals };
  }
  const totalHours = Math.floor((endMs - startMs) / HOUR_MS) + 1;
  const bucketHours = Math.max(1, Math.ceil(totalHours / MAX_CHART_POINTS));

  for (let bucketStart = startMs; bucketStart <= endMs; bucketStart += bucketHours * HOUR_MS) {
    const bucketEnd = Math.min(endMs, bucketStart + (bucketHours - 1) * HOUR_MS);
    let bucketTotal = 0;
    for (let hour = bucketStart; hour <= bucketEnd; hour += HOUR_MS) {
      bucketTotal += Number(hourEventMap.get(hour) || 0);
    }
    labels.push(formatHourLabel(new Date(bucketEnd)));
    totals.push(bucketTotal);
  }

  const endLabel = formatHourLabel(new Date(endMs));
  if (labels[labels.length - 1] !== endLabel) {
    labels.push(endLabel);
    totals.push(Number(hourEventMap.get(endMs) || 0));
  }
  return { labels, totals };
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
  const inputTokens = rec.input_tokens || 0;
  const cachedInputTokens = rec.cached_input_tokens || 0;
  const billableInputTokens = Math.max(0, inputTokens - cachedInputTokens);
  const outputTotal = (rec.output_tokens || 0) + (rec.reasoning_output_tokens || 0);
  return (
    (billableInputTokens / 1_000_000) * (pricing.input || 0) +
    (cachedInputTokens / 1_000_000) * (cachedPrice || 0) +
    (outputTotal / 1_000_000) * (pricing.output || 0)
  );
}

function formatMoneyUSD(value) {
  if (value == null || !Number.isFinite(value)) return "n/a";
  if (value >= 1) return `$${value.toFixed(2)}`;
  return `$${value.toFixed(4)}`;
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
  rebuildHourEventMap();
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
      if (statusEl) setAnimatedText(statusEl, "", { animate: false });
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
        if (statusEl) setAnimatedText(statusEl, formatI18n("import_invalid"), { animate: true });
        return;
      }
      const mergedOk = mergeImportedData([DATA, ...imported]);
      if (!mergedOk) {
        if (statusEl) setAnimatedText(statusEl, formatI18n("import_failed"), { animate: true });
        return;
      }
      if (statusEl) setAnimatedText(statusEl, formatI18n("import_done", { count: imported.length }), { animate: true });
    });
  }
}

function applyRange(startISO, endISO) {
  return applyRangeInternal(startISO, endISO, false);
}

function applyRangePreview(startISO, endISO) {
  return applyRangeInternal(startISO, endISO, true);
}

function applyRangeInternal(startISO, endISO, previewOnly) {
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

  const dayLabels = DATA.daily.labels.slice(startIdx, endIdx + 1);
  const hourlySeries = buildHourlySeries(startISO, endISO);
  const hourlyLabels = hourlySeries.labels;
  const hourlyTotals = hourlySeries.totals;

  const startInput = document.getElementById("range-start");
  const endInput = document.getElementById("range-end");
  if (startInput) setRangeInputValue(startInput, startISO);
  if (endInput) setRangeInputValue(endInput, endISO);
  updateRangeDateButton(startISO, endISO);
  updateQuickRangeState(startISO, endISO);
  const animateMetrics = true;
  setDisplayText("range-text", `${startISO} to ${endISO}`, animateMetrics);
  lineChart(document.getElementById("chart-daily"), hourlyLabels, hourlyTotals);

  if (previewOnly) {
    return;
  }

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
  setDisplayText("sessions-count", formatNumber(sessions), animateMetrics);
  setDisplayText("active-days", formatNumber(activeDays), animateMetrics);
  setDisplayText("value-total", formatNumber(totalTokens), animateMetrics);
  setDisplayText("value-input", formatNumber(inputTokens), animateMetrics);
  setDisplayText("value-output", formatNumber(outputTokens), animateMetrics);
  setDisplayText("value-cached", formatNumber(cachedTokens), animateMetrics);
  setDisplayText("value-reasoning", formatNumber(reasoningTokens), animateMetrics);
  setDisplayText("value-cache-rate", `${(cacheRate * 100).toFixed(1)}%`, animateMetrics);
  setDisplayText("value-avg-day", formatNumber(avgPerDay), animateMetrics);
  setDisplayText("value-avg-session", formatNumber(avgPerSession), animateMetrics);

  const modelTotals = aggregateModels(dayLabels);
  const modelItems = Object.keys(modelTotals).map(model => ({ model, rec: modelTotals[model] }));
  modelItems.sort((a, b) => (b.rec.total_tokens || 0) - (a.rec.total_tokens || 0));

  let totalCost = 0;
  let anyPriced = false;
  modelItems.forEach(item => {
    const pricing = resolvePricing(item.model);
    const cost = costUSD(item.rec, pricing);
    if (cost != null) {
      totalCost += cost;
      anyPriced = true;
    }
  });

  const shareCost = anyPriced ? formatMoneyUSD(totalCost) : "n/a";
  setDisplayText("value-cost", shareCost, animateMetrics);
  hasInitialMetricsRender = true;
}

function syncRangeControls(minISO, maxISO) {
  const startInput = document.getElementById("range-start");
  const endInput = document.getElementById("range-end");
  if (!startInput || !endInput || !minISO || !maxISO) return;
  startInput.min = minISO;
  startInput.max = maxISO;
  endInput.min = minISO;
  endInput.max = maxISO;
  setRangeInputValue(startInput, minISO);
  setRangeInputValue(endInput, maxISO);
}

function setupRangeControls() {
  const startInput = document.getElementById("range-start");
  const endInput = document.getElementById("range-end");
  const minISO = (DATA.range && DATA.range.start) || "";
  const maxISO = (DATA.range && DATA.range.end) || "";
  if (!startInput || !endInput || !minISO || !maxISO) return;
  syncRangeControls(minISO, maxISO);
  updateRangeDateButton(minISO, maxISO);
  updateQuickRangeState(minISO, maxISO);
  if (!quickRangeResizeBound) {
    window.addEventListener("resize", updateQuickRangeSlider);
    quickRangeResizeBound = true;
  }

  document.querySelectorAll("[data-range]").forEach(btn => {
    btn.addEventListener("click", () => {
      const value = btn.dataset.range;
      if (!value) return;
      setQuickRangeActive(value);
      const runApply = (startISO, endISO) => {
        if (window.requestAnimationFrame) {
          window.requestAnimationFrame(() => applyRange(startISO, endISO));
        } else {
          applyRange(startISO, endISO);
        }
      };
      if (value === "all") {
        runApply(minISO, maxISO);
        return;
      }
      const days = parseInt(value, 10);
      if (!days) return;
      const end = maxISO;
      let start = addDaysISO(end, -(days - 1));
      if (start < minISO) start = minISO;
      runApply(start, end);
    });
  });
}

function setupThemeToggle() {
  const btn = document.getElementById("theme-dot-toggle");
  const initialTheme = readStoredTheme();
  applyTheme(initialTheme, { persist: false, refreshChart: false, animate: false });
  if (!btn) return;
  btn.addEventListener("click", () => {
    const current = normalizeTheme(document.documentElement.dataset.theme || "neon");
    const nextTheme = current === "neon" ? "bronze" : "neon";
    applyTheme(nextTheme, { persist: true, refreshChart: true });
  });
}

function setupCustomDatePicker() {
  const popover = document.getElementById("calendar-popover");
  const weekdays = document.getElementById("calendar-weekdays");
  const days = document.getElementById("calendar-days");
  const prevBtn = document.getElementById("calendar-prev");
  const nextBtn = document.getElementById("calendar-next");
  const clearBtn = document.getElementById("calendar-clear");
  const todayBtn = document.getElementById("calendar-today");
  const trigger = document.getElementById("range-date-trigger");
  const startInput = document.getElementById("range-start");
  const endInput = document.getElementById("range-end");
  if (!popover || !weekdays || !days || !prevBtn || !nextBtn || !clearBtn || !todayBtn || !trigger || !startInput || !endInput) return;

  weekdays.innerHTML = WEEKDAY_LABELS.map(label => `<span>${label}</span>`).join("");

  const open = () => {
    if (calendarState.open) {
      closeCalendarPopover();
      return;
    }
    openCalendarPopover();
  };
  trigger.addEventListener("click", open);
  trigger.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " " || event.key === "ArrowDown") {
      event.preventDefault();
      open();
    }
    if (event.key === "Escape") {
      closeCalendarPopover();
    }
  });

  prevBtn.addEventListener("click", () => {
    shiftCalendarMonth(-1);
    positionCalendarPopover();
  });
  nextBtn.addEventListener("click", () => {
    shiftCalendarMonth(1);
    positionCalendarPopover();
  });

  days.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (!target.classList.contains("calendar-day-btn")) return;
    if (target.hasAttribute("disabled")) return;
    const iso = normalizeISO(target.dataset.iso || "");
    if (!iso) return;
    if (calendarState.selectingPhase === "start" || !calendarState.draftStartISO) {
      calendarState.draftStartISO = iso;
      calendarState.draftEndISO = iso;
      calendarState.selectingPhase = "end";
      renderCalendarDays();
      return;
    }
    let startISO = normalizeISO(calendarState.draftStartISO) || iso;
    let endISO = iso;
    if (endISO < startISO) {
      const tmp = startISO;
      startISO = endISO;
      endISO = tmp;
    }
    calendarState.draftStartISO = startISO;
    calendarState.draftEndISO = endISO;
    applyCalendarRange(startISO, endISO);
    closeCalendarPopover();
  });

  clearBtn.addEventListener("click", () => {
    const startISO = calendarState.minISO || getRangeInputValue(startInput);
    const endISO = calendarState.maxISO || getRangeInputValue(endInput) || startISO;
    if (!startISO || !endISO) return;
    calendarState.draftStartISO = startISO;
    calendarState.draftEndISO = endISO;
    applyCalendarRange(startISO, endISO);
    closeCalendarPopover();
  });

  todayBtn.addEventListener("click", () => {
    const todayISO = clampISO(toLocalISODate(new Date()), calendarState.minISO, calendarState.maxISO);
    if (!todayISO) return;
    calendarState.draftStartISO = todayISO;
    calendarState.draftEndISO = todayISO;
    applyCalendarRange(todayISO, todayISO);
    closeCalendarPopover();
  });

  document.addEventListener("mousedown", (event) => {
    if (!calendarState.open) return;
    const target = event.target;
    if (!(target instanceof Node)) {
      closeCalendarPopover();
      return;
    }
    if (popover.contains(target) || trigger.contains(target)) return;
    closeCalendarPopover();
  });

  document.addEventListener("keydown", (event) => {
    if (!calendarState.open) return;
    if (event.key === "Escape") {
      closeCalendarPopover();
    }
  });

  window.addEventListener("resize", () => {
    if (calendarState.open) positionCalendarPopover();
  });
  window.addEventListener("scroll", () => {
    if (calendarState.open) positionCalendarPopover();
  }, true);
}

function setupDailyChartZoom() {
  // 已由 ECharts dataZoom 提供滑动与缩放。
}

window.addEventListener("load", () => {
  applyI18n("en", { animate: false, source: "boot" });
  rebuildHourEventMap();
  setupThemeToggle();
  setupRangeControls();
  setupCustomDatePicker();
  setupDailyChartZoom();
  setupImportExport();
  setupAutoSync();
  const startInput = document.getElementById("range-start");
  const endInput = document.getElementById("range-end");
  applyRange(
    getRangeInputValue(startInput) || (DATA.range && DATA.range.start) || "",
    getRangeInputValue(endInput) || (DATA.range && DATA.range.end) || ""
  );
  window.requestAnimationFrame(() => {
    document.documentElement.classList.add("theme-ready");
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
        "SOURCE_PATH": source_path,
        "EMPTY_BANNER": empty_banner,
        "DATA_JSON": data_json,
        "I18N_JSON": i18n_json,
    }
    for key, value in replacements.items():
        template = template.replace(f"__{key}__", value)
    return template


def sync_frontend_dist(frontend_dist: Path, out_dir: Path) -> Path:
    if not frontend_dist.exists() or not frontend_dist.is_dir():
        raise FileNotFoundError(
            f"frontend dist not found: {frontend_dist}. "
            "请先在 web 目录执行 npm install && npm run build。"
        )

    index_path = frontend_dist / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(
            f"frontend entry not found: {index_path}. "
            "请确认前端构建产物包含 index.html。"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    for item in frontend_dist.iterdir():
        target = out_dir / item.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)

    return out_dir / "index.html"


def _is_local_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _find_free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_local_http_server(out_dir: Path, port: int | None = None) -> str | None:
    if port is None:
        port = _find_free_local_port()
    url = f"http://127.0.0.1:{port}/index.html"

    cmd = [
        sys.executable,
        "-m",
        "http.server",
        str(port),
        "--bind",
        "127.0.0.1",
        "--directory",
        str(out_dir),
    ]
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    else:
        kwargs["start_new_session"] = True

    try:
        subprocess.Popen(cmd, **kwargs)
    except OSError:
        return None

    for _ in range(25):
        if _is_local_port_open(port):
            return url
        time.sleep(0.1)
    return None


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
    parser.add_argument(
        "--frontend-dist",
        default="web/dist",
        help="Path to frontend dist directory (default: web/dist).",
    )
    parser.add_argument("--pricing-file", help="Path to pricing json.")
    parser.add_argument("--json", action="store_true", help="Deprecated: data.json is always written.")
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
    prices, _, aliases = load_pricing(pricing_path)
    usage = collect_usage(session_root, since, until)

    if args.days and since is None and until is None and usage["active_days"]:
        last_day = max(usage["active_days"])
        since = last_day - timedelta(days=args.days - 1)
        usage = collect_usage(session_root, since, until)

    active_days = usage["active_days"]
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
        cached_price = pricing["cached_input"] if pricing["cached_input"] is not None else pricing["input"]
        input_tokens_total = rec["input_tokens"]
        cached_input_tokens = rec["cached_input_tokens"]
        billable_input_tokens = max(0, input_tokens_total - cached_input_tokens)
        output_total = rec["output_tokens"] + rec["reasoning_output_tokens"]
        cost = (
            dollars_from_tokens(billable_input_tokens, pricing["input"])
            + dollars_from_tokens(cached_input_tokens, cached_price)
            + dollars_from_tokens(output_total, pricing["output"])
        )
        model_costs[model] = cost
        total_cost += cost

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
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_path": str(session_root),
    }
    data["meta"] = {
        "generated_at": summary["generated_at"],
        "source_path": str(session_root),
    }

    out_dir = Path(args.out)
    frontend_dist = Path(args.frontend_dist)
    try:
        index_path = sync_frontend_dist(frontend_dist, out_dir)
    except (FileNotFoundError, OSError) as exc:
        print(f"Could not prepare frontend assets: {exc}", file=sys.stderr)
        return 2

    data_path = out_dir / "data.json"
    data_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"Report written to {index_path}")
    if args.open:
        if hasattr(os, "startfile"):
            target = str(index_path)
            server_url = start_local_http_server(out_dir)
            if server_url:
                target = server_url
            try:
                os.startfile(target)
            except Exception as exc:
                print(f"Could not open report: {exc}", file=sys.stderr)
        else:
            print("open is only supported on Windows", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
