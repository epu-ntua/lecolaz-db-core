import { API_BASE } from './client';
import type { DatasetUploadResult } from '@/types/api/datasets';
import type {
  SimulationFileDto,
  SimulationTimeseriesPointDto,
  SimulationVariableDto,
} from '@/types/api/simulations';

export async function uploadSimulationFile(file: File): Promise<DatasetUploadResult> {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${API_BASE}/ingestion/simulations/upload`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) throw new Error('Upload simulation file failed');
  return res.json() as Promise<DatasetUploadResult>;
}

export async function listSimulationFiles(): Promise<SimulationFileDto[]> {
  const res = await fetch(`${API_BASE}/simulations`);
  if (!res.ok) throw new Error('List simulation files failed');
  return res.json() as Promise<SimulationFileDto[]>;
}

export async function getSimulationFileByDataset(
  datasetId: string,
): Promise<SimulationFileDto> {
  const res = await fetch(`${API_BASE}/simulations/by-dataset/${datasetId}`);
  if (!res.ok) throw new Error('Get simulation file failed');
  return res.json() as Promise<SimulationFileDto>;
}

export async function listSimulationVariablesByDataset(
  datasetId: string,
): Promise<SimulationVariableDto[]> {
  const res = await fetch(`${API_BASE}/simulations/by-dataset/${datasetId}/variables`);
  if (!res.ok) throw new Error('List simulation variables failed');
  return res.json() as Promise<SimulationVariableDto[]>;
}

export async function listSimulationTimeseriesByDataset(
  datasetId: string,
  variableId: string,
  limit?: number,
): Promise<SimulationTimeseriesPointDto[]> {
  const params = new URLSearchParams({
    variable_id: variableId,
  });
  if (typeof limit === 'number') {
    params.set('limit', String(limit));
  }
  const res = await fetch(
    `${API_BASE}/simulations/by-dataset/${datasetId}/timeseries?${params}`,
  );
  if (!res.ok) throw new Error('List simulation timeseries failed');
  return res.json() as Promise<SimulationTimeseriesPointDto[]>;
}
