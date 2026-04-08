// NOTE:
// This component owns both data fetching and rendering for BIM files metadata.
// If data logic (pagination, filtering, caching) grows,
// extract a `useBIMfiles` hook.
// If rendering becomes complex (actions, expandable rows),
// extract subcomponents for clarity.

import { useNavigate } from 'react-router-dom';
import type { BimFileDto } from '@/types/api/bim';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

function renderStatsSummary(stats: BimFileDto['stats']) {
  if (!stats) {
    return <span className="text-muted-foreground/60">--</span>;
  }

  const storeys = typeof stats.storeys === 'number' ? stats.storeys : null;
  const spaces = typeof stats.spaces === 'number' ? stats.spaces : null;
  const entities = typeof stats.entities === 'number' ? stats.entities : null;

  if (storeys === null && spaces === null && entities === null) {
    return <span className="text-muted-foreground/60">--</span>;
  }

  return (
    <div className="space-y-1 text-xs">
      {storeys !== null && <div className="text-muted-foreground">Storeys: {storeys}</div>}
      {spaces !== null && <div className="text-muted-foreground">Spaces: {spaces}</div>}
      {entities !== null && <div className="text-muted-foreground">Entities: {entities}</div>}
    </div>
  );
}

export function BIMFilesTable({
  files,
  loading,
}: {
  files: BimFileDto[];
  loading: boolean;
}) {
  const navigate = useNavigate();

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading BIM metadata...</div>;
  }

  return (
    <div className="border border-border rounded-lg bg-card">
      <div className="max-h-[65vh] overflow-auto">
        <Table className="min-w-[980px] text-sm text-foreground">
          <TableHeader className="border-b border-border bg-muted">
            <TableRow className="text-left hover:bg-transparent">
              <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                BIM ID
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
                Schema
              </TableHead>
              <TableHead className="sticky top-0 z-10 bg-muted px-3 py-2 font-medium text-muted-foreground">
                Stats
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
                  <span
                    className="text-primary underline cursor-pointer"
                    onClick={() => navigate(`/bim/${f.id}`)}
                  >
                    {f.filename ?? '--'}
                  </span>
                </TableCell>

                <TableCell className="px-3 py-2 text-muted-foreground">
                  {f.format ?? '--'}
                </TableCell>

                <TableCell className="px-3 py-2">
                  <span className="inline-flex rounded-full bg-muted px-2 py-1 text-xs font-medium capitalize text-foreground">
                    {f.status ?? '--'}
                  </span>
                </TableCell>

                <TableCell className="px-3 py-2 text-muted-foreground">
                  {f.schema ?? '--'}
                </TableCell>

                <TableCell className="px-3 py-2">
                  {renderStatsSummary(f.stats)}
                </TableCell>
              </TableRow>
            ))}

            {files.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="px-4 py-6 text-center text-muted-foreground"
                >
                  No BIM metadata entries
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
