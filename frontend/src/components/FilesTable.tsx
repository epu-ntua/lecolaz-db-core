import { useEffect, useState } from "react";
import { listFiles } from "../api/files";

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
    return <div className="text-sm text-gray-500">Loading metadata…</div>;
  }

  return (
    <div className="border rounded bg-white overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b bg-gray-50">
          <tr className="text-left">
            <th className="px-3 py-2 font-medium">Filename</th>
            <th className="px-3 py-2 font-medium">Content type</th>
            <th className="px-3 py-2 font-medium">Size</th>
            <th className="px-3 py-2 font-medium">Uploaded</th>
            <th className="px-3 py-2 font-medium">Object key</th>
            <th className="px-3 py-2 font-medium">Extra</th>
          </tr>
        </thead>

        <tbody>
          {files.map((f) => (
            <tr key={f.id} className="border-b last:border-b-0 align-top">
              <td className="px-3 py-2">{f.filename}</td>

              <td className="px-3 py-2 text-gray-600">
                {f.content_type ?? "—"}
              </td>

              <td className="px-3 py-2 text-gray-600">
                {f.size_bytes
                  ? `${Math.round(f.size_bytes / 1024)} KB`
                  : "—"}
              </td>

              <td className="px-3 py-2 text-gray-600">
                {new Date(f.created_at).toLocaleString()}
              </td>

              <td className="px-3 py-2 font-mono text-xs text-gray-500">
                {f.object_key}
              </td>

              <td className="px-3 py-2">
                {f.extra ? (
                  <pre className="text-xs bg-gray-100 rounded p-2 max-w-xs overflow-x-auto">
                    {JSON.stringify(f.extra, null, 2)}
                  </pre>
                ) : (
                  <span className="text-gray-400">—</span>
                )}
              </td>
            </tr>
          ))}

          {files.length === 0 && (
            <tr>
              <td
                colSpan={6}
                className="px-4 py-6 text-center text-gray-500"
              >
                No metadata entries
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
