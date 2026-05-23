import type { DateRange, DirectoryRow, ReportData, ReportSlice } from "./types";

export const DAY_MS = 86_400_000;

export const QUICK_RANGES = [
  { value: "1", label: "1D", days: 1 },
  { value: "2", label: "2D", days: 2 },
  { value: "7", label: "1W", days: 7 },
  { value: "30", label: "1M", days: 30 },
  { value: "90", label: "3M", days: 90 },
  { value: "all", label: "ALL", days: null },
] as const;

export type QuickRangeValue = (typeof QUICK_RANGES)[number]["value"];

export function normalizeISO(value: string | undefined | null): string {
  const raw = String(value || "").trim().replace(/\//g, "-");
  return /^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : "";
}

export function parseISODate(value: string): Date {
  const iso = normalizeISO(value);
  if (!iso) return new Date(Number.NaN);
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

export function formatISODate(date: Date): string {
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function addDaysISO(value: string, days: number): string {
  const date = parseISODate(value);
  if (!Number.isFinite(date.getTime())) return "";
  return formatISODate(new Date(date.getTime() + days * DAY_MS));
}

export function daysBetween(start: string, end: string): number {
  const startDate = parseISODate(start);
  const endDate = parseISODate(end);
  if (!Number.isFinite(startDate.getTime()) || !Number.isFinite(endDate.getTime())) return 0;
  return Math.max(0, Math.round((endDate.getTime() - startDate.getTime()) / DAY_MS) + 1);
}

export function clampISO(value: string, minISO: string, maxISO: string): string {
  const iso = normalizeISO(value);
  if (!iso) return minISO || maxISO;
  if (minISO && iso < minISO) return minISO;
  if (maxISO && iso > maxISO) return maxISO;
  return iso;
}

export function orderRange(range: DateRange): DateRange {
  const start = normalizeISO(range.start);
  const end = normalizeISO(range.end);
  if (!start || !end) return { start, end };
  return start <= end ? { start, end } : { start: end, end: start };
}

export function availableBounds(data: ReportData | null): DateRange {
  const available = data?.available_range || data?.range;
  const start = normalizeISO(available?.start);
  const end = normalizeISO(available?.end);
  if (start && end) return start <= end ? { start, end } : { start: end, end: start };
  const today = formatISODate(new Date());
  return { start: today, end: today };
}

export function rangeForPreset(preset: QuickRangeValue, minISO: string, maxISO: string): DateRange {
  if (!minISO || !maxISO || preset === "all") {
    return { start: minISO, end: maxISO };
  }
  const item = QUICK_RANGES.find((range) => range.value === preset);
  if (!item || !item.days) return { start: minISO, end: maxISO };
  const start = clampISO(addDaysISO(maxISO, -(item.days - 1)), minISO, maxISO);
  return { start, end: maxISO };
}

export function presetForRange(range: DateRange, minISO: string, maxISO: string): QuickRangeValue | "" {
  if (!range.start || !range.end || !minISO || !maxISO) return "";
  if (range.start === minISO && range.end === maxISO) return "all";
  if (range.end !== maxISO) return "";
  for (const item of QUICK_RANGES) {
    if (!item.days) continue;
    const expectedStart = clampISO(addDaysISO(maxISO, -(item.days - 1)), minISO, maxISO);
    if (range.start === expectedStart) return item.value;
  }
  return "";
}

export function labelsBetween(startISO: string, endISO: string): string[] {
  const start = normalizeISO(startISO);
  const end = normalizeISO(endISO);
  if (!start || !end || start > end) return [];
  const totalDays = daysBetween(start, end);
  return Array.from({ length: totalDays }, (_, index) => addDaysISO(start, index));
}

export function formatCompactNumber(value: number): string {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0";
  const abs = Math.abs(num);
  if (abs >= 1_000_000_000) return `${trimFixed(num / 1_000_000_000)}B`;
  if (abs >= 1_000_000) return `${trimFixed(num / 1_000_000)}M`;
  if (abs >= 1_000) return `${trimFixed(num / 1_000)}K`;
  return new Intl.NumberFormat("en-US").format(Math.round(num));
}

export function formatFullNumber(value: number): string {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0";
  return new Intl.NumberFormat("en-US").format(Math.round(num));
}

export function formatMoneyUSD(value: number): string {
  const num = Number(value);
  if (!Number.isFinite(num)) return "$0.0000";
  if (Math.abs(num) >= 1) return `$${num.toFixed(2)}`;
  return `$${num.toFixed(4)}`;
}

export function formatPercent(value: number): string {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0%";
  return `${(num * 100).toFixed(1).replace(/\.0$/, "")}%`;
}

export function formatDisplayDate(value: string): string {
  const iso = normalizeISO(value);
  return iso ? iso.replace(/-/g, "/") : "--/--/--";
}

export function formatRangeLabel(range: DateRange): string {
  const start = normalizeISO(range.start);
  const end = normalizeISO(range.end);
  if (!start || !end) return "--/--/-- - --/--";
  const startText = formatDisplayDate(start);
  const endText = start.slice(0, 4) === end.slice(0, 4) ? end.slice(5).replace(/-/g, "/") : formatDisplayDate(end);
  return `${startText} - ${endText}`;
}

export function directoryName(path: string): string {
  const normalized = String(path || "").trim().replace(/\\/g, "/").replace(/\/+$/, "");
  if (!normalized) return "Unknown";
  const segments = normalized.split("/").filter(Boolean);
  return segments[segments.length - 1] || normalized;
}

export function deriveReportSlice(data: ReportData, selectedRange: DateRange): ReportSlice {
  const bounds = availableBounds(data);
  const safeRange = orderRange({
    start: clampISO(selectedRange.start, bounds.start, bounds.end),
    end: clampISO(selectedRange.end, bounds.start, bounds.end),
  });
  const completeLabels = labelsBetween(safeRange.start, safeRange.end);
  const dailyIndex = new Map<string, number>();
  data.daily.labels.forEach((label, index) => {
    dailyIndex.set(label, index);
  });

  const daily = {
    labels: completeLabels,
    total: completeLabels.map((label) => data.daily.total[dailyIndex.get(label) ?? -1] || 0),
    input: completeLabels.map((label) => data.daily.input[dailyIndex.get(label) ?? -1] || 0),
    output: completeLabels.map((label) => data.daily.output[dailyIndex.get(label) ?? -1] || 0),
    reasoning: completeLabels.map((label) => data.daily.reasoning[dailyIndex.get(label) ?? -1] || 0),
    cached: completeLabels.map((label) => data.daily.cached[dailyIndex.get(label) ?? -1] || 0),
  };

  const totalTokens = sum(daily.total);
  const inputTokens = sum(daily.input);
  const outputTokens = sum(daily.output);
  const reasoningTokens = sum(daily.reasoning);
  const cachedTokens = sum(daily.cached);
  const activeDays = daily.total.filter((value) => value > 0).length;
  const totalCost = completeLabels.reduce((acc, label) => acc + Number(data.daily_costs?.[label] || 0), 0);
  const sessions = (data.session_spans || []).filter((span) => span.start <= safeRange.end && span.end >= safeRange.start).length;
  const hourly = new Array(24).fill(0);

  completeLabels.forEach((label) => {
    const values = data.hourly_daily?.[label] || [];
    for (let index = 0; index < 24; index += 1) {
      hourly[index] += Number(values[index] || 0);
    }
  });

  const directoryMap = new Map<string, DirectoryRow>();
  completeLabels.forEach((label) => {
    const directories = data.daily_directories?.[label] || {};
    Object.entries(directories).forEach(([path, record]) => {
      const existing = directoryMap.get(path) || {
        path,
        name: directoryName(path),
        totalTokens: 0,
        totalCost: 0,
      };
      existing.totalTokens += Number(record.total_tokens || 0);
      existing.totalCost += Number(record.total_cost || 0);
      directoryMap.set(path, existing);
    });
  });

  const directories = Array.from(directoryMap.values()).sort((left, right) => {
    if (right.totalTokens !== left.totalTokens) return right.totalTokens - left.totalTokens;
    if (right.totalCost !== left.totalCost) return right.totalCost - left.totalCost;
    return left.path.localeCompare(right.path);
  });

  return {
    range: safeRange,
    labels: completeLabels,
    totals: {
      totalTokens,
      inputTokens,
      outputTokens,
      reasoningTokens,
      cachedTokens,
      totalCost,
      sessions,
      activeDays,
      cacheRate: inputTokens ? cachedTokens / inputTokens : 0,
      averagePerDay: activeDays ? totalTokens / activeDays : 0,
    },
    daily,
    hourly,
    directories,
    empty: totalTokens <= 0,
  };
}

function sum(values: number[]): number {
  return values.reduce((acc, value) => acc + Number(value || 0), 0);
}

function trimFixed(value: number): string {
  return value.toFixed(1).replace(/\.0$/, "");
}
