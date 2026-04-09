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
  return variable.unit ? `${variable.variable_name} (${variable.unit})` : variable.variable_name;
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
  const chartData = points.map((point, index) => ({
    id: point.id,
    value: point.value,
    timestampLabel: point.timestamp
      ? new Date(point.timestamp).toLocaleString()
      : `Point ${index + 1}`,
  }));

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex max-h-[90vh] w-full max-w-7xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4 text-left">
          <DialogTitle className="text-xl">{variable.variable_name}</DialogTitle>
          <DialogDescription>
            Full timeseries
            {variable.unit ? ` in ${variable.unit}` : ''} for the selected simulation variable
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 overflow-y-auto px-6 py-5">
          {loading ? (
            <div className="text-sm text-muted-foreground">Loading timeseries...</div>
          ) : error ? (
            <div className="text-sm text-destructive">{error}</div>
          ) : points.length === 0 ? (
            <div className="text-sm text-muted-foreground">No timeseries values found</div>
          ) : (
            <div className="rounded-md border border-border bg-card p-4">
              <ChartContainer config={chartConfig} className="h-[420px] w-full">
                <LineChart
                  accessibilityLayer
                  data={chartData}
                  margin={{ left: 24, right: 24, top: 16, bottom: 24 }}
                >
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="timestampLabel"
                    tickLine={false}
                    axisLine={false}
                    minTickGap={64}
                    tickFormatter={(value: string) => value.slice(0, 10)}
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
                    type="monotone"
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
