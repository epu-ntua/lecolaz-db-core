import { useCallback, useEffect, useMemo, useState } from 'react';
import { Building2, RadioTower, Unplug } from 'lucide-react';
import { listBimFiles } from '@/api/bim_files';
import { listRegisteredSensors } from '@/api/sensors';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { BimFileDto } from '@/types/api/bim';
import type { RegisteredSensorDto } from '@/types/api/sensors';
import { SensorRegistrationDialog } from './components/SensorRegistrationDialog';

export default function MonitoringPage() {
  const [sensors, setSensors] = useState<RegisteredSensorDto[]>([]);
  const [bims, setBims] = useState<BimFileDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [nextSensors, nextBims] = await Promise.all([
        listRegisteredSensors(),
        listBimFiles(),
      ]);
      setSensors(nextSensors);
      setBims(nextBims);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sensors could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const bimNames = useMemo(
    () => new Map(bims.map((bim) => [bim.id, bim.filename] as const)),
    [bims],
  );
  const linked = sensors.filter((sensor) => sensor.bim_dataset_id).length;

  return (
    <PageContainer size="wide" className="space-y-8">
      <PageHeader
        eyebrow="Operations"
        title="Monitoring & Performance"
        description="Register environmental data sources, connect them to buildings and prepare their observations for ingestion."
        actions={<SensorRegistrationDialog onRegistered={load} />}
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Registered sensors
            </CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-3 text-3xl font-semibold">
            <RadioTower className="text-primary" />
            {sensors.length}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Connected to BIM
            </CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-3 text-3xl font-semibold">
            <Building2 className="text-primary" />
            {linked}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Standalone</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-3 text-3xl font-semibold">
            <Unplug className="text-muted-foreground" />
            {sensors.length - linked}
          </CardContent>
        </Card>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Sensor registry</CardTitle>
          <p className="text-sm text-muted-foreground">
            Sensors saved for ingestion and their current building assignments.
          </p>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-sm text-muted-foreground">
              Loading registered sensors…
            </div>
          ) : sensors.length ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Sensor</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead>Building</TableHead>
                    <TableHead>Location / space</TableHead>
                    <TableHead>Ingestion start</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sensors.map((sensor) => (
                    <TableRow key={sensor.id}>
                      <TableCell>
                        <div className="font-medium">{sensor.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {sensor.external_id}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">
                          {sensor.sensor_family === 'ham' ? 'HAM' : 'OpenMeteo'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {sensor.bim_dataset_id ? (
                          (bimNames.get(sensor.bim_dataset_id) ?? 'Unknown BIM')
                        ) : (
                          <span className="text-muted-foreground">Not connected</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div>{sensor.location ?? '—'}</div>
                        <div className="text-xs text-muted-foreground">
                          {sensor.space ?? 'No space specified'}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(sensor.starting_date).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="p-10 text-center">
              <RadioTower className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
              <div className="font-medium">No sensors registered yet</div>
              <p className="mt-1 text-sm text-muted-foreground">
                Discover provider sensors and connect them to your building models.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  );
}
