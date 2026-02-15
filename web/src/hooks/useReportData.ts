import { useCallback, useEffect, useMemo, useState } from "react";
import { mergeReportData, normalizeImportedData } from "../utils/data";
import { ReportData } from "../types/report";

interface UseReportDataResult {
  data: ReportData | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  importFiles: (files: File[]) => Promise<{ merged: number; invalid: number }>;
}

async function fetchReportData(): Promise<ReportData> {
  const response = await fetch("./data.json", {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`加载 data.json 失败（${response.status}）`);
  }
  return (await response.json()) as ReportData;
}

async function readFileText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("读取文件失败"));
    reader.readAsText(file);
  });
}

export function useReportData(): UseReportDataResult {
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const next = await fetchReportData();
      setData(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载数据失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const importFiles = useCallback(
    async (files: File[]) => {
      if (!data || !files.length) {
        return { merged: 0, invalid: 0 };
      }
      const imported: ReportData[] = [];
      let invalid = 0;

      for (const file of files) {
        try {
          const text = await readFileText(file);
          const parsed = JSON.parse(text) as unknown;
          const normalized = normalizeImportedData(parsed);
          if (normalized) {
            imported.push(normalized);
          } else {
            invalid += 1;
          }
        } catch {
          invalid += 1;
        }
      }

      if (!imported.length) {
        return { merged: 0, invalid };
      }

      const merged = mergeReportData([data, ...imported]);
      if (!merged) {
        return { merged: 0, invalid: invalid + imported.length };
      }
      setData(merged);
      setError(null);

      return { merged: imported.length, invalid };
    },
    [data],
  );

  return useMemo(
    () => ({
      data,
      loading,
      error,
      reload,
      importFiles,
    }),
    [data, error, importFiles, loading, reload],
  );
}
