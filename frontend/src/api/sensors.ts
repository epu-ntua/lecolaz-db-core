import { API_BASE } from './client';
import type {
  EligibleSensorDto,
  RegisteredSensorDto,
  SensorFamily,
  SensorRegistrationResponse,
  SensorRegistrationSettings,
  SensorObservationTypeDto,
  SensorTimestampBoundsDto,
  SensorTimeseriesPointDto,
} from '@/types/api/sensors';

export async function listSensorObservationTypes(
  sensorId: string,
): Promise<SensorObservationTypeDto[]> {
  const response = await sensorFetch(`${API_BASE}/sensors/${sensorId}/observation-types`);
  if (!response.ok)
    throw new Error(await readError(response, 'Sensor measurements could not be loaded'));
  return response.json() as Promise<SensorObservationTypeDto[]>;
}

export async function getSensorTimestampBounds(
  sensorId: string,
  observationTypeId: string,
): Promise<SensorTimestampBoundsDto> {
  const query = new URLSearchParams({ observation_type_id: observationTypeId });
  const response = await sensorFetch(
    `${API_BASE}/sensors/${sensorId}/timeseries/bounds?${query}`,
  );
  if (!response.ok)
    throw new Error(
      await readError(response, 'Measurement date range could not be loaded'),
    );
  return response.json() as Promise<SensorTimestampBoundsDto>;
}

export async function listSensorTimeseries(
  sensorId: string,
  observationTypeId: string,
  start: string,
  end: string,
): Promise<SensorTimeseriesPointDto[]> {
  const query = new URLSearchParams({
    observation_type_id: observationTypeId,
    start,
    end,
  });
  const response = await sensorFetch(
    `${API_BASE}/sensors/${sensorId}/timeseries?${query}`,
  );
  if (!response.ok)
    throw new Error(
      await readError(response, 'Sensor time-series values could not be loaded'),
    );
  return response.json() as Promise<SensorTimeseriesPointDto[]>;
}

async function readError(response: Response, fallback: string) {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === 'string' ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

async function sensorFetch(input: string, init: RequestInit = {}, timeoutMs = 45_000) {
  try {
    return await fetch(input, {
      ...init,
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new Error('The sensor service did not respond in time. Please try again.');
    }
    throw error;
  }
}

export async function listEligibleSensors(
  family: SensorFamily,
): Promise<EligibleSensorDto[]> {
  const response = await sensorFetch(`${API_BASE}/sensors/list/${family}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  });
  if (!response.ok) throw new Error(await readError(response, 'Sensor discovery failed'));
  return response.json() as Promise<EligibleSensorDto[]>;
}

export async function listRegisteredSensors(filters?: {
  family?: SensorFamily;
  bimDatasetId?: string;
  modularComponentId?: string;
  unassigned?: boolean;
}): Promise<RegisteredSensorDto[]> {
  const query = new URLSearchParams();
  if (filters?.family) query.set('sensor_family', filters.family);
  if (filters?.bimDatasetId) query.set('bim_dataset_id', filters.bimDatasetId);
  if (filters?.modularComponentId)
    query.set('modular_component_id', filters.modularComponentId);
  if (filters?.unassigned) query.set('unassigned', 'true');
  const suffix = query.size ? `?${query.toString()}` : '';
  const response = await sensorFetch(
    `${API_BASE}/sensors/registered${suffix}`,
    {},
    15_000,
  );
  if (!response.ok)
    throw new Error(await readError(response, 'Registered sensors could not be loaded'));
  return response.json() as Promise<RegisteredSensorDto[]>;
}

export async function registerSensors(
  family: SensorFamily,
  externalIds: string[],
  settings: SensorRegistrationSettings,
): Promise<SensorRegistrationResponse> {
  const response = await sensorFetch(
    `${API_BASE}/sensors/register`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sensor_family: family,
        sensors: externalIds.map((external_id) => ({ external_id, settings })),
      }),
    },
    75_000,
  );
  if (!response.ok)
    throw new Error(await readError(response, 'Sensor registration failed'));
  return response.json() as Promise<SensorRegistrationResponse>;
}
