import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import type { ReportData } from "./types";

declare global {
  interface Window {
    __TOKEN_ACCOUNT_INITIAL_DATA__?: ReportData;
  }
}

interface InitialSummary {
  rangeLabel: string;
  totalTokens: string;
  inputTokens: string;
  outputTokens: string;
  totalCost: string;
}

const emptySummary: InitialSummary = {
  rangeLabel: "2000/01/01 - 01/01",
  totalTokens: "--",
  inputTokens: "--",
  outputTokens: "--",
  totalCost: "--",
};

export function App() {
  const [data, setData] = useState<ReportData | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const runtimeLoadedRef = useRef(false);
  const summary = summarizeInitialData(data);

  useEffect(() => {
    let cancelled = false;

    async function loadInitialReport() {
      try {
        const response = await fetch(`/api/report?ts=${Date.now()}`, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const nextData = (await response.json()) as ReportData;
        if (cancelled) return;
        window.__TOKEN_ACCOUNT_INITIAL_DATA__ = nextData;
        setData(nextData);
      } catch (_) {
        if (!cancelled) {
          setLoadFailed(true);
        }
      }
    }

    loadInitialReport();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!data || runtimeLoadedRef.current) return;
    runtimeLoadedRef.current = true;
    const run = () => {
      const script = document.createElement("script");
      script.src = `/legacy-report-runtime.js?ts=${Date.now()}`;
      script.async = false;
      document.body.appendChild(script);
    };
    if ("requestIdleCallback" in window) {
      window.requestIdleCallback(run, { timeout: 300 });
      return;
    }
    const script = document.createElement("script");
    script.src = `/legacy-report-runtime.js?ts=${Date.now()}`;
    script.async = false;
    document.body.appendChild(script);
  }, [data]);

  return (
    <LegacyDashboardShell summary={summary} loadFailed={loadFailed} />
  );
}

