import { API_BASE } from './client';

export async function listBimFiles() {
  const res = await fetch(`${API_BASE}/bim`);
  if (!res.ok) throw new Error('List BIM files failed');
  return res.json();
}
