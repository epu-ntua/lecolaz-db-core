import { useCallback, useEffect, useId, useState } from 'react';
import {
  getSensorTimestampBounds,
  listSensorObservationTypes,
  listSensorTimeseries,
} from '@/api/sensors';
import { TimeseriesChart } from '@/components/charts/TimeseriesChart';
import { ErrorNotice, LoadingState } from '@/components/layout/Feedback';
import { DateTimePicker } from '@/components/ui/date-time-picker';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { SensorObservationTypeDto } from '@/types/api/sensors';

// Each selection mounts a keyed child, so old results never appear under new filters.
function useSensorQuery<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    setLoading(true);
    setError(null);
    load(signal)
      .then((result) => {
        if (!signal.aborted) setData(result);
      })
      .catch((reason: unknown) => {
        if (!signal.aborted)
          setError(
            reason instanceof Error ? reason.message : 'Sensor data could not be loaded.',
          );
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false);
      });
    return () => {
      controller.abort();
    };
  }, [load, attempt]);
  return { data, loading, error, retry: () => setAttempt((value) => value + 1) };
}

/** Reusable by any page: only the sensor ID and close handler are required. */
export function SensorChartDialog({
  sensorId,
  sensorName,
  onClose,
}: {
  sensorId: string;
  sensorName?: string;
  onClose: () => void;
}) {
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex max-h-[90vh] w-[calc(100%-2rem)] max-w-6xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4 text-left">
          <DialogTitle className="pr-4 text-lg">
            {sensorName ?? 'Sensor observations'}
          </DialogTitle>
          <DialogDescription>
            Select a measurement to explore its time-series values.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 overflow-y-auto px-6 py-5">
          <SensorMeasurements key={sensorId} sensorId={sensorId} />
        </div>
      </DialogContent>
    </Dialog>
  );
}

function SensorMeasurements({ sensorId }: { sensorId: string }) {
  const load = useCallback(
    (signal: AbortSignal) => listSensorObservationTypes(sensorId, signal),
    [sensorId],
  );
  const { data: types, loading, error, retry } = useSensorQuery(load);
  const [typeId, setTypeId] = useState('');
  const selectId = useId();
  const selected = types?.find((type) => type.id === typeId);
  return (
    <>
      <div className="space-y-2">
        <label htmlFor={selectId} className="text-sm font-medium">
          Measurement
        </label>
        <select
          id={selectId}
          className="field w-full"
          value={typeId}
          disabled={loading || !!error || !types?.length}
          onChange={(event) => setTypeId(event.target.value)}
        >
          <option value="">Select a measurement…</option>
          {types?.map((type) => (
            <option key={type.id} value={type.id}>
              {type.unit || 'Unitless'} — {type.label}
            </option>
          ))}
        </select>
      </div>
      {loading && <LoadingState label="Loading sensor measurements…" />}
      {error && <ErrorNotice message={error} onRetry={retry} />}
      {!loading && !error && !types?.length && (
        <p className="text-sm text-muted-foreground">
          No recorded measurements found for this sensor.
        </p>
      )}
      {selected ? (
        <SensorMeasurement key={selected.id} sensorId={sensorId} measurement={selected} />
      ) : (
        <>
          <DateRangeFields />
          <p className="text-sm text-muted-foreground">
            Select a measurement to enable the date range.
          </p>
        </>
      )}
    </>
  );
}

function DateRangeFields({
  start = '',
  end = '',
  min,
  max,
  onStart,
  onEnd,
}: {
  start?: string;
  end?: string;
  min?: string;
  max?: string;
  onStart?: (value: string) => void;
  onEnd?: (value: string) => void;
}) {
  const id = useId();
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="space-y-2">
        <label htmlFor={`${id}-start`} className="text-sm font-medium">
          Start date (UTC)
        </label>
        <DateTimePicker
          id={`${id}-start`}
          value={start}
          min={min}
          max={end || max}
          onChange={onStart}
        />
      </div>
      <div className="space-y-2">
        <label htmlFor={`${id}-end`} className="text-sm font-medium">
          End date (UTC)
        </label>
        <DateTimePicker
          id={`${id}-end`}
          value={end}
          min={start || min}
          max={max}
          onChange={onEnd}
        />
      </div>
    </div>
  );
}

