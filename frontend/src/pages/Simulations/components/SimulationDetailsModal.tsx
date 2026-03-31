import { useEffect, useState } from 'react';
import { getSimulationFileByDataset } from '@/api/simulation_files';
import { useSimulationTimeseries } from '@/hooks/useSimulationTimeseries';
import { useSimulationVariables } from '@/hooks/useSimulationVariables';
import type {
  SimulationFileDto,
  SimulationProcessingSummary,
} from '@/types/api/simulations';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

function getProcessingSummary(extra: Record<string, unknown> | null): SimulationProcessingSummary | null {
  if (!extra) {
    return null;
  }

  return {
    metadata: {
      variable_count: typeof extra.variable_count === 'number' ? extra.variable_count : null,
      timestep_count: typeof extra.timestep_count === 'number' ? extra.timestep_count : null,
      skipped_values: typeof extra.skipped_values === 'number' ? extra.skipped_values : null,
      processed_at: typeof extra.processed_at === 'string' ? extra.processed_at : null,
    },
  };
}

function getProcessingError(metadata: Record<string, unknown> | null) {
  return typeof metadata?.processing_error === 'string' ? metadata.processing_error : null;
}

export function SimulationDetailsModal({
  file,
  onClose,
}: {
  file: SimulationFileDto;
  onClose: () => void;
}) {
  const [resolvedFile, setResolvedFile] = useState<SimulationFileDto>(file);
  const [selectedVariableId, setSelectedVariableId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setResolvedFile(file);

    getSimulationFileByDataset(file.dataset_id)
      .then((nextFile) => {
        if (!cancelled) {
          setResolvedFile(nextFile);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setResolvedFile(file);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [file.dataset_id, file]);

  const summary = getProcessingSummary(resolvedFile.metadata);
  const processingError = getProcessingError(resolvedFile.metadata);
  const {
    variables,
    loading: variablesLoading,
    error: variablesError,
  } = useSimulationVariables(file.dataset_id);
  const {
    points,
    loading: pointsLoading,
    error: pointsError,
  } = useSimulationTimeseries(file.dataset_id, selectedVariableId, !!selectedVariableId);

  useEffect(() => {
    if (variables.length === 0) {
      setSelectedVariableId(null);
      return;
    }

    const hasSelected = variables.some((variable) => variable.id === selectedVariableId);
    if (!hasSelected) {
      setSelectedVariableId(variables[0].id);
    }
  }, [selectedVariableId, variables]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <div className="max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
        <div className="flex items-start justify-between border-b border-border px-6 py-4">
          <div>
            <h2 className="text-xl font-semibold text-foreground">{resolvedFile.filename}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Parsed simulation output preview
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>

        <div className="max-h-[calc(90vh-81px)] space-y-6 overflow-y-auto px-6 py-5">
          <section className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-border bg-muted/40 p-4">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">Status</div>
              <div className="mt-2 text-lg font-semibold capitalize">{resolvedFile.status}</div>
            </div>
            <div className="rounded-lg border border-border bg-muted/40 p-4">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">Variables</div>
              <div className="mt-2 text-lg font-semibold">
                {summary?.metadata.variable_count ?? '--'}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-muted/40 p-4">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">Timesteps</div>
              <div className="mt-2 text-lg font-semibold">
                {summary?.metadata.timestep_count ?? '--'}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-muted/40 p-4">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">Skipped values</div>
              <div className="mt-2 text-lg font-semibold">
                {summary?.metadata.skipped_values ?? '--'}
              </div>
            </div>
          </section>

          {summary?.metadata.processed_at && (
            <section>
              <div className="text-sm text-muted-foreground">
                Processed at {new Date(summary.metadata.processed_at).toLocaleString()}
              </div>
            </section>
          )}

          {processingError && (
            <section className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {processingError}
            </section>
          )}

          <section className="rounded-lg border border-border bg-muted/30 p-4">
            <div className="mb-3 text-sm font-medium text-foreground">Simulation Variables</div>
            {variablesLoading ? (
              <div className="text-sm text-muted-foreground">Loading variables...</div>
            ) : variablesError ? (
              <div className="text-sm text-red-600">{variablesError}</div>
            ) : variables.length === 0 ? (
              <div className="text-sm text-muted-foreground">No variables found</div>
            ) : (
              <div className="max-h-72 overflow-auto rounded-md border border-border bg-card">
                <Table className="min-w-[720px] text-sm text-foreground">
                  <TableHeader className="border-b border-border bg-muted">
                    <TableRow className="text-left hover:bg-transparent">
                      <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                        Variable
                      </TableHead>
                      <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                        Unit
                      </TableHead>
                      <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                        Frequency
                      </TableHead>
                      <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                        Key
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {variables.map((variable) => (
                      <TableRow
                        key={variable.id}
                        className={`align-top ${selectedVariableId === variable.id ? 'bg-muted/60' : ''}`}
                      >
                        <TableCell className="px-3 py-2">
                          <button
                            type="button"
                            className="w-full text-left font-medium"
                            onClick={() => setSelectedVariableId(variable.id)}
                          >
                            {variable.variable_name}
                          </button>
                        </TableCell>
                        <TableCell className="px-3 py-2 text-muted-foreground">
                          {variable.unit ?? '--'}
                        </TableCell>
                        <TableCell className="px-3 py-2 text-muted-foreground">
                          {variable.frequency ?? '--'}
                        </TableCell>
                        <TableCell className="px-3 py-2 text-muted-foreground">
                          {variable.key ?? '--'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </section>

          <section className="rounded-lg border border-border bg-muted/30 p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="text-sm font-medium text-foreground">Variable Timeseries</div>
              {selectedVariableId && (
                <div className="text-xs text-muted-foreground">
                  Previewing up to 200 points for the selected variable
                </div>
              )}
            </div>
            {!selectedVariableId ? (
              <div className="text-sm text-muted-foreground">
                Select a variable to inspect its timeseries.
              </div>
            ) : pointsLoading ? (
              <div className="text-sm text-muted-foreground">Loading timeseries...</div>
            ) : pointsError ? (
              <div className="text-sm text-red-600">{pointsError}</div>
            ) : points.length === 0 ? (
              <div className="text-sm text-muted-foreground">No timeseries values found</div>
            ) : (
              <div className="max-h-72 overflow-auto rounded-md border border-border bg-card">
                <Table className="min-w-[560px] text-sm text-foreground">
                  <TableHeader className="border-b border-border bg-muted">
                    <TableRow className="text-left hover:bg-transparent">
                      <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                        Timestamp
                      </TableHead>
                      <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                        Value
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {points.map((point) => (
                      <TableRow key={point.id} className="align-top">
                        <TableCell className="px-3 py-2">
                          {point.timestamp ? new Date(point.timestamp).toLocaleString() : '--'}
                        </TableCell>
                        <TableCell className="px-3 py-2 text-muted-foreground">
                          {point.value}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
