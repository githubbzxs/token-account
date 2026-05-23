import { AnimatePresence, LayoutGroup, MotionConfig, motion } from "motion/react";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import React, { startTransition, useDeferredValue, useEffect, useRef, useState } from "react";
import type { DateRange, ReportData, ReportSlice } from "./types";
import {
  QUICK_RANGES,
  addDaysISO,
  availableBounds,
  deriveReportSlice,
  formatCompactNumber,
  formatFullNumber,
  formatMoneyUSD,
  formatPercent,
  formatRangeLabel,
  labelsBetween,
  normalizeISO,
  orderRange,
  presetForRange,
  rangeForPreset,
  type QuickRangeValue,
} from "./reportUtils";

const spring = {
  type: "spring",
  stiffness: 520,
  damping: 42,
  mass: 0.82,
} as const;

const softSpring = {
  type: "spring",
  stiffness: 360,
  damping: 34,
  mass: 0.9,
} as const;

const DIRECTORY_PAGE_SIZE = 6;

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

export function App() {
  const [data, setData] = useState<ReportData | null>(null);
  const [selectedRange, setSelectedRange] = useState<DateRange>({ start: "", end: "" });
  const [selectedPreset, setSelectedPreset] = useState<QuickRangeValue | "">("1");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [datePanelOpen, setDatePanelOpen] = useState(false);
  const deferredRange = useDeferredValue(selectedRange);

  useEffect(() => {
    const controller = new AbortController();
    loadReport(controller.signal, true);
    const intervalId = window.setInterval(() => {
      loadReport(undefined, false);
    }, 30_000);
    return () => {
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    if (!data) return;
    const bounds = availableBounds(data);
    setSelectedRange((previous) => {
      if (selectedPreset) {
        return rangeForPreset(selectedPreset, bounds.start, bounds.end);
      }
      if (!previous.start || !previous.end) {
        return rangeForPreset("1", bounds.start, bounds.end);
      }
      return orderRange({
        start: normalizeISO(previous.start) < bounds.start ? bounds.start : normalizeISO(previous.start),
        end: normalizeISO(previous.end) > bounds.end ? bounds.end : normalizeISO(previous.end),
      });
    });
  }, [data?.meta?.data_stamp, selectedPreset]);

  async function loadReport(signal?: AbortSignal, showLoading = false) {
    if (showLoading) setLoading(true);
    try {
      const response = await fetch("/api/report", {
        cache: "no-store",
        signal,
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const nextData = (await response.json()) as ReportData;
      setData(nextData);
      setError("");
    } catch (nextError) {
      if (nextError instanceof DOMException && nextError.name === "AbortError") return;
      setError(nextError instanceof Error ? nextError.message : "Failed to load report");
    } finally {
      if (showLoading) setLoading(false);
    }
  }

  const bounds = availableBounds(data);
  const slice = data ? deriveReportSlice(data, deferredRange.start && deferredRange.end ? deferredRange : rangeForPreset("1", bounds.start, bounds.end)) : null;

  function updateQuickRange(value: QuickRangeValue) {
    if (!data) return;
    const nextRange = rangeForPreset(value, bounds.start, bounds.end);
    startTransition(() => {
      setSelectedPreset(value);
      setSelectedRange(nextRange);
      setDatePanelOpen(false);
    });
  }

  function updateManualRange(range: DateRange) {
    if (!data) return;
    const nextRange = orderRange({
      start: normalizeISO(range.start),
      end: normalizeISO(range.end),
    });
    startTransition(() => {
      setSelectedRange(nextRange);
      setSelectedPreset(presetForRange(nextRange, bounds.start, bounds.end));
    });
  }

  return (
    <MotionConfig reducedMotion="user" transition={spring}>
      <main className="appShell">
        <div className="ambientLayer" aria-hidden="true" />
        <motion.section
          className="hero"
          initial={{ opacity: 0, y: 18, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={softSpring}
        >
          <div>
            <p className="eyebrow">Token Account</p>
            <h1>Codex usage, tuned like a native control.</h1>
          </div>
          <div className="heroMeta">
            <span>Last sync</span>
            <strong>{data?.meta?.generated_at || "--"}</strong>
          </div>
        </motion.section>

        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div
              key="loading"
              className="statePanel"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
            >
              <div className="skeletonLine wide" />
              <div className="skeletonLine" />
            </motion.div>
          ) : error ? (
            <motion.div
              key="error"
              className="statePanel"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
            >
              <strong>Report unavailable</strong>
              <span>{error}</span>
              <button type="button" className="ghostButton" onClick={() => loadReport(undefined, true)}>
                Retry
              </button>
            </motion.div>
          ) : data && slice ? (
            <motion.div
              key="dashboard"
              className="dashboardStack"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.24 }}
            >
              <RangeControls
                range={selectedRange.start && selectedRange.end ? selectedRange : slice.range}
                bounds={bounds}
                preset={selectedPreset}
                open={datePanelOpen}
                onOpenChange={setDatePanelOpen}
                onPresetChange={updateQuickRange}
                onRangeChange={updateManualRange}
              />
              {slice.empty ? <EmptyBanner /> : null}
              <MetricSummary slice={slice} />
              <div className="contentGrid">
                <DailyAreaChart slice={slice} />
                <HourlyPanel values={slice.hourly} />
              </div>
              <HeatmapPanel data={data} bounds={bounds} />
              <DirectoryPanel slice={slice} />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </main>
    </MotionConfig>
  );
}

function RangeControls(props: {
  range: DateRange;
  bounds: DateRange;
  preset: QuickRangeValue | "";
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPresetChange: (value: QuickRangeValue) => void;
  onRangeChange: (range: DateRange) => void;
}) {
  const [draftRange, setDraftRange] = useState<DateRange>(props.range);

  useEffect(() => {
    if (props.open) {
      setDraftRange(props.range);
    }
  }, [props.open, props.range.start, props.range.end]);

  function applyDraftRange() {
    props.onRangeChange(draftRange);
    props.onOpenChange(false);
  }

  return (
    <section className="rangeBar">
      <div className="dateControlWrap">
        <motion.button
          type="button"
          className="dateTrigger"
          onClick={() => props.onOpenChange(!props.open)}
          whileTap={{ scale: 0.975 }}
          aria-expanded={props.open}
        >
          <span>{formatRangeLabel(props.range)}</span>
        </motion.button>
        <AnimatePresence>
          {props.open ? (
            <motion.div
              className="dateSheet"
              initial={{ opacity: 0, y: -8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.98 }}
              transition={softSpring}
            >
              <label>
                <span>Start</span>
                <input
                  type="date"
                  min={props.bounds.start}
                  max={props.bounds.end}
                  value={draftRange.start}
                  onChange={(event) => setDraftRange((current) => ({ ...current, start: event.target.value }))}
                />
              </label>
              <label>
                <span>End</span>
                <input
                  type="date"
                  min={props.bounds.start}
                  max={props.bounds.end}
                  value={draftRange.end}
                  onChange={(event) => setDraftRange((current) => ({ ...current, end: event.target.value }))}
                />
              </label>
              <div className="dateSheetActions">
                <button type="button" onClick={() => setDraftRange(props.bounds)}>
                  All
                </button>
                <button type="button" className="primaryButton" onClick={applyDraftRange}>
                  Apply
                </button>
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
      <LayoutGroup id="quick-range">
        <div className="segmentedControl">
          {QUICK_RANGES.map((item) => {
            const active = props.preset === item.value;
            return (
              <motion.button
                key={item.value}
                type="button"
                className="segmentedButton"
                onClick={() => props.onPresetChange(item.value)}
                whileTap={{ scale: 0.965 }}
              >
                {active ? <motion.span layoutId="quick-range-pill" className="segmentedPill" transition={spring} /> : null}
                <motion.span
                  className="segmentedLabel"
                  animate={{
                    color: active ? "#fffaf0" : "#b8b5ae",
                    opacity: active ? 1 : 0.72,
                    scale: active ? 1.028 : 1,
                    y: active ? -0.5 : 0,
                  }}
                  transition={{ type: "spring", stiffness: 620, damping: 36, mass: 0.55 }}
                >
                  {item.label}
                </motion.span>
              </motion.button>
            );
          })}
        </div>
      </LayoutGroup>
    </section>
  );
}

function EmptyBanner() {
  return (
    <motion.div className="emptyBanner" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
      No token usage found in this range.
    </motion.div>
  );
}

function MetricSummary({ slice }: { slice: ReportSlice }) {
  const metrics = [
    { label: "Input", value: formatCompactNumber(slice.totals.inputTokens) },
    { label: "Output", value: formatCompactNumber(slice.totals.outputTokens) },
    { label: "Cached", value: formatCompactNumber(slice.totals.cachedTokens) },
    { label: "Sessions", value: formatFullNumber(slice.totals.sessions) },
  ];

  return (
    <motion.section className="summaryPanel" layout>
      <div className="summaryMain">
        <p>Total tokens</p>
        <AnimatedMetric value={formatCompactNumber(slice.totals.totalTokens)} className="heroMetric" />
        <span>{formatFullNumber(Math.round(slice.totals.averagePerDay))} per active day</span>
      </div>
      <div className="summaryCost">
        <p>Estimated cost</p>
        <AnimatedMetric value={formatMoneyUSD(slice.totals.totalCost)} className="costMetric" />
        <span>{formatPercent(slice.totals.cacheRate)} cache rate</span>
      </div>
      <div className="metricRail">
        {metrics.map((metric) => (
          <motion.div className="miniMetric" key={metric.label} layout>
            <span>{metric.label}</span>
            <AnimatedMetric value={metric.value} className="miniMetricValue" />
          </motion.div>
        ))}
      </div>
    </motion.section>
  );
}

function AnimatedMetric({ value, className }: { value: string; className?: string }) {
  const previousRef = useRef(value);
  const [previousValue, setPreviousValue] = useState(value);
  const [animationKey, setAnimationKey] = useState(0);

  useEffect(() => {
    if (previousRef.current === value) return;
    setPreviousValue(previousRef.current);
    previousRef.current = value;
    setAnimationKey((key) => key + 1);
  }, [value]);

  const direction = compareNumericText(previousValue, value);
  const previousDigits = previousValue.match(/\d/g) || [];
  const nextDigits = value.match(/\d/g) || [];
  let nextDigitIndex = 0;

  return (
    <span className={`animatedMetric ${className || ""}`} aria-label={value}>
      {Array.from(value).map((char, index) => {
        if (!/\d/.test(char)) {
          return (
            <motion.span
              key={`${animationKey}-${index}-${char}`}
              className="metricStatic"
              initial={{ opacity: 0.45, y: direction >= 0 ? 4 : -4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: "spring", stiffness: 420, damping: 30, mass: 0.7 }}
            >
              {char === " " ? "\u00a0" : char}
            </motion.span>
          );
        }
        const reverseIndex = nextDigits.length - nextDigitIndex - 1;
        const previousDigit = Number(previousDigits[previousDigits.length - reverseIndex - 1] || 0);
        const nextDigit = Number(char);
        nextDigitIndex += 1;
        return (
          <DigitReel
            key={`${animationKey}-${index}-${char}`}
            previousDigit={previousDigit}
            nextDigit={nextDigit}
            direction={direction}
            delay={Math.max(0, value.length - index - 1) * 0.012}
          />
        );
      })}
    </span>
  );
}

function DigitReel(props: { previousDigit: number; nextDigit: number; direction: number; delay: number }) {
  const fromIndex = 10 + props.previousDigit;
  const delta =
    props.direction >= 0
      ? (props.nextDigit - props.previousDigit + 10) % 10
      : -((props.previousDigit - props.nextDigit + 10) % 10);
  const toIndex = fromIndex + delta;
  const cells = Array.from({ length: 30 }, (_, index) => index % 10);

  return (
    <span className="digitWindow">
      <motion.span
        className="digitTrack"
        initial={{ y: `${-fromIndex}em` }}
        animate={{ y: `${-toIndex}em` }}
        transition={{
          type: "spring",
          stiffness: 430,
          damping: 34,
          mass: 0.74,
          delay: props.delay,
        }}
      >
        {cells.map((digit, index) => (
          <span key={index} className="digitCell">
            {digit}
          </span>
        ))}
      </motion.span>
    </span>
  );
}

function DailyAreaChart({ slice }: { slice: ReportSlice }) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
    }
    const chart = chartInstanceRef.current;
    chart.setOption({
      animationDuration: 520,
      animationEasing: "cubicOut",
      grid: { left: 12, right: 10, top: 22, bottom: 18, containLabel: true },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(18, 15, 12, 0.94)",
        borderColor: "rgba(215, 185, 138, 0.34)",
        textStyle: { color: "#f8fafc" },
        valueFormatter: (value: number) => formatCompactNumber(value),
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: slice.daily.labels,
        axisLine: { lineStyle: { color: "rgba(148, 163, 184, 0.22)" } },
        axisTick: { show: false },
        axisLabel: {
          color: "#8f8b84",
          hideOverlap: true,
          formatter: (value: string) => value.slice(5),
        },
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.10)" } },
        axisLabel: {
          color: "#8f8b84",
          formatter: (value: number) => formatCompactNumber(value),
        },
      },
      series: [
        {
          name: "Total",
          type: "line",
          smooth: 0.46,
          showSymbol: false,
          data: slice.daily.total,
          lineStyle: { width: 1.6, color: "#d7b98a" },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(215, 185, 138, 0.42)" },
              { offset: 0.44, color: "rgba(184, 156, 122, 0.16)" },
              { offset: 1, color: "rgba(184, 156, 122, 0)" },
            ]),
          },
        },
      ],
    });
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    resize();
    return () => {
      window.removeEventListener("resize", resize);
    };
  }, [slice]);

  useEffect(() => {
    return () => {
      chartInstanceRef.current?.dispose();
      chartInstanceRef.current = null;
    };
  }, []);

  return (
    <motion.section className="panel chartPanel" layout>
      <PanelHeading title="Daily usage" value={formatRangeLabel(slice.range)} />
      <div className="chartCanvas" ref={chartRef} />
    </motion.section>
  );
}

