import { useMemo } from 'react';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import { CartesianGrid, Label, Line, LineChart, XAxis, YAxis } from 'recharts';

const chartConfig = {
  value: {
    label: 'Value',
    color: 'hsl(var(--chart-1))',
  },
} satisfies ChartConfig;

type TimeseriesPoint = { id: string; timestamp: string | null; value: number | null };

export function TimeseriesChart({
  points,
  unit,
  timeScale = false,
}: {
  points: TimeseriesPoint[];
  unit?: string | null;
  timeScale?: boolean;
}) {
  const summary = useMemo(() => {
    const values = points
      .map((point) => point.value)
      .filter(
        (value): value is number => typeof value === 'number' && Number.isFinite(value),
      );
    if (!values.length) return null;
    return {
      min: values.reduce((a, b) => Math.min(a, b), Infinity),
      max: values.reduce((a, b) => Math.max(a, b), -Infinity),
      average: values.reduce((a, b) => a + b, 0) / values.length,
    };
  }, [points]);
  const chartData = points.map((point, index) => ({
    id: point.id,
    timestamp: point.timestamp ? new Date(point.timestamp).getTime() : index,
    value: point.value,
    axisLabel: point.timestamp
      ? new Date(point.timestamp).toLocaleString(undefined, {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          timeZone: timeScale ? 'UTC' : undefined,
        })
      : `Point ${index + 1}`,
    timestampLabel: point.timestamp
      ? new Date(point.timestamp).toLocaleString(undefined, {
          timeZone: timeScale ? 'UTC' : undefined,
          timeZoneName: timeScale ? 'short' : undefined,
        })
      : `Point ${index + 1}`,
  }));

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: 'Data points', value: points.length.toLocaleString() },
          {
            label: 'Minimum',
            value:
              summary?.min.toLocaleString(undefined, {
                maximumFractionDigits: 2,
              }) ?? '—',
          },
          {
            label: 'Maximum',
            value:
              summary?.max.toLocaleString(undefined, {
                maximumFractionDigits: 2,
              }) ?? '—',
          },
          {
            label: 'Average',
            value:
              summary?.average.toLocaleString(undefined, {
                maximumFractionDigits: 2,
              }) ?? '—',
          },
        ].map((item) => (
          <div key={item.label} className="rounded-lg border bg-muted/40 p-3">
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="mt-2 text-lg font-semibold tabular-nums">
              {item.value}
              <span className="ml-1 text-xs font-normal text-muted-foreground">
                {item.label !== 'Data points' && unit}
              </span>
            </p>
          </div>
        ))}
      </div>
      <ChartContainer
        config={chartConfig}
        className="aspect-auto h-[300px] w-full sm:h-[420px]"
      >
        <LineChart
          accessibilityLayer
          data={chartData}
          margin={{ left: 0, right: 12, top: 16, bottom: 24 }}
        >
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey={timeScale ? 'timestamp' : 'axisLabel'}
            type={timeScale ? 'number' : 'category'}
            domain={timeScale ? ['dataMin', 'dataMax'] : undefined}
            tickFormatter={
              timeScale
                ? (value: number) =>
                    new Date(value).toLocaleString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      timeZone: 'UTC',
                    })
                : undefined
            }
            tickLine={false}
            axisLine={false}
            minTickGap={64}
          >
            <Label
              value={timeScale ? 'Timestamp (UTC)' : 'Timestamp'}
              position="insideBottom"
              offset={-8}
              className="fill-muted-foreground"
            />
          </XAxis>
          <YAxis tickLine={false} axisLine={false} width={72}>
            <Label
              value={unit ?? 'Value'}
              angle={-90}
              position="insideLeft"
              className="fill-muted-foreground"
              style={{ textAnchor: 'middle' }}
            />
          </YAxis>
          <ChartTooltip
            cursor={false}
            content={
              <ChartTooltipContent
                labelFormatter={(_, payload) =>
                  payload?.[0]?.payload?.timestampLabel ?? ''
                }
              />
            }
          />
          <Line
            type="linear"
            dataKey="value"
            stroke="var(--color-value)"
            strokeWidth={2}
            dot={timeScale && points.length === 1 ? { r: 3 } : false}
            isAnimationActive={false}
          />
        </LineChart>
      </ChartContainer>
    </div>
  );
}
