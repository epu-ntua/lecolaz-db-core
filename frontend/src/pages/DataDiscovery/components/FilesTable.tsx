import { useState } from 'react';
import { Download } from 'lucide-react';
import { getDatasetDownloadUrl } from '@/api/datasets';
import { StatusBadge } from '@/components/ui/status-badge';
import { Button } from '@/components/ui/button';
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
import type { DatasetDto } from '@/types/api/datasets';

export function FilesTable({
  files,
  loading,
}: {
  files: DatasetDto[];
  loading: boolean;
}) {
  const [selected, setSelected] = useState<DatasetDto | null>(null);
  if (loading)
    return (
      <div className="rounded-xl border bg-card p-6 text-sm text-muted-foreground">
        Loading datasets…
      </div>
    );

  return (
    <>
      <div className="overflow-hidden rounded-xl border bg-card">
        <div className="overflow-x-auto">
          <Table className="min-w-[820px]">
            <TableHeader className="bg-muted/50">
              <TableRow className="hover:bg-transparent">
                <TableHead>Filename</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Uploaded</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {files.map((file) => (
                <TableRow key={file.id} className="h-14 hover:bg-muted/30">
                  <TableCell className="max-w-xs">
                    <Button
                      variant="link"
                      className="h-auto max-w-full justify-start truncate p-0"
                      title={file.filename}
                      onClick={() => setSelected(file)}
                    >
                      {file.filename}
                    </Button>
                  </TableCell>
                  <TableCell className="capitalize text-muted-foreground">
                    {file.type}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={file.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {file.size_bytes ? `${Math.round(file.size_bytes / 1024)} KB` : '—'}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {file.created_at ? new Date(file.created_at).toLocaleString() : '—'}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button asChild variant="ghost" size="icon">
                      <a
                        href={getDatasetDownloadUrl(file.id)}
                        download
                        aria-label={`Download ${file.filename}`}
                      >
                        <Download className="h-4 w-4" />
                      </a>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {files.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="h-28 text-center text-muted-foreground"
                  >
                    No datasets to display. Upload a file or adjust your filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
      {selected && (
        <Dialog open onOpenChange={(open) => !open && setSelected(null)}>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>{selected.filename}</DialogTitle>
              <DialogDescription>
                Dataset metadata and source information.
              </DialogDescription>
            </DialogHeader>
            <dl className="grid gap-4 rounded-xl border bg-muted/20 p-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground">Type</dt>
                <dd className="mt-1 capitalize">{selected.type}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Subtype</dt>
                <dd className="mt-1">{selected.subtype ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Content type</dt>
                <dd className="mt-1">{selected.content_type ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Source</dt>
                <dd className="mt-1">{selected.source ?? '—'}</dd>
              </div>
            </dl>
            {selected.metadata && (
              <pre className="max-h-64 overflow-auto rounded-xl bg-muted p-4 text-xs">
                {JSON.stringify(selected.metadata, null, 2)}
              </pre>
            )}
            <div className="flex justify-end">
              <Button asChild>
                <a href={getDatasetDownloadUrl(selected.id)} download>
                  <Download className="h-4 w-4" />
                  Download
                </a>
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