function HourlyPanel({ values }: { values: number[] }) {
  const maxValue = Math.max(1, ...values);
  const peakHour = values.reduce((bestIndex, value, index) => (value > values[bestIndex] ? index : bestIndex), 0);

  return (
    <motion.section className="panel hourlyPanel" layout>
      <PanelHeading title="Hourly shape" value={`${String(peakHour).padStart(2, "0")}:00 peak`} />
      <div className="hourlyBars">
        {values.map((value, index) => (
          <motion.div
            key={index}
            className="hourBar"
            initial={{ scaleY: 0.12, opacity: 0.45 }}
            animate={{ scaleY: Math.max(0.08, value / maxValue), opacity: value > 0 ? 1 : 0.32 }}
            transition={{ type: "spring", stiffness: 300, damping: 32, mass: 0.82, delay: index * 0.008 }}
          />
        ))}
      </div>
      <div className="hourlyScale">
        <span>00</span>
        <span>12</span>
        <span>23</span>
      </div>
    </motion.section>
  );
}

function HeatmapPanel({ data, bounds }: { data: ReportData; bounds: DateRange }) {
  const end = bounds.end;
  const start = addDaysISO(end, -370);
  const labels = labelsBetween(start, end);
  const dailyMap = new Map<string, number>();
  data.daily.labels.forEach((label, index) => {
    dailyMap.set(label, data.daily.total[index] || 0);
  });
  const values = labels.map((label) => dailyMap.get(label) || 0);
  const maxValue = Math.max(1, ...values);

  return (
    <motion.section className="panel heatmapPanel" layout>
      <PanelHeading title="Contribution map" value="Last 53 weeks" />
      <div className="heatmapGrid" style={{ "--heatmap-columns": Math.ceil(labels.length / 7) } as React.CSSProperties}>
        {labels.map((label, index) => {
          const value = values[index];
          const level = value <= 0 ? 0 : Math.min(4, Math.ceil((value / maxValue) * 4));
          return <span key={label} className={`heatCell heatLevel${level}`} title={`${label}: ${formatCompactNumber(value)}`} />;
        })}
      </div>
      <div className="heatmapLegend">
        <span>Less</span>
        {[0, 1, 2, 3, 4].map((level) => (
          <span key={level} className={`heatCell heatLevel${level}`} />
        ))}
        <span>More</span>
      </div>
    </motion.section>
  );
}

