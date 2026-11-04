import { API_BASE } from './client';
import type { RegisteredSensorDto } from '@/types/api/sensors';
import type { DatasetUploadResult } from '@/types/api/datasets';
import type {
  BimFileDto,
  BimCategory,
  BimMetadataDto,
  BimSpaceDto,
  BimStoreyDto,
} from '@/types/api/bim';
import type { SimulationFileDto } from '@/types/api/simulations';

export async function uploadBimFile(
  file: File,
  category: BimCategory,
  image?: File | null,
): Promise<DatasetUploadResult> {
  const form = new FormData();
  form.append('file', file);
  form.append('category', category);
  if (image) form.append('image', image);

  const res = await fetch(`${API_BASE}/ingestion/bim/upload`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) throw new Error('Upload BIM file failed');
  return res.json() as Promise<DatasetUploadResult>;
}

export function getBimImageUrl(bimId: string): string {
  return `${API_BASE}/bim/${bimId}/image`;
}

export async function uploadBimImage(bimId: string, image: File): Promise<BimFileDto> {
  const form = new FormData();
  form.append('image', image);
  const res = await fetch(getBimImageUrl(bimId), { method: 'PUT', body: form });
  if (!res.ok) throw new Error('Upload building image failed');
  return res.json() as Promise<BimFileDto>;
}

export async function updateBimCategory(
  bimId: string,
  category: BimCategory,
): Promise<BimFileDto> {
  const res = await fetch(`${API_BASE}/bim/${bimId}/category`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category }),
  });
  if (!res.ok) throw new Error('Update BIM category failed');
  return res.json() as Promise<BimFileDto>;
}

export async function listBimFiles(): Promise<BimFileDto[]> {
  const res = await fetch(`${API_BASE}/bim`);
  if (!res.ok) throw new Error('List BIM files failed');
  return res.json() as Promise<BimFileDto[]>;
}

export async function getBimFileByDataset(datasetId: string): Promise<BimFileDto> {
  const res = await fetch(`${API_BASE}/bim/by-dataset/${datasetId}`);
  if (!res.ok) throw new Error('Get BIM file failed');
  return res.json() as Promise<BimFileDto>;
}

export async function getBimFile(bimId: string): Promise<BimFileDto> {
  const res = await fetch(`${API_BASE}/bim/${bimId}`);
  if (!res.ok) throw new Error('Get BIM file failed');
  return res.json() as Promise<BimFileDto>;
}

export async function fetchBimStream(bimId: string): Promise<ArrayBuffer> {
  const res = await fetch(`${API_BASE}/bim/${bimId}/stream`);

  if (!res.ok) {
    throw new Error('Failed to fetch BIM file');
  }

  return await res.arrayBuffer();
}

export async function fetchBimMetadata(bimId: string): Promise<BimMetadataDto> {
  const res = await fetch(`${API_BASE}/bim/${bimId}/metadata`);
  if (!res.ok) throw new Error('Failed to fetch BIM metadata');
  return res.json() as Promise<BimMetadataDto>;
}

export async function listBimStoreys(bimId: string): Promise<BimStoreyDto[]> {
  const res = await fetch(`${API_BASE}/bim/${bimId}/storeys`);
  if (!res.ok) throw new Error('Failed to fetch BIM storeys');
  return res.json() as Promise<BimStoreyDto[]>;
}

export async function listBimSpaces(bimId: string): Promise<BimSpaceDto[]> {
  const res = await fetch(`${API_BASE}/bim/${bimId}/spaces`);
  if (!res.ok) throw new Error('Failed to fetch BIM spaces');
  return res.json() as Promise<BimSpaceDto[]>;
}

export async function listBimSimulations(bimId: string): Promise<SimulationFileDto[]> {
  const res = await fetch(`${API_BASE}/bim/${bimId}/simulations`);
  if (!res.ok) throw new Error('Failed to fetch BIM simulations');
  return res.json() as Promise<SimulationFileDto[]>;
}

export async function connectBimSensors(
  bimId: string,
  sensorIds: string[],
): Promise<RegisteredSensorDto[]> {
  const res = await fetch(`${API_BASE}/bim/${bimId}/sensors`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ add: sensorIds }),
  });
  if (!res.ok) throw new Error('Connect BIM sensors failed');
  return res.json() as Promise<RegisteredSensorDto[]>;
}
