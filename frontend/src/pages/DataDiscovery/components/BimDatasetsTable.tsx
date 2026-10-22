import { Link } from 'react-router-dom';
import { Download } from 'lucide-react';
import { getDatasetDownloadUrl } from '@/api/datasets';
import { StatusBadge } from '@/components/ui/status-badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { BimFileDto } from '@/types/api/bim';

export function BimDatasetsTable({
  files,
  loading,
}: {
  files: BimFileDto[];
  loading: boolean;
}) {
  if (loading)
    return (
      <div className="rounded-xl border bg-card p-6 text-sm text-muted-foreground">
        Loading BIM datasets…
      </div>
    );
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <div className="overflow-x-auto">
        <Table className="min-w-[820px]">
          <TableHeader className="bg-muted/50">
            <TableRow className="hover:bg-transparent">
              <TableHead>Filename</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>IFC schema</TableHead>
              <TableHead>Uploaded</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {files.map((file) => (
              <TableRow key={file.id} className="h-14 hover:bg-muted/30">
                <TableCell className="max-w-xs">
                  <Button
                    asChild
                    variant="link"
                    className="h-auto max-w-full justify-start truncate p-0"
                  >
                    <Link to={`/buildings/${file.id}`} title={file.filename}>
                      {file.filename}
                    </Link>
                  </Button>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {file.category === 'archetype'
                    ? 'Building Archetype'
                    : 'Living Lab / Pilot'}
                </TableCell>
                <TableCell>
                  <StatusBadge status={file.status} />
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {file.schema ?? '—'}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {file.created_at ? new Date(file.created_at).toLocaleString() : '—'}
                </TableCell>
                <TableCell className="text-right">
                  <Button asChild variant="ghost" size="icon">
                    <a
                      href={getDatasetDownloadUrl(file.dataset_id)}
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
                <TableCell colSpan={6} className="h-28 text-center text-muted-foreground">
                  No BIM datasets to display. Add a building or adjust your filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
