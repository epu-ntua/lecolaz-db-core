import { useState } from 'react';
import { Button } from '@/components/ui/button';
import type {
  SimulationFileDto,
  SimulationProcessingSummary,
} from '@/types/api/simulations';
import { SimulationDetailsModal } from '@/pages/Simulations/components/SimulationDetailsModal';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

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

function renderMetadataSummary(metadata: Record<string, unknown> | null) {
  if (!metadata) {
    return <span className="text-muted-foreground/60">--</span>;
  }

  const processingError = getProcessingError(metadata);
  const processingSummary = getProcessingSummary(metadata);

  const variableCount =
    typeof processingSummary?.metadata.variable_count === 'number'
      ? processingSummary.metadata.variable_count
      : null;
  const timestepCount =
    typeof processingSummary?.metadata.timestep_count === 'number'
      ? processingSummary.metadata.timestep_count
      : null;
  const skippedValues =
    typeof processingSummary?.metadata.skipped_values === 'number'
      ? processingSummary.metadata.skipped_values
      : null;

  if (
    !processingError &&
    variableCount === null &&
    timestepCount === null &&
    skippedValues === null
  ) {
    return <span className="text-muted-foreground/60">--</span>;
  }

  return (
    <div className="space-y-1 text-xs">
      {variableCount !== null && (
        <div className="text-muted-foreground">Variables: {variableCount}</div>
      )}
      {timestepCount !== null && (
        <div className="text-muted-foreground">Timesteps: {timestepCount}</div>
      )}
      {skippedValues !== null && (
        <div className="text-muted-foreground">Skipped values: {skippedValues}</div>
      )}
      {processingError && (
        <div className="text-destructive break-words">Error: {processingError}</div>
      )}
    </div>
  );
}

export function SimulationsFilesTable({
  files,
  loading,
}: {
  files: SimulationFileDto[];
  loading: boolean;
}) {
  const [selectedFile, setSelectedFile] = useState<SimulationFileDto | null>(null);
  const activeSelectedFile = selectedFile
    ? (files.find((file) => file.id === selectedFile.id) ?? null)
    : null;

  if (loading) {
    return (
      <div className="text-sm text-muted-foreground">Loading simulation metadata...</div>
    );
  }

  return (
    <>
      <div className="border border-border rounded-lg bg-card">
        <div className="max-h-[65vh] overflow-auto">
          <Table className="min-w-[900px] text-sm text-foreground">
            <TableHeader className="border-b border-border bg-muted">
              <TableRow className="text-left hover:bg-transparent">
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                  Simulation ID
                </TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                  Dataset ID
                </TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                  Filename
                </TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                  Format
                </TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                  Status
                </TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                  Metadata
                </TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {files.map((f, index) => (
                <TableRow key={f.id ?? `${index}`} className="align-top">
                  <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground">
                    {f.id}
                  </TableCell>

                  <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground">
                    {f.dataset_id}
                  </TableCell>

                  <TableCell className="px-3 py-2">
                    <Button
                      type="button"
                      variant="link"
                      className="h-auto p-0"
                      onClick={() => setSelectedFile(f)}
                    >
                      {f.filename ?? '--'}
                    </Button>
                  </TableCell>

                  <TableCell className="px-3 py-2 text-muted-foreground">
                    {f.format ?? '--'}
                  </TableCell>

                  <TableCell className="px-3 py-2">
                    <span className="inline-flex rounded-full bg-muted px-2 py-1 text-xs font-medium capitalize text-foreground">
                      {f.status ?? '--'}
                    </span>
                  </TableCell>

                  <TableCell className="px-3 py-2">
                    {renderMetadataSummary(f.metadata)}
                  </TableCell>
                </TableRow>
              ))}

              {files.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="px-4 py-6 text-center text-muted-foreground"
                  >
                    No simulation metadata entries
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
      {activeSelectedFile && (
        <SimulationDetailsModal
          file={activeSelectedFile}
          onClose={() => setSelectedFile(null)}
        />
      )}
    </>
  );
}
