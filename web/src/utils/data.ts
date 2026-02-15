import {
  ChartPoint,
  ComputedStats,
  ModelTokenBreakdown,
  PricingBook,
  ReportData,
  SessionSpan,
} from "../types/report";

function sumRange(values: number[], start: number, end: number): number {
  let total = 0;
  for (let i = start; i <= end; i += 1) {
    total += values[i] || 0;
  }
  return total;
}

function countActive(values: number[], start: number, end: number): number {
  let count = 0;
  for (let i = start; i <= end; i += 1) {
    if ((values[i] || 0) > 0) {
      count += 1;
    }
  }
  return count;
}

function resolveIndex(labels: string[], iso: string, startSide: boolean): number {
  const exact = labels.indexOf(iso);
  if (exact >= 0) {
    return exact;
  }
  if (startSide) {
    const idx = labels.findIndex((label) => label >= iso);
    return idx >= 0 ? idx : 0;
  }
  for (let i = labels.length - 1; i >= 0; i -= 1) {
    if (labels[i] <= iso) {
      return i;
    }
  }
  return labels.length - 1;
}

function overlapSessions(spans: SessionSpan[], startISO: string, endISO: string): number {
  let count = 0;
  for (const span of spans) {
    if (span.start <= endISO && span.end >= startISO) {
      count += 1;
    }
  }
  return count;
}

function normalizeModelName(model: string): string {
  const raw = String(model || "").trim();
  if (!raw) {
    return "unknown";
  }
  const [head, ...tail] = raw.split(":");
  const cleanHead = head.replace(/\s*[\(（][^\)）]*[\)）]\s*/g, " ").replace(/\s+/g, " ").trim();
  const base = cleanHead || "unknown";
  const suffix = tail.join(":").trim();
  return suffix ? `${base}:${suffix}` : base;
}

function resolvePricing(model: string, pricing: PricingBook): { input: number; cached_input: number | null; output: number } | null {
  const prices = pricing?.prices || {};
  const aliases = pricing?.aliases || {};

  const deAlias = (value: string): string => {
    const seen = new Set<string>();
    let cursor = value;
    while (aliases[cursor] && !seen.has(cursor)) {
      seen.add(cursor);
      cursor = aliases[cursor];
    }
    return cursor;
  };

  const normalized = deAlias(normalizeModelName(model));
  if (prices[normalized]) {
    return prices[normalized];
  }

  const base = deAlias(normalized.split(":")[0]);
  if (prices[base]) {
    return prices[base];
  }

  for (const key of Object.keys(prices)) {
    if (base.startsWith(`${key}-`)) {
      return prices[key];
    }
  }

  if (base.includes("gpt-5.3")) return prices["gpt-5.2"] || prices["gpt-5"] || null;
  if (base.includes("gpt-5.2")) return prices["gpt-5.2"] || null;
  if (base.includes("gpt-5.1")) return prices["gpt-5.1"] || null;
  if (base.startsWith("gpt-5")) return prices["gpt-5"] || null;
  return null;
}

function costUSD(rec: ModelTokenBreakdown, pricingEntry: { input: number; cached_input: number | null; output: number } | null): number | null {
  if (!pricingEntry) {
    return null;
  }
  const cachedPrice = pricingEntry.cached_input ?? pricingEntry.input;
  const inputTokens = rec.input_tokens || 0;
  const cachedInputTokens = rec.cached_input_tokens || 0;
  const billableInput = Math.max(0, inputTokens - cachedInputTokens);
  const outputTotal = (rec.output_tokens || 0) + (rec.reasoning_output_tokens || 0);

  return (billableInput / 1_000_000) * pricingEntry.input +
    (cachedInputTokens / 1_000_000) * cachedPrice +
    (outputTotal / 1_000_000) * pricingEntry.output;
}

function aggregateModels(data: ReportData, labels: string[]): Record<string, ModelTokenBreakdown> {
  const out: Record<string, ModelTokenBreakdown> = {};
  for (const day of labels) {
    const dayMap = data.daily_models[day] || {};
    for (const [model, rec] of Object.entries(dayMap)) {
      const key = normalizeModelName(model);
      if (!out[key]) {
        out[key] = {
          input_tokens: 0,
          cached_input_tokens: 0,
          output_tokens: 0,
          reasoning_output_tokens: 0,
          total_tokens: 0,
        };
      }
      out[key].input_tokens += rec.input_tokens || 0;
      out[key].cached_input_tokens += rec.cached_input_tokens || 0;
      out[key].output_tokens += rec.output_tokens || 0;
      out[key].reasoning_output_tokens += rec.reasoning_output_tokens || 0;
      out[key].total_tokens += rec.total_tokens || 0;
    }
  }
  return out;
}

