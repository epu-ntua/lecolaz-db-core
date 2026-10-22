import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { FileUpload } from './FileUpload';
import type { DatasetUploadResult } from '@/types/api/datasets';

export function GenericUploadDialog({
  onUploaded,
}: {
  onUploaded: (result: DatasetUploadResult) => void | Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [uploading, setUploading] = useState(false);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!uploading) setOpen(next);
      }}
    >
      <DialogTrigger asChild>
        <Button size="lg">
          <Plus className="h-4 w-4" />
          Upload File
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Upload a dataset</DialogTitle>
          <DialogDescription>
            Add a file using the platform’s generic ingestion flow.
          </DialogDescription>
        </DialogHeader>
        <div>
          <FileUpload
            onBusyChange={setUploading}
            onUploaded={async (result) => {
              await onUploaded(result);
              setOpen(false);
            }}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
