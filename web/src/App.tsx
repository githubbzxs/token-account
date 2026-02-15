import { AnimatePresence, motion } from "framer-motion";
import { Settings, Cpu } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ControlBar } from "./components/ControlBar";
import { StatsCard } from "./components/StatsCard";
import { UsageChart } from "./components/UsageChart";
import { useReportData } from "./hooks/useReportData";
import { Locale, ThemeMode, TimeRange } from "./types/report";
import { buildChartSeries, calcRangedView, computeStats } from "./utils/data";
import { formatCurrency, formatDateRange, formatNumberDetailed, formatPercent } from "./utils/format";
import { calcRangeByPreset } from "./utils/range";
import { RANGE_SWITCH_DELAY_MS } from "./constants/animation";

const I18N: Record<Locale, Record<string, string>> = {
  zh: {
    title: "Token Usage",
    subtitle: "监控你的 AI 资源消耗",
    totalTokens: "TOTAL TOKENS",
    estimatedCost: "ESTIMATED COST",
    sessions: "会话",
    activeDays: "活跃天数",
    perDay: "日均",
    perSession: "会话均值",
    cacheRate: "缓存率",
    input: "输入",
    output: "输出",
    loading: "正在获取数据...",
    noData: "当前范围暂无数据",
    importOk: "已合并 {count} 个文件",
    importFail: "导入文件无效",
    systemOnline: "SYSTEM ONLINE",
    askAI: "Ask AI",
    refresh: "刷新",
  },
  en: {
    title: "Token Usage",
    subtitle: "Monitor your AI resource consumption",
    totalTokens: "TOTAL TOKENS",
    estimatedCost: "ESTIMATED COST",
    sessions: "Sessions",
    activeDays: "Active days",
    perDay: "Per day",
    perSession: "Per session",
    cacheRate: "Cache rate",
    input: "IN",
    output: "OUT",
    loading: "Fetching data...",
    noData: "No data in current range",
    importOk: "Merged {count} file(s)",
    importFail: "Invalid import file",
    systemOnline: "SYSTEM ONLINE",
    askAI: "Ask AI",
    refresh: "Reload",
  },
};

function formatText(template: string, params: Record<string, string | number>) {
  return template.replace(/\{(\w+)\}/g, (_, key) => String(params[key] ?? ""));
}

function readStoredLocale(): Locale {
  const stored = window.localStorage.getItem("report-locale");
  return stored === "zh" ? "zh" : "en";
}

function readStoredTheme(): ThemeMode {
  const stored = window.localStorage.getItem("report-theme");
  return stored === "bronze" ? "bronze" : "neon";
}

