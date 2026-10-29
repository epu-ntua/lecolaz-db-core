import { useEffect, useMemo, useState } from 'react';
import { Loader2, Plus, RadioTower } from 'lucide-react';
import { listBimFiles } from '@/api/bim_files';
import { listEligibleSensors, registerSensors } from '@/api/sensors';
import { SearchInput } from '@/components/ui/search-input';
import { ErrorNotice } from '@/components/layout/Feedback';
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
  const [query, setQuery] = useState('');
  const [retry, setRetry] = useState(0);
  const [discoveryFailed, setDiscoveryFailed] = useState(false);
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
    setWarning(null);
    setDiscoveryFailed(false);
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
          setDiscoveryFailed(true);
          setError(reason instanceof Error ? reason.message : 'Sensor discovery failed.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [family, open, retry]);

  const reset = () => {
    setQuery('');
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
      const saved = new Map(result.sensors.map((sensor) => [sensor.external_id, sensor]));
      setSensors((current) =>
        current.map((sensor) =>
          saved.has(sensor.external_id)
            ? { ...sensor, ...saved.get(sensor.external_id), registered: true }
            : sensor,
        ),
      );
      const failedIds = new Set(
        result.backfills
          .filter((backfill) => backfill.status === 'failed')
          .map((backfill) => backfill.sensor_id),
      );
      if (result.dagster.status !== 'failed') {
        setSelected(
          new Set(
            result.sensors
              .filter((sensor) => failedIds.has(sensor.id))
              .map((sensor) => sensor.external_id),
          ),
        );
      }
      const confirmation =
        result.sensors.length === 1 ? 'Sensor saved.' : 'Sensors saved.';
      const loadingReadings = result.backfills.some(
        (backfill) => backfill.status === 'submitted',
      );
      setWarning(
        result.dagster.status === 'failed'
          ? `${confirmation} We couldn’t start loading past readings. Please try registering the selected sensors again.`
          : failedIds.size
            ? `${confirmation} We had trouble loading past readings for ${failedIds.size === 1 ? 'the sensor still selected. Please try registering it again.' : 'the sensors still selected. Please try registering them again.'}`
            : loadingReadings
              ? `${confirmation} Past readings will appear as they’re loaded. You can close this window.`
              : confirmation,
      );
      try {
        await onRegistered();
      } catch {
        setWarning(
          (message) =>
            `${message} Refresh the page after closing this window to see your sensors.`,
        );
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sensor registration failed.');
    } finally {
      setSaving(false);
    }
  };

  const visible = sensors.filter((sensor) =>
    [sensor.name, sensor.external_id].some((value) =>
      value.toLowerCase().includes(query.toLowerCase()),
    ),
  );
  const allVisibleSelected =
    visible.length > 0 && visible.every((sensor) => selected.has(sensor.external_id));
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
                disabled={saving}
                aria-pressed={family === value}
                onClick={() => {
                  setFamily(value);
                  setQuery('');
                }}
              >
                {value === 'ham' ? 'HAM' : 'OpenMeteo'}
              </Button>
            ))}
          </div>

          <SearchInput
            value={query}
            onChange={setQuery}
            placeholder="Find a sensor by name or ID…"
            className="sm:max-w-none"
          />
          <div className="rounded-xl border">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <div>
                <div className="text-sm font-semibold">Available sensors</div>
                <div className="text-xs text-muted-foreground">
                  {selected.size} selected
                </div>
              </div>
              {!!visible.length && !loading && (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={saving}
                  onClick={() =>
                    setSelected((current) => {
                      const next = new Set(current);
                      visible.forEach((sensor) => {
                        if (allVisibleSelected) next.delete(sensor.external_id);
                        else if (next.size < 500) next.add(sensor.external_id);
                      });
                      return next;
                    })
                  }
                >
                  {allVisibleSelected ? 'Clear visible' : 'Select visible'}
                </Button>
              )}
            </div>
            <div className="max-h-64 overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center gap-2 p-10 text-sm text-muted-foreground">
                  <Loader2 className="animate-spin" /> Discovering sensors…
                </div>
              ) : discoveryFailed ? (
                <div className="p-4">
                  <ErrorNotice
                    message="Discovery failed. Check the connection and try again."
                    onRetry={() => setRetry((value) => value + 1)}
                  />
                </div>
              ) : visible.length ? (
                visible.map((sensor) => (
                  <label
                    key={sensor.external_id}
                    className="flex cursor-pointer items-start gap-3 border-b px-4 py-3 last:border-0 hover:bg-muted/40"
                  >
                    <input
                      disabled={
                        saving ||
                        (!selected.has(sensor.external_id) && selected.size >= 500)
                      }
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
                  {query
                    ? 'No sensors match your search.'
                    : 'No eligible sensors were returned by this provider.'}
                </div>
              )}
            </div>
          </div>

          <div className="border-t pt-5">
            <h3 className="text-sm font-semibold">Registration settings</h3>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Applied to every selected sensor (up to 500). Blank optional fields keep
              existing settings.
            </p>
          </div>
          <fieldset disabled={saving} className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-2 text-sm font-medium sm:col-span-2">
              Building model
              <select
                aria-label="Building model"
                value={bimId}
                onChange={(event) => setBimId(event.target.value)}
                className="field"
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
                className="field"
              />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Space{' '}
              <span className="text-xs font-normal text-muted-foreground">Optional</span>
              <input
                value={space}
                onChange={(event) => setSpace(event.target.value)}
                placeholder="e.g. Room 101"
                className="field"
              />
            </label>
            <label className="grid gap-2 text-sm font-medium sm:col-span-2">
              Ingestion start{' '}
              <span className="text-xs font-normal text-muted-foreground">Optional</span>
              <input
                type="datetime-local"
                value={startingDate}
                onChange={(event) => setStartingDate(event.target.value)}
                className="field"
              />
            </label>
          </fieldset>

          {error && (
            <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
          {warning && (
            <div
              role="status"
              className="rounded-lg border bg-accent p-3 text-sm text-accent-foreground"
            >
              {warning}
            </div>
          )}
        </div>

        <DialogFooter className="border-t px-6 py-4">
          <Button
            variant="outline"
            disabled={saving}
            onClick={() => {
              setOpen(false);
              reset();
            }}
          >
            {warning ? 'Close' : 'Cancel'}
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
