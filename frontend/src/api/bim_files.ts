import { API_BASE } from './client';

export async function listBimFiles() {
  const res = await fetch(`${API_BASE}/bim`);
  if (!res.ok) throw new Error('List BIM files failed');
  return res.json();
}

export async function fetchBimStream(bimId: string): Promise<ArrayBuffer> {
  const res = await fetch(`${API_BASE}/bim/${bimId}/stream`);

  if (!res.ok) {
    throw new Error("Failed to fetch BIM file");
  }

  return await res.arrayBuffer();
}
