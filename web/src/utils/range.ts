import { TimeRange } from "../types/report";

const DAY_MS = 24 * 60 * 60 * 1000;

export function normalizeISO(value: string): string {
  const input = String(value || "").slice(0, 10);
  const date = new Date(`${input}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toISOString().slice(0, 10);
}

export function addDaysISO(iso: string, offset: number): string {
  const date = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  const next = new Date(date.getTime() + offset * DAY_MS);
  return next.toISOString().slice(0, 10);
}

export function clampISO(iso: string, minISO: string, maxISO: string): string {
  if (!iso) return minISO;
  if (iso < minISO) return minISO;
  if (iso > maxISO) return maxISO;
  return iso;
}

export function calcRangeByPreset(range: TimeRange, minISO: string, maxISO: string): { start: string; end: string } {
  if (range === "ALL") {
    return { start: minISO, end: maxISO };
  }
  const map: Record<Exclude<TimeRange, "ALL">, number> = {
    "1D": 1,
    "2D": 2,
    "1W": 7,
    "1M": 30,
    "3M": 90,
  };
  const days = map[range];
  const end = maxISO;
  const start = clampISO(addDaysISO(end, -(days - 1)), minISO, maxISO);
  return { start, end };
}

export function daysBetween(startISO: string, endISO: string): number {
  const start = new Date(`${startISO}T00:00:00`).getTime();
  const end = new Date(`${endISO}T00:00:00`).getTime();
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return 0;
  }
  return Math.floor((end - start) / DAY_MS) + 1;
}
