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
  filename: string;
  format: string;
  status: string | null;
  created_at: string | null;
  metadata: Record<string, unknown> | null;
};
