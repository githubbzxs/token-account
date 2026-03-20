import { useEffect, useEffectEvent, useMemo, useState, startTransition } from 'react';
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Center,
  Divider,
  Group,
  Loader,
  Paper,
  Progress,
  RingProgress,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core';
import { DateInput } from '@mantine/dates';
import { DonutChart } from '@mantine/charts';
import {
  IconActivityHeartbeat,
  IconCalendarMonth,
  IconClockHour4,
  IconCoins,
  IconCpu,
  IconDatabase,
  IconPrompt,
  IconRefresh,
  IconSparkles,
} from '@tabler/icons-react';
import { HourlyBarsEChart } from './components/HourlyBarsEChart';
import { RollingNumber } from './components/RollingNumber';
import { TrendEChart } from './components/TrendEChart';

type DashboardResponse = {
  data: ReportData;
  summary: Summary;
  empty: boolean;
};

type Summary = {
  range_text: string;
  sessions: string;
  days_active: string;
  total_tokens: string;
  input_tokens: string;
  output_tokens: string;
  reasoning_tokens: string;
  cached_tokens: string;
  cache_rate: string;
  avg_per_day: string;
  avg_per_session: string;
  total_cost: string;
  generated_at: string;
  source_path: string;
};

type ReportData = {
  range: {
    start: string;
    end: string;
    days: number;
  };
  daily: {
    labels: string[];
    total: number[];
    input: number[];
    output: number[];
    reasoning: number[];
    cached: number[];
  };
  models: ModelTotal[];
  hourly: {
    labels: string[];
    total: number[];
  };
  events: EventPoint[];
  sources: SourceRecord[];
  meta: {
    generated_at: string;
    source_path: string;
    source_count: number;
    last_synced_at: string;
    data_stamp: string;
  };
};

type ModelTotal = {
  name: string;
  value: number;
};

type EventPoint = {
  ts: string;
  day: string;
  model: string;
  value: number;
  input: number;
  cached: number;
  output: number;
  reasoning: number;
  total: number;
  source_id: string;
  cost_usd?: number;
};

type SourceRecord = {
  source_id: string;
  hostname: string;
  first_seen_at: string;
  last_seen_at: string;
  last_sync_at: string | null;
  total_events: number;
  last_error: string | null;
};

type Preset = '7d' | '30d' | '90d' | 'all';

const PRESET_LABELS: Record<Preset, string> = {
  '7d': '最近 7 天',
  '30d': '最近 30 天',
  '90d': '最近 90 天',
  all: '全部',
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

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '未同步';
  }
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function parseCacheRate(rateText: string): number {
  const numeric = Number.parseFloat(rateText.replace('%', ''));
  if (Number.isNaN(numeric)) {
    return 0;
  }
  return numeric;
}

function getPresetRange(preset: Preset, data: ReportData | null): { since?: string; until?: string } {
  if (preset === 'all') {
    return {};
  }

  const end = new Date();
  const start = new Date(end);
  const days = preset === '7d' ? 6 : preset === '30d' ? 29 : 89;
  start.setDate(end.getDate() - days);

  const todayText = end.toISOString().slice(0, 10);
  const startText = start.toISOString().slice(0, 10);

  if (!data) {
    return { since: startText, until: todayText };
  }

  const minDate = data.range.start;
  return {
    since: startText < minDate ? minDate : startText,
    until: todayText,
  };
}

function toIsoDate(value: string | null): string | undefined {
  if (!value) {
    return undefined;
  }
  return value;
}

