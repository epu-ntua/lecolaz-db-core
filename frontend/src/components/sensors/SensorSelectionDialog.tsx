import { useEffect, useState } from 'react';
import { listRegisteredSensors } from '@/api/sensors';
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
import type { RegisteredSensorDto } from '@/types/api/sensors';

export function SensorSelectionDialog({
  description,
  onConnect,
  onClose,
}: {
  description: string;
  onConnect: (sensorIds: string[]) => Promise<void>;
  onClose: () => void;
}) {
  const [freeSensors, setFreeSensors] = useState<RegisteredSensorDto[]>([]);
  const [freeLoading, setFreeLoading] = useState(true);
  const [freeError, setFreeError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const visibleFree = freeSensors.filter((sensor) =>
    `${sensor.name} ${sensor.external_id}`.toLowerCase().includes(query.toLowerCase()),
  );

  // Reload free sensors each time the picker opens: another user may have taken some.
  useEffect(() => {
    let cancelled = false;
    setFreeLoading(true);
    setFreeError(null);
    listRegisteredSensors({ unassigned: true })
      .then((rows) => {
        if (!cancelled) setFreeSensors(rows);
      })
      .catch(() => {
        if (!cancelled) setFreeError('Available sensors could not be loaded.');
      })
      .finally(() => {
        if (!cancelled) setFreeLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!saving && !open) onClose();
      }}
    >
      <DialogContent className="flex max-h-[80vh] w-[calc(100%-2rem)] max-w-md flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4 text-left">
          <DialogTitle className="text-lg">Connect sensors</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="px-4 pt-4 sm:px-6">
          <SearchInput
            value={query}
            onChange={setQuery}
            placeholder="Search sensors…"
            className="sm:max-w-none"
          />
        </div>
        <div className="max-h-72 min-h-0 space-y-3 overflow-y-auto px-4 py-4 text-sm sm:px-6">
          {freeLoading ? (
            <p className="text-muted-foreground">Loading sensors…</p>
          ) : freeError ? (
            <p className="text-destructive">{freeError}</p>
          ) : visibleFree.length ? (
            <ul className="divide-y rounded-lg border">
              {visibleFree.map((sensor) => (
                <li key={sensor.id}>
                  <label className="flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-muted">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 accent-primary"
                      disabled={saving}
                      checked={selected.has(sensor.id)}
                      onChange={() => {
                        const next = new Set(selected);
                        if (next.has(sensor.id)) next.delete(sensor.id);
                        else next.add(sensor.id);
                        setSelected(next);
                      }}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">{sensor.name}</span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {sensor.external_id} ·{' '}
                        {sensor.sensor_family === 'ham' ? 'HAM' : 'OpenMeteo'}
                      </span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground">
              {freeSensors.length
                ? 'No sensors match the current search.'
                : 'No available sensors. Register sensors or unlink them from a building or component first.'}
            </p>
          )}
          {saveError && <p className="text-destructive">{saveError}</p>}
        </div>
        <DialogFooter className="border-t border-border px-6 py-4">
          <Button type="button" variant="outline" disabled={saving} onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={saving || !selected.size}
            onClick={async () => {
              try {
                setSaving(true);
                setSaveError(null);
                await onConnect([...selected]);
                onClose();
              } catch {
                setSaveError(
                  'Sensors could not be updated. Some may have just been linked elsewhere; reopen the list and try again.',
                );
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? 'Connecting…' : `Connect (${selected.size})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
