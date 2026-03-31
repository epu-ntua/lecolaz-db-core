import { API_BASE } from './client';
import type { FileDto, FileUploadResult } from '@/types/api/files';

export async function uploadFile(file: File): Promise<FileUploadResult> {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${API_BASE}/ingestion/upload`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) throw new Error('Upload failed');
  return res.json() as Promise<FileUploadResult>;
}

export async function listFiles(): Promise<FileDto[]> {
  const res = await fetch(`${API_BASE}/files`); // or `/files` if you switch later
  if (!res.ok) throw new Error('List failed');
  return res.json() as Promise<FileDto[]>;
}

export async function getFile(datasetId: string): Promise<FileDto> {
  const res = await fetch(`${API_BASE}/files/${datasetId}`);
  if (!res.ok) throw new Error('Get file failed');
  return res.json() as Promise<FileDto>;
}
