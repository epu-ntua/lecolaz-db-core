import { useEffect, useState } from 'react';
import { Plus, RadioTower } from 'lucide-react';
import { updateComponentSensors } from '@/api/components';
import { listRegisteredSensors } from '@/api/sensors';
import { SensorChartDialog } from '@/components/sensors/SensorChartDialog';
import { Badge } from '@/components/ui/badge';
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
import { SearchInput } from '@/components/ui/search-input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { ModularComponentDto } from '@/types/api/components';
import type { RegisteredSensorDto } from '@/types/api/sensors';

const SAVE_ERROR =
  'Sensors could not be updated. Some may have just been linked elsewhere; reopen the list and try again.';

export function ComponentSensorsTab({ component }: { component: ModularComponentDto }) {
  const [sensors, setSensors] = useState<RegisteredSensorDto[]>([]);
  const [selectedSensor, setSelectedSensor] = useState<RegisteredSensorDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [picking, setPicking] = useState(false);
  const [freeSensors, setFreeSensors] = useState<RegisteredSensorDto[]>([]);
  const [freeLoading, setFreeLoading] = useState(false);
  const [freeError, setFreeError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState('');
  const [toRemove, setToRemove] = useState<RegisteredSensorDto | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const visibleFree = freeSensors.filter((sensor) =>
    `${sensor.name} ${sensor.external_id}`.toLowerCase().includes(query.toLowerCase()),
  );

  useEffect(() => {
    let cancelled = false;
    listRegisteredSensors({ modularComponentId: component.id })
      .then((rows) => {
        if (!cancelled) setSensors(rows);
      })
      .catch(() => {
        if (!cancelled) setLoadError('Sensors could not be loaded.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [component.id]);

  // Reload free sensors each time the picker opens: another user may have taken some.
  useEffect(() => {
    if (!picking) return;
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
  }, [picking]);

  const save = async (changes: { add?: string[]; remove?: string[] }) => {
    try {
      setSaving(true);
      setSaveError(null);
      setSensors(await updateComponentSensors(component.id, changes));
      return true;
    } catch {
      setSaveError(SAVE_ERROR);
      return false;
    } finally {
      setSaving(false);
    }
  };

  const closePicker = () => {
    setPicking(false);
    setSelected(new Set());
    setQuery('');
    setSaveError(null);
  };

  return (
    <>
      <Card className="shadow-none">
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <CardTitle className="text-sm font-medium">
                Sensors for {component.name}
              </CardTitle>
              <DialogDescription className="mt-1 text-left">
                Registered monitoring sources placed on this component.
              </DialogDescription>
            </div>
            <Button type="button" size="lg" onClick={() => setPicking(true)}>
              <Plus />
              Connect Sensors
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loadError ? (
            <div className="text-sm text-destructive">{loadError}</div>
          ) : loading ? (
            <div className="text-sm text-muted-foreground">Loading sensors…</div>
          ) : sensors.length ? (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Sensor</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Space</TableHead>
                    <TableHead className="w-0" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sensors.map((sensor) => (
                    <TableRow key={sensor.id}>
                      <TableCell>
                        <Button
                          variant="link"
                          className="h-auto whitespace-normal p-0 text-left"
                          onClick={() => setSelectedSensor(sensor)}
                        >
                          {sensor.name}
                        </Button>
                        <div className="text-xs text-muted-foreground">
                          {sensor.external_id}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">
                          {sensor.sensor_family === 'ham' ? 'HAM' : 'OpenMeteo'}
                        </Badge>
                      </TableCell>
                      <TableCell>{sensor.location ?? '—'}</TableCell>
                      <TableCell>{sensor.space ?? '—'}</TableCell>
                      <TableCell>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={saving}
                          onClick={() => setToRemove(sensor)}
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
              <RadioTower className="h-5 w-5" />
              No sensors are connected to this component yet.
            </div>
          )}
        </CardContent>
      </Card>

      {selectedSensor && (
        <SensorChartDialog
          sensorId={selectedSensor.id}
          sensorName={selectedSensor.name}
          onClose={() => setSelectedSensor(null)}
        />
      )}

      <Dialog
        open={picking}
        onOpenChange={(open) => {
          if (saving) return;
          if (open) setPicking(true);
          else closePicker();
        }}
      >
        <DialogContent className="flex max-h-[80vh] w-[calc(100%-2rem)] max-w-md flex-col gap-0 overflow-hidden p-0">
          <DialogHeader className="border-b border-border px-6 py-4 text-left">
            <DialogTitle className="text-lg">Connect sensors</DialogTitle>
            <DialogDescription>
              Select sensors to place on {component.name}.
            </DialogDescription>
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
                  : 'No available sensors. Register sensors or unlink them from a building first.'}
              </p>
            )}
            {saveError && <p className="text-destructive">{saveError}</p>}
          </div>
          <DialogFooter className="border-t border-border px-6 py-4">
            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={closePicker}
            >
              Cancel
            </Button>
            <Button
              type="button"
              disabled={saving || !selected.size}
              onClick={async () => {
                if (await save({ add: [...selected] })) closePicker();
              }}
            >
              {saving ? 'Connecting…' : `Connect (${selected.size})`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
            <DialogTitle>Remove sensor?</DialogTitle>
            <DialogDescription>
              {toRemove?.name} will no longer be placed on {component.name}. It stays
              registered and can be connected again.
            </DialogDescription>
          </DialogHeader>
          {saveError && <p className="text-sm text-destructive">{saveError}</p>}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={() => {
                setToRemove(null);
                setSaveError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={saving}
              onClick={async () => {
                if (toRemove && (await save({ remove: [toRemove.id] })))
                  setToRemove(null);
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
