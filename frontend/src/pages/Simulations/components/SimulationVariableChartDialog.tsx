import { LoadingState, ErrorNotice } from '@/components/layout/Feedback';
import { TimeseriesChart } from '@/components/charts/TimeseriesChart';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useSimulationTimeseries } from '@/hooks/useSimulationTimeseries';
import type { SimulationVariableDto } from '@/types/api/simulations';

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
            <TimeseriesChart points={points} unit={variable.unit} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
