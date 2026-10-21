import { API_BASE } from './client';
import type {
  EligibleSensorDto,
  RegisteredSensorDto,
  SensorFamily,
  SensorRegistrationResponse,
  SensorRegistrationSettings,
} from '@/types/api/sensors';

async function readError(response: Response, fallback: string) {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? fallback;
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
}): Promise<RegisteredSensorDto[]> {
  const query = new URLSearchParams();
  if (filters?.family) query.set('sensor_family', filters.family);
  if (filters?.bimDatasetId) query.set('bim_dataset_id', filters.bimDatasetId);
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
