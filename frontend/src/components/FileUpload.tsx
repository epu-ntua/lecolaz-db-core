import { useState } from "react";
import { uploadFile } from "../api/files";

export function FileUpload({ onUploaded }: { onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    if (!file) return;

    try {
      setLoading(true);
      setError(null);
      await uploadFile(file);
      console.log("UPLOAD DONE");
      setFile(null);
      onUploaded();
    } catch (e) {
      setError("Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="text-sm"
      />

      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className="px-3 py-1.5 rounded border text-sm
                   disabled:opacity-50
                   bg-gray-800 text-white hover:bg-gray-700"
      >
        {loading ? "Uploading…" : "Upload"}
      </button>

      {error && (
        <span className="text-sm text-red-600">{error}</span>
      )}
    </div>
  );
}
