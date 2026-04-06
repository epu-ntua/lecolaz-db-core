import { API_BASE } from './client';
import type { DatasetDto, DatasetUploadResult } from '@/types/api/datasets';

export async function uploadDataset(file: File): Promise<DatasetUploadResult> {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${API_BASE}/ingestion/upload`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) throw new Error('Upload failed');
  return res.json() as Promise<DatasetUploadResult>;
}

export async function listDatasets(): Promise<DatasetDto[]> {
  const res = await fetch(`${API_BASE}/datasets`);
  if (!res.ok) throw new Error('List datasets failed');
  return res.json() as Promise<DatasetDto[]>;
}

export async function getDataset(datasetId: string): Promise<DatasetDto> {
  const res = await fetch(`${API_BASE}/datasets/${datasetId}`);
  if (!res.ok) throw new Error('Get dataset failed');
  return res.json() as Promise<DatasetDto>;
}

export function getDatasetDownloadUrl(datasetId: string): string {
  return `${API_BASE}/datasets/${datasetId}/download`;
}
