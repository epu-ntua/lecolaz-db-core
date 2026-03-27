import { useEffect, useState } from 'react';
import { listSimulationFiles, processSimulationFile } from '@/api/simulation_files';
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

  if (!processingError && variableCount === null && timestepCount === null && skippedValues === null) {
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
        <div className="text-red-600 break-words">Error: {processingError}</div>
      )}
    </div>
  );
}

function SimulationDetailsModal({
  file,
  onClose,
}: {
  file: SimulationFileDto;
  onClose: () => void;
}) {
  const summary = getProcessingSummary(file.metadata);
  const processingError = getProcessingError(file.metadata);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <div className="max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
        <div className="flex items-start justify-between border-b border-border px-6 py-4">
          <div>
            <h2 className="text-xl font-semibold text-foreground">{file.filename}</h2>
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
              <div className="mt-2 text-lg font-semibold capitalize">{file.status}</div>
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

          <section className="rounded-lg border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
            Detailed variables and time-series are now stored in dedicated backend tables and are not returned by this endpoint.
          </section>
        </div>
      </div>
    </div>
  );
}

export function SimulationsFilesTable({ refreshKey }: { refreshKey: number }) {
  const [files, setFiles] = useState<SimulationFileDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<SimulationFileDto | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [processError, setProcessError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listSimulationFiles()
      .then(setFiles)
      .finally(() => setLoading(false));
  }, [refreshKey]);

  async function handleProcess(fileId: string) {
    try {
      setProcessingId(fileId);
      setProcessError(null);
      await processSimulationFile(fileId);
      const updatedFiles = await listSimulationFiles();
      setFiles(updatedFiles);
      setSelectedFile(updatedFiles.find((file) => file.id === fileId) ?? null);
    } catch {
      setProcessError('Processing failed');
    } finally {
      setProcessingId(null);
    }
  }

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading simulation metadata...</div>;
  }

  return (
    <>
      <div className="border border-border rounded-lg bg-card">
        <Table className="text-sm text-foreground">
          <TableHeader className="border-b border-border bg-muted">
            <TableRow className="text-left hover:bg-transparent">
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Simulation ID</TableHead>
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Dataset ID</TableHead>
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Filename</TableHead>
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Format</TableHead>
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Status</TableHead>
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Metadata</TableHead>
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Actions</TableHead>
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
                  <button
                    type="button"
                    className="text-primary underline underline-offset-4"
                    onClick={() => setSelectedFile(f)}
                  >
                    {f.filename ?? '--'}
                  </button>
                </TableCell>

                <TableCell className="px-3 py-2 text-muted-foreground">{f.format ?? '--'}</TableCell>

                <TableCell className="px-3 py-2">
                  <span className="inline-flex rounded-full bg-muted px-2 py-1 text-xs font-medium capitalize text-foreground">
                    {f.status ?? '--'}
                  </span>
                </TableCell>

                <TableCell className="px-3 py-2">
                  {renderMetadataSummary(f.metadata)}
                </TableCell>

                <TableCell className="px-3 py-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={processingId === f.id}
                    onClick={() => handleProcess(f.id)}
                  >
                    {processingId === f.id ? 'Processing...' : 'Process'}
                  </Button>
                </TableCell>
              </TableRow>
            ))}

            {files.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="px-4 py-6 text-center text-muted-foreground">
                  No simulation metadata entries
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        {processError && (
          <div className="border-t border-border px-4 py-3 text-sm text-red-600">
            {processError}
          </div>
        )}
      </div>
      {selectedFile && (
        <SimulationDetailsModal file={selectedFile} onClose={() => setSelectedFile(null)} />
      )}
    </>
  );
}
