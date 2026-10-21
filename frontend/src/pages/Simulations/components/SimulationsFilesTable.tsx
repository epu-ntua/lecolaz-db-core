import { Link } from 'react-router-dom';
import { Download } from 'lucide-react';
import { getDatasetDownloadUrl } from '@/api/datasets';
import { Badge } from '@/components/ui/badge';
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
import type { SimulationFileDto } from '@/types/api/simulations';

export function SimulationsFilesTable({
  files,
  bims,
  loading,
}: {
  files: SimulationFileDto[];
  bims: BimFileDto[];
  loading: boolean;
}) {
  const bimNames = new Map(bims.map((bim) => [bim.id, bim.filename]));
  if (loading)
    return (
      <div className="rounded-xl border bg-card p-6 text-sm text-muted-foreground">
        Loading simulation datasets…
      </div>
    );
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <div className="overflow-x-auto">
        <Table className="min-w-[820px]">
          <TableHeader className="bg-muted/50">
            <TableRow className="hover:bg-transparent">
              <TableHead>Filename</TableHead>
              <TableHead>Associated BIM</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Uploaded</TableHead>
              <TableHead>Variables</TableHead>
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
                    <Link to={`/data/simulations/${file.id}`} title={file.filename}>
                      {file.filename}
                    </Link>
                  </Button>
                </TableCell>
                <TableCell
                  className="max-w-xs truncate text-muted-foreground"
                  title={
                    file.bim_dataset_id ? bimNames.get(file.bim_dataset_id) : undefined
                  }
                >
                  {file.bim_dataset_id
                    ? (bimNames.get(file.bim_dataset_id) ?? 'Linked BIM')
                    : '—'}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={
                      file.status === 'failed'
                        ? 'destructive'
                        : file.status === 'processed'
                          ? 'default'
                          : 'secondary'
                    }
                    className="capitalize"
                  >
                    {file.status ?? 'Unknown'}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {file.created_at ? new Date(file.created_at).toLocaleString() : '—'}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {typeof file.metadata?.variable_count === 'number'
                    ? file.metadata.variable_count
                    : '—'}
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
                  No simulation datasets available.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
