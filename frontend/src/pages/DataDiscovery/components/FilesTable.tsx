import { useEffect, useState } from 'react';
import { listFiles } from '@/api/files';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

type FileMeta = {
  id: string;
  filename: string;
  object_key: string;
  content_type: string | null;
  size_bytes: number | null;
  created_at: string;
  extra: Record<string, any> | null;
};

export function FilesTable({ refreshKey }: { refreshKey: number }) {
  const [files, setFiles] = useState<FileMeta[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listFiles()
      .then(setFiles)
      .finally(() => setLoading(false));
  }, [refreshKey]);

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading metadata...</div>;
  }

  return (
    <div className="border border-border rounded-lg bg-card">
      <Table className="text-sm text-foreground">
        <TableHeader className="border-b border-border bg-muted">
          <TableRow className="text-left hover:bg-transparent">
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">Filename</TableHead>
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">Content type</TableHead>
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">Size</TableHead>
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">Uploaded</TableHead>
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">Object key</TableHead>
            <TableHead className="px-3 py-2 font-medium text-muted-foreground">Extra</TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {files.map((f) => (
            <TableRow key={f.id} className="align-top">
              <TableCell className="px-3 py-2">{f.filename}</TableCell>

              <TableCell className="px-3 py-2 text-muted-foreground">{f.content_type ?? '--'}</TableCell>

              <TableCell className="px-3 py-2 text-muted-foreground">
                {f.size_bytes ? `${Math.round(f.size_bytes / 1024)} KB` : '--'}
              </TableCell>

              <TableCell className="px-3 py-2 text-muted-foreground">
                {new Date(f.created_at).toLocaleString()}
              </TableCell>

              <TableCell className="px-3 py-2 font-mono text-xs text-muted-foreground">
                {f.object_key}
              </TableCell>

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
                No metadata entries
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}