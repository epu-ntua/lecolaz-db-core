// NOTE:
// This component owns both data fetching and rendering for BIM files metadata.
// If data logic (pagination, filtering, caching) grows,
// extract a `useBIMfiles` hook.
// If rendering becomes complex (actions, expandable rows),
// extract subcomponents for clarity.

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listBimFiles } from '@/api/bim_files';
import { listFiles } from '@/api/files';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

type BimFileMeta = {
  id: string;
  file_id: string;
  filename?: string;
  format: string;
  schema: string | null;
  extra: Record<string, any> | null;
};

type FileMeta = {
  id: string;
  filename: string;
};

export function BIMFilesTable({ refreshKey }: { refreshKey: number }) {
  const navigate = useNavigate();
  const [files, setFiles] = useState<BimFileMeta[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([listBimFiles(), listFiles()])
      .then(([bimFiles, allFiles]) => {
        const filenameById = new Map<string, string>(
          (allFiles as FileMeta[]).map((f) => [f.id, f.filename])
        );
        const rows = (bimFiles as BimFileMeta[]).map((f) => ({
          ...f,
          filename: filenameById.get(f.file_id) ?? '--',
        }));
        setFiles(rows);
      })
      .finally(() => setLoading(false));
  }, [refreshKey]);

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading BIM metadata...</div>;
  }

  return (
    <div className="border border-border rounded-lg bg-card">
      <Table className="text-sm text-foreground">
        <TableHeader className="border-b border-border bg-muted">
          <TableRow className="text-left hover:bg-transparent">
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">BIM ID</TableHead>
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">File ID</TableHead>
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">Filename</TableHead>
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">Format</TableHead>
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">Schema</TableHead>
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">Extra</TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {files.map((f, index) => (
            <TableRow key={f.id ?? `${index}`} className="align-top">
              {console.log(f)}
              <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground">
                {f.id}
              </TableCell>

              <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground">
                {f.file_id}
              </TableCell>

              <TableCell className="px-3 py-2">
                <span
                  className="text-primary underline cursor-pointer"
                  onClick={() => navigate(`/bim/${f.id}`)}
                >
                  {f.filename ?? '--'}
                </span>
              </TableCell>

              <TableCell className="px-3 py-2 text-muted-foreground">{f.format ?? '--'}</TableCell>

              <TableCell className="px-3 py-2 text-muted-foreground">{f.schema ?? '--'}</TableCell>

              <TableCell className="px-3 py-2">
                {f.extra ? (
                  <pre className="text-xs bg-muted rounded p-2 max-w-xs overflow-x-auto">
                    {JSON.stringify(f.extra, null, 2)}
                  </pre>
                ) : (
                  <span className="text-muted-foreground/60">--</span>
                )}
              </TableCell>
            </TableRow>
          ))}

          {files.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="px-4 py-6 text-center text-muted-foreground">
                No BIM metadata entries
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
