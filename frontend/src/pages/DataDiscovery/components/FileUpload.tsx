import { useState } from 'react';
import { uploadDataset } from '@/api/datasets';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import type { DatasetUploadResult } from '@/types/api/datasets';

type FileUploadProps = {
  onUploaded: (result: DatasetUploadResult) => void;
  uploadAction?: (file: File) => Promise<DatasetUploadResult>;
  accept?: string;
  buttonLabel?: string;
  uploadingLabel?: string;
  errorMessage?: string;
};

export function FileUpload({
  onUploaded,
  uploadAction = uploadDataset,
  accept,
  buttonLabel = 'Upload',
  uploadingLabel = 'Uploading...',
  errorMessage = 'Upload failed',
}: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    if (!file) return;

    try {
      setLoading(true);
      setError(null);
      const result = await uploadAction(file);
      setFile(null);
      onUploaded(result);
    } catch (e) {
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <input
        type="file"
        accept={accept}
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20 cursor-pointer"
      />

      <Button
        onClick={handleUpload}
        disabled={!file || loading}
        variant="default"
        size="sm"
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            {uploadingLabel}
          </>
        ) : (
          buttonLabel
        )}
      </Button>

      {error && <span className="text-sm text-red-600 font-medium">{error}</span>}
    </div>
  );
}
