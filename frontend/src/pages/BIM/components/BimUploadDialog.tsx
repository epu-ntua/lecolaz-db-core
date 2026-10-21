import { useState } from 'react';
import { Loader2, Plus, Upload } from 'lucide-react';
import { uploadBimFile } from '@/api/bim_files';
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
  const [category, setCategory] = useState<BimCategory | ''>('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setFile(null);
    setCategory('');
    setError(null);
  };

  const handleUpload = async () => {
    if (!file || !category) return;

    try {
      setUploading(true);
      setError(null);
      const result = await uploadBimFile(file, category);
      await onUploaded(result);
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
          <label className="grid gap-2 text-sm font-medium">
            BIM file
            <div className="rounded-xl border border-dashed bg-muted/40 p-4">
              <div className="mb-3 flex items-center gap-3 text-muted-foreground">
                <div className="rounded-lg bg-accent p-2 text-accent-foreground">
                  <Upload className="h-4 w-4" />
                </div>
                <span className="text-xs">IFC, IFCZIP or IFCXML</span>
              </div>
              <input
                type="file"
                accept=".ifc,.ifczip,.ifcxml"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                className="w-full cursor-pointer text-sm file:mr-4 file:rounded-md file:border-0 file:bg-primary/10 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-primary hover:file:bg-primary/20"
              />
            </div>
          </label>

          <label className="grid gap-2 text-sm font-medium">
            Category
            <select
              required
              value={category}
              onChange={(event) => setCategory(event.target.value as BimCategory | '')}
              className="h-10 rounded-md border border-input bg-background px-3 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="" disabled>
                Select a category
              </option>
              <option value="archetype">Building Archetype</option>
              <option value="pilot">Living Lab / Pilot</option>
            </select>
          </label>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            disabled={uploading}
            onClick={() => setOpen(false)}
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
