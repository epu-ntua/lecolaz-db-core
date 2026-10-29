export type SensorFamily = 'ham' | 'openmeteo';

export type SensorObservationTypeDto = {
  id: string;
  unit: string;
  label: string;
};

export type SensorTimestampBoundsDto = {
  start: string | null;
  end: string | null;
};

export type SensorTimeseriesPointDto = {
  id: string;
  timestamp: string;
  value: number;
};

export type RegisteredSensorDto = {
  id: string;
  sensor_family: SensorFamily;
  external_id: string;
  name: string;
  location: string | null;
  space: string | null;
  starting_date: string;
  bim_dataset_id: string | null;
  modular_component_id: string | null;
};

export type EligibleSensorDto = Omit<RegisteredSensorDto, 'id' | 'starting_date'> & {
  id: string | null;
  registered: boolean;
  starting_date: string | null;
};

export type SensorRegistrationSettings = {
  bim_dataset_id?: string | null;
  starting_date?: string;
  location?: string | null;
  space?: string | null;
};

export type SensorRegistrationResponse = {
  sensors: RegisteredSensorDto[];
  dagster: {
    status: 'reloaded' | 'failed';
    message?: string | null;
  };
  backfills: {
    sensor_id: string;
    status: 'submitted' | 'skipped' | 'failed';
    backfill_id: string | null;
    target_count: number;
    message: string | null;
  }[];
};
