import { useState } from 'react';
import { uploadDataset } from '@/api/datasets';
import { FilePicker } from '@/components/ui/file-picker';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import type { DatasetUploadResult } from '@/types/api/datasets';

type FileUploadProps = {
  onUploaded: (result: DatasetUploadResult) => void | Promise<void>;
  uploadAction?: (file: File) => Promise<DatasetUploadResult>;
  accept?: string;
  buttonLabel?: string;
  uploadingLabel?: string;
  errorMessage?: string;
  onBusyChange?: (busy: boolean) => void;
};

export function FileUpload({
  onUploaded,
  uploadAction = uploadDataset,
  accept,
  buttonLabel = 'Upload',
  uploadingLabel = 'Uploading...',
  errorMessage = 'Upload failed',
  onBusyChange,
}: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    if (!file) return;

    try {
      setLoading(true);
      onBusyChange?.(true);
      setError(null);
      const result = await uploadAction(file);
      setFile(null);
      try {
        await onUploaded(result);
      } catch {
        setError(
          'Upload accepted, but the list could not refresh. Reload the page; do not upload the same file again.',
        );
      }
    } catch {
      setError(errorMessage);
    } finally {
      setLoading(false);
      onBusyChange?.(false);
    }
  }

  return (
    <div className="space-y-5">
      <FilePicker file={file} onChange={setFile} accept={accept} disabled={loading} />

      <Button
        onClick={handleUpload}
        disabled={!file || loading}
        variant="default"
        className="w-full"
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

      {error && (
        <span role="alert" className="text-sm text-destructive font-medium">
          {error}
        </span>
      )}
    </div>
  );
}
