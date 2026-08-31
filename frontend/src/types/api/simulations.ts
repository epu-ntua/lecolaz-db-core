export type SimulationProcessingMetadata = {
  variable_count: number | null;
  timestep_count: number | null;
  skipped_values: number | null;
  processed_at: string | null;
};

export type SimulationProcessingSummary = {
  metadata: SimulationProcessingMetadata;
};

export type SimulationFileDto = {
  id: string;
  dataset_id: string;
  bim_dataset_id: string | null;
  filename: string;
  format: string;
  status: string | null;
  created_at: string | null;
  metadata: Record<string, unknown> | null;
};

export type SimulationVariableDto = {
  id: string;
  simulation_dataset_id: string;
  bim_space_id: string | null;
  variable_id: string;
  variable_name: string;
  unit: string | null;
  frequency: string | null;
  key: string | null;
  created_at: string | null;
};

export type SimulationTimeseriesPointDto = {
  id: string;
  simulation_dataset_id: string;
  variable_id: string;
  timestamp: string | null;
  value: number;
  created_at: string | null;
};
