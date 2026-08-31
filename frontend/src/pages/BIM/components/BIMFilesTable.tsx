import { useState } from 'react';
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
import { BIMDetailsDialog } from '@/pages/BIM/components/BIMDetailsDialog';
import type { BimFileDto } from '@/types/api/bim';

function getStatusVariant(status: string | null) {
  if (status === 'failed') {
    return 'destructive' as const;
  }

  if (status === 'processed') {
    return 'default' as const;
  }

  return 'secondary' as const;
}

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
  const [selectedFile, setSelectedFile] = useState<BimFileDto | null>(null);
  const activeSelectedFile = selectedFile
    ? (files.find((file) => file.id === selectedFile.id) ?? selectedFile)
    : null;

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading BIM metadata...</div>;
  }

  return (
    <>
      <div className="rounded-lg border border-border bg-card">
        <div className="max-h-[65vh] overflow-auto">
          <Table className="min-w-[1120px] text-sm text-foreground">
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
                    <Badge variant={getStatusVariant(f.status)} className="capitalize">
                      {f.status ?? '--'}
                    </Badge>
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
      {activeSelectedFile && (
        <BIMDetailsDialog
          file={activeSelectedFile}
          onClose={() => setSelectedFile(null)}
        />
      )}
    </>
  );
}
