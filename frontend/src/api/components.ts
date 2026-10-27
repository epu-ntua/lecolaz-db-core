import { API_BASE } from './client';
import type { ComponentFileKind, ModularComponentDto } from '@/types/api/components';

export async function listComponents(): Promise<ModularComponentDto[]> {
  const res = await fetch(`${API_BASE}/components`);
  if (!res.ok) throw new Error('List components failed');
  return res.json() as Promise<ModularComponentDto[]>;
}

export async function updateComponentBuilding(
  componentId: string,
  bimDatasetId: string | null,
): Promise<ModularComponentDto> {
  const res = await fetch(`${API_BASE}/components/${componentId}/building`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bim_dataset_id: bimDatasetId }),
  });
  if (!res.ok) throw new Error('Update component building failed');
  return res.json() as Promise<ModularComponentDto>;
}

export function getComponentFileUrl(
  componentId: string,
  kind: ComponentFileKind,
): string {
  return `${API_BASE}/components/${componentId}/files/${kind}`;
}
