import { API_BASE } from './client';
import type { FileUploadResult } from '@/types/api/files';
import type { BimFileDto, BimMetadataDto } from '@/types/api/bim';

export async function uploadBimFile(file: File): Promise<FileUploadResult> {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${API_BASE}/ingestion/bim/upload`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) throw new Error('Upload BIM file failed');
  return res.json() as Promise<FileUploadResult>;
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

export async function fetchBimStream(bimId: string): Promise<ArrayBuffer> {
  const res = await fetch(`${API_BASE}/bim/${bimId}/stream`);

  if (!res.ok) {
    throw new Error("Failed to fetch BIM file");
  }

  return await res.arrayBuffer();
}

export async function fetchBimMetadata(bimId: string): Promise<BimMetadataDto> {
  const res = await fetch(`${API_BASE}/bim/${bimId}/metadata`);
  if (!res.ok) throw new Error('Failed to fetch BIM metadata');
  return res.json() as Promise<BimMetadataDto>;
}