export interface RangedView {
  startISO: string;
  endISO: string;
  labels: string[];
  startIndex: number;
  endIndex: number;
}

export function calcRangedView(data: ReportData, startISO: string, endISO: string): RangedView {
  const labels = data.daily.labels || [];
  if (!labels.length) {
    return {
      startISO,
      endISO,
      labels: [],
      startIndex: 0,
      endIndex: -1,
    };
  }

  let start = startISO;
  let end = endISO;
  if (start > end) {
    [start, end] = [end, start];
  }

  const startIndex = resolveIndex(labels, start, true);
  const endIndex = resolveIndex(labels, end, false);
  const safeStart = Math.max(0, Math.min(startIndex, labels.length - 1));
  const safeEnd = Math.max(0, Math.min(endIndex, labels.length - 1));
  const finalStart = Math.min(safeStart, safeEnd);
  const finalEnd = Math.max(safeStart, safeEnd);

  return {
    startISO: labels[finalStart],
    endISO: labels[finalEnd],
    labels: labels.slice(finalStart, finalEnd + 1),
    startIndex: finalStart,
    endIndex: finalEnd,
  };
}

export function computeStats(data: ReportData, view: RangedView): ComputedStats {
  if (view.endIndex < view.startIndex) {
    return {
      totalTokens: 0,
      inputTokens: 0,
      outputTokens: 0,
      cachedTokens: 0,
      reasoningTokens: 0,
      cacheRate: 0,
      sessions: 0,
      activeDays: 0,
      avgPerDay: 0,
      avgPerSession: 0,
      estimatedCost: null,
    };
  }

  const totalTokens = sumRange(data.daily.total, view.startIndex, view.endIndex);
  const inputTokens = sumRange(data.daily.input, view.startIndex, view.endIndex);
  const outputTokens = sumRange(data.daily.output, view.startIndex, view.endIndex);
  const cachedTokens = sumRange(data.daily.cached, view.startIndex, view.endIndex);
  const reasoningTokens = sumRange(data.daily.reasoning, view.startIndex, view.endIndex);

  const activeDays = countActive(data.daily.total, view.startIndex, view.endIndex);
  const sessions = overlapSessions(data.session_spans || [], view.startISO, view.endISO);
  const avgPerDay = activeDays > 0 ? Math.round(totalTokens / activeDays) : 0;
  const avgPerSession = sessions > 0 ? Math.round(totalTokens / sessions) : 0;
  const cacheRate = inputTokens > 0 ? cachedTokens / inputTokens : 0;

  const modelTotals = aggregateModels(data, view.labels);
  let estimatedCost = 0;
  let hasPriced = false;
  for (const [model, rec] of Object.entries(modelTotals)) {
    const pricing = resolvePricing(model, data.pricing);
    const cost = costUSD(rec, pricing);
    if (cost != null) {
      estimatedCost += cost;
      hasPriced = true;
    }
  }

  return {
    totalTokens,
    inputTokens,
    outputTokens,
    cachedTokens,
    reasoningTokens,
    cacheRate,
    sessions,
    activeDays,
    avgPerDay,
    avgPerSession,
    estimatedCost: hasPriced ? estimatedCost : null,
  };
}

function buildHourlyPoints(data: ReportData, labels: string[]): ChartPoint[] {
  const points: ChartPoint[] = [];
  for (const day of labels) {
    const hours = data.hourly_daily?.[day] || [];
    for (let hour = 0; hour < 24; hour += 1) {
      const value = Number(hours[hour] || 0);
      const hourLabel = `${String(hour).padStart(2, "0")}:00`;
      points.push({
        label: `${day} ${hourLabel}`,
        tokens: value,
      });
    }
  }
  return points;
}

function compressPoints(points: ChartPoint[], maxPoints: number): ChartPoint[] {
  if (points.length <= maxPoints) {
    return points;
  }
  const bucketSize = Math.ceil(points.length / maxPoints);
  const out: ChartPoint[] = [];
  for (let i = 0; i < points.length; i += bucketSize) {
    const slice = points.slice(i, i + bucketSize);
    const tokens = slice.reduce((acc, item) => acc + item.tokens, 0);
    const label = slice[slice.length - 1]?.label || points[i].label;
    out.push({ label, tokens });
  }
  return out;
}

export function buildChartSeries(data: ReportData, view: RangedView, maxPoints = 260): ChartPoint[] {
  const points = buildHourlyPoints(data, view.labels);
  return compressPoints(points, maxPoints);
}

