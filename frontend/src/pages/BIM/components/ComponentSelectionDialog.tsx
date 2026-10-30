import { useEffect, useState } from 'react';
import { getBimFile } from '@/api/bim_files';
import { listComponents, updateComponentBuilding } from '@/api/components';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { SearchInput } from '@/components/ui/search-input';
import { COMPONENT_CLASS_LABELS } from '@/lib/constants';
import { buildingName } from '@/lib/format';
import type { BimFileDto } from '@/types/api/bim';
import type { ModularComponentDto } from '@/types/api/components';

export function ComponentSelectionDialog({
  file,
  onUpdated,
  onClose,
}: {
  file: BimFileDto;
  onUpdated: (component: ModularComponentDto) => void;
  onClose: () => void;
}) {
  const [components, setComponents] = useState<ModularComponentDto[]>([]);
  const [buildingNames, setBuildingNames] = useState<Map<string, string>>(new Map());
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const selectedComponents = components.filter((component) => selected.has(component.id));
  const reassignments = selectedComponents.filter(
    (component) => component.bim_dataset_id,
  );
  const visible = components
    .filter((component) =>
      `${component.name} ${COMPONENT_CLASS_LABELS[component.component_class]}`
        .toLowerCase()
        .includes(query.toLowerCase()),
    )
    .sort(
      (a, b) =>
        Number(!!a.bim_dataset_id) - Number(!!b.bim_dataset_id) ||
        a.name.localeCompare(b.name),
    );

  // Fetch again when opening the picker, since assignments may have changed.
  useEffect(() => {
    let cancelled = false;
    listComponents()
      .then(async (rows) => {
        if (cancelled) return;
        const available = rows.filter(
          (component) => component.bim_dataset_id !== file.id,
        );
        setComponents(available);
        setLoading(false);
        const ids = [
          ...new Set(
            available.flatMap((component) =>
              component.bim_dataset_id ? [component.bim_dataset_id] : [],
            ),
          ),
        ];
        const buildings = await Promise.allSettled(ids.map(getBimFile));
        if (!cancelled) {
          setBuildingNames(
            new Map(
              buildings.flatMap((result) =>
                result.status === 'fulfilled'
                  ? [[result.value.id, buildingName(result.value.filename)] as const]
                  : [],
              ),
            ),
          );
        }
      })
      .catch(() => {
        if (!cancelled)
          setLoadError(
            'Available components could not be loaded. Close the list and try again.',
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [file.id]);

  const connect = async () => {
    setSaving(true);
    setSaveError(null);
    // The existing endpoint updates one component at a time. Keep successful
    // updates and retain only failed selections if a batch partially succeeds.
    const results = await Promise.allSettled(
      selectedComponents.map((component) =>
        updateComponentBuilding(component.id, file.id),
      ),
    );
    const failed = selectedComponents.filter(
      (_, index) => results[index].status === 'rejected',
    );
    results.forEach((result) => {
      if (result.status === 'fulfilled') onUpdated(result.value);
    });
    setSaving(false);
    setConfirming(false);
    if (!failed.length) {
      onClose();
      return;
    }
    const failedIds = new Set(failed.map((component) => component.id));
    setComponents((current) =>
      current.filter(
        (component) => !selected.has(component.id) || failedIds.has(component.id),
      ),
    );
    setSelected(failedIds);
    setSaveError(
      `${results.length - failed.length} connected; ${failed.length} could not be connected. The failed components remain selected. Please try again.`,
    );
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!saving && !open) onClose();
      }}
    >
      <DialogContent className="flex max-h-[80vh] w-[calc(100%-2rem)] max-w-lg flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4 text-left">
          <DialogTitle className="text-lg">Connect Components</DialogTitle>
          <DialogDescription>
            Select components to place in {buildingName(file.filename)}. Unlinked
            components are listed first. Components already connected here are omitted.
          </DialogDescription>
        </DialogHeader>
        <div className="px-4 pt-4 sm:px-6">
          <SearchInput
            value={query}
            onChange={setQuery}
            placeholder="Search components…"
            className="sm:max-w-none"
          />
        </div>
        <div className="max-h-72 min-h-0 space-y-3 overflow-y-auto px-4 py-4 text-sm sm:px-6">
          {loading ? (
            <p className="text-muted-foreground">Loading components…</p>
          ) : loadError ? (
            <p role="alert" className="text-destructive">
              {loadError}
            </p>
          ) : visible.length ? (
            <ul className="divide-y rounded-lg border">
              {visible.map((component) => (
                <li key={component.id}>
                  <label className="flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-muted">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 accent-primary"
                      disabled={saving}
                      checked={selected.has(component.id)}
                      onChange={() => {
                        const next = new Set(selected);
                        if (next.has(component.id)) next.delete(component.id);
                        else next.add(component.id);
                        setSelected(next);
                        setSaveError(null);
                      }}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block break-words font-medium">
                        {component.name}
                      </span>
                      <span className="block text-xs text-muted-foreground">
                        {COMPONENT_CLASS_LABELS[component.component_class]}
                      </span>
                      <span className="block break-words text-xs text-muted-foreground">
                        {component.bim_dataset_id
                          ? `Connected to ${buildingNames.get(component.bim_dataset_id) ?? 'another building'} — will be reassigned`
                          : 'No linked building'}
                      </span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground">
              {components.length
                ? 'No components match the current search.'
                : 'No components available to connect.'}
            </p>
          )}
          {saveError && (
            <p role="alert" className="text-destructive">
              {saveError}
            </p>
          )}
        </div>
        <DialogFooter className="border-t border-border px-6 py-4">
          <Button type="button" variant="outline" disabled={saving} onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={saving || loading || !!loadError || !selected.size}
            onClick={() => {
              if (reassignments.length) setConfirming(true);
              else void connect();
            }}
          >
            {saving ? 'Connecting…' : `Connect (${selected.size})`}
          </Button>
        </DialogFooter>
      </DialogContent>
      <Dialog
        open={confirming}
        onOpenChange={(open) => {
          if (!saving) setConfirming(open);
        }}
      >
        <DialogContent className="w-[calc(100%-2rem)] max-w-md">
          <DialogHeader className="text-left">
            <DialogTitle>Reassign components?</DialogTitle>
            <DialogDescription>
              The following {reassignments.length} component(s) will be disconnected from
              their current buildings. All {selected.size} selected component(s) will be
              connected to {buildingName(file.filename)}.
            </DialogDescription>
          </DialogHeader>
          <ul className="max-h-48 space-y-2 overflow-y-auto text-sm">
            {reassignments.map((component) => (
              <li key={component.id} className="break-words">
                <span className="font-medium">{component.name}</span>
                <span className="text-muted-foreground">
                  {' '}
                  — {buildingNames.get(component.bim_dataset_id!) ?? 'Another building'}
                </span>
              </li>
            ))}
          </ul>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={() => setConfirming(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={saving}
              onClick={() => void connect()}
            >
              {saving ? 'Connecting…' : 'Reassign and connect'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Dialog>
  );
}
