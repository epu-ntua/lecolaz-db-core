// NOTE:
// This component owns both data fetching and rendering for file metadata.
// If data logic (pagination, filtering, caching) grows,
// extract a `useFiles` hook.
// If rendering becomes complex (actions, expandable rows),
// extract subcomponents for clarity.

import { useState } from 'react';
import type { FileDto } from '@/types/api/files';
import { SimulationDetailsModal } from '@/pages/Simulations/components/SimulationDetailsModal';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export function FilesTable({
  files,
  loading,
}: {
  files: FileDto[];
  loading: boolean;
}) {
  const [selectedSimulation, setSelectedSimulation] = useState<FileDto | null>(null);

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading metadata...</div>;
  }

  return (
    <>
      <div className="border border-border rounded-lg bg-card">
        <div className="max-h-[65vh] overflow-auto">
          <Table className="min-w-[1100px] text-sm text-foreground">
            <TableHeader className="border-b border-border bg-muted">
              <TableRow className="text-left hover:bg-transparent">
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">Dataset ID</TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">Type</TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">Subtype</TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">Filename</TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">Status</TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">Content type</TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">Size</TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">Uploaded</TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">Object key</TableHead>
                <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">Metadata</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {files.map((f) => (
                <TableRow key={f.id} className="align-top">
                  <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground">{f.id}</TableCell>
                  <TableCell className="px-3 py-2 text-muted-foreground capitalize">{f.type}</TableCell>
                  <TableCell className="px-3 py-2 text-muted-foreground">{f.subtype ?? '--'}</TableCell>
                  <TableCell className="px-3 py-2">
                    {f.type === 'simulation' ? (
                      <button
                        type="button"
                        className="text-primary underline underline-offset-4"
                        onClick={() => setSelectedSimulation(f)}
                      >
                        {f.filename}
                      </button>
                    ) : (
                      f.filename
                    )}
                  </TableCell>

                  <TableCell className="px-3 py-2">
                    <span className="inline-flex rounded-full bg-muted px-2 py-1 text-xs font-medium capitalize text-foreground">
                      {f.status}
                    </span>
                  </TableCell>

                  <TableCell className="px-3 py-2 text-muted-foreground">{f.content_type ?? '--'}</TableCell>

                  <TableCell className="px-3 py-2 text-muted-foreground">
                    {f.size_bytes ? `${Math.round(f.size_bytes / 1024)} KB` : '--'}
                  </TableCell>

                  <TableCell className="px-3 py-2 text-muted-foreground">
                    {f.created_at ? new Date(f.created_at).toLocaleString() : '--'}
                  </TableCell>

                  <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground">
                    {f.object_key}
                  </TableCell>

                  <TableCell className="px-3 py-2">
                    {f.metadata ? (
                      <pre className="text-xs bg-muted rounded p-2 max-w-xs overflow-x-auto">
                        {JSON.stringify(f.metadata, null, 2)}
                      </pre>
                    ) : (
                      <span className="text-muted-foreground/60">--</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}

              {files.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10} className="px-4 py-6 text-center text-muted-foreground">
                    No metadata entries
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
      {selectedSimulation && (
        <SimulationDetailsModal
          file={{
            id: selectedSimulation.id,
            dataset_id: selectedSimulation.id,
            filename: selectedSimulation.filename,
            format: selectedSimulation.subtype ?? '--',
            status: selectedSimulation.status,
            created_at: selectedSimulation.created_at,
            metadata: selectedSimulation.metadata,
          }}
          onClose={() => setSelectedSimulation(null)}
        />
      )}
    </>
  );
}