export function App() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preset, setPreset] = useState<Preset>('30d');
  const [sinceDate, setSinceDate] = useState<string | null>(null);
  const [untilDate, setUntilDate] = useState<string | null>(null);

  const fetchDashboard = useEffectEvent(async (showBusy: boolean) => {
    const range = sinceDate && untilDate
      ? {
          since: toIsoDate(sinceDate),
          until: toIsoDate(untilDate),
        }
      : getPresetRange(preset, dashboard?.data ?? null);

    const params = new URLSearchParams();
    if (range.since) {
      params.set('since', range.since);
    }
    if (range.until) {
      params.set('until', range.until);
    }

    if (showBusy) {
      setRefreshing(true);
    }

    try {
      const response = await fetch(`/api/dashboard?${params.toString()}`, {
        headers: {
          Accept: 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`请求失败：${response.status}`);
      }

      const payload = (await response.json()) as DashboardResponse;
      startTransition(() => {
        setDashboard(payload);
        setError(null);
      });
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : '加载失败');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  });

  useEffect(() => {
    void fetchDashboard(false);
  }, [fetchDashboard, preset, sinceDate, untilDate]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void fetchDashboard(true);
    }, 30_000);

    return () => {
      window.clearInterval(timer);
    };
  }, [fetchDashboard]);

  const modelRows = useMemo(() => (dashboard ? dashboard.data.models : []), [dashboard]);

  if (loading && !dashboard) {
    return (
      <Center mih="100vh">
        <Stack align="center" gap="sm">
          <Loader color="blue" />
          <Text c="dimmed">正在整理你的 Token 面板…</Text>
        </Stack>
      </Center>
    );
  }

  if (!dashboard) {
    return (
      <Center mih="100vh">
        <Stack align="center" gap="sm">
          <Text fw={600}>页面暂时不可用</Text>
          <Text c="dimmed">{error ?? '暂时没有可展示的数据。'}</Text>
          <Button onClick={() => void fetchDashboard(true)}>重新加载</Button>
        </Stack>
      </Center>
    );
  }

  const { data, summary, empty } = dashboard;
  const cacheRate = parseCacheRate(summary.cache_rate);
  const topModels = modelRows.slice(0, 5);
  const latestEvents = [...data.events].slice(-8).reverse();
  const totalModelTokens = Math.max(modelRows.reduce((sum, current) => sum + current.value, 0), 1);
  const modelDonutData = topModels.map((item, index) => ({
    name: item.name,
    value: item.value,
    color: ['#7ca8ff', '#89c8ff', '#8fe0d6', '#c3d8ff', '#d7e7ff'][index] ?? '#d7e7ff',
  }));
  const hourlyLabels = data.hourly.labels.map((label) => `${label}:00`);

  return (
    <Box className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <main className="page-frame">
        <section className="hero-panel">
          <div className="hero-copy">
            <Group gap="xs">
              <Badge variant="light" color="blue" radius="xl">
                Token Account
              </Badge>
              <Badge variant="dot" color={empty ? 'gray' : 'teal'} radius="xl">
                {empty ? '当前无数据' : '自动同步中'}
              </Badge>
            </Group>
            <Title order={1} className="hero-title">
              像苹果系统仪表盘一样，安静地看清每一次 Codex 消耗。
            </Title>
            <Text className="hero-text">
              保留原来的同步链路与数据库，把展示层彻底换成更清爽、更有秩序的总览界面。
            </Text>
            <Group gap="sm" mt="xl" wrap="wrap">
              <Button
                size="md"
                radius="xl"
                className="hero-button"
                leftSection={<IconRefresh size={18} />}
                loading={refreshing}
                onClick={() => void fetchDashboard(true)}
              >
                立即刷新
              </Button>
              <Group gap={10} className="hero-meta">
                <Text fw={600}>最近同步</Text>
                <Text c="dimmed">{formatDateTime(data.meta.last_synced_at)}</Text>
              </Group>
              <Group gap={10} className="hero-meta">
                <Text fw={600}>统计范围</Text>
                <Text c="dimmed">{summary.range_text}</Text>
              </Group>
            </Group>
          </div>
          <Paper className="hero-spotlight" radius={32}>
            <Text className="eyebrow">今日质感卡片</Text>
            <RollingNumber value={summary.total_tokens} className="spotlight-value" />
            <Text className="spotlight-caption">总 Token</Text>
            <Divider my="md" color="rgba(138, 155, 180, 0.12)" />
            <SimpleGrid cols={2} spacing="md">
              <div>
                <Text className="mini-label">会话</Text>
                <RollingNumber value={summary.sessions} className="mini-metric-value" />
              </div>
              <div>
                <Text className="mini-label">活跃天数</Text>
                <RollingNumber value={summary.days_active} className="mini-metric-value" />
              </div>
              <div>
                <Text className="mini-label">成本</Text>
                <RollingNumber value={summary.total_cost} className="mini-metric-value" />
              </div>
              <div>
                <Text className="mini-label">缓存率</Text>
                <RollingNumber value={summary.cache_rate} className="mini-metric-value" />
              </div>
            </SimpleGrid>
          </Paper>
        </section>

        <Paper className="range-panel" radius={28}>
          <Group justify="space-between" align="flex-start" gap="lg" wrap="wrap">
            <Stack gap={6}>
              <Text className="eyebrow">时间范围</Text>
              <Text fw={600}>快速查看不同统计窗口</Text>
            </Stack>
            <Group gap="sm" wrap="wrap">
              <SegmentedControl
                radius="xl"
                value={preset}
                onChange={(value) => {
                  setPreset(value as Preset);
                  setSinceDate(null);
                  setUntilDate(null);
                }}
                data={Object.entries(PRESET_LABELS).map(([value, label]) => ({ value, label }))}
              />
              <DateInput
                value={sinceDate}
                onChange={(value) => {
                  setSinceDate(value);
                }}
                valueFormat="YYYY-MM-DD"
                leftSection={<IconCalendarMonth size={18} />}
                placeholder="开始日期"
                radius="xl"
                clearable
              />
              <DateInput
                value={untilDate}
                onChange={(value) => {
                  setUntilDate(value);
                }}
                valueFormat="YYYY-MM-DD"
                leftSection={<IconCalendarMonth size={18} />}
                placeholder="结束日期"
                radius="xl"
                clearable
              />
            </Group>
          </Group>
        </Paper>

        {error ? (
          <Paper className="notice-panel" radius={24}>
            <Text fw={600}>数据刷新遇到问题</Text>
            <Text c="dimmed">{error}</Text>
          </Paper>
        ) : null}

        <SimpleGrid cols={{ base: 1, md: 2, xl: 4 }} spacing="lg" mt="lg">
          <MetricCard
            icon={IconSparkles}
            title="总 Token"
            value={summary.total_tokens}
            detail={`最近生成于 ${summary.generated_at}`}
          />
          <MetricCard
            icon={IconPrompt}
            title="平均每会话"
            value={summary.avg_per_session}
            detail={`日均 ${summary.avg_per_day}`}
          />
          <MetricCard
            icon={IconCoins}
            title="估算成本"
            value={summary.total_cost}
            detail={`输入 ${summary.input_tokens} / 输出 ${summary.output_tokens}`}
          />
          <MetricCard
            icon={IconDatabase}
            title="缓存与推理"
            value={summary.cached_tokens}
            detail={`推理 ${summary.reasoning_tokens}`}
          />
        </SimpleGrid>

        <section className="content-grid">
          <Paper className="canvas-panel chart-panel" radius={32}>
            <Group justify="space-between" align="flex-end" mb="lg">
              <div>
                <Text className="eyebrow">趋势画布</Text>
                <Title order={3}>每日走势</Title>
              </div>
              <Text c="dimmed">按天汇总输入、输出、推理与缓存变化</Text>
            </Group>
            <TrendEChart
              labels={data.daily.labels}
              total={data.daily.total}
              input={data.daily.input}
              output={data.daily.output}
              reasoning={data.daily.reasoning}
            />
          </Paper>

          <Stack gap="lg">
            <Paper className="canvas-panel" radius={32}>
              <Group justify="space-between" align="center" mb="lg">
                <div>
                  <Text className="eyebrow">资源配比</Text>
                  <Title order={3}>缓存效率</Title>
                </div>
                <ThemeIcon size={42} radius="xl" variant="light" color="teal">
                  <IconActivityHeartbeat size={22} />
                </ThemeIcon>
              </Group>
              <Group align="center" wrap="nowrap">
                <RingProgress
                  size={164}
                  thickness={16}
                  roundCaps
                  sections={[
                    { value: cacheRate, color: '#7ca8ff' },
                    { value: Math.max(100 - cacheRate, 0), color: '#d7e7ff' },
                  ]}
                  label={
                    <Stack gap={0} align="center">
                      <RollingNumber value={summary.cache_rate} className="ring-number" />
                      <Text size="sm" c="dimmed">
                        缓存率
                      </Text>
                    </Stack>
                  }
                />
                <Stack className="detail-stack" gap="sm">
                  <DetailRow label="输入" value={summary.input_tokens} progress={100} />
                  <DetailRow label="缓存" value={summary.cached_tokens} progress={cacheRate} />
                  <DetailRow
                    label="推理"
                    value={summary.reasoning_tokens}
                    progress={Math.min(Math.max((parseCacheRate(summary.cache_rate) / 2), 8), 58)}
                  />
                </Stack>
              </Group>
            </Paper>

            <Paper className="canvas-panel" radius={32}>
              <Group justify="space-between" align="center" mb="lg">
                <div>
                  <Text className="eyebrow">模型偏好</Text>
                  <Title order={3}>Top Models</Title>
                </div>
                <ThemeIcon size={42} radius="xl" variant="light" color="blue">
                  <IconCpu size={22} />
                </ThemeIcon>
              </Group>
              <div className="donut-wrap">
                <DonutChart
                  size={220}
                  thickness={26}
                  data={modelDonutData}
                  withLabelsLine={false}
                  withTooltip
                />
                <div className="donut-center">
                  <RollingNumber value={summary.total_tokens} className="donut-number" />
                  <Text className="mini-label">总量</Text>
                </div>
              </div>
              <Stack gap="sm" mt="lg">
                {topModels.map((item, index) => (
                  <Group key={item.name} justify="space-between" className="list-row">
                    <Group gap="sm">
                      <span className="model-swatch" style={{ background: modelDonutData[index]?.color ?? '#d7e7ff' }} />
                      <Text fw={600}>{item.name}</Text>
                    </Group>
                    <RollingNumber value={formatLargeNumber(item.value)} className="model-value" />
                  </Group>
                ))}
              </Stack>
            </Paper>
          </Stack>
        </section>

        <section className="content-grid lower-grid">
          <Paper className="canvas-panel" radius={32}>
            <Group justify="space-between" align="flex-end" mb="lg">
              <div>
                <Text className="eyebrow">节奏分布</Text>
                <Title order={3}>24 小时热度</Title>
              </div>
              <Text c="dimmed">找到你最常触发高消耗的时间段</Text>
            </Group>
            <HourlyBarsEChart labels={hourlyLabels} values={data.hourly.total} />
          </Paper>

          <Paper className="canvas-panel" radius={32}>
            <Group justify="space-between" align="flex-end" mb="lg">
              <div>
                <Text className="eyebrow">来源状态</Text>
                <Title order={3}>同步设备</Title>
              </div>
              <Text c="dimmed">{data.meta.source_count} 台设备在线汇总</Text>
            </Group>
            <Stack gap="sm">
              {data.sources.map((source) => (
                <div key={source.source_id} className="source-card">
                  <Group justify="space-between" align="flex-start" wrap="nowrap">
                    <div>
                      <Text fw={600}>{source.hostname}</Text>
                      <Text size="sm" c="dimmed">
                        {source.source_id}
                      </Text>
                    </div>
                    <Badge color={source.last_error ? 'red' : 'teal'} variant="light" radius="xl">
                      {source.last_error ? '异常' : '健康'}
                    </Badge>
                  </Group>
                  <SimpleGrid cols={2} spacing="md" mt="md">
                    <div>
                      <Text className="mini-label">最近同步</Text>
                      <Text fw={600}>{formatDateTime(source.last_sync_at)}</Text>
                    </div>
                    <div>
                      <Text className="mini-label">事件总数</Text>
                      <Text fw={600}>{source.total_events.toLocaleString('en-US')}</Text>
                    </div>
                  </SimpleGrid>
                  {source.last_error ? (
                    <Text mt="sm" c="red">
                      {source.last_error}
                    </Text>
                  ) : null}
                </div>
              ))}
            </Stack>
          </Paper>
        </section>

        <section className="content-grid lower-grid">
          <Paper className="canvas-panel" radius={32}>
            <Group justify="space-between" align="flex-end" mb="lg">
              <div>
                <Text className="eyebrow">最近脉冲</Text>
                <Title order={3}>最新事件</Title>
              </div>
              <ActionIcon
                variant="light"
                radius="xl"
                size={40}
                color="blue"
                onClick={() => void fetchDashboard(true)}
              >
                <IconClockHour4 size={20} />
              </ActionIcon>
            </Group>
            <Stack gap="sm">
              {latestEvents.map((event) => (
                <div key={`${event.ts}-${event.total}`} className="event-row">
                  <div>
                    <Text fw={600}>{event.model}</Text>
                    <Text size="sm" c="dimmed">
                      {event.ts} · {event.source_id}
                    </Text>
                  </div>
                  <div className="event-value">
                    <RollingNumber value={formatLargeNumber(event.total)} className="event-number" />
                    <Text size="sm" c="dimmed">
                      {event.cost_usd ? `$${event.cost_usd.toFixed(4)}` : '未估价'}
                    </Text>
                  </div>
                </div>
              ))}
            </Stack>
          </Paper>

          <Paper className="canvas-panel" radius={32}>
            <Group justify="space-between" align="flex-end" mb="lg">
              <div>
                <Text className="eyebrow">模型明细</Text>
                <Title order={3}>Token 分布表</Title>
              </div>
              <Text c="dimmed">按总消耗排序</Text>
            </Group>
            <Table highlightOnHover withTableBorder={false} verticalSpacing="md">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>模型</Table.Th>
                  <Table.Th>总量</Table.Th>
                  <Table.Th>占比</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {topModels.map((item) => (
                  <Table.Tr key={item.name}>
                    <Table.Td>{item.name}</Table.Td>
                    <Table.Td>
                      <RollingNumber value={formatLargeNumber(item.value)} className="table-number" />
                    </Table.Td>
                    <Table.Td>{((item.value / totalModelTokens) * 100).toFixed(1)}%</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Paper>
        </section>
      </main>
    </Box>
  );
}

type MetricCardProps = {
  icon: typeof IconSparkles;
  title: string;
  value: string;
  detail: string;
};

function MetricCard({ icon: Icon, title, value, detail }: MetricCardProps) {
  return (
    <Paper className="metric-card" radius={28}>
      <Group justify="space-between" align="flex-start">
        <Stack gap={6}>
          <Text className="eyebrow">{title}</Text>
          <RollingNumber value={value} className="metric-value" />
          <Text c="dimmed">{detail}</Text>
        </Stack>
        <ThemeIcon size={46} radius="xl" variant="light" color="blue">
          <Icon size={24} />
        </ThemeIcon>
      </Group>
    </Paper>
  );
}

type DetailRowProps = {
  label: string;
  value: string;
  progress: number;
};

function DetailRow({ label, value, progress }: DetailRowProps) {
  return (
    <div>
      <Group justify="space-between" mb={6}>
        <Text fw={600}>{label}</Text>
        <RollingNumber value={value} className="detail-value" />
      </Group>
      <Progress value={progress} radius="xl" color="blue" size="md" />
    </div>
  );
}
