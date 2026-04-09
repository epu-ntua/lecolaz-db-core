import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { getBimFile, listBimSpaces } from '@/api/bim_files';
import { getDatasetDownloadUrl } from '@/api/datasets';
import { getSimulationFileByDataset } from '@/api/simulation_files';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useSimulationVariables } from '@/hooks/useSimulationVariables';
import { cn } from '@/lib/utils';
import { BIMDetailsDialog } from '@/pages/BIM/components/BIMDetailsDialog';
import { SimulationVariableChartDialog } from '@/pages/Simulations/components/SimulationVariableChartDialog';
import type { BimFileDto, BimSpaceDto } from '@/types/api/bim';
import type {
  SimulationFileDto,
  SimulationProcessingSummary,
  SimulationVariableDto,
} from '@/types/api/simulations';

function getProcessingSummary(
  extra: Record<string, unknown> | null,
): SimulationProcessingSummary | null {
  if (!extra) {
    return null;
  }

  return {
    metadata: {
      variable_count:
        typeof extra.variable_count === 'number' ? extra.variable_count : null,
      timestep_count:
        typeof extra.timestep_count === 'number' ? extra.timestep_count : null,
      skipped_values:
        typeof extra.skipped_values === 'number' ? extra.skipped_values : null,
      processed_at: typeof extra.processed_at === 'string' ? extra.processed_at : null,
    },
  };
}

function getProcessingError(metadata: Record<string, unknown> | null) {
  return typeof metadata?.processing_error === 'string'
    ? metadata.processing_error
    : null;
}

function getStatusVariant(status: string | null) {
  if (status === 'failed') {
    return 'destructive' as const;
  }

  if (status === 'processed') {
    return 'default' as const;
  }

  return 'secondary' as const;
}