function SensorMeasurement({
  sensorId,
  measurement,
}: {
  sensorId: string;
  measurement: SensorObservationTypeDto;
}) {
  const load = useCallback(
    (signal: AbortSignal) => getSensorTimestampBounds(sensorId, measurement.id, signal),
    [sensorId, measurement.id],
  );
  const { data: bounds, loading, error, retry } = useSensorQuery(load);
  return (
    <>
      <SensorRange
        sensorId={sensorId}
        measurement={measurement}
        earliest={bounds?.start}
        latest={bounds?.end}
      />
      {loading && <LoadingState label="Loading measurement date range…" />}
      {error && <ErrorNotice message={error} onRetry={retry} />}
      {!loading && !error && (!bounds?.start || !bounds.end) && (
        <p className="text-sm text-muted-foreground">
          No time-series values found for this measurement.
        </p>
      )}
    </>
  );
}

// Date controls use whole UTC seconds; round outward and retain the exact database
// bounds in requests so subsecond observations at either endpoint are included.
function dateInput(timestamp: string, roundUp = false) {
  const seconds = Date.parse(timestamp) / 1000;
  return new Date((roundUp ? Math.ceil(seconds) : Math.floor(seconds)) * 1000)
    .toISOString()
    .slice(0, 19);
}

function SensorRange({
  sensorId,
  measurement,
  earliest,
  latest,
}: {
  sensorId: string;
  measurement: SensorObservationTypeDto;
  earliest?: string | null;
  latest?: string | null;
}) {
  const min = earliest ? dateInput(earliest) : undefined;
  const max = latest ? dateInput(latest, true) : undefined;
  // Bounds can arrive after editing starts; only default untouched fields.
  const [selectedStart, setStart] = useState<string | null>(null);
  const [selectedEnd, setEnd] = useState<string | null>(null);
  const start = selectedStart ?? min ?? '';
  const end = selectedEnd ?? max ?? '';
  const startTime = Date.parse(`${start}Z`);
  const endTime = Date.parse(`${end}Z`);
  const from = earliest && startTime === Date.parse(`${min}Z`) ? earliest : `${start}Z`;
  const to = latest && endTime === Date.parse(`${max}Z`) ? latest : `${end}Z`;
  const valid =
    Number.isFinite(startTime) &&
    Number.isFinite(endTime) &&
    startTime <= endTime &&
    Date.parse(from) <= Date.parse(to) &&
    (!min || startTime >= Date.parse(`${min}Z`)) &&
    (!max || endTime <= Date.parse(`${max}Z`));
  return (
    <>
      <DateRangeFields
        start={start}
        end={end}
        min={min}
        max={max}
        onStart={setStart}
        onEnd={setEnd}
      />
      {valid ? (
        <SensorRangeChart
          key={`${from}/${to}`}
          sensorId={sensorId}
          measurement={measurement}
          start={from}
          end={to}
        />
      ) : start || end ? (
        <p role="alert" className="text-sm text-destructive">
          Choose both dates within the available range, with start at or before end.
        </p>
      ) : null}
    </>
  );
}

function SensorRangeChart({
  sensorId,
  measurement,
  start,
  end,
}: {
  sensorId: string;
  measurement: SensorObservationTypeDto;
  start: string;
  end: string;
}) {
  const load = useCallback(
    (signal: AbortSignal) =>
      listSensorTimeseries(sensorId, measurement.id, start, end, signal),
    [sensorId, measurement.id, start, end],
  );
  const { data: points, loading, error, retry } = useSensorQuery(load);
  if (loading) return <LoadingState label="Loading time-series values…" />;
  if (error) return <ErrorNotice message={error} onRetry={retry} />;
  return (
    <>
      <TimeseriesChart points={points ?? []} unit={measurement.unit} timeScale />
      {!points?.length && (
        <p className="text-sm text-muted-foreground">
          No time-series values found in this range.
        </p>
      )}
    </>
  );
}
