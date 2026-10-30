import { useEffect, useState } from 'react';
import { Plus, RadioTower } from 'lucide-react';
import { updateComponentSensors } from '@/api/components';
import { listRegisteredSensors } from '@/api/sensors';
import { SensorSelectionDialog } from '@/components/sensors/SensorSelectionDialog';
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
  const [toRemove, setToRemove] = useState<RegisteredSensorDto | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

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

      {picking && (
        <SensorSelectionDialog
          description={`Select sensors to place on ${component.name}.`}
          onConnect={async (sensorIds) => {
            setSensors(await updateComponentSensors(component.id, { add: sensorIds }));
          }}
          onClose={() => setPicking(false)}
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
