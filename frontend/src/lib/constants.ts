// global constants
import type { ComponentClass } from '@/types/api/components';
import type { SensorFamily } from '@/types/api/sensors';

export const COMPONENT_CLASS_LABELS: Record<ComponentClass, string> = {
  InteriorWall: 'Interior wall',
  FacadeElement: 'Facade element',
  FloorCovering: 'Floor covering',
};

export const SENSOR_FAMILY_LABELS: Record<SensorFamily, string> = {
  ham: 'HAM',
  openmeteo: 'OpenMeteo',
};
