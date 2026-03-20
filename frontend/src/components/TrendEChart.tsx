import { useEffect, useMemo, useRef } from 'react';
import { LineChart, type LineSeriesOption } from 'echarts/charts';
import { GridComponent, LegendComponent, TooltipComponent, type GridComponentOption, type LegendComponentOption, type TooltipComponentOption } from 'echarts/components';
import { type ComposeOption, type ECharts, graphic, init, use } from 'echarts/core';
import { SVGRenderer } from 'echarts/renderers';
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion';

use([LineChart, GridComponent, TooltipComponent, LegendComponent, SVGRenderer]);

type TrendChartOption = ComposeOption<
  GridComponentOption | TooltipComponentOption | LegendComponentOption | LineSeriesOption
>;

type TrendEChartProps = {
  labels: string[];
  total: number[];
  input: number[];
  output: number[];
  reasoning: number[];
  height?: number;
  className?: string;
};

function formatLargeNumber(value: number): string {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(2)}B`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toString();
}

function formatDateLabel(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
  }).format(new Date(`${value}T00:00:00`));
}

function joinClassNames(...classNames: Array<string | undefined>): string {
  return classNames.filter(Boolean).join(' ');
}

export function TrendEChart({
  labels,
  total,
  input,
  output,
  reasoning,
  height = 360,
  className,
}: TrendEChartProps) {
  const prefersReducedMotion = usePrefersReducedMotion();
  const hostRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ECharts | null>(null);

  const option = useMemo<TrendChartOption>(() => ({
    animation: !prefersReducedMotion,
    animationDuration: prefersReducedMotion ? 0 : 650,
    animationDurationUpdate: prefersReducedMotion ? 0 : 820,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
    grid: {
      left: 12,
      right: 12,
      top: 56,
      bottom: 10,
      containLabel: true,
    },
    legend: {
      top: 8,
      right: 8,
      itemWidth: 10,
      itemHeight: 10,
      icon: 'circle',
      textStyle: {
        color: '#718198',
        fontFamily: 'Instrument Sans, sans-serif',
        fontSize: 12,
      },
      data: ['总量', '输入', '输出', '推理'],
    },
    tooltip: {
      trigger: 'axis',
      transitionDuration: prefersReducedMotion ? 0 : 0.16,
      backgroundColor: 'rgba(247, 250, 255, 0.96)',
      borderColor: 'rgba(126, 145, 176, 0.16)',
      borderWidth: 1,
      textStyle: {
        color: '#0f1728',
        fontFamily: 'Instrument Sans, sans-serif',
      },
      extraCssText: 'box-shadow: 0 24px 60px rgba(115, 133, 163, 0.18); border-radius: 18px; padding: 12px 14px;',
      axisPointer: {
        type: 'line',
        animation: !prefersReducedMotion,
        lineStyle: {
          color: 'rgba(124, 168, 255, 0.55)',
          width: 1,
          type: 'solid',
        },
      },
      formatter(params) {
        const items = Array.isArray(params) ? params : [params];
        const firstItem = items[0] as { axisValue?: string } | undefined;
        const label = firstItem?.axisValue ? formatDateLabel(String(firstItem.axisValue)) : '';
        const rows = items
          .map((item) => {
            const marker = item.marker ?? '';
            const seriesName = item.seriesName ?? '';
            const value = Array.isArray(item.value) ? Number(item.value[1]) : Number(item.value ?? 0);
            return `<div style="display:flex;justify-content:space-between;gap:20px;"><span>${marker}${seriesName}</span><strong>${formatLargeNumber(value)}</strong></div>`;
          })
          .join('');
        return `<div style="display:grid;gap:8px;"><div style="font-weight:600;">${label}</div>${rows}</div>`;
      },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisTick: {
        show: false,
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(138, 155, 180, 0.18)',
        },
      },
      axisLabel: {
        color: '#718198',
        margin: 14,
        formatter(value: string) {
          return formatDateLabel(value);
        },
      },
    },
    yAxis: {
      type: 'value',
      splitNumber: 4,
      axisTick: {
        show: false,
      },
      axisLine: {
        show: false,
      },
      axisLabel: {
        color: '#718198',
        formatter(value: number) {
          return formatLargeNumber(value);
        },
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(138, 155, 180, 0.12)',
        },
      },
    },
    series: [
      {
        id: 'trend-total',
        name: '总量',
        type: 'line',
        data: total,
        smooth: 0.42,
        showSymbol: false,
        symbolSize: 8,
        universalTransition: true,
        lineStyle: {
          width: 3,
          color: '#6f9cff',
        },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(124, 168, 255, 0.34)' },
            { offset: 0.62, color: 'rgba(124, 168, 255, 0.12)' },
            { offset: 1, color: 'rgba(124, 168, 255, 0)' },
          ]),
        },
        emphasis: {
          focus: 'series',
        },
        z: 4,
      },
      {
        id: 'trend-input',
        name: '输入',
        type: 'line',
        data: input,
        smooth: 0.35,
        showSymbol: false,
        universalTransition: true,
        lineStyle: {
          width: 2,
          color: 'rgba(140, 216, 255, 0.88)',
        },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(140, 216, 255, 0.18)' },
            { offset: 1, color: 'rgba(140, 216, 255, 0)' },
          ]),
        },
        z: 3,
      },
      {
        id: 'trend-output',
        name: '输出',
        type: 'line',
        data: output,
        smooth: 0.35,
        showSymbol: false,
        universalTransition: true,
        lineStyle: {
          width: 2,
          color: 'rgba(147, 222, 207, 0.94)',
        },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(147, 222, 207, 0.16)' },
            { offset: 1, color: 'rgba(147, 222, 207, 0)' },
          ]),
        },
        z: 2,
      },
      {
        id: 'trend-reasoning',
        name: '推理',
        type: 'line',
        data: reasoning,
        smooth: 0.32,
        showSymbol: false,
        universalTransition: true,
        lineStyle: {
          width: 1.8,
          color: 'rgba(197, 210, 255, 0.96)',
        },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(197, 210, 255, 0.14)' },
            { offset: 1, color: 'rgba(197, 210, 255, 0)' },
          ]),
        },
        z: 1,
      },
    ],
  }), [input, labels, output, prefersReducedMotion, reasoning, total]);

  useEffect(() => {
    if (!hostRef.current) {
      return undefined;
    }

    const chart = init(hostRef.current, undefined, {
      renderer: 'svg',
    });
    const resizeObserver = new ResizeObserver(() => {
      chart.resize();
    });

    chartRef.current = chart;
    resizeObserver.observe(hostRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, {
      replaceMerge: ['xAxis', 'yAxis', 'series', 'legend'],
    });
  }, [option]);

  return (
    <div
      ref={hostRef}
      className={joinClassNames('chart-surface', 'is-trend', className)}
      style={{ height }}
      aria-label="每日走势"
    />
  );
}
