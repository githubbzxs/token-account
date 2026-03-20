import { useEffect, useMemo, useRef } from 'react';
import { BarChart, type BarSeriesOption } from 'echarts/charts';
import { GridComponent, TooltipComponent, type GridComponentOption, type TooltipComponentOption } from 'echarts/components';
import { type ComposeOption, type ECharts, graphic, init, use } from 'echarts/core';
import { SVGRenderer } from 'echarts/renderers';
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion';

use([BarChart, GridComponent, TooltipComponent, SVGRenderer]);

type HourlyChartOption = ComposeOption<
  GridComponentOption | TooltipComponentOption | BarSeriesOption
>;

type HourlyBarsEChartProps = {
  labels: string[];
  values: number[];
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

function joinClassNames(...classNames: Array<string | undefined>): string {
  return classNames.filter(Boolean).join(' ');
}

export function HourlyBarsEChart({
  labels,
  values,
  height = 300,
  className,
}: HourlyBarsEChartProps) {
  const prefersReducedMotion = usePrefersReducedMotion();
  const hostRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ECharts | null>(null);

  const option = useMemo<HourlyChartOption>(() => ({
    animation: !prefersReducedMotion,
    animationDuration: prefersReducedMotion ? 0 : 600,
    animationDurationUpdate: prefersReducedMotion ? 0 : 760,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
    grid: {
      left: 12,
      right: 12,
      top: 20,
      bottom: 10,
      containLabel: true,
    },
    tooltip: {
      trigger: 'axis',
      transitionDuration: prefersReducedMotion ? 0 : 0.14,
      backgroundColor: 'rgba(247, 250, 255, 0.96)',
      borderColor: 'rgba(126, 145, 176, 0.16)',
      borderWidth: 1,
      textStyle: {
        color: '#0f1728',
        fontFamily: 'Instrument Sans, sans-serif',
      },
      extraCssText: 'box-shadow: 0 24px 60px rgba(115, 133, 163, 0.18); border-radius: 18px; padding: 12px 14px;',
      axisPointer: {
        type: 'shadow',
        animation: !prefersReducedMotion,
        shadowStyle: {
          color: 'rgba(124, 168, 255, 0.08)',
        },
      },
      formatter(params) {
        const item = Array.isArray(params) ? params[0] : params;
        const label = ((item as { axisValue?: string } | undefined)?.axisValue) ?? '';
        const value = Array.isArray(item?.value) ? Number(item.value[1]) : Number(item?.value ?? 0);
        return `<div style="display:grid;gap:8px;"><div style="font-weight:600;">${label}</div><div style="display:flex;justify-content:space-between;gap:20px;"><span>总量</span><strong>${formatLargeNumber(value)}</strong></div></div>`;
      },
    },
    xAxis: {
      type: 'category',
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
        margin: 12,
        formatter(value: string) {
          return value.slice(0, 2);
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
        id: 'hourly-total',
        name: '总量',
        type: 'bar',
        data: values,
        universalTransition: true,
        barWidth: '48%',
        animationDelayUpdate(index) {
          return index * 10;
        },
        itemStyle: {
          borderRadius: [999, 999, 16, 16],
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#7ca8ff' },
            { offset: 0.58, color: '#90c8ff' },
            { offset: 1, color: '#cde1ff' },
          ]),
          shadowBlur: 16,
          shadowColor: 'rgba(124, 168, 255, 0.16)',
        },
        emphasis: {
          itemStyle: {
            color: new graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#6f9cff' },
              { offset: 1, color: '#9bd7ff' },
            ]),
          },
        },
      },
    ],
  }), [labels, prefersReducedMotion, values]);

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
      replaceMerge: ['xAxis', 'yAxis', 'series'],
    });
  }, [option]);

  return (
    <div
      ref={hostRef}
      className={joinClassNames('chart-surface', 'is-bars', className)}
      style={{ height }}
      aria-label="24 小时热度"
    />
  );
}