export function normalizeImportedData(raw: unknown): ReportData | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const root = raw as Record<string, unknown>;
  const data = (root.data && typeof root.data === "object" ? root.data : root) as Record<string, unknown>;
  if (!data.daily || !data.range) {
    return null;
  }
  const daily = data.daily as Record<string, unknown>;
  if (!Array.isArray(daily.labels) || !Array.isArray(daily.total)) {
    return null;
  }
  return data as unknown as ReportData;
}

function mergeDayMap(dayMap: Record<string, { total: number; input: number; output: number; reasoning: number; cached: number }>, data: ReportData): void {
  const labels = data.daily.labels || [];
  for (let i = 0; i < labels.length; i += 1) {
    const day = labels[i];
    if (!dayMap[day]) {
      dayMap[day] = { total: 0, input: 0, output: 0, reasoning: 0, cached: 0 };
    }
    dayMap[day].total += data.daily.total[i] || 0;
    dayMap[day].input += data.daily.input[i] || 0;
    dayMap[day].output += data.daily.output[i] || 0;
    dayMap[day].reasoning += data.daily.reasoning[i] || 0;
    dayMap[day].cached += data.daily.cached[i] || 0;
  }
}

function mergeDailyModels(target: ReportData["daily_models"], data: ReportData): void {
  const source = data.daily_models || {};
  for (const [day, modelMap] of Object.entries(source)) {
    if (!target[day]) {
      target[day] = {};
    }
    for (const [model, rec] of Object.entries(modelMap)) {
      const key = normalizeModelName(model);
      if (!target[day][key]) {
        target[day][key] = {
          input_tokens: 0,
          cached_input_tokens: 0,
          output_tokens: 0,
          reasoning_output_tokens: 0,
          total_tokens: 0,
        };
      }
      target[day][key].input_tokens += rec.input_tokens || 0;
      target[day][key].cached_input_tokens += rec.cached_input_tokens || 0;
      target[day][key].output_tokens += rec.output_tokens || 0;
      target[day][key].reasoning_output_tokens += rec.reasoning_output_tokens || 0;
      target[day][key].total_tokens += rec.total_tokens || 0;
    }
  }
}

function mergeHourlyDaily(target: ReportData["hourly_daily"], data: ReportData): void {
  const source = data.hourly_daily || {};
  for (const [day, hours] of Object.entries(source)) {
    if (!target[day]) {
      target[day] = Array.from({ length: 24 }, () => 0);
    }
    for (let i = 0; i < 24; i += 1) {
      target[day][i] += Number(hours[i] || 0);
    }
  }
}

export function mergeReportData(datasets: ReportData[]): ReportData | null {
  const valid = datasets.filter((item) => item.daily?.labels?.length);
  if (!valid.length) {
    return null;
  }

  const dayMap: Record<string, { total: number; input: number; output: number; reasoning: number; cached: number }> = {};
  const dailyModels: ReportData["daily_models"] = {};
  const hourlyDaily: ReportData["hourly_daily"] = {};
  const sessionSpans: SessionSpan[] = [];
  const events = [] as ReportData["events"];

  for (const data of valid) {
    mergeDayMap(dayMap, data);
    mergeDailyModels(dailyModels, data);
    mergeHourlyDaily(hourlyDaily, data);
    sessionSpans.push(...(data.session_spans || []));
    events.push(...(data.events || []));
  }

  const labels = Object.keys(dayMap).sort();
  if (!labels.length) {
    return null;
  }

  const daily = {
    labels,
    total: [] as number[],
    input: [] as number[],
    output: [] as number[],
    reasoning: [] as number[],
    cached: [] as number[],
  };

  for (const day of labels) {
    const rec = dayMap[day];
    daily.total.push(rec.total);
    daily.input.push(rec.input);
    daily.output.push(rec.output);
    daily.reasoning.push(rec.reasoning);
    daily.cached.push(rec.cached);
  }

  const hourlyTotal = Array.from({ length: 24 }, () => 0);
  for (const hours of Object.values(hourlyDaily)) {
    for (let i = 0; i < 24; i += 1) {
      hourlyTotal[i] += Number(hours[i] || 0);
    }
  }

  const basePricing = valid.find((item) => item.pricing)?.pricing || { prices: {}, aliases: {} };
  const baseMeta = valid.find((item) => item.meta)?.meta;

  return {
    range: {
      start: labels[0],
      end: labels[labels.length - 1],
      days: labels.length,
    },
    daily,
    hourly: {
      labels: Array.from({ length: 24 }, (_, idx) => String(idx).padStart(2, "0")),
      total: hourlyTotal,
    },
    hourly_daily: hourlyDaily,
    daily_models: dailyModels,
    session_spans: sessionSpans,
    events,
    pricing: basePricing,
    meta: baseMeta,
  };
}
