import { useEffect, useState } from 'react';
import { Blocks, Plus } from 'lucide-react';
import { listComponents, updateComponentBuilding } from '@/api/components';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { COMPONENT_CLASS_LABELS } from '@/lib/constants';
import { buildingName } from '@/lib/format';
import type { BimFileDto } from '@/types/api/bim';
import type { ModularComponentDto } from '@/types/api/components';
import { ComponentSelectionDialog } from './ComponentSelectionDialog';

export function BIMComponentsTab({
  file,
  onUpdated,
}: {
  file: BimFileDto;
  onUpdated?: (component: ModularComponentDto) => void;
}) {
  const [components, setComponents] = useState<ModularComponentDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [picking, setPicking] = useState(false);
  const [toRemove, setToRemove] = useState<ModularComponentDto | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const name = buildingName(file.filename);

  // This tab mounts on each visit, so connections are refreshed when switching to it.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    listComponents()
      .then((rows) => {
        if (!cancelled)
          setComponents(rows.filter((component) => component.bim_dataset_id === file.id));
      })
      .catch(() => {
        if (!cancelled) setLoadError('Connected components could not be loaded.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [file.id, retry]);

  const applyUpdate = (updated: ModularComponentDto) => {
    setComponents((current) => {
      const others = current.filter((component) => component.id !== updated.id);
      return updated.bim_dataset_id === file.id ? [...others, updated] : others;
    });
    onUpdated?.(updated);
  };

  return (
    <>
      <Card className="shadow-none">
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <CardTitle className="text-sm font-medium">Components for {name}</CardTitle>
              <DialogDescription className="mt-1 text-left">
                Modular components placed in this building.
              </DialogDescription>
            </div>
            <Button
              type="button"
              size="lg"
              disabled={loading || !!loadError}
              onClick={() => setPicking(true)}
            >
              <Plus />
              Connect Components
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading components…</p>
          ) : loadError ? (
            <div className="space-y-2">
              <p role="alert" className="text-sm text-destructive">
                {loadError}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setRetry((value) => value + 1)}
              >
                Retry
              </Button>
            </div>
          ) : components.length ? (
            <div className="overflow-x-auto rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Component</TableHead>
                    <TableHead>Class</TableHead>
                    <TableHead className="w-0">
                      <span className="sr-only">Actions</span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[...components]
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map((component) => (
                      <TableRow key={component.id}>
                        <TableCell className="font-medium">{component.name}</TableCell>
                        <TableCell>
                          {COMPONENT_CLASS_LABELS[component.component_class]}
                        </TableCell>
                        <TableCell>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSaveError(null);
                              setToRemove(component);
                            }}
                          >
                            Remove
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="flex items-center gap-3 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
              <Blocks className="h-5 w-5" />
              No components are connected to this building yet.
            </div>
          )}
        </CardContent>
      </Card>

      {picking && (
        <ComponentSelectionDialog
          file={file}
          onUpdated={applyUpdate}
          onClose={() => {
            setPicking(false);
            setRetry((value) => value + 1);
          }}
        />
      )}

      <Dialog
        open={toRemove !== null}
        onOpenChange={(open) => {
          if (saving || open) return;
          setToRemove(null);
          setSaveError(null);
        }}
      >
        <DialogContent className="w-[calc(100%-2rem)] max-w-md">
          <DialogHeader className="text-left">
            <DialogTitle>Remove component?</DialogTitle>
            <DialogDescription>
              {toRemove?.name} will no longer be connected to {name}. The component will
              remain available and can be connected again.
            </DialogDescription>
          </DialogHeader>
          {saveError && (
            <p role="alert" className="text-sm text-destructive">
              {saveError}
            </p>
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={() => setToRemove(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={saving}
              onClick={async () => {
                if (!toRemove) return;
                try {
                  setSaving(true);
                  setSaveError(null);
                  applyUpdate(await updateComponentBuilding(toRemove.id, null));
                  setToRemove(null);
                } catch {
                  setSaveError('Component could not be disconnected. Please try again.');
                } finally {
                  setSaving(false);
                }
              }}
            >
              {saving ? 'Removing…' : 'Remove'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
