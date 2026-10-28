import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, RadioTower, Unplug, ArrowUpRight, RefreshCw } from 'lucide-react';
import { listBimFiles } from '@/api/bim_files';
import { listRegisteredSensors } from '@/api/sensors';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';
import { MetricCard } from '@/components/layout/MetricCard';
import { ErrorNotice, LoadingState } from '@/components/layout/Feedback';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { SearchInput } from '@/components/ui/search-input';
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
import { SensorChartDialog } from '@/components/sensors/SensorChartDialog';

export default function MonitoringPage() {
  const [sensors, setSensors] = useState<RegisteredSensorDto[]>([]);
  const [bims, setBims] = useState<BimFileDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bimError, setBimError] = useState(false);
  const [query, setQuery] = useState('');
  const [family, setFamily] = useState('all');
  const [connection, setConnection] = useState('all');
  const [selectedSensor, setSelectedSensor] = useState<RegisteredSensorDto | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setBimError(false);
    const [nextSensors, nextBims] = await Promise.allSettled([
      listRegisteredSensors(),
      listBimFiles(),
    ]);
    if (nextSensors.status === 'fulfilled') setSensors(nextSensors.value);
    else
      setError(
        nextSensors.reason instanceof Error
          ? nextSensors.reason.message
          : 'Sensors could not be loaded.',
      );
    if (nextBims.status === 'fulfilled') setBims(nextBims.value);
    else setBimError(true);
    setLoading(false);
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  const bimNames = useMemo(
    () => new Map(bims.map((bim) => [bim.id, bim.filename])),
    [bims],
  );
  const linked = sensors.filter((sensor) => sensor.bim_dataset_id).length;
  const visible = sensors.filter(
    (sensor) =>
      (family === 'all' || sensor.sensor_family === family) &&
      (connection === 'all' ||
        (connection === 'linked' ? !!sensor.bim_dataset_id : !sensor.bim_dataset_id)) &&
      [
        sensor.name,
        sensor.external_id,
        sensor.location,
        sensor.space,
        bimNames.get(sensor.bim_dataset_id ?? ''),
      ].some((value) => value?.toLowerCase().includes(query.toLowerCase())),
  );
  return (
    <PageContainer size="wide" className="space-y-7">
      <PageHeader
        eyebrow="Operations"
        title="Monitoring & Performance"
        description="Connect environmental data sources to your buildings and manage their ingestion settings."
        actions={<SensorRegistrationDialog onRegistered={load} />}
      />
      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        <MetricCard
          label="Registered sensors"
          value={loading || error ? '—' : sensors.length}
          detail="Saved for observation ingestion"
          icon={RadioTower}
        />
        <MetricCard
          label="Connected to BIM"
          value={loading || error ? '—' : linked}
          detail="Sensors assigned to building models"
          icon={Building2}
        />
        <MetricCard
          label="Standalone sources"
          value={loading || error ? '—' : sensors.length - linked}
          detail="Sensors without a building assignment"
          icon={Unplug}
        />
      </div>
      {error && <ErrorNotice message={error} onRetry={load} />}
      {bimError && (
        <ErrorNotice
          message="Building names could not be loaded. Sensor assignments are still preserved."
          onRetry={load}
        />
      )}
      <section className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div className="flex items-center justify-between gap-3 border-b px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold">Sensor registry</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Select a sensor to explore its measurements and time-series values
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            aria-label="Refresh sensor registry"
            disabled={loading}
            onClick={load}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex flex-col gap-3 border-b p-4 lg:flex-row">
          <SearchInput
            value={query}
            onChange={setQuery}
            placeholder="Search sensors, buildings or spaces…"
            className="lg:mr-auto"
          />
          <select
            aria-label="Filter sensors by provider"
            className="field lg:w-40"
            value={family}
            onChange={(event) => setFamily(event.target.value)}
          >
            <option value="all">All providers</option>
            <option value="ham">HAM</option>
            <option value="openmeteo">OpenMeteo</option>
          </select>
          <select
            aria-label="Filter building connection"
            className="field lg:w-44"
            value={connection}
            onChange={(event) => setConnection(event.target.value)}
          >
            <option value="all">All connections</option>
            <option value="linked">Connected to BIM</option>
            <option value="standalone">Standalone</option>
          </select>
        </div>
        {loading ? (
          <LoadingState label="Loading registered sensors…" />
        ) : error ? (
          <p className="p-10 text-center text-sm text-muted-foreground">
            The registry is unavailable. Retry above to reload it.
          </p>
        ) : visible.length ? (
          <>
            <div className="overflow-x-auto">
              <Table className="min-w-[850px]">
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
                  {visible.map((sensor) => (
                    <TableRow key={sensor.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent text-primary">
                            <RadioTower className="h-4 w-4" />
                          </span>
                          <div>
                            <Button
                              variant="link"
                              className="h-auto whitespace-normal p-0 text-left"
                              onClick={() => setSelectedSensor(sensor)}
                            >
                              {sensor.name}
                            </Button>
                            <div className="mt-1 text-xs text-muted-foreground">
                              {sensor.external_id}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">
                          {sensor.sensor_family === 'ham' ? 'HAM' : 'OpenMeteo'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {sensor.bim_dataset_id ? (
                          <Link
                            to={`/buildings/${sensor.bim_dataset_id}`}
                            className="inline-flex max-w-52 items-center gap-1 text-primary hover:underline"
                          >
                            <span className="truncate">
                              {bimNames.get(sensor.bim_dataset_id) ?? 'View linked BIM'}
                            </span>
                            <ArrowUpRight className="h-3 w-3 shrink-0" />
                          </Link>
                        ) : (
                          <span className="text-muted-foreground">Not connected</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div>{sensor.location ?? '—'}</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {sensor.space ?? 'No space specified'}
                        </div>
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                        {new Date(sensor.starting_date).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div className="border-t px-5 py-3 text-xs text-muted-foreground">
              {visible.length} of {sensors.length} registered sensors
            </div>
          </>
        ) : (
          <div className="flex min-h-56 flex-col items-center justify-center p-7 text-center">
            <RadioTower className="mb-4 h-7 w-7 text-muted-foreground/60" />
            <h3 className="text-sm font-medium">
              {sensors.length
                ? 'No sensors match your filters'
                : 'Connect your first data source'}
            </h3>
            <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
              {sensors.length
                ? 'Try another name, provider or building connection.'
                : 'Discover HAM or OpenMeteo sensors using Register sensors, then assign them to a building.'}
            </p>
            {sensors.length > 0 && (
              <Button
                variant="ghost"
                className="mt-3"
                onClick={() => {
                  setQuery('');
                  setFamily('all');
                  setConnection('all');
                }}
              >
                Clear filters
              </Button>
            )}
          </div>
        )}
      </section>
      {selectedSensor && (
        <SensorChartDialog
          sensorId={selectedSensor.id}
          sensorName={selectedSensor.name}
          onClose={() => setSelectedSensor(null)}
        />
      )}
    </PageContainer>
  );
}
