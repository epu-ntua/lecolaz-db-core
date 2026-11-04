import { Badge } from '@/components/ui/badge';
import { SENSOR_FAMILY_LABELS } from '@/lib/constants';
import type { SensorFamily } from '@/types/api/sensors';

export function SensorFamilyBadge({ family }: { family: SensorFamily }) {
  return <Badge variant="secondary">{SENSOR_FAMILY_LABELS[family]}</Badge>;
}
