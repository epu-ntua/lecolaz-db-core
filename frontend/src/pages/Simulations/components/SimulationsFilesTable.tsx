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
  const processingSummary = extra?.processing_summary;
  if (!processingSummary || typeof processingSummary !== 'object' || Array.isArray(processingSummary)) {
    return null;
  }

  const summary = processingSummary as Record<string, unknown>;
  const metadata =
    summary.metadata && typeof summary.metadata === 'object' && !Array.isArray(summary.metadata)
      ? (summary.metadata as SimulationProcessingSummary['metadata'])
      : { variable_count: null, timestep_count: null, processed_at: null };
  const variables = Array.isArray(summary.variables)
    ? (summary.variables as SimulationProcessingSummary['variables'])
    : [];
  const records = Array.isArray(summary.records)
    ? (summary.records as SimulationProcessingSummary['records'])
    : [];

  return { metadata, variables, records };
}

function getProcessingError(extra: Record<string, unknown> | null) {
  return typeof extra?.processing_error === 'string' ? extra.processing_error : null;
}

function renderExtraSummary(extra: Record<string, unknown> | null) {
  if (!extra) {
    return <span className="text-muted-foreground/60">--</span>;
  }

  const processingError = getProcessingError(extra);
  const processingSummary = getProcessingSummary(extra);

  const variableCount =
    typeof processingSummary?.metadata.variable_count === 'number'
      ? processingSummary.metadata.variable_count
      : null;
  const timestepCount =
    typeof processingSummary?.metadata.timestep_count === 'number'
      ? processingSummary.metadata.timestep_count
      : null;

  if (!processingError && variableCount === null && timestepCount === null) {
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
  const summary = getProcessingSummary(file.extra);
  const processingError = getProcessingError(file.extra);

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
          <section className="grid gap-4 md:grid-cols-3">
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

          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">Variables</h3>
              <span className="text-xs text-muted-foreground">
                {summary?.variables.length ?? 0} entries
              </span>
            </div>
            <div className="overflow-hidden rounded-lg border border-border">
              <Table className="text-sm text-foreground">
                <TableHeader className="bg-muted">
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="px-3 py-2">ID</TableHead>
                    <TableHead className="px-3 py-2">Variable</TableHead>
                    <TableHead className="px-3 py-2">Unit</TableHead>
                    <TableHead className="px-3 py-2">Frequency</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(summary?.variables ?? []).slice(0, 20).map((variable) => (
                    <TableRow key={variable.id}>
                      <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground">
                        {variable.id}
                      </TableCell>
                      <TableCell className="px-3 py-2">{variable.variable ?? '--'}</TableCell>
                      <TableCell className="px-3 py-2 text-muted-foreground">
                        {variable.unit ?? '--'}
                      </TableCell>
                      <TableCell className="px-3 py-2 text-muted-foreground">
                        {variable.frequency ?? '--'}
                      </TableCell>
                    </TableRow>
                  ))}
                  {(summary?.variables.length ?? 0) === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="px-3 py-4 text-center text-muted-foreground">
                        No processed variables available
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </section>

          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">Record Preview</h3>
              <span className="text-xs text-muted-foreground">
                {(summary?.records.length ?? 0)} rows
              </span>
            </div>
            <div className="overflow-hidden rounded-lg border border-border">
              <Table className="text-sm text-foreground">
                <TableHeader className="bg-muted">
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="px-3 py-2">Timestamp</TableHead>
                    <TableHead className="px-3 py-2">Variable</TableHead>
                    <TableHead className="px-3 py-2">Value</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(summary?.records ?? []).slice(0, 20).map((record, index) => (
                    <TableRow key={`${record.timestamp ?? 'no-time'}-${record.variable ?? 'no-var'}-${index}`}>
                      <TableCell className="px-3 py-2 text-muted-foreground">
                        {record.timestamp ?? '--'}
                      </TableCell>
                      <TableCell className="px-3 py-2">{record.variable ?? '--'}</TableCell>
                      <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground">
                        {typeof record.value === 'object'
                          ? JSON.stringify(record.value)
                          : String(record.value)}
                      </TableCell>
                    </TableRow>
                  ))}
                  {(summary?.records.length ?? 0) === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} className="px-3 py-4 text-center text-muted-foreground">
                        No processed records available
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
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
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">File ID</TableHead>
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Filename</TableHead>
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Format</TableHead>
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Schema</TableHead>
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Status</TableHead>
              <TableHead className="px-3 py-2 font-medium text-muted-foreground">Extra</TableHead>
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
                  {f.file_id}
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

                <TableCell className="px-3 py-2 text-muted-foreground">{f.schema ?? '--'}</TableCell>

                <TableCell className="px-3 py-2">
                  <span className="inline-flex rounded-full bg-muted px-2 py-1 text-xs font-medium capitalize text-foreground">
                    {f.status}
                  </span>
                </TableCell>

                <TableCell className="px-3 py-2">
                  {renderExtraSummary(f.extra)}
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
                <TableCell colSpan={8} className="px-4 py-6 text-center text-muted-foreground">
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
