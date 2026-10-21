import { useEffect, useMemo, useState } from 'react';
import { Loader2, Plus, RadioTower } from 'lucide-react';
import { listBimFiles } from '@/api/bim_files';
import { listEligibleSensors, registerSensors } from '@/api/sensors';
import { Badge } from '@/components/ui/badge';
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
import type { EligibleSensorDto, SensorFamily } from '@/types/api/sensors';

const PRESERVE_BIM = '__preserve__';

export function SensorRegistrationDialog({
  initialBimId,
  buttonLabel = 'Register Sensors',
  onRegistered,
}: {
  initialBimId?: string;
  buttonLabel?: string;
  onRegistered: () => void | Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [family, setFamily] = useState<SensorFamily>('ham');
  const [sensors, setSensors] = useState<EligibleSensorDto[]>([]);
  const [bims, setBims] = useState<BimFileDto[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bimId, setBimId] = useState(initialBimId ?? PRESERVE_BIM);
  const [location, setLocation] = useState('');
  const [space, setSpace] = useState('');
  const [startingDate, setStartingDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  const bimNames = useMemo(
    () => new Map(bims.map((bim) => [bim.id, bim.filename] as const)),
    [bims],
  );

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSelected(new Set());
    Promise.all([listEligibleSensors(family), listBimFiles()])
      .then(([nextSensors, nextBims]) => {
        if (!cancelled) {
          setSensors(nextSensors);
          setBims(nextBims);
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setSensors([]);
          setError(reason instanceof Error ? reason.message : 'Sensor discovery failed.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [family, open]);

  const reset = () => {
    setFamily('ham');
    setSensors([]);
    setSelected(new Set());
    setBimId(initialBimId ?? PRESERVE_BIM);
    setLocation('');
    setSpace('');
    setStartingDate('');
    setError(null);
    setWarning(null);
  };

  const submit = async () => {
    if (!selected.size) return;
    try {
      setSaving(true);
      setError(null);
      setWarning(null);
      const settings: {
        bim_dataset_id?: string | null;
        location?: string;
        space?: string;
        starting_date?: string;
      } = {};
      if (bimId !== PRESERVE_BIM) settings.bim_dataset_id = bimId || null;
      if (location.trim()) settings.location = location.trim();
      if (space.trim()) settings.space = space.trim();
      if (startingDate) settings.starting_date = new Date(startingDate).toISOString();

      const result = await registerSensors(family, [...selected], settings);
      await onRegistered();
      if (result.dagster.status === 'failed') {
        setWarning(
          result.dagster.message ?? 'Sensors were saved, but ingestion reload failed.',
        );
        return;
      }
      setOpen(false);
      reset();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sensor registration failed.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!saving) {
          setOpen(next);
          if (!next) reset();
        }
      }}
    >
      <DialogTrigger asChild>
        <Button size="lg">
          <Plus />
          {buttonLabel}
        </Button>
      </DialogTrigger>
      <DialogContent className="flex max-h-[90vh] max-w-3xl flex-col overflow-hidden p-0">
        <DialogHeader className="border-b px-6 py-5">
          <DialogTitle>Discover and register sensors</DialogTitle>
          <DialogDescription>
            Select provider sensors and optionally connect them to a building model.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 overflow-y-auto px-6 py-5">
          <div className="grid grid-cols-2 gap-2 rounded-lg bg-muted p-1">
            {(['ham', 'openmeteo'] as const).map((value) => (
              <Button
                key={value}
                type="button"
                variant={family === value ? 'default' : 'ghost'}
                onClick={() => setFamily(value)}
              >
                {value === 'ham' ? 'HAM' : 'OpenMeteo'}
              </Button>
            ))}
          </div>

          <div className="rounded-xl border">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <div>
                <div className="text-sm font-semibold">Available sensors</div>
                <div className="text-xs text-muted-foreground">
                  {selected.size} selected
                </div>
              </div>
              {!!sensors.length && (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    setSelected(
                      selected.size === sensors.length
                        ? new Set()
                        : new Set(sensors.map((sensor) => sensor.external_id)),
                    )
                  }
                >
                  {selected.size === sensors.length ? 'Clear all' : 'Select all'}
                </Button>
              )}
            </div>
            <div className="max-h-64 overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center gap-2 p-10 text-sm text-muted-foreground">
                  <Loader2 className="animate-spin" /> Discovering sensors…
                </div>
              ) : sensors.length ? (
                sensors.map((sensor) => (
                  <label
                    key={sensor.external_id}
                    className="flex cursor-pointer items-start gap-3 border-b px-4 py-3 last:border-0 hover:bg-muted/40"
                  >
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 accent-primary"
                      checked={selected.has(sensor.external_id)}
                      onChange={() => {
                        const next = new Set(selected);
                        if (next.has(sensor.external_id)) next.delete(sensor.external_id);
                        else next.add(sensor.external_id);
                        setSelected(next);
                      }}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2 text-sm font-medium">
                        {sensor.name}
                        {sensor.registered && (
                          <Badge variant="secondary">Registered</Badge>
                        )}
                      </span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {sensor.external_id}
                        {sensor.bim_dataset_id &&
                          ` · ${bimNames.get(sensor.bim_dataset_id) ?? 'Linked BIM'}`}
                      </span>
                    </span>
                  </label>
                ))
              ) : (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  No eligible sensors were returned by this provider.
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-2 text-sm font-medium sm:col-span-2">
              Building model
              <select
                value={bimId}
                onChange={(event) => setBimId(event.target.value)}
                className="h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                {!initialBimId && (
                  <option value={PRESERVE_BIM}>Keep current assignment</option>
                )}
                <option value="">No BIM — disconnect</option>
                {bims.map((bim) => (
                  <option key={bim.id} value={bim.id}>
                    {bim.filename}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Location{' '}
              <span className="text-xs font-normal text-muted-foreground">Optional</span>
              <input
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                placeholder="e.g. Athens pilot"
                className="h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Space{' '}
              <span className="text-xs font-normal text-muted-foreground">Optional</span>
              <input
                value={space}
                onChange={(event) => setSpace(event.target.value)}
                placeholder="e.g. Room 101"
                className="h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </label>
            <label className="grid gap-2 text-sm font-medium sm:col-span-2">
              Ingestion start{' '}
              <span className="text-xs font-normal text-muted-foreground">Optional</span>
              <input
                type="datetime-local"
                value={startingDate}
                onChange={(event) => setStartingDate(event.target.value)}
                className="h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </label>
          </div>

          {error && (
            <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
          {warning && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              {warning}
            </div>
          )}
        </div>

        <DialogFooter className="border-t px-6 py-4">
          <Button variant="outline" disabled={saving} onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button disabled={!selected.size || loading || saving} onClick={submit}>
            {saving ? <Loader2 className="animate-spin" /> : <RadioTower />}
            {saving
              ? 'Registering…'
              : `Register ${selected.size || ''} sensor${selected.size === 1 ? '' : 's'}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
