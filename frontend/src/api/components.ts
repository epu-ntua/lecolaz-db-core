import { API_BASE } from './client';
import type { ComponentFileKind, ModularComponentDto } from '@/types/api/components';

export async function listComponents(): Promise<ModularComponentDto[]> {
  const res = await fetch(`${API_BASE}/components`);
  if (!res.ok) throw new Error('List components failed');
  return res.json() as Promise<ModularComponentDto[]>;
}

export function getComponentFileUrl(
  componentId: string,
  kind: ComponentFileKind,
): string {
  return `${API_BASE}/components/${componentId}/files/${kind}`;
}