export function SimulationDetailsModal({
  file,
  onClose,
}: {
  file: SimulationFileDto;
  onClose: () => void;
}) {
  const [resolvedFile, setResolvedFile] = useState<SimulationFileDto>(file);
  const [selectedVariable, setSelectedVariable] = useState<SimulationVariableDto | null>(
    null,
  );
  const [linkedBim, setLinkedBim] = useState<BimFileDto | null>(null);
  const [linkedBimSpaces, setLinkedBimSpaces] = useState<BimSpaceDto[]>([]);
  const [showLinkedBimDialog, setShowLinkedBimDialog] = useState(false);

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
  } = useSimulationVariables(resolvedFile.id);
  useEffect(() => {
    if (!resolvedFile.bim_dataset_id) {
      setLinkedBim(null);
      setLinkedBimSpaces([]);
      return;
    }

    let cancelled = false;

    getBimFile(resolvedFile.bim_dataset_id)
      .then((bim) => {
        if (cancelled) {
          return;
        }
        setLinkedBim(bim);
        return listBimSpaces(bim.id).then((spaces) => {
          if (!cancelled) {
            setLinkedBimSpaces(spaces);
          }
        });
      })
      .catch(() => {
        if (!cancelled) {
          setLinkedBim(null);
          setLinkedBimSpaces([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [resolvedFile.bim_dataset_id]);

  const spaceLabelById = new Map(
    linkedBimSpaces.map((space) => [
      space.id,
      space.name || space.global_id,
    ] as const),
  );

  return (
    <>
      <Dialog open onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="flex max-h-[90vh] w-full max-w-5xl flex-col gap-0 overflow-hidden p-0">
          <DialogHeader className="border-b border-border px-6 py-4 text-left">
            <div className="flex items-start justify-between gap-4 pr-8">
              <div className="space-y-2">
                <DialogTitle className="text-xl">{resolvedFile.filename}</DialogTitle>
                <DialogDescription>Parsed simulation output preview</DialogDescription>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={getStatusVariant(resolvedFile.status)} className="capitalize">
                  {resolvedFile.status ?? '--'}
                </Badge>
                <Button asChild variant="outline" size="sm">
                  <a href={getDatasetDownloadUrl(resolvedFile.dataset_id)} download>
                    <Download />
                    Download
                  </a>
                </Button>
              </div>
            </div>
          </DialogHeader>

          <div className="space-y-6 overflow-y-auto px-6 py-5">
            <section className="grid gap-4 md:grid-cols-4">
              <Card className="shadow-none">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                    Status
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Badge
                    variant={getStatusVariant(resolvedFile.status)}
                    className="capitalize"
                  >
                    {resolvedFile.status ?? '--'}
                  </Badge>
                </CardContent>
              </Card>
              <Card className="shadow-none">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                    Variables
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-lg font-semibold">
                  {summary?.metadata.variable_count ?? '--'}
                </CardContent>
              </Card>
              <Card className="shadow-none">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                    Timesteps
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-lg font-semibold">
                  {summary?.metadata.timestep_count ?? '--'}
                </CardContent>
              </Card>
              <Card className="shadow-none">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
                    Skipped values
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-lg font-semibold">
                  {summary?.metadata.skipped_values ?? '--'}
                </CardContent>
              </Card>
            </section>

            {summary?.metadata.processed_at && (
              <section className="text-sm text-muted-foreground">
                Processed at {new Date(summary.metadata.processed_at).toLocaleString()}
              </section>
            )}

            {processingError && (
              <section className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                {processingError}
              </section>
            )}

            {linkedBim && (
              <section className="rounded-lg border border-border bg-muted/30 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="text-sm font-medium text-foreground">
                      Connected BIM file
                    </div>
                    <div className="text-sm text-muted-foreground">
                      This simulation is linked to <span className="font-medium text-foreground">{linkedBim.filename}</span>.
                    </div>
                  </div>
                  <Button size="sm" onClick={() => setShowLinkedBimDialog(true)}>
                    Open BIM
                  </Button>
                </div>
              </section>
            )}

            <Card className="shadow-none">
              <CardHeader className="pb-4">
                <CardTitle className="text-sm font-medium">Simulation Variables</CardTitle>
                <DialogDescription className="text-left">
                  Select a variable to open its full timeseries chart.
                </DialogDescription>
              </CardHeader>
              <CardContent>
                {variablesLoading ? (
                  <div className="text-sm text-muted-foreground">Loading variables...</div>
                ) : variablesError ? (
                  <div className="text-sm text-destructive">{variablesError}</div>
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
                            Space / Key
                          </TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {variables.map((variable) => (
                          <TableRow
                            key={variable.id}
                            className={cn(
                              'align-top',
                              selectedVariable?.id === variable.id && 'bg-muted/60',
                            )}
                          >
                            <TableCell className="px-3 py-2">
                              <Button
                                type="button"
                                variant="ghost"
                                className="h-auto w-full justify-start px-0 py-0 font-medium"
                                onClick={() => setSelectedVariable(variable)}
                              >
                                {variable.variable_name}
                              </Button>
                            </TableCell>
                            <TableCell className="px-3 py-2 text-muted-foreground">
                              {variable.unit ?? '--'}
                            </TableCell>
                            <TableCell className="px-3 py-2 text-muted-foreground">
                              {variable.frequency ?? '--'}
                            </TableCell>
                            <TableCell className="px-3 py-2 text-muted-foreground">
                              {variable.bim_space_id
                                ? (spaceLabelById.get(variable.bim_space_id) ?? variable.key ?? '--')
                                : (variable.key ?? '--')}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </DialogContent>
      </Dialog>
      {selectedVariable && (
        <SimulationVariableChartDialog
          simulationId={resolvedFile.id}
          variable={selectedVariable}
          onClose={() => setSelectedVariable(null)}
        />
      )}
      {linkedBim && showLinkedBimDialog && (
        <BIMDetailsDialog
          file={linkedBim}
          onClose={() => setShowLinkedBimDialog(false)}
        />
      )}
    </>
  );
}