function DirectoryPanel({ slice }: { slice: ReportSlice }) {
  const [page, setPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(slice.directories.length / DIRECTORY_PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const rows = slice.directories.slice((safePage - 1) * DIRECTORY_PAGE_SIZE, safePage * DIRECTORY_PAGE_SIZE);

  useEffect(() => {
    setPage(1);
  }, [slice.range.start, slice.range.end]);

  return (
    <motion.section className="panel directoryPanel" layout>
      <PanelHeading title="Directory breakdown" value={`${slice.directories.length} paths`} />
      <div className="directoryList">
        {rows.length ? (
          rows.map((row, index) => (
            <motion.div
              key={row.path}
              className="directoryRow"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: "spring", stiffness: 330, damping: 30, mass: 0.8, delay: index * 0.035 }}
            >
              <span className="directoryRank">#{(safePage - 1) * DIRECTORY_PAGE_SIZE + index + 1}</span>
              <div className="directoryMeta">
                <strong>{row.name}</strong>
                <span title={row.path}>{row.path}</span>
              </div>
              <div className="directoryNumbers">
                <AnimatedMetric value={formatCompactNumber(row.totalTokens)} className="directoryValue" />
                <span>{formatMoneyUSD(row.totalCost)}</span>
              </div>
            </motion.div>
          ))
        ) : (
          <div className="directoryEmpty">No data</div>
        )}
      </div>
      <div className="pagination">
        <button type="button" disabled={safePage <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
          Prev
        </button>
        <span>
          Page {safePage} / {totalPages}
        </span>
        <button type="button" disabled={safePage >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>
          Next
        </button>
      </div>
    </motion.section>
  );
}

function PanelHeading({ title, value }: { title: string; value: string }) {
  return (
    <div className="panelHeading">
      <h2>{title}</h2>
      <span>{value}</span>
    </div>
  );
}

function compareNumericText(previousText: string, nextText: string): number {
  const previousDigits = previousText.replace(/\D/g, "").replace(/^0+/, "") || "0";
  const nextDigits = nextText.replace(/\D/g, "").replace(/^0+/, "") || "0";
  if (previousDigits.length !== nextDigits.length) {
    return nextDigits.length > previousDigits.length ? 1 : -1;
  }
  return nextDigits >= previousDigits ? 1 : -1;
}
