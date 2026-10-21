import { useEffect, useState } from 'react';
import { Loader2, Plus } from 'lucide-react';
import { listBimFiles } from '@/api/bim_files';
import { uploadSimulationFile } from '@/api/simulation_files';
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
import type { BimFileDto } from '@/types/api/bim';
import type { DatasetUploadResult } from '@/types/api/datasets';

export function SimulationUploadDialog({
  onUploaded,
}: {
  onUploaded: (result: DatasetUploadResult) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [bimId, setBimId] = useState('');
  const [bims, setBims] = useState<BimFileDto[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    listBimFiles()
      .then(setBims)
      .catch(() => setBims([]));
  }, [open]);

  const reset = () => {
    setFile(null);
    setBimId('');
    setError(null);
  };

  const submit = async () => {
    if (!file) return;
    try {
      setUploading(true);
      setError(null);
      const result = await uploadSimulationFile(file, bimId || undefined);
      await onUploaded(result);
      setOpen(false);
      reset();
    } catch {
      setError('Simulation upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!uploading) {
          setOpen(next);
          if (!next) reset();
        }
      }}
    >
      <DialogTrigger asChild>
        <Button size="lg">
          <Plus className="h-4 w-4" />
          Upload Simulation
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Upload simulation</DialogTitle>
          <DialogDescription>
            Import an EnergyPlus output and optionally associate it with a BIM model.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-5 py-2">
          <label className="grid gap-2 text-sm font-medium">
            Simulation file
            <input
              type="file"
              accept=".eso"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="w-full cursor-pointer rounded-xl border border-dashed bg-muted/30 p-4 text-sm file:mr-4 file:rounded-md file:border-0 file:bg-primary/10 file:px-4 file:py-2 file:font-semibold file:text-primary"
            />
          </label>
          <label className="grid gap-2 text-sm font-medium">
            Associated BIM model
            <select
              value={bimId}
              onChange={(event) => setBimId(event.target.value)}
              className="h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="">No associated BIM</option>
              {bims.map((bim) => (
                <option key={bim.id} value={bim.id}>
                  {bim.filename}
                </option>
              ))}
            </select>
          </label>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" disabled={uploading} onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button disabled={!file || uploading} onClick={submit}>
            {uploading && <Loader2 className="h-4 w-4 animate-spin" />}
            {uploading ? 'Uploading…' : 'Upload Simulation'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
