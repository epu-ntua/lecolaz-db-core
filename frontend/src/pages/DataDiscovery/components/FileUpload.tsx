import { useState } from 'react';
import { uploadFile } from '@/api/files';
// 1. Import your new Shadcn component
import { Button } from '@/components/ui/button';
// 2. (Optional) If you want a nice spinner, Lucide is already installed!
import { Loader2 } from 'lucide-react';

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
      console.log('UPLOAD DONE');
      setFile(null);
      onUploaded();
    } catch (e) {
      setError('Upload failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20 cursor-pointer"
      />

      {/* 3. Swap out the old button for the Shadcn Button */}
      <Button
        onClick={handleUpload}
        disabled={!file || loading}
        variant="default"
        size="sm"
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Uploading...
          </>
        ) : (
          'Upload'
        )}
      </Button>

      {error && <span className="text-sm text-red-600 font-medium">{error}</span>}
    </div>
  );
}
