import { API_BASE } from './client';

export const ONTOLOGY_QUERY_URL = `${API_BASE}/ontology/query`;

export async function getInitialOntologyInstances(
  signal?: AbortSignal,
): Promise<string[]> {
  const response = await fetch(`${API_BASE}/ontology/instances`, {
    signal,
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('The knowledge graph could not be loaded.');
  return response.json() as Promise<string[]>;
}
