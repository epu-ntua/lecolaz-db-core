import { API_BASE } from './client';
import type { BimFileDto, BimMetadataDto } from '@/types/api/bim';

export async function listBimFiles(): Promise<BimFileDto[]> {
  const res = await fetch(`${API_BASE}/bim`);
  if (!res.ok) throw new Error('List BIM files failed');
  return res.json() as Promise<BimFileDto[]>;
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
