import { Calendar, Download, Upload, Languages, Palette } from "lucide-react";
import { LayoutGroup, motion } from "framer-motion";
import { ChangeEvent } from "react";
import { Locale, ThemeMode, TimeRange } from "../types/report";

const RANGES: TimeRange[] = ["1D", "2D", "1W", "1M", "3M", "ALL"];

interface ControlBarProps {
  activeRange: TimeRange;
  rangeLabel: string;
  locale: Locale;
  theme: ThemeMode;
  importing: boolean;
  onRangeChange: (range: TimeRange) => void;
  onExport: () => void;
  onImport: (files: File[]) => void;
  onToggleLocale: () => void;
  onToggleTheme: () => void;
}

export function ControlBar(props: ControlBarProps) {
  const {
    activeRange,
    rangeLabel,
    locale,
    theme,
    importing,
    onRangeChange,
    onExport,
    onImport,
    onToggleLocale,
    onToggleTheme,
  } = props;

  const handleImport = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (files.length) {
      onImport(files);
    }
    event.currentTarget.value = "";
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="control-bar"
    >
      <button type="button" className="date-trigger" aria-label="当前日期范围">
        <Calendar size={15} />
        <span>{rangeLabel}</span>
      </button>

      <LayoutGroup>
        <div className="range-group" role="tablist" aria-label="快捷时间范围">
          {RANGES.map((range) => (
            <button
              key={range}
              type="button"
              role="tab"
              aria-selected={activeRange === range}
              className={`range-btn${activeRange === range ? " is-active" : ""}`}
              onClick={() => onRangeChange(range)}
            >
              {activeRange === range ? (
                <motion.span
                  layoutId="range-active-pill"
                  className="range-pill"
                  transition={{ type: "spring", stiffness: 420, damping: 34 }}
                />
              ) : null}
              <span className="range-label">{range}</span>
            </button>
          ))}
        </div>
      </LayoutGroup>

      <div className="control-actions">
        <button
          type="button"
          className="icon-btn"
          onClick={onToggleLocale}
          title={locale === "en" ? "切换到中文" : "Switch to English"}
        >
          <Languages size={15} />
        </button>

        <button
          type="button"
          className={`icon-btn${theme === "bronze" ? " is-theme-active" : ""}`}
          onClick={onToggleTheme}
          title="切换主题"
        >
          <Palette size={15} />
        </button>

        <label className="icon-btn file-btn" title="导入 JSON">
          <Upload size={15} />
          <input type="file" accept="application/json" multiple onChange={handleImport} disabled={importing} />
        </label>

        <button type="button" className="icon-btn" onClick={onExport} title="导出数据">
          <Download size={15} />
        </button>
      </div>
    </motion.div>
  );
}
