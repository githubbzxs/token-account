export interface RangeInfo {
  start: string;
  end: string;
  days?: number;
}

export interface DailySeries {
  labels: string[];
  total: number[];
  input: number[];
  output: number[];
  reasoning: number[];
  cached: number[];
}

export interface DirectoryRecord {
  total_tokens: number;
  total_cost: number;
}

export interface SourceRecord {
  source_id?: string;
  hostname?: string;
  last_sync_at?: string;
  last_seen_at?: string;
}

export interface ReportData {
  range: RangeInfo;
  available_range?: RangeInfo;
  daily: DailySeries;
  daily_models?: Record<string, Record<string, Record<string, number>>>;
  hourly?: {
    labels: string[];
    total: number[];
  };
  hourly_daily?: Record<string, number[]>;
  session_spans?: RangeInfo[];
  daily_costs?: Record<string, number>;
  daily_directories?: Record<string, Record<string, DirectoryRecord>>;
  recent_events?: Array<Record<string, unknown>>;
  sources?: SourceRecord[];
  meta?: {
    generated_at?: string;
    source_path?: string;
    source_count?: number;
    last_synced_at?: string;
    data_stamp?: string;
  };
}

export interface DateRange {
  start: string;
  end: string;
}

export interface DirectoryRow {
  path: string;
  name: string;
  totalTokens: number;
  totalCost: number;
}

export interface ReportSlice {
  range: DateRange;
  labels: string[];
  totals: {
    totalTokens: number;
    inputTokens: number;
    outputTokens: number;
    reasoningTokens: number;
    cachedTokens: number;
    totalCost: number;
    sessions: number;
    activeDays: number;
    cacheRate: number;
    averagePerDay: number;
  };
  daily: {
    labels: string[];
    total: number[];
    input: number[];
    output: number[];
    reasoning: number[];
    cached: number[];
  };
  hourly: number[];
  directories: DirectoryRow[];
  empty: boolean;
}
