import { motion } from "framer-motion";
import * as echarts from "echarts";
import { useEffect, useMemo, useRef } from "react";
import { ChartPoint } from "../types/report";
import { formatNumberCompact } from "../utils/format";
import { CHART_DRAW_DURATION_MS } from "../constants/animation";

interface UsageChartProps {
  data: ChartPoint[];
}

function pickLabelMode(points: ChartPoint[]): "hour" | "day" {
  if (points.length <= 24) {
    return "hour";
  }
  return "day";
}

function formatXAxisLabel(label: string, mode: "hour" | "day"): string {
  if (mode === "hour") {
    return label.slice(11, 16);
  }
  return label.slice(5, 10);
}

export function UsageChart({ data }: UsageChartProps) {
  const chartRef = useRef<HTMLDivElement | null>(null);

  const { labels, values, mode } = useMemo(() => {
    const nextLabels = data.map((item) => item.label);
    const nextValues = data.map((item) => item.tokens);
    return {
      labels: nextLabels,
      values: nextValues,
      mode: pickLabelMode(data),
    };
  }, [data]);

  useEffect(() => {
    if (!chartRef.current) {
      return;
    }

    const chart = echarts.init(chartRef.current, undefined, {
      renderer: "canvas",
    });

    chart.setOption({
      backgroundColor: "transparent",
      grid: {
        left: 40,
        right: 16,
        top: 18,
        bottom: 34,
      },
      animationDuration: CHART_DRAW_DURATION_MS,
      animationEasing: "cubicOut",
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "line",
          lineStyle: {
            color: "rgba(224, 177, 58, 0.55)",
            width: 1,
            type: "dashed",
          },
        },
        backgroundColor: "rgba(14, 16, 24, 0.92)",
        borderColor: "rgba(224, 177, 58, 0.35)",
        borderWidth: 1,
        textStyle: {
          color: "#f8fafc",
          fontFamily: "JetBrains Mono",
        },
        valueFormatter: (value: string | number) => formatNumberCompact(Number(value || 0)),
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: labels,
        axisLine: {
          lineStyle: {
            color: "rgba(148, 163, 184, 0.25)",
          },
        },
        axisTick: {
          show: false,
        },
        axisLabel: {
          color: "#697289",
          fontSize: 11,
          formatter: (value: string) => formatXAxisLabel(value, mode),
          hideOverlap: true,
          interval: "auto",
        },
      },
      yAxis: {
        type: "value",
        splitNumber: 4,
        axisLine: {
          show: false,
        },
        axisTick: {
          show: false,
        },
        axisLabel: {
          color: "#697289",
          fontSize: 11,
          formatter: (value: number) => formatNumberCompact(value),
        },
        splitLine: {
          lineStyle: {
            color: "rgba(148, 163, 184, 0.12)",
            type: "dashed",
          },
        },
      },
      series: [
        {
          type: "line",
          smooth: 0.35,
          showSymbol: false,
          data: values,
          lineStyle: {
            width: 2,
            color: "#e0b13a",
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(224, 177, 58, 0.32)" },
              { offset: 0.62, color: "rgba(224, 177, 58, 0.16)" },
              { offset: 1, color: "rgba(224, 177, 58, 0.02)" },
            ]),
          },
          emphasis: {
            focus: "series",
          },
        },
      ],
    });

    const resize = () => chart.resize();
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [labels, mode, values]);

  return (
    <motion.div
      className="usage-chart-shell"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.35 }}
    >
      <div className="usage-chart-head">
        <h3>Usage Trends</h3>
        <span>Area animation replays on range change</span>
      </div>
      <div ref={chartRef} className="usage-chart" />
    </motion.div>
  );
}
