import { useState } from 'react';
import { uploadBimImage } from '@/api/bim_files';
import { Button } from '@/components/ui/button';
import { FilePicker } from '@/components/ui/file-picker';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { buildingName } from '@/lib/format';
import type { BimFileDto } from '@/types/api/bim';

export function BuildingImageDialog({
  building,
  onClose,
  onSaved,
}: {
  building: BimFileDto;
  onClose: () => void;
  onSaved: (updated: BimFileDto) => void;
}) {
  const [image, setImage] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    if (!image) return;
    try {
      setSaving(true);
      setError(null);
      onSaved(await uploadBimImage(building.id, image));
    } catch {
      setError('Building image could not be uploaded. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && !saving && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {building.image_object_key ? 'Edit building image' : 'Add building image'}
          </DialogTitle>
          <DialogDescription>
            Choose a thumbnail for {buildingName(building.filename)}. JPEG, PNG, or WebP,
            up to 10 MB.
          </DialogDescription>
        </DialogHeader>
        <FilePicker
          label="Choose an image"
          file={image}
          onChange={setImage}
          accept=".jpg,.jpeg,.png,.webp"
          disabled={saving}
        />
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <DialogFooter>
          <Button type="button" variant="outline" disabled={saving} onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" disabled={!image || saving} onClick={save}>
            {saving ? 'Saving…' : 'Save image'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
