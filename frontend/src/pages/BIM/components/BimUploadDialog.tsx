import { useState } from 'react';
import { Loader2, Plus } from 'lucide-react';
import { uploadBimFile } from '@/api/bim_files';
import { FilePicker } from '@/components/ui/file-picker';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import type { BimCategory } from '@/types/api/bim';
import type { DatasetUploadResult } from '@/types/api/datasets';

type BimUploadDialogProps = {
  onUploaded: (result: DatasetUploadResult) => Promise<void>;
};

export function BimUploadDialog({ onUploaded }: BimUploadDialogProps) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [image, setImage] = useState<File | null>(null);
  const [category, setCategory] = useState<BimCategory | ''>('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setFile(null);
    setImage(null);
    setCategory('');
    setError(null);
  };

  const handleUpload = async () => {
    if (!file || !category) return;

    try {
      setUploading(true);
      setError(null);
      const result = await uploadBimFile(file, category, image);
      setFile(null);
      try {
        await onUploaded(result);
      } catch {
        setError(
          'Upload accepted, but the portfolio could not refresh. Close this dialog and reload the page; do not upload the same file again.',
        );
        return;
      }
      setOpen(false);
      reset();
    } catch {
      setError('BIM upload failed. Please check the file and try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (uploading) return;
        setOpen(nextOpen);
        if (!nextOpen) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button size="lg">
          <Plus className="h-4 w-4" />
          Add Building
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Add a building model</DialogTitle>
          <DialogDescription>
            Upload a BIM file and choose where it belongs in the portfolio.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          <FilePicker
            label="Choose a BIM model"
            file={file}
            onChange={setFile}
            accept=".ifc,.ifczip,.ifcxml"
            disabled={uploading}
          />
          <FilePicker
            label="Building image (optional)"
            file={image}
            onChange={setImage}
            accept=".jpg,.jpeg,.png,.webp"
            disabled={uploading}
          />

          <label className="grid gap-2 text-sm font-medium">
            Category
            <select
              aria-label="Building category"
              disabled={uploading}
              required
              value={category}
              onChange={(event) => setCategory(event.target.value as BimCategory | '')}
              className="field"
            >
              <option value="" disabled>
                Select a category
              </option>
              <option value="archetype">Building Archetype</option>
              <option value="pilot">Living Lab / Pilot</option>
            </select>
          </label>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            disabled={uploading}
            onClick={() => {
              setOpen(false);
              reset();
            }}
          >
            Cancel
          </Button>
          <Button
            type="button"
            disabled={!file || !category || uploading}
            onClick={handleUpload}
          >
            {uploading && <Loader2 className="h-4 w-4 animate-spin" />}
            {uploading ? 'Uploading…' : 'Upload building'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