function LegacyDashboardShell(props: { summary: InitialSummary; loadFailed: boolean }) {
  return (
    <div className="page">
      <div className="hero">
        <div className="title">
          <h1 data-i18n="title">Codex Token Usage</h1>
        </div>
      </div>
      <div className="range-controls">
        <div className="range-fields">
          <button type="button" id="range-date-trigger" className="range-date-trigger" aria-haspopup="dialog" aria-expanded="false">
            <span id="range-date-label">{props.summary.rangeLabel}</span>
          </button>
          <input type="hidden" id="range-start" />
          <input type="hidden" id="range-end" />
        </div>
        <div className="range-buttons range-segmented" id="quick-range-segmented">
          <span className="range-segmented-slider" id="quick-range-slider" aria-hidden="true" />
          <button type="button" data-range="1" data-i18n="last_1">
            1D
          </button>
          <button type="button" data-range="2" data-i18n="last_2">
            2D
          </button>
          <button type="button" data-range="7" data-i18n="last_7">
            1W
          </button>
          <button type="button" data-range="30" data-i18n="last_30">
            1M
          </button>
          <button type="button" data-range="all" data-i18n="all_time">
            ALL
          </button>
        </div>
      </div>
      <div id="calendar-popover" className="calendar-popover hidden" aria-hidden="true">
        <div className="calendar-head">
          <button type="button" id="calendar-prev" className="calendar-nav-btn" aria-label="Previous month">
            &lsaquo;
          </button>
          <div className="calendar-title" id="calendar-title">
            January 2000
          </div>
          <button type="button" id="calendar-next" className="calendar-nav-btn" aria-label="Next month">
            &rsaquo;
          </button>
        </div>
        <div className="calendar-weekdays" id="calendar-weekdays" />
        <div className="calendar-days" id="calendar-days" />
        <div className="calendar-actions">
          <button type="button" id="calendar-clear" data-i18n="calendar_clear">
            Clear
          </button>
          <button type="button" id="calendar-today" data-i18n="calendar_today">
            Today
          </button>
        </div>
      </div>
      <div className={`banner ${props.loadFailed ? "" : "hidden"}`} id="range-banner" data-i18n="empty_banner">
        No token usage found in this range.
      </div>
      <div className="cards">
        <div className="card metric-card summary-card" style={delayStyle("0.05s")}>
          <div className="summary-card-main">
            <div className="label" data-i18n="card_total">
              Total tokens
            </div>
            <div className="value" id="value-total">
              {props.summary.totalTokens}
            </div>
            <div className="summary-card-inline">
              <div className="summary-card-inline-item">
                <div className="summary-card-inline-label" data-i18n="input">
                  Input
                </div>
                <div className="summary-card-inline-value" id="value-input">
                  {props.summary.inputTokens}
                </div>
              </div>
              <div className="summary-card-inline-item">
                <div className="summary-card-inline-label" data-i18n="output">
                  Output
                </div>
                <div className="summary-card-inline-value" id="value-output">
                  {props.summary.outputTokens}
                </div>
              </div>
            </div>
          </div>
          <div className="summary-card-divider" aria-hidden="true" />
          <div className="summary-card-side">
            <div className="label" data-i18n="card_cost">
              Estimated cost
            </div>
            <div className="value cost-value" id="value-cost">
              {props.summary.totalCost}
            </div>
          </div>
        </div>
      </div>
      <div className="panel-grid">
        <div className="panel wide chart-panel" style={delayStyle("0.25s")}>
          <div id="chart-daily" className="chart" />
        </div>
        <div className="panel wide chart-panel" style={delayStyle("0.32s")}>
          <div id="chart-heatmap" className="chart heatmap-chart">
            <div id="chart-heatmap-inner" className="heatmap-canvas" />
          </div>
        </div>
      </div>
      <div className="panel directory-panel" style={delayStyle("0.4s")}>
        <div id="directory-list" className="directory-list" />
        <div className="directory-pagination">
          <button type="button" id="directory-prev" className="directory-page-btn" data-i18n="directory_prev">
            Prev
          </button>
          <div id="directory-page" className="directory-page-text">
            Page 1 / 1
          </div>
          <button type="button" id="directory-next" className="directory-page-btn" data-i18n="directory_next">
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

function delayStyle(value: string): CSSProperties {
  return { "--delay": value } as CSSProperties;
}

function summarizeInitialData(data: ReportData | null): InitialSummary {
  if (!data?.daily?.labels?.length) {
    return emptySummary;
  }
  const totalTokens = sumValues(data.daily.total);
  const inputTokens = sumValues(data.daily.input);
  const outputTokens = sumValues(data.daily.output);
  const totalCost = Object.values(data.daily_costs || {}).reduce((sum, value) => sum + Number(value || 0), 0);
  const start = data.range?.start || data.daily.labels[0] || "";
  const end = data.range?.end || data.daily.labels[data.daily.labels.length - 1] || "";

  return {
    rangeLabel: formatRangeLabel(start, end),
    totalTokens: formatCompactNumber(totalTokens),
    inputTokens: formatCompactNumber(inputTokens),
    outputTokens: formatCompactNumber(outputTokens),
    totalCost: totalCost > 0 ? formatMoneyUSD(totalCost) : "n/a",
  };
}

function sumValues(values: number[] | undefined): number {
  return (values || []).reduce((sum, value) => sum + Number(value || 0), 0);
}

function formatCompactNumber(value: number): string {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0";
  const absNum = Math.abs(num);
  if (absNum >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
  }
  if (absNum >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  }
  if (absNum >= 1_000) {
    return `${(num / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
  }
  return new Intl.NumberFormat("en-US").format(num);
}

function formatMoneyUSD(value: number): string {
  if (!Number.isFinite(value)) return "n/a";
  if (value >= 1) return `$${value.toFixed(2)}`;
  return `$${value.toFixed(4)}`;
}

function formatRangeLabel(startISO: string, endISO: string): string {
  const start = normalizeISO(startISO);
  const end = normalizeISO(endISO);
  if (!start || !end) return "--/--/-- - --/--";
  const startText = start.replace(/-/g, "/");
  const endText = start.slice(0, 4) === end.slice(0, 4) ? end.slice(5).replace(/-/g, "/") : end.replace(/-/g, "/");
  return `${startText} - ${endText}`;
}

function normalizeISO(value: string): string {
  const raw = String(value || "").trim().replace(/\//g, "-");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) return "";
  return raw;
}
