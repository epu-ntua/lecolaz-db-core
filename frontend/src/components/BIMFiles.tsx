import { useEffect, useState } from 'react';
import { listBimFiles } from '../api/bim_files';

type BimFileMeta = {
  bim_id: string;
  file_id: string;
  format: string;
  schema: string | null;
  extra: Record<string, any> | null;
};

export function BIMFiles({ refreshKey }: { refreshKey: number }) {
  const [files, setFiles] = useState<BimFileMeta[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listBimFiles()
      .then(setFiles)
      .finally(() => setLoading(false));
  }, [refreshKey]);

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading BIM metadata...</div>;
  }

  return (
    <div className="border border-border rounded-lg bg-card overflow-x-auto">
      <table className="w-full text-sm text-foreground">
        <thead className="border-b border-border bg-muted">
          <tr className="text-left">
            <th className="px-3 py-2 font-medium text-muted-foreground">BIM ID</th>
            <th className="px-3 py-2 font-medium text-muted-foreground">File ID</th>
            <th className="px-3 py-2 font-medium text-muted-foreground">Format</th>
            <th className="px-3 py-2 font-medium text-muted-foreground">Schema</th>
            <th className="px-3 py-2 font-medium text-muted-foreground">Extra</th>
          </tr>
        </thead>

        <tbody>
          {files.map((f, index) => (
            <tr key={f.bim_id ?? `${index}`} className="border-b last:border-b-0 align-top">
              <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{f.bim_id}</td>

              <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{f.file_id}</td>

              <td className="px-3 py-2 text-muted-foreground">{f.format ?? '--'}</td>

              <td className="px-3 py-2 text-muted-foreground">{f.schema ?? '--'}</td>

              <td className="px-3 py-2">
                {f.extra ? (
                  <pre className="text-xs bg-muted rounded p-2 max-w-xs overflow-x-auto">
                    {JSON.stringify(f.extra, null, 2)}
                  </pre>
                ) : (
                  <span className="text-muted-foreground/60">--</span>
                )}
              </td>
            </tr>
          ))}

          {files.length === 0 && (
            <tr>
              <td colSpan={5} className="px-4 py-6 text-center text-muted-foreground">
                No BIM metadata entries
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
