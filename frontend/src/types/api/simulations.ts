export type SimulationProcessingMetadata = {
  variable_count: number | null;
  timestep_count: number | null;
  processed_at: string | null;
};

export type SimulationProcessingVariable = {
  id: string;
  variable: string | null;
  unit: string | null;
  frequency: string | null;
};

export type SimulationProcessingRecord = {
  timestamp: string | null;
  variable: string | null;
  value: unknown;
};

export type SimulationProcessingSummary = {
  metadata: SimulationProcessingMetadata;
  variables: SimulationProcessingVariable[];
  records: SimulationProcessingRecord[];
};

export type SimulationFileDto = {
  id: string;
  file_id: string;
  filename: string;
  format: string;
  schema: string | null;
  status: string;
  created_at: string | null;
  extra: Record<string, unknown> | null;
};
