import { useEffect, useState } from 'react';
import { Loader2, Plus } from 'lucide-react';
import { listBimFiles } from '@/api/bim_files';
import { uploadSimulationFile } from '@/api/simulation_files';
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
  const [bimError, setBimError] = useState(false);
  const [bimLoading, setBimLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setBimLoading(true);
    setBimError(false);
    listBimFiles()
      .then(setBims)
      .catch(() => {
        setBims([]);
        setBimError(true);
      })
      .finally(() => setBimLoading(false));
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
      setFile(null);
      try {
        await onUploaded(result);
      } catch {
        setError(
          'Upload accepted, but the list could not refresh. Close this dialog and reload the page; do not upload the same file again.',
        );
        return;
      }
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
          <FilePicker
            label="Choose an EnergyPlus output"
            file={file}
            onChange={setFile}
            accept=".eso"
            disabled={uploading}
          />
          <label className="grid gap-2 text-sm font-medium">
            Associated BIM model
            <select
              aria-label="Associated BIM model"
              disabled={uploading || bimLoading || bimError}
              value={bimId}
              onChange={(event) => setBimId(event.target.value)}
              className="field"
            >
              <option value="">No associated BIM</option>
              {bims.map((bim) => (
                <option key={bim.id} value={bim.id}>
                  {bim.filename}
                </option>
              ))}
            </select>
          </label>
          {bimLoading && (
            <p role="status" className="text-xs text-muted-foreground">
              Loading building models…
            </p>
          )}
          {bimError && (
            <p role="alert" className="text-xs text-destructive">
              Building models could not be loaded. Reopen this dialog to retry before
              linking a simulation.
            </p>
          )}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            disabled={uploading}
            onClick={() => {
              setOpen(false);
              reset();
            }}
          >
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