export function App() {
  const { data, loading, error, reload, importFiles } = useReportData();
  const [activeRange, setActiveRange] = useState<TimeRange>("ALL");
  const [rangeLoading, setRangeLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importStatus, setImportStatus] = useState("");
  const [locale, setLocale] = useState<Locale>(() => readStoredLocale());
  const [theme, setTheme] = useState<ThemeMode>(() => readStoredTheme());
  const timerRef = useRef<number | null>(null);

  const t = I18N[locale];

  useEffect(() => {
    document.documentElement.lang = locale;
    window.localStorage.setItem("report-locale", locale);
  }, [locale]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("report-theme", theme);
  }, [theme]);

  useEffect(() => {
    return () => {
      if (timerRef.current != null) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!data) return;
    if (!data.daily.labels.length) return;
    setActiveRange((prev) => (prev ? prev : "ALL"));
  }, [data]);

  const rangeWindow = useMemo(() => {
    if (!data) return null;
    return calcRangeByPreset(activeRange, data.range.start, data.range.end);
  }, [activeRange, data]);

  const rangedView = useMemo(() => {
    if (!data || !rangeWindow) return null;
    return calcRangedView(data, rangeWindow.start, rangeWindow.end);
  }, [data, rangeWindow]);

  const stats = useMemo(() => {
    if (!data || !rangedView) return null;
    return computeStats(data, rangedView);
  }, [data, rangedView]);

  const chartData = useMemo(() => {
    if (!data || !rangedView) return [];
    return buildChartSeries(data, rangedView);
  }, [data, rangedView]);

  const rangeLabel = useMemo(() => {
    if (!rangedView) {
      return "-";
    }
    return formatDateRange(rangedView.startISO, rangedView.endISO);
  }, [rangedView]);

  const handleRangeChange = (range: TimeRange) => {
    if (range === activeRange || rangeLoading) {
      return;
    }
    setRangeLoading(true);
    if (timerRef.current != null) {
      window.clearTimeout(timerRef.current);
    }
    timerRef.current = window.setTimeout(() => {
      setActiveRange(range);
      setRangeLoading(false);
      timerRef.current = null;
    }, RANGE_SWITCH_DELAY_MS);
  };

  const handleImport = async (files: File[]) => {
    setImporting(true);
    const result = await importFiles(files);
    if (result.merged > 0) {
      setImportStatus(formatText(t.importOk, { count: result.merged }));
    } else {
      setImportStatus(t.importFail);
    }
    setImporting(false);
  };

  const handleExport = () => {
    if (!data) {
      return;
    }
    const payload = {
      version: 2,
      exported_at: new Date().toISOString(),
      data,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    const day = new Date().toISOString().slice(0, 10);
    link.download = `codex-token-export-${day}.json`;
    link.href = URL.createObjectURL(blob);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  };

  const toggleLocale = () => setLocale((prev) => (prev === "en" ? "zh" : "en"));
  const toggleTheme = () => setTheme((prev) => (prev === "neon" ? "bronze" : "neon"));

  const showLoader = loading || rangeLoading;
  const hasData = Boolean(data && stats && rangedView && chartData.length);

  return (
    <div className="app-shell">
      <div className="atmo-glow atmo-glow-a" />
      <div className="atmo-glow atmo-glow-b" />

      <main className="page">
        <header className="page-header">
          <div className="brand">
            <div className="brand-icon">
              <span />
            </div>
            <div>
              <motion.h1 initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}>
                {t.title}
              </motion.h1>
              <p>{t.subtitle}</p>
            </div>
          </div>

          <div className="header-right">
            <div className="status-pill">
              <span className="pulse" />
              {t.systemOnline}
            </div>
            <button type="button" className="icon-btn" onClick={() => void reload()} title={t.refresh}>
              <Settings size={18} />
            </button>
          </div>
        </header>

        <ControlBar
          activeRange={activeRange}
          rangeLabel={rangeLabel}
          locale={locale}
          theme={theme}
          importing={importing}
          onRangeChange={handleRangeChange}
          onExport={handleExport}
          onImport={(files) => {
            void handleImport(files);
          }}
          onToggleLocale={toggleLocale}
          onToggleTheme={toggleTheme}
        />

        {importStatus ? <p className="import-status">{importStatus}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}

        <div className="cards-grid">
          <StatsCard
            title={t.totalTokens}
            value={stats?.totalTokens ?? 0}
            type="number"
            delay={0.1}
            subtext={
              <>
                <span className="muted-label">{t.input}</span>
                <span>{formatNumberDetailed(stats?.inputTokens ?? 0)}</span>
                <span className="divider">|</span>
                <span className="muted-label">{t.output}</span>
                <span>{formatNumberDetailed(stats?.outputTokens ?? 0)}</span>
              </>
            }
          />
          <StatsCard
            title={t.estimatedCost}
            value={stats?.estimatedCost ?? 0}
            type="currency"
            delay={0.2}
            subtext={
              <>
                <span>{t.sessions} {stats?.sessions ?? 0}</span>
                <span className="divider">|</span>
                <span>{t.activeDays} {stats?.activeDays ?? 0}</span>
                <span className="divider">|</span>
                <span>{t.cacheRate} {formatPercent(stats?.cacheRate ?? 0)}</span>
              </>
            }
          />
        </div>

        <section className="chart-section">
          <AnimatePresence mode="wait">
            {showLoader ? (
              <motion.div
                key="loading"
                className="chart-loader"
                initial={{ opacity: 0, scale: 0.985 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.985 }}
                transition={{ duration: 0.2 }}
              >
                <div className="loader-ring" />
                <p>{t.loading}</p>
              </motion.div>
            ) : hasData ? (
              <UsageChart key={activeRange} data={chartData} />
            ) : (
              <motion.div
                key="empty"
                className="chart-empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                {t.noData}
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        <footer className="summary-row">
          <span>{t.perDay}: {formatNumberDetailed(stats?.avgPerDay ?? 0)}</span>
          <span>{t.perSession}: {formatNumberDetailed(stats?.avgPerSession ?? 0)}</span>
          <span>{t.estimatedCost}: {formatCurrency(stats?.estimatedCost ?? 0)}</span>
        </footer>
      </main>

      <motion.button
        type="button"
        className="ask-ai"
        initial={{ x: 100 }}
        animate={{ x: 0 }}
        transition={{ delay: 0.8 }}
      >
        <span>{t.askAI}</span>
        <Cpu size={18} />
      </motion.button>
    </div>
  );
}
