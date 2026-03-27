import { API_BASE } from './client';
import type { SimulationFileDto } from '@/types/api/simulations';

export async function uploadSimulationFile(file: File) {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${API_BASE}/ingestion/simulations/upload`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) throw new Error('Upload simulation file failed');
  return res.json();
}

export async function listSimulationFiles(): Promise<SimulationFileDto[]> {
  const res = await fetch(`${API_BASE}/simulations`);
  if (!res.ok) throw new Error('List simulation files failed');
  return res.json() as Promise<SimulationFileDto[]>;
}

export async function processSimulationFile(simulationId: string) {
  const res = await fetch(`${API_BASE}/simulations/${simulationId}/process`, {
    method: 'POST',
  });

  if (!res.ok) throw new Error('Process simulation file failed');
  return res.json();
}
