import { useEffect, useState } from 'react';
import { listFiles } from '../api/files';

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
    return <div className="text-sm text-muted-foreground">Loading metadata…</div>;
  }

  return (
    <div className="border border-border rounded-lg bg-card overflow-x-auto">
      <table className="w-full text-sm text-foreground">
        <thead className="border-b border-border bg-muted">
          <tr className="text-left">
            <th className="px-3 py-2 font-medium text-muted-foreground">Filename</th>
            <th className="px-3 py-2 font-medium text-muted-foreground">Content type</th>
            <th className="px-3 py-2 font-medium text-muted-foreground">Size</th>
            <th className="px-3 py-2 font-medium text-muted-foreground">Uploaded</th>
            <th className="px-3 py-2 font-medium text-muted-foreground">Object key</th>
            <th className="px-3 py-2 font-medium text-muted-foreground">Extra</th>
          </tr>
        </thead>

        <tbody>
          {files.map((f) => (
            <tr key={f.id} className="border-b last:border-b-0 align-top">
              <td className="px-3 py-2">{f.filename}</td>

              <td className="px-3 py-2 text-muted-foreground">{f.content_type ?? '—'}</td>

              <td className="px-3 py-2 text-muted-foreground">
                {f.size_bytes ? `${Math.round(f.size_bytes / 1024)} KB` : '—'}
              </td>

              <td className="px-3 py-2 text-muted-foreground">
                {new Date(f.created_at).toLocaleString()}
              </td>

              <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                {f.object_key}
              </td>

              <td className="px-3 py-2">
                {f.extra ? (
                  <pre className="text-xs bg-muted rounded p-2 max-w-xs overflow-x-auto">
                    {JSON.stringify(f.extra, null, 2)}
                  </pre>
                ) : (
                  <span className="text-muted-foreground/60">—</span>
                )}
              </td>
            </tr>
          ))}

          {files.length === 0 && (
            <tr>
              <td colSpan={6} className="px-4 py-6 text-center text-muted-foreground">
                No metadata entries
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
