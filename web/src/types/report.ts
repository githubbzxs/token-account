export type Locale = "zh" | "en";

export type ThemeMode = "neon" | "bronze";

export type TimeRange = "1D" | "2D" | "1W" | "1M" | "3M" | "ALL";

export interface RangeInfo {
  start: string;
  end: string;
  days: number;
}

export interface DailySeries {
  labels: string[];
  total: number[];
  input: number[];
  output: number[];
  reasoning: number[];
  cached: number[];
}

export interface HourlySeries {
  labels: string[];
  total: number[];
}

export interface ModelTokenBreakdown {
  input_tokens: number;
  cached_input_tokens: number;
  output_tokens: number;
  reasoning_output_tokens: number;
  total_tokens: number;
}

export interface SessionSpan {
  start: string;
  end: string;
}

export interface UsageEvent {
  ts: string;
  day: string;
  value: number;
  input: number;
  cached: number;
  output: number;
  reasoning: number;
  total: number;
}

export interface PricingEntry {
  input: number;
  cached_input: number | null;
  output: number;
}

export interface PricingBook {
  prices: Record<string, PricingEntry>;
  aliases: Record<string, string>;
}

export interface ReportMeta {
  generated_at: string;
  source_path: string;
}

export interface ReportData {
  range: RangeInfo;
  daily: DailySeries;
  hourly?: HourlySeries;
  hourly_daily: Record<string, number[]>;
  daily_models: Record<string, Record<string, ModelTokenBreakdown>>;
  session_spans: SessionSpan[];
  events: UsageEvent[];
  pricing: PricingBook;
  meta?: ReportMeta;
}

export interface ComputedStats {
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  cachedTokens: number;
  reasoningTokens: number;
  cacheRate: number;
  sessions: number;
  activeDays: number;
  avgPerDay: number;
  avgPerSession: number;
  estimatedCost: number | null;
}

export interface ChartPoint {
  label: string;
  tokens: number;
}
