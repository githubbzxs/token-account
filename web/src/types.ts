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

export interface ReportData {
  range?: RangeInfo;
  daily?: DailySeries;
  daily_models?: Record<string, Record<string, Record<string, number>>>;
  hourly?: {
    labels: string[];
    total: number[];
  };
  hourly_daily?: Record<string, number[]>;
  hourly_buckets?: Record<string, number>;
  session_spans?: RangeInfo[];
  events?: Array<Record<string, unknown>>;
  daily_costs?: Record<string, number>;
  daily_directories?: Record<string, Record<string, { total_tokens: number; total_cost: number }>>;
  recent_events?: Array<Record<string, unknown>>;
  pricing?: Record<string, unknown>;
  meta?: {
    generated_at?: string;
    source_path?: string;
    source_count?: number;
    last_synced_at?: string;
    data_stamp?: string;
  };
}
