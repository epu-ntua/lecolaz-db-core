import { useMemo } from 'react';
import { LoadingState, ErrorNotice } from '@/components/layout/Feedback';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useSimulationTimeseries } from '@/hooks/useSimulationTimeseries';
import type { SimulationVariableDto } from '@/types/api/simulations';
import { CartesianGrid, Label, Line, LineChart, XAxis, YAxis } from 'recharts';

const chartConfig = {
  value: {
    label: 'Value',
    color: 'hsl(var(--chart-1))',
  },
} satisfies ChartConfig;

function getYAxisTitle(variable: SimulationVariableDto) {
  return variable.unit ?? 'Value';
}

export function SimulationVariableChartDialog({
  simulationId,
  variable,
  onClose,
}: {
  simulationId: string;
  variable: SimulationVariableDto;
  onClose: () => void;
}) {
  const { points, loading, error } = useSimulationTimeseries(
    simulationId,
    variable.id,
    true,
  );
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
    value: point.value,
    axisLabel: point.timestamp
      ? new Date(point.timestamp).toLocaleString(undefined, {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      : `Point ${index + 1}`,
    timestampLabel: point.timestamp
      ? new Date(point.timestamp).toLocaleString()
      : `Point ${index + 1}`,
  }));

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex max-h-[90vh] w-[calc(100%-2rem)] max-w-6xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4 text-left">
          <DialogTitle className="pr-4 text-lg">{variable.variable_name}</DialogTitle>
          <DialogDescription>
            Full timeseries
            {variable.unit ? ` in ${variable.unit}` : ''} for the selected simulation
            variable
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 overflow-y-auto px-6 py-5">
          {loading ? (
            <LoadingState label="Loading time-series values…" />
          ) : error ? (
            <ErrorNotice message={error} />
          ) : points.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              No timeseries values found
            </div>
          ) : (
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
                        {item.label !== 'Data points' && variable.unit}
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
                    dataKey="axisLabel"
                    tickLine={false}
                    axisLine={false}
                    minTickGap={64}
                  >
                    <Label
                      value="Timestamp"
                      position="insideBottom"
                      offset={-8}
                      className="fill-muted-foreground"
                    />
                  </XAxis>
                  <YAxis tickLine={false} axisLine={false} width={72}>
                    <Label
                      value={getYAxisTitle(variable)}
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
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ChartContainer>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
